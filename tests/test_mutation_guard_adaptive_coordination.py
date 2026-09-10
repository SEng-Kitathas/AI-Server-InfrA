from __future__ import annotations

import json
import sys
import tempfile
import threading
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baseline"))

from pcmmad_receiver import execution_routes as er
from pcmmad_receiver import project_mutation_authority as pma
from pcmmad_receiver.control_plane_models import ExecutionJobRecord


class AdaptiveConsequenceGuardTests(unittest.TestCase):
    def test_healthy_holder_extends_wait_beyond_base_timeout_and_goes_dormant(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-adaptive-guard-") as td:
            root = Path(td)
            entered = threading.Event()
            release = threading.Event()
            errors: list[BaseException] = []

            def project_root(project_id: str) -> Path:
                path = root / project_id
                path.mkdir(parents=True, exist_ok=True)
                return path

            def holder() -> None:
                try:
                    with pma.compatibility_session_guard(
                        "p1", session_id="holder", timeout_seconds=0.1
                    ):
                        entered.set()
                        release.wait(timeout=5)
                except BaseException as exc:  # pragma: no cover - surfaced below
                    errors.append(exc)

            with ExitStack() as stack:
                stack.enter_context(patch.object(pma, "get_project_root", side_effect=project_root))
                stack.enter_context(
                    patch.object(
                        pma,
                        "init_project_layout",
                        side_effect=lambda project_id: project_root(project_id),
                    )
                )
                stack.enter_context(patch.object(pma, "CONSEQUENCE_HEALTHY_WAIT_MAX_SECONDS", 3.0))
                stack.enter_context(patch.object(pma, "CONSEQUENCE_HEARTBEAT_INTERVAL_SECONDS", 0.05))
                stack.enter_context(patch.object(pma, "CONSEQUENCE_HEARTBEAT_FRESH_SECONDS", 0.4))
                thread = threading.Thread(target=holder, daemon=True)
                thread.start()
                self.assertTrue(entered.wait(timeout=2))
                time.sleep(0.12)

                observed = pma.observe_lease("p1")
                guard = observed["consequence_guard"]
                self.assertTrue(guard["active"])
                self.assertTrue(guard["heartbeat_fresh"])
                self.assertEqual(guard["holder_pid"], pma.os.getpid())
                self.assertGreaterEqual(guard["heartbeat_sequence"], 1)

                timer = threading.Timer(0.35, release.set)
                timer.start()
                started = time.monotonic()
                with pma.compatibility_session_guard(
                    "p1", session_id="waiter", timeout_seconds=0.1
                ):
                    waited = time.monotonic() - started
                timer.cancel()
                self.assertGreater(waited, 0.2)
                self.assertLess(waited, 2.0)
                thread.join(timeout=2)
                self.assertFalse(thread.is_alive())
                self.assertEqual(errors, [])

                dormant = pma.observe_lease("p1")["consequence_guard"]
                self.assertFalse(dormant["active"])
                self.assertFalse(dormant["heartbeat_fresh"])

    def test_stale_holder_metadata_does_not_extend_wait_forever(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-adaptive-guard-stale-") as td:
            root = Path(td)

            def project_root(project_id: str) -> Path:
                path = root / project_id
                path.mkdir(parents=True, exist_ok=True)
                return path

            with ExitStack() as stack:
                stack.enter_context(patch.object(pma, "get_project_root", side_effect=project_root))
                stack.enter_context(
                    patch.object(
                        pma,
                        "init_project_layout",
                        side_effect=lambda project_id: project_root(project_id),
                    )
                )
                stale_path = pma._consequence_state_path("p1")
                stale_path.parent.mkdir(parents=True, exist_ok=True)
                stale_path.write_text(
                    json.dumps(
                        {
                            "schema": "pcmmad.project-mutation-consequence-holder.v1",
                            "project_id": "p1",
                            "holder_token": "stale",
                            "holder_pid": 999999,
                            "heartbeat_at_epoch": time.time() - 100,
                            "heartbeat_sequence": 7,
                        }
                    ),
                    encoding="utf-8",
                )
                observed = pma.observe_lease("p1")["consequence_guard"]
                self.assertFalse(observed["heartbeat_fresh"])
                self.assertEqual(observed["holder_token"], "stale")


class ExclusiveExecutionAdmissionTests(unittest.TestCase):
    @staticmethod
    def _job(project_id: str, job_id: str, *, bound: bool, status: str) -> ExecutionJobRecord:
        job = ExecutionJobRecord(
            project_id=project_id,
            job_id=job_id,
            status=status,
            stage=status.lower(),
            execution_mode="one_shot",
            replay_of=None,
            command=[sys.executable, "-c", "print('ok')"],
            cwd=str(ROOT),
            cwd_rel=".",
            submitted_at="2026-09-10T00:00:00+00:00",
        )
        if bound:
            job.extra["project_mutation_binding"] = {
                "project_id": project_id,
                "mode": "compatibility_no_lease",
                "generation": 0,
                "owner_id": "",
                "session_id": "execution",
            }
            job.extra["execution_project_exclusive"] = True
        return job

    def test_bound_jobs_are_explicitly_project_exclusive(self) -> None:
        self.assertTrue(er._job_requires_project_exclusive_execution(self._job("p1", "a", bound=True, status="QUEUED")))
        self.assertFalse(er._job_requires_project_exclusive_execution(self._job("p1", "b", bound=False, status="QUEUED")))

    def test_queue_drain_keeps_second_same_project_exclusive_job_queued(self) -> None:
        running = self._job("p1", "running", bound=True, status="RUNNING")
        queued = self._job("p1", "queued", bound=True, status="QUEUED")
        with ExitStack() as stack:
            stack.enter_context(
                patch.object(
                    er,
                    "_running_census",
                    return_value=er._RunningCensusResult(
                        1, {"p1": 1}, frozenset({"p1"})
                    ),
                )
            )
            stack.enter_context(patch.object(er, "_read_job", return_value=queued))
            spawn = stack.enter_context(patch.object(er, "_spawn_job"))
            started = er._drain_queue_locked(
                candidates=[("2026", "p1", "queued")],
                limit=8,
            )
        self.assertEqual(started, [])
        spawn.assert_not_called()

    def test_spawn_or_queue_labels_project_exclusive_wait(self) -> None:
        queued = self._job("p1", "queued", bound=True, status="SUBMITTED")
        with ExitStack() as stack:
            stack.enter_context(patch.object(er, "_can_start_now", return_value=False))
            stack.enter_context(patch.object(er, "_queue_allowed", return_value=True))
            stack.enter_context(
                patch.object(
                    er,
                    "_running_census",
                    return_value=er._RunningCensusResult(
                        1, {"p1": 1}, frozenset({"p1"})
                    ),
                )
            )
            stack.enter_context(patch.object(er, "_effective_queue_count", return_value=1))
            out = er._spawn_or_queue_job(queued)
        self.assertEqual(out.status, "QUEUED")
        self.assertEqual(out.stage, "queued_project_exclusive")
        self.assertEqual(out.extra["queue_reason"], "project_exclusive_execution")

    def test_queue_drain_still_starts_exclusive_job_in_other_project(self) -> None:
        running = self._job("p1", "running", bound=True, status="RUNNING")
        queued = self._job("p2", "queued", bound=True, status="QUEUED")
        spawned = self._job("p2", "queued", bound=True, status="RUNNING")
        with ExitStack() as stack:
            stack.enter_context(
                patch.object(
                    er,
                    "_running_census",
                    return_value=er._RunningCensusResult(
                        1, {"p1": 1, "p2": 0}, frozenset({"p1"})
                    ),
                )
            )
            stack.enter_context(patch.object(er, "_read_job", return_value=queued))
            stack.enter_context(patch.object(er, "_write_job"))
            spawn = stack.enter_context(patch.object(er, "_spawn_job", return_value=spawned))
            started = er._drain_queue_locked(
                candidates=[("2026", "p2", "queued")],
                limit=8,
            )
        self.assertEqual(started, ["queued"])
        spawn.assert_called_once()


if __name__ == "__main__":
    unittest.main()
