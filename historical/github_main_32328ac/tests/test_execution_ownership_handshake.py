from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import execution_routes as er

if os.name == "nt":
    import windows_job_object as wjo


@unittest.skipUnless(os.name == "nt", "Windows ownership-handshake tests")
class ExecutionOwnershipHandshakeTests(unittest.TestCase):
    def test_scheduler_handshake_failure_cannot_start_user_command(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td).resolve()
            projects = base / "projects"
            project = projects / "alpha"
            project.mkdir(parents=True)
            marker = base / "USER_COMMAND_STARTED.txt"
            code = f"from pathlib import Path; Path(r'{marker}').write_text('started')"

            with patch.object(er, "PROJECTS_ROOT", projects), patch.object(
                er, "get_project_root", lambda project_id: projects / project_id
            ), patch.object(er, "_ensure_scheduler_started", return_value=None), patch.object(
                er, "_wait_for_ownership_ready", side_effect=RuntimeError("FORCED_HANDSHAKE_FAILURE")
            ):
                er._RUNNING.clear()
                with self.assertRaises(er.ExecutionRequestError):
                    er.submit_execution_job(
                        {
                            "project_id": "alpha",
                            "command": [sys.executable],
                            "args": ["-c", code],
                            "cwd": ".",
                            "timeout_seconds": 5,
                        }
                    )
                time.sleep(0.2)
                self.assertFalse(marker.exists(), "user command started before ownership release")

    def _standalone_worker(self, base: Path, *, marker: Path):
        name = f"Local\\PCMMAD_TEST_{uuid.uuid4().hex}"
        token = uuid.uuid4().hex
        job = wjo.create_named_job(name)
        wjo.set_kill_on_close(job, True)
        req = {
            "job_id": "handshake-test",
            "worker_token": token,
            "command": [sys.executable, "-c", f"from pathlib import Path; Path(r'{marker}').write_text('started'); import time; time.sleep(10)"],
            "cwd": str(base),
            "env_allowlist": {},
            "stdout_path": str(base / "stdout.log"),
            "stderr_path": str(base / "stderr.log"),
            "heartbeat_path": str(base / "heartbeat.json"),
            "completion_path": str(base / "completion.json"),
            "cancel_path": str(base / "cancel.json"),
            "ownership_release_path": str(base / "release.json"),
            "job_object_name": name,
            "timeout_seconds": 10,
        }
        request_path = base / "request.json"
        request_path.write_text(json.dumps(req), encoding="utf-8")
        proc = subprocess.Popen([sys.executable, str(RUNTIME_ROOT / "execution_worker.py"), str(request_path)])
        wjo.assign_pid(job, proc.pid)
        deadline = time.time() + 5
        heartbeat = None
        while time.time() < deadline:
            hp = base / "heartbeat.json"
            if hp.exists():
                try:
                    heartbeat = json.loads(hp.read_text(encoding="utf-8"))
                except Exception:
                    heartbeat = None
                if heartbeat and heartbeat.get("state") == "OWNERSHIP_READY":
                    break
            if proc.poll() is not None:
                break
            time.sleep(0.03)
        self.assertIsNotNone(heartbeat)
        self.assertEqual(heartbeat.get("state"), "OWNERSHIP_READY")
        return job, proc, req

    def test_wrong_token_release_does_not_authorize_spawn(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td).resolve()
            marker = base / "started.txt"
            job, proc, req = self._standalone_worker(base, marker=marker)
            try:
                (base / "release.json").write_text(
                    json.dumps({"job_id": req["job_id"], "worker_token": "WRONG", "permit_spawn": True}),
                    encoding="utf-8",
                )
                time.sleep(0.4)
                self.assertFalse(marker.exists(), "forged release authorized user command")
            finally:
                try:
                    wjo.terminate(job, 9)
                except Exception:
                    pass
                job.close()
                try:
                    proc.wait(timeout=3)
                except Exception:
                    proc.kill()

    def test_cancel_before_release_terminates_without_user_command(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td).resolve()
            marker = base / "started.txt"
            job, proc, req = self._standalone_worker(base, marker=marker)
            try:
                (base / "cancel.json").write_text("{}", encoding="utf-8")
                deadline = time.time() + 5
                completion = None
                while time.time() < deadline:
                    cp = base / "completion.json"
                    if cp.exists():
                        completion = json.loads(cp.read_text(encoding="utf-8"))
                        break
                    time.sleep(0.03)
                self.assertIsNotNone(completion)
                self.assertEqual(completion.get("state"), "TERMINATED")
                self.assertEqual(completion.get("reason"), "CANCEL_BEFORE_SPAWN")
                self.assertFalse(marker.exists(), "cancel-before-release still started user command")
            finally:
                try:
                    job.close()
                except Exception:
                    pass
                if proc.poll() is None:
                    proc.kill()
                try:
                    proc.wait(timeout=3)
                except Exception:
                    pass


if __name__ == "__main__":
    unittest.main()
