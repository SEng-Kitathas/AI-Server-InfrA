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
class WindowsJobObjectAnchorTests(unittest.TestCase):
    def test_runner_held_handle_keeps_named_job_reopenable(self) -> None:
        name = f"Local\\PCMMAD_TEST_{uuid.uuid4().hex}"
        with tempfile.TemporaryDirectory() as td:
            ready = Path(td) / "ready.txt"
            code = (
                "import sys,time; "
                f"sys.path.insert(0, r'{RUNTIME_ROOT.parent}'); "
                "import windows_job_object as wjo; "
                f"j=wjo.open_named_job(r'{name}', terminate=False); "
                f"open(r'{ready}','w').write('ready'); "
                "time.sleep(30)"
            )
            job = wjo.create_named_job(name)
            wjo.set_kill_on_close(job, True)
            proc = subprocess.Popen([sys.executable, "-c", code])
            try:
                wjo.assign_pid(job, proc.pid)
                deadline = time.time() + 5
                while time.time() < deadline and not ready.exists():
                    time.sleep(0.05)
                self.assertTrue(ready.exists(), "runner never opened/anchored named Job Object")

                job.close()
                self.assertIsNone(proc.poll())

                reopened = wjo.open_named_job(name)
                try:
                    self.assertIn(proc.pid, wjo.query_process_ids(reopened))
                    wjo.terminate(reopened, exit_code=9)
                finally:
                    reopened.close()
                proc.wait(timeout=5)
                self.assertIsNotNone(proc.returncode)
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
