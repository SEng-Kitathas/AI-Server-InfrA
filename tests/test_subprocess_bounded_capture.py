from __future__ import annotations

import sys
import unittest
from unittest import mock
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

import server_hardening as sh


class SubprocessBoundedCaptureTests(unittest.TestCase):
    def test_large_stdout_and_stderr_are_return_bounded_and_temp_capture_is_cleaned(self) -> None:
        created: list[Path] = []
        real_mkdtemp = sh.tempfile.mkdtemp

        def tracked_mkdtemp(*args, **kwargs):
            path = Path(real_mkdtemp(*args, **kwargs))
            created.append(path)
            return str(path)

        with mock.patch.object(sh.tempfile, "mkdtemp", side_effect=tracked_mkdtemp):
            result = sh.run_subprocess_envelope(
                [
                    sys.executable,
                    "-c",
                    "import sys; sys.stdout.write('x'*2000000); sys.stderr.write('y'*1500000)",
                ],
                cwd=PROJECT_ROOT,
                timeout_seconds=30,
                stdout_max_bytes=4096,
                stderr_max_bytes=3072,
            )
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "COMPLETED")
        self.assertLessEqual(len(result["stdout"].encode("utf-8")), 4096)
        self.assertLessEqual(len(result["stderr"].encode("utf-8")), 3072)
        self.assertTrue(result["stdout_truncated"])
        self.assertTrue(result["stderr_truncated"])
        self.assertEqual(len(created), 1)
        self.assertFalse(created[0].exists())

    def test_nonzero_exit_semantics_are_preserved(self) -> None:
        result = sh.run_subprocess_envelope(
            [sys.executable, "-c", "import sys; print('bad'); sys.exit(7)"],
            cwd=PROJECT_ROOT,
            timeout_seconds=10,
            stdout_max_bytes=1024,
            stderr_max_bytes=1024,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["return_code"], 7)
        self.assertIn("bad", result["stdout"])

    def test_timeout_semantics_are_preserved_and_output_remains_bounded(self) -> None:
        result = sh.run_subprocess_envelope(
            [
                sys.executable,
                "-c",
                "import sys,time; sys.stdout.write('z'*500000); sys.stdout.flush(); time.sleep(5)",
            ],
            cwd=PROJECT_ROOT,
            timeout_seconds=1,
            stdout_max_bytes=2048,
            stderr_max_bytes=2048,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "TIMEOUT")
        self.assertIsNone(result["return_code"])
        self.assertTrue(result["stdout_truncated"])
        self.assertLessEqual(len(result["stdout"].encode("utf-8")), 2048)
        self.assertIn("timeout after 1s", result["error"] or "")


if __name__ == "__main__":
    unittest.main()
