from __future__ import annotations

import base64
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baseline"))

import project_mutation_authority as pma
import transfer_plane as tp


class TransferIdentityWarfortTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pcmmad-warfort-transfer-")
        self.root = Path(self.temp.name).resolve()
        self.projects = self.root / "projects"
        self.alpha = self.projects / "alpha"
        self.alpha.mkdir(parents=True)
        self.state = self.root / "transfer-state"
        self.state.mkdir()
        self.patches = [
            patch.object(tp, "_STATE", self.state),
            patch.object(tp, "get_mount_roots", return_value=[self.root]),
            patch.object(tp, "get_project_root", lambda project_id: self.projects / project_id),
            patch.object(pma, "PROJECTS_ROOT", self.projects),
            patch.object(pma, "get_project_root", side_effect=lambda project_id: self.projects / project_id),
            patch.object(
                pma,
                "init_project_layout",
                side_effect=lambda project_id: (self.projects / project_id).mkdir(parents=True, exist_ok=True)
                or (self.projects / project_id),
            ),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def test_import_stage_hardlink_swap_cannot_write_external_inode(self):
        data = b"ABCD"
        created = tp.create_import(
            "out.bin",
            expected_size=len(data),
            expected_sha256=hashlib.sha256(data).hexdigest(),
            project_id="alpha",
        )
        row = tp._load(created["ticket"])
        stage = Path(row["stage"])
        external = self.root / "outside.bin"
        external.write_bytes(b"WXYZ")
        stage.unlink()
        os.link(external, stage)
        before = external.read_bytes()
        with self.assertRaises(ValueError) as ctx:
            tp.append_chunk(
                created["ticket"],
                0,
                base64.b64encode(data).decode("ascii"),
                hashlib.sha256(data).hexdigest(),
            )
        self.assertIn("stage identity", str(ctx.exception).lower())
        self.assertEqual(external.read_bytes(), before)

    def test_import_stage_replacement_with_different_regular_file_rejected(self):
        data = b"ABCD"
        created = tp.create_import(
            "out.bin",
            expected_size=len(data),
            expected_sha256=hashlib.sha256(data).hexdigest(),
            project_id="alpha",
        )
        row = tp._load(created["ticket"])
        stage = Path(row["stage"])
        stage.unlink()
        stage.write_bytes(b"")
        with self.assertRaises(ValueError) as ctx:
            tp.append_chunk(
                created["ticket"],
                0,
                base64.b64encode(data).decode("ascii"),
                hashlib.sha256(data).hexdigest(),
            )
        self.assertIn("stage identity", str(ctx.exception).lower())

    def test_export_same_size_same_mtime_content_change_is_detected(self):
        source = self.alpha / "src.bin"
        source.write_bytes(b"AAAA")
        st = source.stat()
        created = tp.create_export("src.bin", project_id="alpha")
        source.write_bytes(b"BBBB")
        os.utime(source, ns=(st.st_atime_ns, st.st_mtime_ns))
        with self.assertRaises(ValueError) as ctx:
            tp.read_chunk(created["ticket"], 0, 4)
        self.assertIn("source changed", str(ctx.exception).lower())

    def test_export_source_inode_swap_same_content_metadata_is_detected(self):
        source = self.alpha / "src.bin"
        source.write_bytes(b"AAAA")
        st = source.stat()
        created = tp.create_export("src.bin", project_id="alpha")
        source.unlink()
        source.write_bytes(b"AAAA")
        os.utime(source, ns=(st.st_atime_ns, st.st_mtime_ns))
        with self.assertRaises(ValueError) as ctx:
            tp.read_chunk(created["ticket"], 0, 4)
        self.assertIn("source identity", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
