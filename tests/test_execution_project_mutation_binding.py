from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import execution_routes
import execution_worker
import project_mutation_authority as pma
from control_plane_models import ExecutionJobRecord


class _Clock:
    def __init__(self) -> None:
        self.value = datetime(2026, 9, 7, 16, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += timedelta(seconds=seconds)


class ExecutionProjectMutationBindingTests(unittest.TestCase):
    @staticmethod
    def _job() -> ExecutionJobRecord:
        job = ExecutionJobRecord(
            project_id="p1",
            job_id="job-a042-binding",
            status="QUEUED",
            stage="queued",
            execution_mode="one_shot",
            replay_of=None,
            command=[sys.executable, "-c", "print('ok')"],
            cwd=str(PROJECT_ROOT),
            cwd_rel=".",
            submitted_at="2026-09-07T00:00:00+00:00",
        )
        job.extra["project_mutation_binding"] = {
            "project_id": "p1",
            "generation": 7,
            "owner_id": "owner-a",
            "session_id": "session-a",
        }
        return job

    def test_worker_request_persists_non_secret_binding_without_lease_token(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-a042-worker-request-") as td:
            root = Path(td)
            paths = {
                "request": root / "worker_request.json",
                "heartbeat": root / "worker_heartbeat.json",
                "completion": root / "worker_completion.json",
                "cancel": root / "worker_cancel.request.json",
                "ownership_release": root / "worker_ownership.release.json",
                "control_stdout": root / "worker_control.stdout.log",
                "control_stderr": root / "worker_control.stderr.log",
            }
            job = self._job()
            with patch.object(execution_routes, "_worker_paths", return_value=paths):
                request_path = execution_routes._write_worker_request(job)
            row = json.loads(request_path.read_text(encoding="utf-8"))
            self.assertEqual(row["project_mutation_binding"], job.extra["project_mutation_binding"])
            self.assertEqual(row["project_id"], "p1")
            self.assertNotIn("lease_id", request_path.read_text(encoding="utf-8"))

    def test_no_lease_compatibility_guard_exports_worker_binding(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-a042-compat-binding-") as td:
            root = Path(td)
            with ExitStack() as stack:
                stack.enter_context(
                    patch.object(pma, "get_project_root", side_effect=lambda project_id: root / project_id)
                )
                stack.enter_context(
                    patch.object(
                        pma,
                        "init_project_layout",
                        side_effect=lambda project_id: (root / project_id).mkdir(parents=True, exist_ok=True)
                        or (root / project_id),
                    )
                )
                self.assertIsNone(pma.current_mutation_binding("p1"))
                with pma.compatibility_session_guard("p1", session_id="legacy-session"):
                    binding = pma.current_mutation_binding("p1")
                    self.assertIsNotNone(binding)
                    assert binding is not None
                    self.assertEqual(binding["mode"], "compatibility_no_lease")
                    self.assertEqual(binding["project_id"], "p1")
                    self.assertEqual(binding["session_id"], "legacy-session")
                self.assertIsNone(pma.current_mutation_binding("p1"))

    def test_compatibility_worker_enters_only_if_no_governed_lease_appeared(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-a042-compat-worker-") as td:
            root = Path(td)
            with ExitStack() as stack:
                stack.enter_context(
                    patch.object(pma, "get_project_root", side_effect=lambda project_id: root / project_id)
                )
                stack.enter_context(
                    patch.object(
                        pma,
                        "init_project_layout",
                        side_effect=lambda project_id: (root / project_id).mkdir(parents=True, exist_ok=True)
                        or (root / project_id),
                    )
                )
                request = {
                    "project_id": "p1",
                    "project_mutation_binding": {
                        "project_id": "p1",
                        "mode": "compatibility_no_lease",
                        "generation": 0,
                        "owner_id": "",
                        "session_id": "legacy-session",
                    },
                }
                with execution_worker._project_mutation_context(request):
                    self.assertEqual(
                        pma.current_mutation_binding("p1")["mode"], "compatibility_no_lease"
                    )

                pma.acquire_lease(
                    "p1", expected_generation=0, owner_id="owner-new", session_id="new-session"
                )
                with self.assertRaises(pma.ProjectMutationAuthorityError) as blocked:
                    with execution_worker._project_mutation_context(request):
                        self.fail("compatibility worker crossed a newly active lease")
                self.assertEqual(blocked.exception.error_code, "PROJECT_MUTATION_AUTHORITY_REQUIRED")

    def test_worker_revalidates_stale_binding_before_entering_process_consequence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-a042-worker-stale-") as td:
            root = Path(td)
            with ExitStack() as stack:
                stack.enter_context(
                    patch.object(pma, "get_project_root", side_effect=lambda project_id: root / project_id)
                )
                stack.enter_context(
                    patch.object(
                        pma,
                        "init_project_layout",
                        side_effect=lambda project_id: (root / project_id).mkdir(parents=True, exist_ok=True)
                        or (root / project_id),
                    )
                )
                first = pma.acquire_lease(
                    "p1", expected_generation=0, owner_id="owner-a", session_id="session-a"
                )
                pma.release_lease(
                    "p1",
                    lease_id=str(first["lease_id"]),
                    generation=1,
                    owner_id="owner-a",
                    session_id="session-a",
                )
                pma.acquire_lease(
                    "p1", expected_generation=1, owner_id="owner-b", session_id="session-b"
                )
                request = {
                    "project_id": "p1",
                    "project_mutation_binding": {
                        "project_id": "p1",
                        "generation": 1,
                        "owner_id": "owner-a",
                        "session_id": "session-a",
                    },
                }
                with self.assertRaises(pma.ProjectMutationAuthorityError) as fenced:
                    with execution_worker._project_mutation_context(request):
                        self.fail("stale worker binding entered consequence context")
                self.assertEqual(fenced.exception.error_code, "PROJECT_MUTATION_LEASE_FENCED")

    def test_completion_journal_records_after_expiry_before_takeover(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-a042-completion-expired-") as td:
            root = Path(td)
            clock = _Clock()
            with ExitStack() as stack:
                stack.enter_context(
                    patch.object(pma, "get_project_root", side_effect=lambda project_id: root / project_id)
                )
                stack.enter_context(
                    patch.object(
                        pma,
                        "init_project_layout",
                        side_effect=lambda project_id: (root / project_id).mkdir(parents=True, exist_ok=True)
                        or (root / project_id),
                    )
                )
                stack.enter_context(patch.object(pma, "_now", side_effect=clock))
                stack.enter_context(
                    patch.object(pma, "utc_now", side_effect=lambda: clock().isoformat())
                )
                pma.acquire_lease(
                    "p1", expected_generation=0, owner_id="owner-a", session_id="session-a", ttl_seconds=10
                )
                job = self._job()
                job.status = "COMPLETED"
                job.return_code = 0
                job.journal_on_complete = True
                job.extra["project_mutation_binding"] = {
                    "project_id": "p1", "generation": 1, "owner_id": "owner-a", "session_id": "session-a"
                }
                clock.advance(11)
                with patch.object(execution_routes, "_append_job_journal") as append_journal:
                    execution_routes._record_completion_journal("p1", job)
                append_journal.assert_called_once()
                self.assertEqual(job.extra["completion_journal_status"], "recorded")

    def test_completion_journal_is_suppressed_after_generation_takeover(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-a042-completion-takeover-") as td:
            root = Path(td)
            with ExitStack() as stack:
                stack.enter_context(
                    patch.object(pma, "get_project_root", side_effect=lambda project_id: root / project_id)
                )
                stack.enter_context(
                    patch.object(
                        pma,
                        "init_project_layout",
                        side_effect=lambda project_id: (root / project_id).mkdir(parents=True, exist_ok=True)
                        or (root / project_id),
                    )
                )
                first = pma.acquire_lease(
                    "p1", expected_generation=0, owner_id="owner-a", session_id="session-a"
                )
                pma.release_lease(
                    "p1", lease_id=str(first["lease_id"]), generation=1, owner_id="owner-a", session_id="session-a"
                )
                pma.acquire_lease(
                    "p1", expected_generation=1, owner_id="owner-b", session_id="session-b"
                )
                job = self._job()
                job.status = "COMPLETED"
                job.return_code = 0
                job.journal_on_complete = True
                with patch.object(execution_routes, "_append_job_journal") as append_journal:
                    execution_routes._record_completion_journal("p1", job)
                append_journal.assert_not_called()
                self.assertEqual(job.extra["completion_journal_status"], "fenced")
                self.assertEqual(job.extra["completion_journal_error"], "PROJECT_MUTATION_LEASE_FENCED")


if __name__ == "__main__":
    unittest.main()
