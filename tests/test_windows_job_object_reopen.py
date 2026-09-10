from __future__ import annotations

import os
import subprocess
import sys
import unittest
import uuid
from pathlib import Path

if os.name == "nt":
    RUNTIME_ROOT = Path(__file__).resolve().parents[1] / "baseline" / "pcmmad_receiver"
    sys.path.insert(0, str(RUNTIME_ROOT.parent))
    import windows_job_object as wjo


@unittest.skipUnless(os.name == "nt", "Windows Job Object test")
class WindowsJobObjectLastHandleScarTests(unittest.TestCase):
    def test_named_job_is_not_reopenable_after_last_handle_closes(self) -> None:
        """Observed Windows scar: naming does not make a Job Object durable by itself."""
        name = f"Local\\PCMMAD_TEST_{uuid.uuid4().hex}"
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        try:
            job = wjo.create_named_job(name)
            wjo.assign_pid(job, proc.pid)
            self.assertIn(proc.pid, wjo.query_process_ids(job))
            job.close()

            # The assigned process can remain alive, but the named object disappears
            # when its last handle closes. This is why the runner must hold an anchor.
            self.assertIsNone(proc.poll())
            with self.assertRaises(FileNotFoundError):
                wjo.open_named_job(name)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)

    def test_create_rejects_existing_named_job_instead_of_hijacking_it(self) -> None:
        name = f"Local\\PCMMAD_TEST_{uuid.uuid4().hex}"
        first = wjo.create_named_job(name)
        try:
            with self.assertRaises(FileExistsError):
                wjo.create_named_job(name)
        finally:
            first.close()


if __name__ == "__main__":
    unittest.main()
