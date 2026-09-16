from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask, g

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

import shared_core
import workload_identity as wid


class WorkloadIdentityProofTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = Flask(__name__)
        self.secret_a = b"A" * 32
        self.secret_b = b"B" * 32
        self.keys = {
            "workload-alpha": {
                "kid-a": base64.urlsafe_b64encode(self.secret_a).decode("ascii").rstrip("="),
                "kid-b": base64.urlsafe_b64encode(self.secret_b).decode("ascii").rstrip("="),
            }
        }
        self.base_env = {
            "GITHOME_API_KEY": "receiver-key",
            wid.MODE_ENV: "optional",
            wid.KEYS_ENV: json.dumps(self.keys, sort_keys=True),
        }

    def _headers(
        self,
        *,
        secret: bytes | None = None,
        key_id: str = "kid-a",
        timestamp: int | None = None,
        nonce: str = "nonce-abcdefghijklmnopqr",
        method: str = "POST",
        target: str = "/lab/dispatch?x=1",
        body: bytes = b'{"a":1}',
    ) -> dict[str, str]:
        ts = int(time.time()) if timestamp is None else int(timestamp)
        chosen = self.secret_a if secret is None else secret
        signature = wid.sign_proof_for_test_or_client(
            chosen,
            workload_id="workload-alpha",
            key_id=key_id,
            timestamp=ts,
            nonce=nonce,
            method=method,
            target=target,
            body=body,
        )
        return {
            "X-GitHome-Key": "receiver-key",
            wid.HEADER_WORKLOAD_ID: "workload-alpha",
            wid.HEADER_KEY_ID: key_id,
            wid.HEADER_TIMESTAMP: str(ts),
            wid.HEADER_NONCE: nonce,
            wid.HEADER_SIGNATURE: signature,
        }

    def test_optional_mode_preserves_bearer_only_hosted_reachability(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-workload-optional-") as td, patch.dict(
            os.environ, self.base_env, clear=False
        ), patch.object(shared_core, "TEMP_ROOT", Path(td)):
            with self.app.test_request_context(
                "/lab/health", method="GET", headers={"X-GitHome-Key": "receiver-key"}
            ):
                shared_core.require_valid_api_key({"X-GitHome-Key": "receiver-key"})
                self.assertIsNone(g.pcmmad_workload_identity)

    def test_valid_proof_binds_identity_to_exact_request_and_reserves_nonce(self) -> None:
        body = b'{"a":1}'
        headers = self._headers(body=body)
        with tempfile.TemporaryDirectory(prefix="pcmmad-workload-valid-") as td, patch.dict(
            os.environ, self.base_env, clear=False
        ), patch.object(shared_core, "TEMP_ROOT", Path(td)):
            with self.app.test_request_context(
                "/lab/dispatch?x=1", method="POST", data=body, headers=headers
            ):
                shared_core.require_valid_api_key(headers)
                identity = g.pcmmad_workload_identity
                self.assertTrue(identity["verified"])
                self.assertEqual(identity["workload_id"], "workload-alpha")
                self.assertEqual(identity["key_id"], "kid-a")
                self.assertEqual(identity["request_body_sha256"], hashlib.sha256(body).hexdigest())
                replay_files = list((Path(td) / "workload_identity").glob("*/*.json"))
                self.assertEqual(len(replay_files), 1)
                receipt = json.loads(replay_files[0].read_text(encoding="utf-8"))
                self.assertEqual(receipt["method"], "POST")
                self.assertEqual(receipt["request_body_sha256"], hashlib.sha256(body).hexdigest())
                self.assertEqual(
                    receipt["target_sha256"], hashlib.sha256(b"/lab/dispatch?x=1").hexdigest()
                )
                self.assertEqual(receipt["proof_message_sha256"], identity["proof_message_sha256"])
                self.assertNotIn("signature", receipt)
                self.assertNotIn("secret", receipt)

    def test_replay_of_same_signed_request_is_rejected(self) -> None:
        body = b'{"a":1}'
        headers = self._headers(body=body)
        with tempfile.TemporaryDirectory(prefix="pcmmad-workload-replay-") as td, patch.dict(
            os.environ, self.base_env, clear=False
        ), patch.object(shared_core, "TEMP_ROOT", Path(td)):
            with self.app.test_request_context(
                "/lab/dispatch?x=1", method="POST", data=body, headers=headers
            ):
                shared_core.require_valid_api_key(headers)
            with self.app.test_request_context(
                "/lab/dispatch?x=1", method="POST", data=body, headers=headers
            ):
                with self.assertRaises(PermissionError) as raised:
                    shared_core.require_valid_api_key(headers)
            self.assertIn("WORKLOAD_IDENTITY_REPLAY", str(raised.exception))

    def test_invalid_body_does_not_consume_nonce_and_correct_body_can_then_succeed(self) -> None:
        signed_body = b'{"a":1}'
        wrong_body = b'{"a":2}'
        headers = self._headers(body=signed_body, nonce="nonce-body-binding-abcdef")
        with tempfile.TemporaryDirectory(prefix="pcmmad-workload-body-") as td, patch.dict(
            os.environ, self.base_env, clear=False
        ), patch.object(shared_core, "TEMP_ROOT", Path(td)):
            with self.app.test_request_context(
                "/lab/dispatch?x=1", method="POST", data=wrong_body, headers=headers
            ):
                with self.assertRaises(PermissionError) as raised:
                    shared_core.require_valid_api_key(headers)
            self.assertIn("WORKLOAD_IDENTITY_INVALID", str(raised.exception))
            self.assertFalse((Path(td) / "workload_identity").exists())

            with self.app.test_request_context(
                "/lab/dispatch?x=1", method="POST", data=signed_body, headers=headers
            ):
                shared_core.require_valid_api_key(headers)
                self.assertEqual(g.pcmmad_workload_identity["workload_id"], "workload-alpha")

    def test_path_query_and_method_are_part_of_signature(self) -> None:
        body = b"{}"
        headers = self._headers(body=body, nonce="nonce-target-bind-abcdefgh")
        with tempfile.TemporaryDirectory(prefix="pcmmad-workload-target-") as td, patch.dict(
            os.environ, self.base_env, clear=False
        ), patch.object(shared_core, "TEMP_ROOT", Path(td)):
            for path, method in (("/lab/dispatch?x=2", "POST"), ("/lab/dispatch?x=1", "PUT")):
                with self.app.test_request_context(path, method=method, data=body, headers=headers):
                    with self.assertRaises(PermissionError) as raised:
                        shared_core.require_valid_api_key(headers)
                    self.assertIn("WORKLOAD_IDENTITY_INVALID", str(raised.exception))

    def test_stale_timestamp_and_partial_proof_fail_closed(self) -> None:
        stale = int(time.time()) - wid.MAX_CLOCK_SKEW_SECONDS - 1
        stale_headers = self._headers(timestamp=stale, nonce="nonce-stale-proof-abcdefgh")
        partial = {"X-GitHome-Key": "receiver-key", wid.HEADER_WORKLOAD_ID: "workload-alpha"}
        with tempfile.TemporaryDirectory(prefix="pcmmad-workload-stale-") as td, patch.dict(
            os.environ, self.base_env, clear=False
        ), patch.object(shared_core, "TEMP_ROOT", Path(td)):
            with self.app.test_request_context(
                "/lab/dispatch?x=1", method="POST", data=b'{"a":1}', headers=stale_headers
            ):
                with self.assertRaises(PermissionError) as raised:
                    shared_core.require_valid_api_key(stale_headers)
                self.assertIn("WORKLOAD_IDENTITY_STALE", str(raised.exception))
            with self.app.test_request_context("/lab/health", method="GET", headers=partial):
                with self.assertRaises(PermissionError) as raised:
                    shared_core.require_valid_api_key(partial)
                self.assertIn("WORKLOAD_IDENTITY_BAD_PROOF", str(raised.exception))

    def test_key_rotation_accepts_multiple_kids_without_exposing_secrets(self) -> None:
        body = b"{}"
        headers_a = self._headers(body=body, nonce="nonce-rotation-key-a-abc", key_id="kid-a", secret=self.secret_a)
        headers_b = self._headers(body=body, nonce="nonce-rotation-key-b-abc", key_id="kid-b", secret=self.secret_b)
        with tempfile.TemporaryDirectory(prefix="pcmmad-workload-rotation-") as td, patch.dict(
            os.environ, self.base_env, clear=False
        ), patch.object(shared_core, "TEMP_ROOT", Path(td)):
            for headers, kid in ((headers_a, "kid-a"), (headers_b, "kid-b")):
                with self.app.test_request_context(
                    "/lab/dispatch?x=1", method="POST", data=body, headers=headers
                ):
                    shared_core.require_valid_api_key(headers)
                    identity = g.pcmmad_workload_identity
                    self.assertEqual(identity["key_id"], kid)
                    self.assertNotIn("secret", identity)
                    self.assertNotIn("signature", identity)

    def test_workload_proof_never_substitutes_for_invalid_receiver_api_key(self) -> None:
        body = b"{}"
        headers = self._headers(body=body, nonce="nonce-invalid-bearer-abcdef")
        headers["X-GitHome-Key"] = "wrong-key"
        with tempfile.TemporaryDirectory(prefix="pcmmad-workload-bearer-") as td, patch.dict(
            os.environ, self.base_env, clear=False
        ), patch.object(shared_core, "TEMP_ROOT", Path(td)):
            with self.app.test_request_context(
                "/lab/dispatch?x=1", method="POST", data=body, headers=headers
            ):
                with self.assertRaises(PermissionError) as raised:
                    shared_core.require_valid_api_key(headers)
            self.assertEqual(str(raised.exception), "Invalid or missing API key")
            self.assertFalse((Path(td) / "workload_identity").exists())

    def test_malformed_configured_secret_fails_closed_when_proof_is_supplied(self) -> None:
        body = b"{}"
        headers = self._headers(body=body, nonce="nonce-bad-secret-config-abcd")
        env = dict(self.base_env)
        env[wid.KEYS_ENV] = json.dumps({"workload-alpha": {"kid-a": "!!!!"}})
        with tempfile.TemporaryDirectory(prefix="pcmmad-workload-config-") as td, patch.dict(
            os.environ, env, clear=False
        ), patch.object(shared_core, "TEMP_ROOT", Path(td)):
            with self.app.test_request_context(
                "/lab/dispatch?x=1", method="POST", data=body, headers=headers
            ):
                with self.assertRaises(PermissionError) as raised:
                    shared_core.require_valid_api_key(headers)
            self.assertIn("WORKLOAD_IDENTITY_CONFIG_INVALID", str(raised.exception))

    def test_concurrent_same_nonce_has_exactly_one_acceptance(self) -> None:
        now = int(time.time())
        nonce = "nonce-concurrent-proof-abcdef"
        body = b"{}"
        headers = self._headers(
            body=body, nonce=nonce, timestamp=now, method="POST", target="/lab/dispatch"
        )
        with tempfile.TemporaryDirectory(prefix="pcmmad-workload-race-") as td:
            replay_root = Path(td) / "replay"

            def attempt(_idx: int) -> str:
                try:
                    wid.verify_workload_proof(
                        headers,
                        method="POST",
                        target="/lab/dispatch",
                        body=body,
                        replay_root=replay_root,
                        now_epoch=now,
                        mode="optional",
                        keys_json=json.dumps(self.keys, sort_keys=True),
                    )
                    return "accepted"
                except wid.WorkloadIdentityError as exc:
                    return exc.error_code

            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(attempt, range(8)))
            self.assertEqual(results.count("accepted"), 1, results)
            self.assertEqual(results.count("WORKLOAD_IDENTITY_REPLAY"), 7, results)
            self.assertEqual(len(list(replay_root.glob("*/*.json"))), 1)

    def test_required_mode_rejects_bearer_only_and_off_mode_rejects_identity_illusion(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-workload-modes-") as td, patch.object(
            shared_core, "TEMP_ROOT", Path(td)
        ):
            required_env = dict(self.base_env, **{wid.MODE_ENV: "required"})
            with patch.dict(os.environ, required_env, clear=False):
                with self.app.test_request_context(
                    "/lab/health", method="GET", headers={"X-GitHome-Key": "receiver-key"}
                ):
                    with self.assertRaises(PermissionError) as raised:
                        shared_core.require_valid_api_key({"X-GitHome-Key": "receiver-key"})
                    self.assertIn("WORKLOAD_IDENTITY_REQUIRED", str(raised.exception))

            off_env = dict(self.base_env, **{wid.MODE_ENV: "off"})
            proof = self._headers(body=b"", method="GET", target="/lab/health", nonce="nonce-off-mode-proof-abcdef")
            with patch.dict(os.environ, off_env, clear=False):
                with self.app.test_request_context("/lab/health", method="GET", headers=proof):
                    with self.assertRaises(PermissionError) as raised:
                        shared_core.require_valid_api_key(proof)
                    self.assertIn("WORKLOAD_IDENTITY_DISABLED", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
