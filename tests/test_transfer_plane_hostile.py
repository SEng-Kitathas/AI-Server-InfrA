from __future__ import annotations

import base64
import hashlib
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

import lab_tools
import transfer_plane as tp


class TransferPlaneHostileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.projects = self.root / "projects"
        self.alpha = self.projects / "alpha"
        self.beta = self.projects / "beta"
        self.alpha.mkdir(parents=True)
        self.beta.mkdir(parents=True)
        self.state = self.root / "transfer-state"
        self.state.mkdir()
        self.patches = [
            patch.object(tp, "_STATE", self.state),
            patch.object(tp, "get_mount_roots", return_value=[self.root]),
            patch.object(tp, "get_project_root", lambda project_id: self.projects / project_id),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def test_project_scoped_transfer_rejects_absolute_other_project_path(self) -> None:
        target = self.beta / "secret.bin"
        target.write_bytes(b"secret")
        with self.assertRaises(ValueError) as caught:
            tp.create_export(str(target), project_id="alpha")
        self.assertIn("project transfer scope", str(caught.exception))

    def test_ticket_manifest_tamper_is_detected(self) -> None:
        source = self.alpha / "x.bin"
        source.write_bytes(b"abcdef")
        ticket = tp.create_export("x.bin", project_id="alpha")["ticket"]
        manifest = tp._mp(ticket)
        row = json.loads(manifest.read_text(encoding="utf-8"))
        row["size"] = 999
        manifest.write_text(json.dumps(row), encoding="utf-8")
        with self.assertRaises(ValueError) as caught:
            tp._load(ticket)
        self.assertIn("manifest integrity", str(caught.exception))

    def test_expired_ticket_is_rejected_after_valid_integrity_rewrite(self) -> None:
        source = self.alpha / "x.bin"
        source.write_bytes(b"abcdef")
        ticket = tp.create_export("x.bin", project_id="alpha")["ticket"]
        manifest = tp._mp(ticket)
        row = json.loads(manifest.read_text(encoding="utf-8"))
        row["expires_epoch"] = time.time() - 1
        row["manifest_sha256"] = tp._manifest_digest(row)
        manifest.write_text(json.dumps(row), encoding="utf-8")
        with self.assertRaises(TimeoutError):
            tp._load(ticket)

    def test_import_chunk_requires_exact_hash_and_does_not_advance_on_missing_hash(self) -> None:
        data = b"hello"
        digest = hashlib.sha256(data).hexdigest()
        created = tp.create_import(
            "out.bin",
            expected_size=len(data),
            expected_sha256=digest,
            project_id="alpha",
        )
        encoded = base64.b64encode(data).decode("ascii")
        with self.assertRaises(ValueError) as caught:
            tp.append_chunk(created["ticket"], 0, encoded, None)
        self.assertIn("chunk_sha256 is required", str(caught.exception))
        self.assertEqual(tp._load(created["ticket"])["offset"], 0)

    def test_destination_change_after_overwrite_ticket_creation_blocks_finalize(self) -> None:
        dst = self.alpha / "out.bin"
        dst.write_bytes(b"old")
        data = b"replacement"
        digest = hashlib.sha256(data).hexdigest()
        created = tp.create_import(
            "out.bin",
            expected_size=len(data),
            expected_sha256=digest,
            project_id="alpha",
            overwrite=True,
        )
        dst.write_bytes(b"someone-else-changed-it")
        tp.append_chunk(
            created["ticket"],
            0,
            base64.b64encode(data).decode("ascii"),
            digest,
        )
        with self.assertRaises(ValueError) as caught:
            tp.finalize_import(created["ticket"])
        self.assertIn("destination changed", str(caught.exception))
        self.assertEqual(dst.read_bytes(), b"someone-else-changed-it")

    def test_happy_import_finalizes_atomically_after_full_hash(self) -> None:
        data = b"complete-transfer"
        digest = hashlib.sha256(data).hexdigest()
        created = tp.create_import(
            "new.bin",
            expected_size=len(data),
            expected_sha256=digest,
            project_id="alpha",
        )
        tp.append_chunk(
            created["ticket"], 0, base64.b64encode(data).decode("ascii"), digest
        )
        result = tp.finalize_import(created["ticket"])
        self.assertTrue(result["verified"])
        self.assertTrue(result["complete"])
        self.assertEqual((self.alpha / "new.bin").read_bytes(), data)
        self.assertEqual(hashlib.sha256((self.alpha / "new.bin").read_bytes()).hexdigest(), digest)

    def test_concurrent_same_offset_writes_cannot_both_advance(self) -> None:
        first = b"aaaa"
        second = b"bbbb"
        expected = first + second
        created = tp.create_import(
            "race.bin",
            expected_size=len(expected),
            expected_sha256=hashlib.sha256(expected).hexdigest(),
            project_id="alpha",
        )
        barrier = threading.Barrier(3)
        results = []
        errors = []

        def writer(data: bytes) -> None:
            barrier.wait(timeout=5)
            try:
                results.append(
                    tp.append_chunk(
                        created["ticket"],
                        0,
                        base64.b64encode(data).decode("ascii"),
                        hashlib.sha256(data).hexdigest(),
                    )
                )
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(first,)), threading.Thread(target=writer, args=(second,))]
        for thread in threads:
            thread.start()
        barrier.wait(timeout=5)
        for thread in threads:
            thread.join(timeout=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(len(errors), 1)
        self.assertIn("offset mismatch", str(errors[0]))
        self.assertEqual(tp._load(created["ticket"])["offset"], 4)

    def test_all_direct_http_routes_require_api_key(self) -> None:
        app = Flask(__name__)
        app.register_blueprint(tp.transfer_bp)
        client = app.test_client()
        ticket = "a" * 64
        calls = [
            ("post", "/transfer/export/create", {}),
            ("post", "/transfer/import/create", {}),
            ("get", f"/transfer/{ticket}/meta", None),
            ("get", f"/transfer/{ticket}/chunk", None),
            ("get", f"/transfer/{ticket}/file", None),
            ("post", f"/transfer/{ticket}/upload-chunk", {}),
            ("post", f"/transfer/{ticket}/finalize", {}),
            ("post", "/transfer/cleanup", {}),
        ]
        with patch.object(tp, "require_valid_api_key", side_effect=RuntimeError("no key")):
            for method, url, body in calls:
                with self.subTest(url=url):
                    response = getattr(client, method)(url, json=body) if body is not None else getattr(client, method)(url)
                    self.assertEqual(response.status_code, 401)
                    self.assertEqual(response.get_json()["error_code"], "UNAUTHORIZED")

    def test_mutating_http_import_route_delegates_to_native_dispatch_authority(self) -> None:
        app = Flask(__name__)
        app.register_blueprint(tp.transfer_bp)
        client = app.test_client()
        fake = {
            "ok": True,
            "approved": True,
            "approval_mode": "bound_challenge",
            "approval_handle": "apr-test",
            "result": {"ticket": "t", "direction": "import"},
        }
        with patch.object(tp, "require_valid_api_key", return_value=None), patch.object(
            lab_tools, "dispatch_tool", return_value=fake
        ) as dispatch:
            response = client.post(
                "/transfer/import/create",
                json={
                    "path": "out.bin",
                    "expected_size": 1,
                    "expected_sha256": "a" * 64,
                    "project_id": "alpha",
                    "authority": {"approval_handle": "apr-test", "permit": True},
                },
            )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["ticket"], "t")
        self.assertTrue(payload["policy"]["approved"])
        args, kwargs = dispatch.call_args
        self.assertEqual(args[0], "transfer.import.create")
        self.assertNotIn("authority", args[1])
        self.assertEqual(kwargs["authority"]["approval_handle"], "apr-test")

    def test_transfer_capability_effect_contracts_are_explicit(self) -> None:
        tools = {row["name"]: row for row in lab_tools.list_tools()}
        self.assertIn("source_currentness_check", tools["transfer.chunk.read"]["effect_traits"])
        self.assertIn("requires_chunk_hash", tools["transfer.chunk.write"]["effect_traits"])
        self.assertIn("binds_destination_identity", tools["transfer.import.create"]["effect_traits"])
        self.assertIn("postcondition_verified", tools["transfer.import.finalize"]["effect_traits"])


if __name__ == "__main__":
    unittest.main()
