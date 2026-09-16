"""
Arrange: set up focused fixtures.
Act: exercise the target behavior.
Assert: verify the expected contract.
Regression tests for unbounded timeout and output policy behavior."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "baseline" / "pcmmad_receiver"))

from execution_routes import _request_optional_positive_int
from server_hardening import read_text_window, run_subprocess_envelope


class UnboundedPolicyTests(unittest.TestCase):
    def test_request_optional_positive_int_treats_zero_and_negative_one_as_unbounded(self) -> None:
        self.assertIsNone(_request_optional_positive_int(0, 123, minimum=1, maximum=None))
        self.assertIsNone(_request_optional_positive_int(-1, 123, minimum=1, maximum=None))
        self.assertIsNone(_request_optional_positive_int(None, None, minimum=1, maximum=None))

    def test_read_text_window_unbounded_modes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "large.txt"
            payload = "abc\n" * 1000
            path.write_text(payload, encoding="utf-8")
            stored = path.read_text(encoding="utf-8")
            for value in (None, 0, -1):
                window = read_text_window(path, max_bytes=value, mode="tail")
                self.assertFalse(window["truncated"])
                self.assertGreaterEqual(len(window["content"]), len(stored))
                self.assertEqual(window["content"].replace("\r\n", "\n"), stored)
                self.assertTrue(window["content"].startswith("abc"))
                self.assertTrue(
                    window["content"].endswith("abc\n") or window["content"].endswith("abc\r\n")
                )

    def test_subprocess_envelope_unbounded_output_and_no_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_subprocess_envelope(
                ["python", "-c", 'print("x" * 2000)'],
                cwd=Path(tmp),
                timeout_seconds=None,
                stdout_max_bytes=None,
                stderr_max_bytes=None,
            )
            self.assertTrue(result["ok"])
            self.assertFalse(result["stdout_truncated"])
            self.assertGreater(len(result["stdout"]), 1900)


if __name__ == "__main__":
    unittest.main()
