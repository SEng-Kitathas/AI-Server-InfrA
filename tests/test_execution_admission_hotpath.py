from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import execution_routes as er


class _AliveProc:
    def poll(self):
        return None


class ExecutionAdmissionHotpathTests(unittest.TestCase):
    def test_saturated_drain_is_two_tree_walks_not_per_candidate_recensus(self) -> None:
        paths = [Path(f"job-{i}.json") for i in range(60)]
        counters = {"iter": 0, "load": 0, "read": 0, "can": 0}

        def fake_iter(project_id=None):
            counters["iter"] += 1
            return iter(paths)

        def fake_load(path):
            counters["load"] += 1
            idx = int(path.stem.split("-")[-1])
            if idx < 40:
                status, pid = "SUCCEEDED", 0
            elif idx < 48:
                status, pid = "RUNNING", 1234
            else:
                status, pid = "QUEUED", 0
            return (
                SimpleNamespace(
                    job_id=f"job-{idx}",
                    project_id="p1",
                    status=status,
                    pid=pid,
                    submitted_at=f"2026-09-05T00:00:{idx:02d}+00:00",
                ),
                None,
            )

        def forbidden_read(project_id, job_id):
            counters["read"] += 1
            raise AssertionError("saturated drain must break before reading a candidate")

        def forbidden_can(project_id):
            counters["can"] += 1
            raise AssertionError("drain must not call per-candidate _can_start_now")

        with patch.object(er, "_iter_job_files", side_effect=fake_iter), patch.object(
            er, "_load_job_file", side_effect=fake_load
        ), patch.object(er, "_pid_alive", return_value=True), patch.object(
            er, "_read_job", side_effect=forbidden_read
        ), patch.object(er, "_can_start_now", side_effect=forbidden_can), patch.object(
            er, "EXECUTION_GLOBAL_CONCURRENCY", 8
        ), patch.object(er, "EXECUTION_PROJECT_CONCURRENCY", None), patch.object(
            er, "_RUNNING", {}
        ):
            started = er._drain_queue("p1")

        self.assertEqual(started, [])
        self.assertEqual(counters["iter"], 2)
        self.assertEqual(counters["load"], 120)
        self.assertEqual(counters["read"], 0)
        self.assertEqual(counters["can"], 0)

    def test_local_global_budget_prevents_overadmission_without_recensus(self) -> None:
        jobs = {
            "q1": SimpleNamespace(job_id="q1", project_id="p1", status="QUEUED"),
            "q2": SimpleNamespace(job_id="q2", project_id="p1", status="QUEUED"),
        }
        reads: list[str] = []
        spawns: list[str] = []

        def fake_read(project_id, job_id):
            reads.append(job_id)
            return jobs[job_id]

        def fake_spawn(job):
            spawns.append(job.job_id)
            job.status = "RUNNING"
            return job

        with patch.object(er, "_running_census", return_value=(7, {"p1": 7})) as census, patch.object(
            er, "_read_job", side_effect=fake_read
        ), patch.object(er, "_spawn_job", side_effect=fake_spawn), patch.object(
            er, "_write_job", return_value=None
        ), patch.object(er, "EXECUTION_GLOBAL_CONCURRENCY", 8), patch.object(
            er, "EXECUTION_PROJECT_CONCURRENCY", None
        ), patch.object(er, "_can_start_now", side_effect=AssertionError("must not recensus")):
            started = er._drain_queue_locked(
                candidates=[("1", "p1", "q1"), ("2", "p1", "q2")]
            )

        census.assert_called_once_with()
        self.assertEqual(started, ["q1"])
        self.assertEqual(reads, ["q1"])
        self.assertEqual(spawns, ["q1"])

    def test_full_project_is_skipped_while_other_project_can_start(self) -> None:
        jobs = {
            ("p1", "q1"): SimpleNamespace(job_id="q1", project_id="p1", status="QUEUED"),
            ("p2", "q2"): SimpleNamespace(job_id="q2", project_id="p2", status="QUEUED"),
        }
        spawns: list[str] = []

        def fake_read(project_id, job_id):
            return jobs[(project_id, job_id)]

        def fake_spawn(job):
            spawns.append(job.job_id)
            job.status = "RUNNING"
            return job

        with patch.object(er, "_running_census", return_value=(1, {"p1": 1, "p2": 0})), patch.object(
            er, "_read_job", side_effect=fake_read
        ), patch.object(er, "_spawn_job", side_effect=fake_spawn), patch.object(
            er, "_write_job", return_value=None
        ), patch.object(er, "EXECUTION_GLOBAL_CONCURRENCY", 8), patch.object(
            er, "EXECUTION_PROJECT_CONCURRENCY", 1
        ):
            started = er._drain_queue_locked(
                candidates=[("1", "p1", "q1"), ("2", "p2", "q2")]
            )

        self.assertEqual(started, ["q2"])
        self.assertEqual(spawns, ["q2"])

    def test_running_census_preserves_live_managed_process_semantics(self) -> None:
        record = SimpleNamespace(
            job_id="managed-1",
            project_id="p1",
            status="SUCCEEDED",  # transiently stale durable status
            pid=None,
        )
        with patch.object(er, "_RUNNING", {"managed-1": _AliveProc()}), patch.object(
            er, "_iter_job_files", return_value=iter([Path("managed-1.json")])
        ), patch.object(er, "_load_job_file", return_value=(record, None)), patch.object(
            er, "_pid_alive", side_effect=AssertionError("managed process should not need PID probe")
        ):
            total, per_project = er._running_census()

        self.assertEqual(total, 1)
        self.assertEqual(per_project, {"p1": 1})


if __name__ == "__main__":
    unittest.main()
