from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

import execution_routes as er
from control_plane_models import ExecutionJobRecord
from api_wire_execution import ExecutionReplayRequest


def _record(job_id: str, status: str, project_id: str = "p1") -> ExecutionJobRecord:
    return ExecutionJobRecord.from_dict(
        {
            "job_id": job_id,
            "project_id": project_id,
            "status": status,
            "pid": 0,
            "command": ["noop"],
            "stdout_path": "",
            "stderr_path": "",
            "created_at": "2026-09-06T00:00:00+00:00",
            "submitted_at": "2026-09-06T00:00:00+00:00",
        }
    )


@contextmanager
def _store_root():
    with tempfile.TemporaryDirectory(prefix="pcmmad-a035-") as td:
        root = Path(td)
        projects = root / "projects"
        projects.mkdir(parents=True)
        with patch.object(er, "PROJECTS_ROOT", projects), patch.object(
            er, "get_project_root", side_effect=lambda project_id: projects / project_id
        ), patch.object(er, "_EXECUTION_STORE_LAYOUT_READY_ROOTS", set()):
            yield projects


def _legacy_write(projects: Path, job: ExecutionJobRecord, *, filename: str | None = None) -> Path:
    root = projects / job.project_id / "system" / "logs" / "execution"
    root.mkdir(parents=True, exist_ok=True)
    path = root / (filename or f"{job.job_id}.json")
    path.write_text(json.dumps(job.to_dict()), encoding="utf-8")
    return path


