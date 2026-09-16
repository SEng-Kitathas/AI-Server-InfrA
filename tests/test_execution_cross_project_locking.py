"""Hostile concurrency regression for cross-project execution lock isolation."""

from __future__ import annotations

import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

import execution_routes as er


class CrossProjectLockingTests(unittest.TestCase):
    def test_slow_project_a_reconciliation_does_not_block_project_b_admission(self) -> None:
        """Desired V30 invariant: unrelated project work must not serialize behind one project scan."""
        entered = threading.Event()
        release = threading.Event()
        submit_entered = threading.Event()
        submit_completed = threading.Event()

        def slow_iter(project_id=None):
            if project_id is None:
                entered.set()
                release.wait(timeout=2.0)
            return iter(())

        def fake_submit_locked(payload, replay_of):
            submit_entered.set()
            return object()

        with patch.object(er, "_iter_job_files", side_effect=slow_iter), patch.object(
            er, "_submit_job_locked", side_effect=fake_submit_locked
        ), patch.object(er, "_normalize_submit_payload", return_value=object()), patch.object(
            er, "_ensure_scheduler_started", return_value=None
        ):
            t1 = threading.Thread(target=er._scheduler_tick, daemon=True)
            t1.start()
            self.assertTrue(entered.wait(0.5), "scheduler scan did not enter")

            def submit_b():
                er.submit_execution_job({"project_id": "project-b", "command": ["noop"]})
                submit_completed.set()

            t2 = threading.Thread(target=submit_b, daemon=True)
            started = time.perf_counter()
            t2.start()
            time.sleep(0.1)

            blocked = not submit_entered.is_set()
            release.set()
            t1.join(timeout=1.0)
            t2.join(timeout=1.0)
            elapsed = time.perf_counter() - started

        self.assertFalse(blocked, "project-b admission was blocked by unrelated global reconciliation")
        self.assertTrue(submit_completed.is_set())
        self.assertLess(elapsed, 0.5)


if __name__ == "__main__":
    unittest.main()
