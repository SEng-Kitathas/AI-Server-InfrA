from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

from server_hardening import run_subprocess_envelope


class SubprocessEnvironmentTests(unittest.TestCase):
    def test_explicit_environment_is_passed_without_mutating_parent(self) -> None:
        key = "PCMMAD_TEST_CHILD_ONLY_ENV"
        original = os.environ.get(key)
        child_env = os.environ.copy()
        child_env[key] = "child-value"
        try:
            result = run_subprocess_envelope(
                [sys.executable, "-c", f"import os,sys; sys.stdout.write(os.environ.get('{key}','MISSING'))"],
                cwd=PROJECT_ROOT,
                timeout_seconds=10,
                stdout_max_bytes=4096,
                stderr_max_bytes=4096,
                env=child_env,
            )
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["stdout"], "child-value")
            self.assertEqual(os.environ.get(key), original)
        finally:
            if original is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original


if __name__ == "__main__":
    unittest.main()