class ExecutionActiveTerminalPartitionTests(unittest.TestCase):
    def test_legacy_migration_partitions_jobs_and_preserves_idempotency_root(self) -> None:
        with _store_root() as projects:
            queued = _legacy_write(projects, _record("job-q", "QUEUED"))
            done = _legacy_write(projects, _record("job-d", "COMPLETED"))
            root = queued.parent
            idempotency = root / "idempotency.json"
            idempotency.write_text('{"keys":{}}', encoding="utf-8")

            er._ensure_execution_store_layout()

            self.assertFalse(queued.exists())
            self.assertFalse(done.exists())
            self.assertTrue((root / "active" / "job-q.json").is_file())
            self.assertTrue((root / "terminal" / "job-d.json").is_file())
            self.assertTrue(idempotency.is_file())
            self.assertEqual(er._read_job("p1", "job-q").status, "QUEUED")
            self.assertEqual(er._read_job("p1", "job-d").status, "COMPLETED")

    def test_corrupt_legacy_job_remains_hot_visible_after_migration(self) -> None:
        with _store_root() as projects:
            root = projects / "p1" / "system" / "logs" / "execution"
            root.mkdir(parents=True)
            bad = root / "broken.json"
            bad.write_text("{ definitely not json", encoding="utf-8")

            er._ensure_execution_store_layout()

            moved = root / "active" / "broken.json"
            self.assertTrue(moved.is_file())
            self.assertFalse(bad.exists())
            self.assertIn(moved, list(er._iter_job_files("p1")))
            job, error = er._load_job_file(moved)
            self.assertIsNone(job)
            self.assertIsNotNone(error)

    def test_terminal_transition_atomically_moves_active_record(self) -> None:
        with _store_root():
            job = _record("job-a", "QUEUED")
            er._write_job("p1", job.job_id, job)
            active = er._active_job_path("p1", job.job_id)
            terminal = er._terminal_job_path("p1", job.job_id)
            self.assertTrue(active.is_file())
            self.assertFalse(terminal.exists())

            job.status = "COMPLETED"
            replace_calls: list[tuple[Path, Path]] = []
            real_replace = er.os.replace

            def observed_replace(src, dst):
                replace_calls.append((Path(src), Path(dst)))
                return real_replace(src, dst)

            with patch.object(er.os, "replace", side_effect=observed_replace):
                er._write_job("p1", job.job_id, job)

            self.assertFalse(active.exists())
            self.assertTrue(terminal.is_file())
            self.assertIn((active, terminal), replace_calls)
            self.assertEqual(er._read_job("p1", job.job_id).status, "COMPLETED")

    def test_startup_repair_moves_terminal_status_stranded_in_active(self) -> None:
        with _store_root() as projects:
            root = projects / "p1" / "system" / "logs" / "execution"
            active = root / "active"
            active.mkdir(parents=True)
            stranded = active / "job-stranded.json"
            stranded.write_text(json.dumps(_record("job-stranded", "FAILED").to_dict()), encoding="utf-8")

            er._ensure_execution_store_layout()

            self.assertFalse(stranded.exists())
            self.assertTrue((root / "terminal" / "job-stranded.json").is_file())

    def test_conflicting_legacy_and_partition_record_refuses_to_guess(self) -> None:
        with _store_root() as projects:
            root = projects / "p1" / "system" / "logs" / "execution"
            active = root / "active"
            active.mkdir(parents=True)
            active_job = _record("job-x", "QUEUED")
            (active / "job-x.json").write_text(json.dumps(active_job.to_dict()), encoding="utf-8")
            conflicting = _record("job-x", "RUNNING")
            _legacy_write(projects, conflicting)

            with self.assertRaisesRegex(RuntimeError, "migration conflict"):
                er._ensure_execution_store_layout()

    def test_history_iterator_sees_terminal_but_hot_iterator_does_not(self) -> None:
        with _store_root():
            active = _record("job-active", "QUEUED")
            terminal = _record("job-terminal", "COMPLETED")
            er._write_job("p1", active.job_id, active)
            er._write_job("p1", terminal.job_id, terminal)

            hot = {path.name for path in er._iter_job_files("p1")}
            history = {path.name for path in er._iter_all_job_files("p1")}

            self.assertEqual(hot, {"job-active.json"})
            self.assertEqual(history, {"job-active.json", "job-terminal.json"})

    def test_direct_terminal_read_preserves_replay_source_compatibility(self) -> None:
        with _store_root():
            prior = _record("job-prior", "COMPLETED")
            prior.command = ["python", "-c", "print('ok')"]
            er._write_job("p1", prior.job_id, prior)
            captured = {}

            def fake_submit(payload, **kwargs):
                captured["payload"] = payload
                captured["kwargs"] = kwargs
                return _record("job-replay", "QUEUED")

            replay = ExecutionReplayRequest(project_id="p1", job_id="job-prior")
            with patch.object(er, "submit_execution_job", side_effect=fake_submit):
                response = er._replay_payload(replay)

            self.assertTrue(response["ok"])
            self.assertEqual(captured["payload"]["command"], prior.command)
            self.assertEqual(captured["kwargs"]["replay_of"], "job-prior")

    def test_hot_scan_cost_is_independent_of_terminal_history_count(self) -> None:
        with _store_root():
            for i in range(500):
                er._write_job("p1", f"job-h{i}", _record(f"job-h{i}", "COMPLETED"))
            for i in range(8):
                er._write_job("p1", f"job-r{i}", _record(f"job-r{i}", "RUNNING"))
            for i in range(50):
                er._write_job("p1", f"job-q{i}", _record(f"job-q{i}", "QUEUED"))

            loads = 0
            real_load = er._load_job_file

            def counted(path):
                nonlocal loads
                loads += 1
                return real_load(path)

            with patch.object(er, "_load_job_file", side_effect=counted):
                queued = er._queued_job_candidates("p1")
            self.assertEqual(len(queued), 50)
            self.assertEqual(loads, 58)

            loads = 0
            with patch.object(er, "_load_job_file", side_effect=counted), patch.object(
                er, "_pid_alive", return_value=True
            ), patch.object(er, "_RUNNING", {}):
                total, per_project = er._running_census()
            self.assertEqual(total, 8)
            self.assertEqual(per_project, {"p1": 8})
            self.assertEqual(loads, 58)

    def test_late_mounted_legacy_project_is_migrated_on_next_layout_check(self) -> None:
        with _store_root() as projects:
            _legacy_write(projects, _record("job-p1", "QUEUED", project_id="p1"))
            er._ensure_execution_store_layout()
            p1_root = projects / "p1" / "system" / "logs" / "execution"
            self.assertTrue((p1_root / "active" / "job-p1.json").is_file())

            _legacy_write(projects, _record("job-p2", "RUNNING", project_id="p2"))
            p2_root = projects / "p2" / "system" / "logs" / "execution"
            self.assertTrue((p2_root / "job-p2.json").is_file())

            er._ensure_execution_store_layout()

            self.assertFalse((p2_root / "job-p2.json").exists())
            self.assertTrue((p2_root / "active" / "job-p2.json").is_file())
            self.assertEqual(
                len(er._EXECUTION_STORE_LAYOUT_READY_ROOTS),
                2,
            )

    def test_all_history_iterator_excludes_idempotency_ledger(self) -> None:
        with _store_root():
            root = er._jobs_dir("p1")
            (root / "idempotency.json").write_text('{"keys":{}}', encoding="utf-8")
            er._write_job("p1", "job-d", _record("job-d", "COMPLETED"))
            self.assertEqual(
                {p.name for p in er._iter_all_job_files("p1")},
                {"job-d.json"},
            )


if __name__ == "__main__":
    unittest.main()
