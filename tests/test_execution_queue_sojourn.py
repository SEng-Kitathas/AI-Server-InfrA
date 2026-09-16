from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

import execution_routes as er
from control_plane_models import CapacitySnapshot


class ExecutionQueueSojournTests(unittest.TestCase):
    def test_queue_census_measures_global_and_project_oldest_sojourn(self) -> None:
        jobs = {
            "a": SimpleNamespace(
                status=er.JOB_STATUS_QUEUED,
                submitted_at="2026-09-08T00:00:00+00:00",
                project_id="alpha",
            ),
            "b": SimpleNamespace(
                status=er.JOB_STATUS_QUEUED,
                submitted_at="2026-09-08T00:00:05+00:00",
                project_id="beta",
            ),
            "c": SimpleNamespace(
                status=er.JOB_STATUS_RUNNING,
                submitted_at="2026-09-07T23:00:00+00:00",
                project_id="alpha",
            ),
        }
        paths = [Path(name) for name in jobs]
        with patch.object(er, "_iter_job_files", return_value=iter(paths)), patch.object(
            er, "_load_job_file", side_effect=lambda path: (jobs[path.name], None)
        ), patch.object(er.time, "time", return_value=1788825610.0), patch.object(
            er, "_readiness_queue_age",
            side_effect=lambda job, _now: {"a": 10.0, "b": 5.0}.get(
                next(k for k, v in jobs.items() if v is job)
            ),
        ):
            observed = er._queue_census("alpha")
        self.assertEqual(observed, (2, 1, 10.0, 10.0))

    def test_capacity_snapshot_uses_one_running_census_and_one_queue_census(self) -> None:
        with patch.object(
            er, "_running_census", return_value=(3, {"alpha": 1})
        ) as running, patch.object(
            er, "_queue_census", return_value=(5, 2, 12.5, 7.25)
        ) as queued:
            observed = er._capacity_snapshot("alpha")
        running.assert_called_once_with()
        queued.assert_called_once_with("alpha")
        self.assertEqual(observed.running_global, 3)
        self.assertEqual(observed.running_project, 1)
        self.assertEqual(observed.queued_global, 5)
        self.assertEqual(observed.queued_project, 2)
        self.assertEqual(observed.oldest_queued_age_seconds, 12.5)
        self.assertEqual(observed.oldest_project_queued_age_seconds, 7.25)

    def test_queue_full_rejection_exposes_sojourn_but_does_not_invent_retry_eta(self) -> None:
        snapshot = CapacitySnapshot(
            running_global=8,
            running_project=3,
            global_limit=8,
            project_limit=3,
            queued_global=20,
            queued_project=7,
            global_queue_limit=20,
            project_queue_limit=7,
            oldest_queued_age_seconds=42.5,
            oldest_project_queued_age_seconds=19.75,
        )
        job = SimpleNamespace(project_id="alpha", job_id="job-r9")
        with patch.object(er, "_can_start_now", return_value=False), patch.object(
            er, "_queue_allowed", return_value=False
        ), patch.object(er, "_capacity_snapshot", return_value=snapshot):
            with self.assertRaises(er.ExecutionOverCapacity) as raised:
                er._spawn_or_queue_job(job)
        err = raised.exception
        self.assertEqual(err.status, 429)
        self.assertEqual(err.error_code, "EXECUTION_OVER_CAPACITY")
        self.assertEqual(err.extra["capacity"]["oldest_queued_age_seconds"], 42.5)
        self.assertEqual(err.extra["queue_sojourn"]["oldest_project_queued_age_seconds"], 19.75)
        self.assertIsNone(err.extra["retry_after_seconds"])
        self.assertEqual(
            err.extra["retry_after_basis"],
            "not_claimed_without_observed_service-time_model",
        )


if __name__ == "__main__":
    unittest.main()
