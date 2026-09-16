from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import execution_routes as er
from control_plane_models import ExecutionJobRecord, GlobalExecutionSnapshot, SchedulerTelemetry


def _job_record(
    job_id: str = "poison",
    *,
    project_id: str = "p1",
    status: str = "RUNNING",
    pid: int | None = 999998,
    stdout_path: str = "",
    stderr_path: str = "",
) -> ExecutionJobRecord:
    return ExecutionJobRecord.from_dict(
        {
            "job_id": job_id,
            "project_id": project_id,
            "status": status,
            "pid": pid,
            "command": ["noop"],
            "stdout_path": stdout_path,
            "stderr_path": stderr_path,
            "worker_token": None,
            "supervision_state": "supervised",
            "created_at": "2026-09-05T00:00:00+00:00",
            "submitted_at": "2026-09-05T00:00:00+00:00",
        }
    )


class ExecutionSchedulerPoisonIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.telemetry_patch = patch.object(er, "_SCHEDULER_TELEMETRY", SchedulerTelemetry())
        self.telemetry_patch.start()

    def tearDown(self) -> None:
        self.telemetry_patch.stop()

    def test_empty_log_paths_no_longer_abort_tick_or_block_drain(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-poison-") as td:
            root = Path(td)
            projects = root / "projects"
            project_root = projects / "p1"
            jobs = project_root / "system" / "logs" / "execution"
            jobs.mkdir(parents=True)

            poison = _job_record("aaa_poison")
            poison_path = jobs / "aaa_poison.json"
            poison_path.write_text(json.dumps(poison.to_dict()), encoding="utf-8")
            for i in range(3):
                queued = _job_record(
                    f"zzz_queued{i}", status="QUEUED", pid=0
                )
                (jobs / f"zzz_queued{i}.json").write_text(
                    json.dumps(queued.to_dict()), encoding="utf-8"
                )

            drain_calls: list[str | None] = []
            with patch.object(er, "PROJECTS_ROOT", projects), patch.object(
                er, "get_project_root", side_effect=lambda project_id: projects / project_id
            ), patch.object(er, "_pid_alive", return_value=False), patch.object(
                er, "_drain_queue", side_effect=lambda project_id=None, **_: drain_calls.append(project_id) or []
            ), patch.object(
                er,
                "_job_failure_excerpt",
                side_effect=AssertionError("scheduler reconciliation must not tail output logs"),
            ), patch.object(er, "_EXECUTION_STORE_LAYOUT_READY_ROOTS", set()):
                er._ensure_execution_store_layout()
                er._scheduler_tick()
                persisted = er._read_job("p1", "aaa_poison").to_dict()

            self.assertEqual(persisted["status"], "FAILED")
            self.assertEqual(persisted["stage"], "supervision_lost")
            self.assertEqual(persisted["failure_digest"]["failure_kind"], "SUPERVISION_LOST")
            self.assertEqual(persisted["failure_digest"]["stderr_excerpt"], "")
            self.assertEqual(persisted["failure_digest"]["stdout_excerpt"], "")
            self.assertEqual(
                persisted["failure_digest"]["excerpt_capture"],
                "deferred_to_output_read",
            )
            self.assertEqual(drain_calls, [None])
            self.assertEqual(er._scheduler_snapshot()["last_tick_reconcile_errors"], 0)

    def test_mark_supervision_lost_is_filesystem_independent(self) -> None:
        job = _job_record()
        writes: list[ExecutionJobRecord] = []

        with patch.object(
            er,
            "_job_failure_excerpt",
            side_effect=AssertionError("scheduler transition must not read output"),
        ), patch.object(
            er, "_write_job", side_effect=lambda _project, _job_id, record: writes.append(record)
        ):
            result = er._mark_supervision_lost("p1", "poison", job)

        self.assertEqual(result.status, "FAILED")
        self.assertEqual(result.stage, "supervision_lost")
        self.assertEqual(len(writes), 1)
        digest = result.failure_digest.to_dict()
        self.assertEqual(digest["stderr_excerpt"], "")
        self.assertEqual(digest["stdout_excerpt"], "")
        self.assertEqual(digest["excerpt_capture"], "deferred_to_output_read")

    def test_one_reconcile_error_isolated_and_drain_still_runs(self) -> None:
        paths = [Path("bad.json"), Path("good.json")]
        bad = SimpleNamespace(job_id="bad", project_id="p1")
        good = SimpleNamespace(job_id="good", project_id="p1")
        seen: list[str] = []
        drain_calls: list[str | None] = []

        def reconcile(job):
            seen.append(job.job_id)
            if job.job_id == "bad":
                raise PermissionError("poison path")

        with patch.object(er, "_iter_job_files", return_value=iter(paths)), patch.object(
            er,
            "_load_job_file",
            side_effect=[(bad, None), (good, None)],
        ), patch.object(er, "_reconcile_job_locked", side_effect=reconcile), patch.object(
            er, "_drain_queue", side_effect=lambda project_id=None, **_: drain_calls.append(project_id) or []
        ):
            er._scheduler_tick()

        self.assertEqual(seen, ["bad", "good"])
        self.assertEqual(drain_calls, [None])
        telemetry = er._scheduler_snapshot()
        self.assertEqual(telemetry["jobs_reconcile_errors"], 1)
        self.assertEqual(telemetry["last_tick_reconcile_errors"], 1)
        self.assertIn("bad.json: PermissionError: poison path", telemetry["last_reconcile_error"])
        self.assertIsNotNone(telemetry["last_reconcile_error_at"])
        self.assertLessEqual(len(telemetry["last_reconcile_error"]), 500)

    def test_clean_tick_resets_current_error_count_but_preserves_history(self) -> None:
        bad = SimpleNamespace(job_id="bad", project_id="p1")
        with patch.object(er, "_iter_job_files", return_value=iter([Path("bad.json")])), patch.object(
            er, "_load_job_file", return_value=(bad, None)
        ), patch.object(
            er, "_reconcile_job_locked", side_effect=RuntimeError("first tick fails")
        ), patch.object(er, "_drain_queue", return_value=[]):
            er._scheduler_tick()

        first = er._scheduler_snapshot()
        self.assertEqual(first["last_tick_reconcile_errors"], 1)
        historical_error = first["last_reconcile_error"]

        with patch.object(er, "_iter_job_files", return_value=iter(())), patch.object(
            er, "_drain_queue", return_value=[]
        ):
            er._scheduler_tick()

        second = er._scheduler_snapshot()
        self.assertEqual(second["last_tick_reconcile_errors"], 0)
        self.assertEqual(second["jobs_reconcile_errors"], 1)
        self.assertEqual(second["last_reconcile_error"], historical_error)

    def test_readiness_degrades_only_for_current_tick_reconcile_errors(self) -> None:
        global_snapshot = GlobalExecutionSnapshot(
            running=0,
            queued=0,
            global_limit=8,
            global_queue_limit=0,
            oldest_queued_age_seconds=None,
        )
        with patch.object(
            er, "_readiness_scan_jobs", return_value=({}, [], [], None)
        ), patch.object(
            er, "_readiness_global_snapshot", return_value=global_snapshot
        ), patch.object(er, "_SCHEDULER_THREAD", None):
            er._scheduler_stat_set("last_reconcile_error", "historical")
            er._scheduler_stat_set("last_tick_reconcile_errors", 1)
            self.assertEqual(er.execution_readiness()["status"], "degraded")

            er._scheduler_stat_set("last_tick_reconcile_errors", 0)
            self.assertEqual(er.execution_readiness()["status"], "online")
            self.assertEqual(
                er.execution_readiness()["scheduler_telemetry"]["last_reconcile_error"],
                "historical",
            )


if __name__ == "__main__":
    unittest.main()
