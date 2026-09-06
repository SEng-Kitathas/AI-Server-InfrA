from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

import execution_routes as er
from control_plane_models import ExecutionJobRecord
from tools.hostile.execution_lifecycle_sim import run_pid_reuse_probe


def _legacy_job(
    job_id: str = "legacy",
    *,
    pid: int = 4242,
    creation_time: int | None = 111,
) -> ExecutionJobRecord:
    return ExecutionJobRecord.from_dict(
        {
            "job_id": job_id,
            "project_id": "p1",
            "status": "RUNNING",
            "stage": "runtime",
            "pid": pid,
            "pid_creation_time_100ns": creation_time,
            "worker_token": None,
            "command": ["legacy"],
            "stdout_path": "",
            "stderr_path": "",
            "created_at": "2026-09-06T00:00:00+00:00",
            "submitted_at": "2026-09-06T00:00:00+00:00",
            "started_at": "2026-09-06T00:00:00+00:00",
            "supervision_state": "legacy_process",
        }
    )


class ExecutionLegacyPidIdentityTests(unittest.TestCase):
    def test_job_record_round_trips_legacy_creation_time_witness(self) -> None:
        original = _legacy_job(creation_time=987654321)
        payload = original.to_dict()
        self.assertEqual(payload["pid_creation_time_100ns"], 987654321)
        restored = ExecutionJobRecord.from_dict(payload)
        self.assertEqual(restored.pid_creation_time_100ns, 987654321)

    def test_identity_classifier_distinguishes_same_mismatch_dead_and_unverifiable(self) -> None:
        job = _legacy_job(creation_time=111)
        with patch.object(er, "_pid_alive", return_value=True), patch.object(
            er, "_process_creation_time_100ns", return_value=111
        ):
            self.assertEqual(
                er._legacy_process_identity_state(job),
                (er.LEGACY_PROCESS_IDENTITY_SAME, 111),
            )

        with patch.object(er, "_pid_alive", return_value=True), patch.object(
            er, "_process_creation_time_100ns", return_value=222
        ):
            self.assertEqual(
                er._legacy_process_identity_state(job),
                (er.LEGACY_PROCESS_IDENTITY_MISMATCH, 222),
            )

        with patch.object(er, "_pid_alive", return_value=False):
            self.assertEqual(
                er._legacy_process_identity_state(job),
                (er.LEGACY_PROCESS_IDENTITY_DEAD, None),
            )

        no_witness = _legacy_job(creation_time=None)
        with patch.object(er, "_pid_alive", return_value=True), patch.object(
            er, "_process_creation_time_100ns", return_value=222
        ):
            self.assertEqual(
                er._legacy_process_identity_state(no_witness),
                (er.LEGACY_PROCESS_IDENTITY_UNVERIFIABLE, 222),
            )

        with patch.object(er, "_pid_alive", return_value=True), patch.object(
            er, "_process_creation_time_100ns", return_value=None
        ):
            self.assertEqual(
                er._legacy_process_identity_state(job),
                (er.LEGACY_PROCESS_IDENTITY_UNVERIFIABLE, None),
            )

    def test_recycled_pid_moves_legacy_record_terminal_with_identity_receipt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-a039-") as td:
            projects = Path(td) / "projects"
            job = _legacy_job("recycled", creation_time=111)
            with patch.object(
                er, "get_project_root", side_effect=lambda pid: projects / pid
            ):
                er._write_job("p1", job.job_id, job)
                active = er._active_job_path("p1", job.job_id)
                terminal = er._terminal_job_path("p1", job.job_id)
                self.assertTrue(active.is_file())

                with patch.object(er, "_pid_alive", return_value=True), patch.object(
                    er, "_process_creation_time_100ns", return_value=222
                ):
                    er._reconcile_job_locked(job)

                self.assertFalse(active.exists())
                self.assertTrue(terminal.is_file())
                persisted = json.loads(terminal.read_text(encoding="utf-8"))

        self.assertEqual(persisted["status"], "FAILED")
        self.assertEqual(persisted["stage"], "supervision_lost")
        digest = persisted["failure_digest"]
        self.assertEqual(digest["failure_kind"], "SUPERVISION_LOST")
        self.assertEqual(
            digest["legacy_process_identity_state"],
            er.LEGACY_PROCESS_IDENTITY_MISMATCH,
        )
        self.assertEqual(digest["expected_creation_time_100ns"], 111)
        self.assertEqual(digest["observed_creation_time_100ns"], 222)

    def test_missing_historical_witness_fails_safe_without_tofu_adoption(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-a039-nowitness-") as td:
            projects = Path(td) / "projects"
            job = _legacy_job("no-witness", creation_time=None)
            with patch.object(
                er, "get_project_root", side_effect=lambda pid: projects / pid
            ):
                er._write_job("p1", job.job_id, job)
                with patch.object(er, "_pid_alive", return_value=True), patch.object(
                    er, "_process_creation_time_100ns", return_value=333
                ):
                    er._reconcile_job_locked(job)
                terminal = er._terminal_job_path("p1", job.job_id)
                persisted = json.loads(terminal.read_text(encoding="utf-8"))

        self.assertEqual(persisted["status"], "FAILED")
        self.assertIsNone(persisted["pid_creation_time_100ns"])
        digest = persisted["failure_digest"]
        self.assertEqual(
            digest["legacy_process_identity_state"],
            er.LEGACY_PROCESS_IDENTITY_UNVERIFIABLE,
        )
        self.assertIsNone(digest["expected_creation_time_100ns"])
        self.assertEqual(digest["observed_creation_time_100ns"], 333)

    def test_effective_running_count_excludes_mismatch_but_conservatively_counts_unverifiable(self) -> None:
        matching = _legacy_job("same", creation_time=100)
        mismatch = _legacy_job("mismatch", creation_time=200)
        no_witness = _legacy_job("unknown", creation_time=None)
        rows = [
            (Path("same.json"), matching),
            (Path("mismatch.json"), mismatch),
            (Path("unknown.json"), no_witness),
        ]
        observed = {4242: 100}

        def fake_load(path: Path):
            for candidate, job in rows:
                if candidate == path:
                    return job, None
            raise AssertionError(path)

        def fake_creation(pid: int | None):
            if pid is None:
                return None
            job_by_id = {
                "same": 100,
                "mismatch": 201,
                "unknown": 300,
            }
            # The caller has only a PID, and these fixtures share it deliberately.
            # Return values are selected through the currently loaded job below instead.
            return observed.get(int(pid))

        # Use distinct PIDs here so observed creation-time can vary by record.
        matching.pid = 1001
        mismatch.pid = 1002
        no_witness.pid = 1003
        observed = {1001: 100, 1002: 201, 1003: 300}

        with patch.object(er, "_RUNNING", {}), patch.object(
            er, "_iter_job_files", return_value=iter([row[0] for row in rows])
        ), patch.object(er, "_load_job_file", side_effect=fake_load), patch.object(
            er, "_pid_alive", return_value=True
        ), patch.object(er, "_process_creation_time_100ns", side_effect=fake_creation):
            self.assertEqual(er._effective_running_count(None), 2)

    def test_same_process_legacy_record_remains_running_but_is_marked_unsupervised(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-a039-same-") as td:
            projects = Path(td) / "projects"
            job = _legacy_job("same-process", creation_time=444)
            with patch.object(
                er, "get_project_root", side_effect=lambda pid: projects / pid
            ):
                er._write_job("p1", job.job_id, job)
                with patch.object(er, "_pid_alive", return_value=True), patch.object(
                    er, "_process_creation_time_100ns", return_value=444
                ):
                    er._reconcile_job_locked(job)
                persisted = er._read_job("p1", job.job_id)
                self.assertTrue(er._active_job_path("p1", job.job_id).is_file())
                self.assertFalse(er._terminal_job_path("p1", job.job_id).exists())

        self.assertEqual(persisted.status, "RUNNING")
        self.assertEqual(persisted.supervision_state, "unsupervised")
        self.assertIsNone(persisted.failure_digest)

    def test_readiness_flags_invalid_legacy_identity_not_same_process(self) -> None:
        same = _legacy_job("same", pid=2001, creation_time=101)
        mismatch = _legacy_job("mismatch", pid=2002, creation_time=202)
        unknown = _legacy_job("unknown", pid=2003, creation_time=None)
        rows = {
            Path("same.json"): same,
            Path("mismatch.json"): mismatch,
            Path("unknown.json"): unknown,
        }
        observed = {2001: 101, 2002: 999, 2003: 303}

        with patch.object(er, "_iter_job_files", return_value=iter(rows)), patch.object(
            er, "_load_job_file", side_effect=lambda path: (rows[path], None)
        ), patch.object(er, "_pid_alive", return_value=True), patch.object(
            er, "_process_creation_time_100ns", side_effect=lambda pid: observed[int(pid)]
        ), patch.object(er, "_capacity_snapshot", return_value=object()):
            _per_project, _corrupt, unsupervised, _oldest = er._readiness_scan_jobs()

        self.assertNotIn("same", unsupervised)
        self.assertIn("mismatch", unsupervised)
        self.assertIn("unknown", unsupervised)

    def test_fixed_pid_reuse_probe_preserves_vulnerable_specimen_and_repairs_current(self) -> None:
        vulnerable = run_pid_reuse_probe(legacy_identity_variant="pid_only")
        current = run_pid_reuse_probe(legacy_identity_variant="current")

        self.assertEqual(vulnerable["target_active_after"], "RUNNING")
        self.assertIsNone(vulnerable["target_terminal_after"])
        self.assertIn(vulnerable["target_job_id"], vulnerable["final_state"]["pid_alias_jobs"])

        self.assertIsNone(current["target_active_after"])
        self.assertEqual(current["target_terminal_after"], "FAILED")
        self.assertNotIn(current["target_job_id"], current["final_state"]["pid_alias_jobs"])


if __name__ == "__main__":
    unittest.main()
