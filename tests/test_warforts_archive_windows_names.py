from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baseline" / "pcmmad_receiver"))

import server_hardening as hardening


class WindowsZipNamespaceHostileTests(unittest.TestCase):
    def make_zip(self, names: list[str]) -> Path:
        root = Path(self.temp.name)
        path = root / "hostile.zip"
        with zipfile.ZipFile(path, "w") as zf:
            for i, name in enumerate(names):
                zf.writestr(name, f"payload-{i}")
        return path

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pcmmad-warfort-zip-")

    def tearDown(self):
        self.temp.cleanup()

    def assert_unsafe(self, names: list[str], contains: str | None = None):
        result = hardening.inspect_zip_safety(self.make_zip(names))
        self.assertFalse(result["ok"])
        if contains:
            self.assertTrue(any(contains in row for row in result["unsafe_entries"]), result["unsafe_entries"])

    def test_ntfs_alternate_data_stream_rejected(self):
        self.assert_unsafe(["safe/file.txt:secret"], "alternate data stream")

    def test_reserved_con_device_rejected(self):
        self.assert_unsafe(["safe/CON.txt"], "reserved Windows device")

    def test_reserved_nul_device_rejected(self):
        self.assert_unsafe(["NUL"], "reserved Windows device")

    def test_reserved_com_port_rejected(self):
        self.assert_unsafe(["safe/COM1.log"], "reserved Windows device")

    def test_trailing_dot_component_rejected(self):
        self.assert_unsafe(["safe/name."], "trailing dot/space")

    def test_trailing_space_component_rejected(self):
        self.assert_unsafe(["safe/name "] , "trailing dot/space")

    def test_windows_alias_pair_rejected_even_if_strings_differ(self):
        self.assert_unsafe(["safe/name", "safe/name."], "trailing dot/space")

    def test_colon_in_directory_component_rejected(self):
        self.assert_unsafe(["safe:stream/name.txt"], "alternate data stream")

    def test_normal_dotted_filename_remains_safe(self):
        result = hardening.inspect_zip_safety(self.make_zip(["safe/name.txt", "safe/other.json"]))
        self.assertTrue(result["ok"], result["unsafe_entries"])


if __name__ == "__main__":
    unittest.main()
