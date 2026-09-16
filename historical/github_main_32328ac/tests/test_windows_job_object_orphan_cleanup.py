from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path

if os.name == "nt":
    RUNTIME_ROOT = Path(__file__).resolve().parents[1] / "baseline" / "pcmmad_receiver"
    sys.path.insert(0, str(RUNTIME_ROOT.parent))
    import windows_job_object as wjo


@unittest.skipUnless(os.name == "nt", "Windows Job Object test")
class WindowsJobObjectOrphanCleanupTests(unittest.TestCase):
    def test_runner_crash_with_receiver_absent_kills_descendant(self) -> None:
        name = f"Local\\PCMMAD_TEST_{uuid.uuid4().hex}"
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            ready = td_path / "ready.txt"
            go = td_path / "go.txt"
            child_pid_file = td_path / "child_pid.txt"
            code = (
                "import sys,time,subprocess,pathlib; "
                f"sys.path.insert(0, r'{RUNTIME_ROOT.parent}'); "
                "import windows_job_object as wjo; "
                f"j=wjo.open_named_job(r'{name}', terminate=False); "
                f"pathlib.Path(r'{ready}').write_text('ready'); "
                f"go=pathlib.Path(r'{go}'); "
                "deadline=time.time()+10; "
                "exec(\"while time.time()<deadline and not go.exists():\\n time.sleep(0.02)\"); "
                "c=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); "
                f"pathlib.Path(r'{child_pid_file}').write_text(str(c.pid)); "
                "time.sleep(30)"
            )
            job = wjo.create_named_job(name)
            wjo.set_kill_on_close(job, True)
            runner = subprocess.Popen([sys.executable, "-c", code])
            child_pid = None
            try:
                wjo.assign_pid(job, runner.pid)
                deadline = time.time() + 5
                while time.time() < deadline and not ready.exists():
                    time.sleep(0.05)
                self.assertTrue(ready.exists(), "runner never opened Job Object handle")

                # Runner is now in the job; descendants it creates inherit membership.
                go.write_text("go")
                deadline = time.time() + 5
                while time.time() < deadline and not child_pid_file.exists():
                    time.sleep(0.05)
                self.assertTrue(child_pid_file.exists(), "runner never spawned descendant")
                child_pid = int(child_pid_file.read_text())
                self.assertGreater(wjo.process_creation_time_100ns(child_pid), 0)
                self.assertIn(child_pid, wjo.query_process_ids(job))

                # Simulate receiver crash: runner is now the only Job Object handle owner.
                job.close()
                runner.kill()
                runner.wait(timeout=5)

                deadline = time.time() + 5
                while time.time() < deadline:
                    try:
                        wjo.process_creation_time_100ns(child_pid)
                    except OSError:
                        break
                    time.sleep(0.05)
                else:
                    self.fail(f"descendant PID {child_pid} survived last Job Object handle loss")
            finally:
                try:
                    job.close()
                except Exception:
                    pass
                if runner.poll() is None:
                    runner.kill()
                    runner.wait(timeout=5)
                if child_pid is not None:
                    subprocess.run(["taskkill", "/PID", str(child_pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


if __name__ == "__main__":
    unittest.main()
