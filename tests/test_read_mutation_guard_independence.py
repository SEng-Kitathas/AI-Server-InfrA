from __future__ import annotations

import tempfile
import threading
import time

from flask import Flask
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(PROJECT_ROOT / "baseline"))

import execution_routes
import lab_tools
import project_mutation_authority as pma
import power_routes
from control_plane_models import ExecutionJobRecord, CapacitySnapshot
from api_wire_execution import ExecutionStatusRequest, ExecutionOutputRequest, ExecutionListRequest


class ReadMutationGuardIndependenceTests(unittest.TestCase):
    def _patched_authority(self, root: Path) -> ExitStack:
        stack = ExitStack()
        stack.enter_context(patch.object(pma, "get_project_root", side_effect=lambda project_id: root / project_id))
        stack.enter_context(
            patch.object(
                pma,
                "init_project_layout",
                side_effect=lambda project_id: (root / project_id).mkdir(parents=True, exist_ok=True) or (root / project_id),
            )
        )
        return stack

    def test_pure_lease_observation_does_not_wait_for_transition_guard(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-read-guard-") as td:
            root = Path(td)
            with self._patched_authority(root):
                lease = pma.acquire_lease("p1", expected_generation=0, owner_id="owner", session_id="session")
                entered = threading.Event(); release = threading.Event()

                def holder() -> None:
                    with pma._project_guard("p1", timeout_seconds=1.0):
                        entered.set(); release.wait(timeout=5)

                thread = threading.Thread(target=holder)
                thread.start(); self.assertTrue(entered.wait(timeout=2))
                try:
                    observed = pma.observe_lease("p1")
                finally:
                    release.set(); thread.join(timeout=5)
                self.assertEqual(observed["generation"], lease["generation"])
                self.assertEqual(observed["status"], pma.LEASE_STATUS_ACTIVE)

    def test_dispatch_lease_observation_remains_available_while_transition_guard_is_busy(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-read-guard-dispatch-") as td:
            root = Path(td)
            with self._patched_authority(root):
                lease = pma.acquire_lease("p1", expected_generation=0, owner_id="owner", session_id="session")
                entered = threading.Event()
                release = threading.Event()

                def holder() -> None:
                    with pma._project_guard("p1", timeout_seconds=1.0):
                        entered.set()
                        release.wait(timeout=5)

                thread = threading.Thread(target=holder)
                thread.start()
                self.assertTrue(entered.wait(timeout=2))
                started = time.monotonic()
                try:
                    result = lab_tools.dispatch_tool("project.mutation.inspect", {"project_id": "p1"})
                finally:
                    release.set()
                    thread.join(timeout=5)
                self.assertLess(time.monotonic() - started, 1.0)
                self.assertEqual(result["result"]["generation"], lease["generation"])
                self.assertEqual(result["result"]["status"], pma.LEASE_STATUS_ACTIVE)

    def test_execution_status_observation_does_not_write_or_advance_queue(self) -> None:
        job = ExecutionJobRecord(project_id="p1", job_id="job-x", status="RUNNING", stage="running", execution_mode="one_shot", replay_of=None, command=["python"], cwd=".", cwd_rel=".", submitted_at="2026-09-10T00:00:00+00:00")
        import lab_tools_execution as execution_tools
        dep = execution_tools.ExecutionToolDeps(
            error_cls=lab_tools.LabToolError,
            request_optional_positive_int=lambda *a, **k: None,
            resolve_cwd=lambda *a, **k: Path("."),
            exec_env=lambda: {},
            finalize_job=lambda *a, **k: (_ for _ in ()).throw(AssertionError("finalize must not run")),
            read_job=lambda _project_id, _job_id: job,
            tail_text=lambda *a, **k: ("", False),
            execution_modes=("one_shot",),
            max_output_bytes=1024,
            default_timeout_seconds=30,
            default_stdout_max_bytes=1024,
            default_stderr_max_bytes=1024,
            max_timeout_seconds=60,
            submit_job=lambda *a, **k: {},
            terminate_job=lambda *a, **k: {},
            utc_now=lambda: "2026-09-10T00:00:00+00:00",
        )
        observed = execution_tools._observed_job(execution_tools.ExecutionIdentity("p1", "job-x"), dep)
        self.assertEqual(observed["status"], "RUNNING")

    def test_power_wait_projection_does_not_finalize_or_advance_queue(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-power-wait-read-") as td:
            root = Path(td)
            stdout = root / "stdout.log"
            stderr = root / "stderr.log"
            stdout.write_text("done", encoding="utf-8")
            stderr.write_text("", encoding="utf-8")
            job = ExecutionJobRecord(
                project_id="p1",
                job_id="job-x",
                status="COMPLETED",
                stage="terminal",
                execution_mode="one_shot",
                replay_of=None,
                command=["python"],
                cwd=".",
                cwd_rel=".",
                submitted_at="2026-09-10T00:00:00+00:00",
                stdout_path=str(stdout),
                stderr_path=str(stderr),
                return_code=0,
                duration_ms=1,
            )
            app = Flask(__name__)
            with app.test_request_context(
                "/project/execution/wait",
                method="POST",
                json={"project_id": "p1", "job_id": "job-x", "timeout_seconds": 1, "max_bytes": 1024},
            ), patch.object(power_routes, "_auth", return_value=None), patch.object(
                power_routes, "_read_job", return_value=job
            ) as read, patch.object(
                power_routes, "_finalize", side_effect=AssertionError("projection must not finalize")
            ) as finalize:
                response = power_routes.wait_for_project_execution()
                payload = response.get_json()
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["status"], "COMPLETED")
            self.assertEqual(payload["stdout"], "done")
            read.assert_called()
            finalize.assert_not_called()

    def _terminal_job(self, root: Path) -> ExecutionJobRecord:
        stdout = root / "stdout.log"
        stderr = root / "stderr.log"
        stdout.write_text("done", encoding="utf-8")
        stderr.write_text("", encoding="utf-8")
        return ExecutionJobRecord(
            project_id="p1", job_id="job-x", status="COMPLETED", stage="terminal",
            execution_mode="one_shot", replay_of=None, command=["python"], cwd=".", cwd_rel=".",
            submitted_at="2026-09-10T00:00:00+00:00", stdout_path=str(stdout), stderr_path=str(stderr),
            return_code=0, duration_ms=1,
        )

    def test_direct_execution_status_payload_is_observation_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-status-read-") as td:
            job = self._terminal_job(Path(td))
            with patch.object(execution_routes, "_read_job", return_value=job), patch.object(
                execution_routes, "_finalize", side_effect=AssertionError("status must not finalize")
            ) as finalize:
                payload = execution_routes._status_payload(ExecutionStatusRequest("p1", "job-x"))
        self.assertEqual(payload["status"], "COMPLETED")
        finalize.assert_not_called()

    def test_direct_execution_output_payload_is_observation_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-output-read-") as td:
            job = self._terminal_job(Path(td))
            with patch.object(execution_routes, "_read_job", return_value=job), patch.object(
                execution_routes, "_finalize", side_effect=AssertionError("output must not finalize")
            ) as finalize:
                payload = execution_routes._output_payload(ExecutionOutputRequest("p1", "job-x", max_bytes=1024))
        self.assertEqual(payload["status"], "COMPLETED")
        self.assertEqual(payload["stdout"], "done")
        finalize.assert_not_called()

    def test_direct_execution_list_payload_does_not_finalize_or_drain_queue(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-list-read-") as td:
            root = Path(td)
            job = self._terminal_job(root)
            fake = root / "job-x.json"
            fake.write_text("{}", encoding="utf-8")
            capacity = CapacitySnapshot(
                running_global=0, running_project=0, global_limit=12, project_limit=12,
                queued_global=0, queued_project=0, global_queue_limit=0, project_queue_limit=0,
            )
            with patch.object(execution_routes, "_iter_all_job_files", return_value=[fake]), patch.object(
                execution_routes, "_load_job_file", return_value=(job, None)
            ), patch.object(execution_routes, "_capacity_snapshot", return_value=capacity), patch.object(
                execution_routes, "_drain_queue", side_effect=AssertionError("list must not drain queue")
            ) as drain, patch.object(
                execution_routes, "_finalize", side_effect=AssertionError("list must not finalize")
            ) as finalize:
                payload = execution_routes._list_payload(ExecutionListRequest("p1", limit=10))
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["jobs"][0]["status"], "COMPLETED")
        drain.assert_not_called()
        finalize.assert_not_called()

    def test_direct_execution_list_serializes_corrupt_job_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-list-corrupt-read-") as td:
            root = Path(td)
            fake = root / "broken.json"
            fake.write_text("{broken", encoding="utf-8")
            capacity = CapacitySnapshot(
                running_global=0, running_project=0, global_limit=12, project_limit=12,
                queued_global=0, queued_project=0, global_queue_limit=0, project_queue_limit=0,
            )
            with patch.object(execution_routes, "_iter_all_job_files", return_value=[fake]), patch.object(
                execution_routes, "_load_job_file", return_value=(None, "bad json")
            ), patch.object(execution_routes, "_capacity_snapshot", return_value=capacity), patch.object(
                execution_routes, "_drain_queue", side_effect=AssertionError("list must not drain queue")
            ) as drain, patch.object(
                execution_routes, "_finalize", side_effect=AssertionError("list must not finalize")
            ) as finalize:
                payload = execution_routes._list_payload(ExecutionListRequest("p1", limit=10))
        self.assertEqual(payload["count"], 0)
        self.assertEqual(payload["corrupt_job_files"][0]["error"], "bad json")
        drain.assert_not_called()
        finalize.assert_not_called()

    def test_read_capability_contracts_are_truthfully_non_reconciling(self) -> None:
        cards = {row["name"]: row for row in lab_tools.list_tools()}
        for name in ("execution.status", "execution.output", "execution.progress", "execution.wait"):
            card = cards[name]
            self.assertEqual(card["side_effect_class"], "read", name)
            self.assertNotIn("reconciles_state", card["effect_traits"], name)
            self.assertNotIn("may_advance_queue", card["effect_traits"], name)
        inspect = cards["project.mutation.inspect"]
        self.assertFalse(inspect["mutating"])
        self.assertEqual(inspect["side_effect_class"], "read")
        self.assertFalse(inspect["effective_approval_required"])
        self.assertNotIn("may_reconcile_expiry", inspect["effect_traits"])


if __name__ == "__main__":
    unittest.main()
