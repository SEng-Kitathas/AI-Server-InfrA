from __future__ import annotations

import math
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baseline"))

import lab_tools_project
import lab_tools_filesystem
import power_routes
import shared_core
from api_wire_power import WriteFileRequest
from contextlib import nullcontext
from unittest.mock import patch
import ucm_v1_runtime as ucm
import user_continuity_store as backend
from test_ucm_v1_runtime import fact, source_provenance


class ToolError(Exception):
    def __init__(self, error_code: str, message: str, status: int = 400, **extra):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status = status
        self.extra = extra


class ProjectWriteAliasTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pcmmad-warfort-fs-")
        self.base = Path(self.temp.name)
        self.project = self.base / "project"
        self.project.mkdir()
        self.external = self.base / "external.txt"
        self.external.write_text("EXTERNAL-ORIGINAL", encoding="utf-8")
        self.dep = SimpleNamespace(
            error_cls=ToolError,
            ensure_project_layout=lambda payload: str(payload["project_id"]),
            get_project_root=lambda _project_id: self.project,
            ensure_parent=lambda path: path.parent.mkdir(parents=True, exist_ok=True),
            sha256_file=shared_core.sha256_file,
            utc_now=shared_core.utc_now,
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_overwrite_hardlink_cannot_modify_external_inode(self):
        inside = self.project / "inside.txt"
        os.link(self.external, inside)
        self.assertGreaterEqual(inside.stat().st_nlink, 2)
        before = self.external.read_bytes()
        try:
            out = lab_tools_project._project_write_payload(
                {"project_id": "p", "path": "inside.txt", "content": "NEW", "mode": "overwrite", "encoding": "utf-8"},
                self.dep,
            )
        except ToolError as exc:
            self.assertEqual(exc.error_code, "BAD_PATH_ALIAS")
        else:
            self.assertEqual(Path(out["absolute_path"]).read_text(encoding="utf-8"), "NEW")
        self.assertEqual(self.external.read_bytes(), before)

    def test_append_hardlink_fails_closed_without_external_mutation(self):
        inside = self.project / "inside.txt"
        os.link(self.external, inside)
        before = self.external.read_bytes()
        with self.assertRaises(ToolError) as ctx:
            lab_tools_project._project_write_payload(
                {"project_id": "p", "path": "inside.txt", "content": "+APPEND", "mode": "append", "encoding": "utf-8"},
                self.dep,
            )
        self.assertEqual(ctx.exception.error_code, "BAD_PATH_ALIAS")
        self.assertEqual(self.external.read_bytes(), before)

    def test_power_route_target_guard_rejects_hardlink_alias(self):
        inside = self.project / "power.txt"
        os.link(self.external, inside)
        req = WriteFileRequest(project_id="p", path="power.txt", content="NEW", mode="overwrite")
        before = self.external.read_bytes()
        with patch.object(power_routes, "init_project_layout", return_value=self.project):
            with self.assertRaises(ValueError) as ctx:
                power_routes._write_file_target(req)
        self.assertIn("multiply-linked", str(ctx.exception))
        self.assertEqual(self.external.read_bytes(), before)

    def test_filesystem_writer_guard_rejects_hardlink_alias(self):
        inside = self.project / "fs.txt"
        os.link(self.external, inside)
        before = self.external.read_bytes()
        dep = SimpleNamespace(
            error_cls=ToolError,
            ensure_within_allowed=lambda path: path,
            resolve_general_path=lambda payload: inside,
            ensure_parent=lambda path: path.parent.mkdir(parents=True, exist_ok=True),
        )
        with patch.object(lab_tools_filesystem, "resolved_paths_consequence_guard", return_value=nullcontext()):
            with self.assertRaises(ToolError) as ctx:
                lab_tools_filesystem._fs_write_payload({"content": "NEW", "session_id": "s"}, dep)
        self.assertEqual(ctx.exception.error_code, "BAD_PATH_ALIAS")
        self.assertEqual(self.external.read_bytes(), before)

    def test_external_symlink_target_is_rejected_when_supported(self):
        inside = self.project / "inside-link.txt"
        try:
            inside.symlink_to(self.external)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        before = self.external.read_bytes()
        with self.assertRaises(ToolError) as ctx:
            lab_tools_project._project_write_payload(
                {"project_id": "p", "path": "inside-link.txt", "content": "NEW", "mode": "overwrite", "encoding": "utf-8"},
                self.dep,
            )
        self.assertEqual(ctx.exception.error_code, "BAD_PATH")
        self.assertEqual(self.external.read_bytes(), before)


class UcmCanonicalJsonPoisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pcmmad-warfort-json-")
        self.old_root = backend.MEMORY_ROOT
        backend.MEMORY_ROOT = Path(self.temp.name) / "memory"
        with backend._CACHE_GUARD:
            backend._STATE_CACHE.clear()
        with backend._LOCKS_GUARD:
            backend._PROFILE_LOCKS.clear()
        self.profile = "json-poison"

    def tearDown(self):
        backend.MEMORY_ROOT = self.old_root
        with backend._CACHE_GUARD:
            backend._STATE_CACHE.clear()
        with backend._LOCKS_GUARD:
            backend._PROFILE_LOCKS.clear()
        self.temp.cleanup()

    def payload(self, record: dict):
        h = ucm.head(self.profile)
        return {
            "profile_id": self.profile,
            "actor": "assistant",
            "source_instance": "warfort",
            "provenance": source_provenance("json"),
            "idempotency_key": "json-test",
            "expected_head_seq": h["ledger_head_seq"],
            "expected_head_hash": h["ledger_head_hash"],
            "write_posture": "DIRECT_USER_AUTHORIZED",
            "record_type": "FACT",
            "record": record,
        }

    def assert_invalid_without_append(self, value):
        record = fact("json.fact", value=value)
        before = ucm.head(self.profile)["ledger_head_seq"]
        with self.assertRaises(ucm.UcmError) as ctx:
            ucm.add(self.payload(record))
        self.assertEqual(ctx.exception.error_code, "UCM_CONTRACT_INVALID")
        self.assertEqual(ucm.head(self.profile)["ledger_head_seq"], before)

    def test_nan_rejected_before_hash_or_append(self):
        self.assert_invalid_without_append(float("nan"))

    def test_positive_infinity_rejected_before_hash_or_append(self):
        self.assert_invalid_without_append(float("inf"))

    def test_negative_infinity_nested_rejected(self):
        self.assert_invalid_without_append({"a": [1, {"b": float("-inf")} ]})

    def test_lone_surrogate_string_rejected_cleanly(self):
        self.assert_invalid_without_append("bad-\ud800-surrogate")

    def test_excessive_nested_depth_rejected_without_recursion_crash(self):
        value = "leaf"
        for _ in range(100):
            value = [value]
        self.assert_invalid_without_append(value)

    def test_normal_finite_json_value_still_roundtrips(self):
        value = {"finite": 1.25, "nested": [True, None, "ok", {"n": 3}]}
        out = ucm.add(self.payload(fact("json.fact", value=value)))
        self.assertTrue(out["post_write_readback"])
        self.assertEqual(ucm.get_fact(self.profile, "json.fact")["value"], value)


if __name__ == "__main__":
    unittest.main()
