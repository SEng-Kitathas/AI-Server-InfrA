"""End-to-end hostile tests for durable worker-capsule recovery."""

from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

import execution_routes as er


class WorkerRestartRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name).resolve()
        self.projects = root / "projects"
        self.project_root = self.projects / "alpha"
        self.project_root.mkdir(parents=True, exist_ok=True)
        self.patchers = [
            patch.object(er, "PROJECTS_ROOT", self.projects),
            patch.object(er, "get_project_root", lambda project_id: self.projects / project_id),
            patch.object(er, "_ensure_scheduler_started", return_value=None),
        ]
        for item in self.patchers:
            item.start()
        er._RUNNING.clear()

    def tearDown(self) -> None:
        # Kill any worker capsules still owned by this test process.
        for proc in list(er._RUNNING.values()):
            try:
                if proc.poll() is None:
                    proc.kill()
            except Exception:
                pass
        er._RUNNING.clear()
        for item in reversed(self.patchers):
            item.stop()
        self.tempdir.cleanup()

    def _submit(self, code: str, *, timeout_seconds: int | None = 10):
        return er.submit_execution_job(
            {
                "project_id": "alpha",
                "command": [sys.executable],
                "args": ["-c", code],
                "cwd": ".",
                "timeout_seconds": timeout_seconds,
                "stdout_max_bytes": 65536,
                "stderr_max_bytes": 65536,
            }
        )

    def _wait_terminal(self, job_id: str, timeout: float = 8.0):
        deadline = time.time() + timeout
        last = None
        while time.time() < deadline:
            last = er._finalize("alpha", job_id, er._read_job("alpha", job_id))
            if last.status in er.JOB_TERMINAL_STATUSES:
                return last
            time.sleep(0.05)
        self.fail(f"job did not become terminal: {last}")

    def test_completion_survives_loss_of_receiver_popen_handle(self) -> None:
        job = self._submit("import time; time.sleep(0.35); print('SURVIVED', flush=True)")
        self.assertEqual(job.status, er.JOB_STATUS_RUNNING)
        self.assertTrue(job.worker_token)
        worker = er._RUNNING.pop(job.job_id)
        self.assertIsNone(worker.poll())

        final = self._wait_terminal(job.job_id)
        self.assertEqual(final.status, er.JOB_STATUS_COMPLETED)
        self.assertEqual(final.return_code, 0)
        self.assertEqual(final.supervision_state, "worker_receipt_complete")
        self.assertIn("SURVIVED", Path(final.stdout_path).read_text(encoding="utf-8"))

    def test_termination_survives_loss_of_receiver_popen_handle(self) -> None:
        job = self._submit("import time; print('RUNNING', flush=True); time.sleep(30)", timeout_seconds=None)
        worker = er._RUNNING.pop(job.job_id)
        self.assertIsNone(worker.poll())

        requested = er.terminate_execution_job("alpha", job.job_id)
        self.assertEqual(requested.status, er.JOB_STATUS_TERMINATING)
        self.assertTrue(Path(str(requested.worker_cancel_path)).is_file())

        final = self._wait_terminal(job.job_id)
        self.assertEqual(final.status, er.JOB_STATUS_TERMINATED)
        self.assertEqual(final.supervision_state, "worker_receipt_terminated")

    def test_timeout_is_enforced_by_worker_without_receiver_handle(self) -> None:
        job = self._submit("import time; time.sleep(30)", timeout_seconds=1)
        worker = er._RUNNING.pop(job.job_id)
        self.assertIsNone(worker.poll())

        final = self._wait_terminal(job.job_id, timeout=6.0)
        self.assertEqual(final.status, er.JOB_STATUS_FAILED)
        self.assertEqual(final.stage, "timeout")
        self.assertEqual(final.supervision_state, "worker_receipt_timeout")


if __name__ == "__main__":
    unittest.main()
