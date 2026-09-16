from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import context_engine


class ContextBoundedMaterializationTests(unittest.TestCase):
    def test_prefix_read_does_not_use_whole_file_read_text(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "large.txt"
            target.write_bytes((b"0123456789\n" * 200000))
            with patch.object(Path, "read_text", side_effect=AssertionError("whole-file read_text forbidden")):
                result = context_engine.read_file(
                    context_engine.FileReadRequest(
                        path="large.txt",
                        base_root=str(root),
                        max_bytes=4096,
                    )
                )
        payload = result.to_dict()
        self.assertLessEqual(len(payload["content"].encode("utf-8")), 4096)
        self.assertGreater(payload["file"]["size_bytes"], 4096)

    def test_line_window_does_not_use_whole_file_read_text(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "window.txt"
            target.write_text("\n".join(f"line-{i}" for i in range(1, 2000)), encoding="utf-8")
            with patch.object(Path, "read_text", side_effect=AssertionError("whole-file read_text forbidden")):
                result = context_engine.read_file(
                    context_engine.FileReadRequest(
                        path="window.txt",
                        base_root=str(root),
                        start_line=1500,
                        end_line=1502,
                        max_bytes=4096,
                    )
                )
        payload = result.to_dict()
        self.assertEqual(payload["content"], "line-1500\nline-1501\nline-1502")
        self.assertEqual(payload["slice"]["start_line"], 1500)
        self.assertEqual(payload["slice"]["end_line"], 1502)

    def test_huge_preceding_line_is_skipped_without_entering_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "huge-line.txt"
            target.write_bytes((b"x" * 300000) + b"\nTARGET\nAFTER\n")
            result = context_engine.read_file(
                context_engine.FileReadRequest(
                    path="huge-line.txt",
                    base_root=str(root),
                    start_line=2,
                    end_line=3,
                    max_bytes=1024,
                )
            )
        self.assertEqual(result.to_dict()["content"], "TARGET\nAFTER")

    def test_explicit_end_line_is_capped_by_max_read_lines(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "many.txt"
            count = context_engine.MAX_READ_LINES + 100
            target.write_text("\n".join(f"L{i}" for i in range(1, count + 1)), encoding="utf-8")
            result = context_engine.read_file(
                context_engine.FileReadRequest(
                    path="many.txt",
                    base_root=str(root),
                    start_line=1,
                    end_line=999999999,
                    max_bytes=context_engine.MAX_READ_BYTES,
                )
            )
        payload = result.to_dict()
        self.assertLessEqual(payload["slice"]["end_line"], context_engine.MAX_READ_LINES)
        self.assertLessEqual(len(payload["content"].splitlines()), context_engine.MAX_READ_LINES)


if __name__ == "__main__":
    unittest.main()
