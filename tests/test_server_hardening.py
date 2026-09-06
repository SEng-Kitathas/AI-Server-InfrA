"""
Arrange: set up focused fixtures.
Act: exercise the target behavior.
Assert: verify the expected contract.
Regression tests for server hardening primitives and bounded execution envelopes."""

from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "baseline" / "pcmmad_receiver"))

from server_hardening import (
    command_preflight,
    inspect_zip_safety,
    read_text_window,
    run_subprocess_envelope,
    safe_extract_zip,
    safe_json_dumps,
    safe_project_cwd,
    tolerant_rglob,
    write_json_report_atomic,
)


class ServerHardeningTests(unittest.TestCase):
    def test_safe_json_dumps_stringifies_non_string_keys(self) -> None:
        text = safe_json_dumps({1: Path("x/y")})
        self.assertIn('"1"', text)
        self.assertIn("x/y", text)

    def test_safe_project_cwd_rejects_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(safe_project_cwd(root, "."), root.resolve())
            with self.assertRaises(ValueError):
                safe_project_cwd(root, "..")

    def test_tolerant_rglob_returns_files_and_error_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("alpha", encoding="utf-8")
            result = tolerant_rglob(root)
            self.assertEqual(len(result["files"]), 1)
            self.assertIn("errors", result)

    def test_safe_extract_zip_rejects_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            zpath = root / "bad.zip"
            with zipfile.ZipFile(zpath, "w") as archive:
                archive.writestr("../evil.txt", "nope")
            safety = inspect_zip_safety(zpath)
            self.assertFalse(safety["ok"])
            with self.assertRaises(ValueError):
                safe_extract_zip(zpath, root / "out")


    def test_safe_extract_zip_rejects_windows_and_special_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cases = {
                "backslash": ("..\\evil.txt", 0),
                "drive": ("C:\\evil.txt", 0),
                "unc": ("\\\\server\\share\\evil.txt", 0),
                "symlink": ("link", 0o120777 << 16),
            }
            for label, (name, attrs) in cases.items():
                zpath = root / f"{label}.zip"
                with zipfile.ZipFile(zpath, "w") as archive:
                    info = zipfile.ZipInfo(name)
                    info.external_attr = attrs
                    archive.writestr(info, "nope")
                with self.subTest(label=label):
                    self.assertFalse(inspect_zip_safety(zpath)["ok"])
                    with self.assertRaises(ValueError):
                        safe_extract_zip(zpath, root / f"out-{label}")

    def test_safe_extract_zip_writes_only_selected_regular_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            zpath = root / "good.zip"
            with zipfile.ZipFile(zpath, "w") as archive:
                archive.writestr("nested/a.txt", "alpha")
                archive.writestr("nested/b.txt", "beta")
            result = safe_extract_zip(
                zpath,
                root / "out",
                selected_entries=["nested/a.txt"],
            )
            self.assertEqual(result["extracted"], ["nested/a.txt"])
            self.assertEqual((root / "out" / "nested" / "a.txt").read_text(), "alpha")
            self.assertFalse((root / "out" / "nested" / "b.txt").exists())

    def test_write_json_report_atomic_and_text_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "report.json"
            result = write_json_report_atomic(report, {"path": Path("a/b"), "value": 1})
            self.assertTrue(result["ok"])
            window = read_text_window(report, max_bytes=12, mode="head")
            self.assertTrue(window["truncated"])
            self.assertGreater(window["returned_bytes"], 0)

    def test_command_preflight_and_subprocess_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good = command_preflight(root, ["python", "--version"], ".")
            self.assertTrue(good["ok"])
            bad = command_preflight(root, ["python"], "..")
            self.assertFalse(bad["ok"])
            envelope = run_subprocess_envelope(
                ["python", "-c", 'print("ok")'],
                cwd=root,
                timeout_seconds=5,
                stdout_max_bytes=20,
                stderr_max_bytes=20,
            )
            self.assertTrue(envelope["ok"])
            self.assertIn("ok", envelope["stdout"])


if __name__ == "__main__":
    unittest.main()
