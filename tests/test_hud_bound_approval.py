from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HUD_ROOT = PROJECT_ROOT / "operator_hud"
HUD_SERVER = HUD_ROOT / "server.py"


def load_hud_module():
    name = "pcmmad_test_operator_hud_server"
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, HUD_SERVER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    module.app.config.update(TESTING=True)
    return module


class HudBoundApprovalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.hud = load_hud_module()

    def setUp(self) -> None:
        self.client = self.hud.app.test_client()
        self.auth_patch = patch.object(self.hud, "_require_hud_token", return_value=None)
        self.auth_patch.start()

    def tearDown(self) -> None:
        self.auth_patch.stop()

    def test_initial_dispatch_forwards_no_synthetic_authority_and_strips_embedded_smuggling(self) -> None:
        seen = {}

        def receiver_request(path, method="GET", payload=None, timeout=5.0):
            seen.update({"path": path, "method": method, "payload": payload})
            return 403, {
                "ok": False,
                "error_code": "APPROVAL_REQUIRED",
                "message": "exact approval required",
                "approval_challenge": {
                    "handle": "apr-abc",
                    "capability_id": "git.commit",
                    "contract_digest": "c" * 64,
                    "arguments_digest": "a" * 64,
                    "target": {"project_id": "alpha"},
                    "expires_at": "2026-09-05T06:00:00+00:00",
                },
            }

        with patch.object(self.hud, "receiver_request", side_effect=receiver_request):
            response = self.client.post(
                "/api/dispatch",
                json={
                    "tool_name": "git.commit",
                    "payload": {
                        "project_id": "alpha",
                        "message": "m",
                        "approval": {"permit": True},
                        "approval_handle": "forged",
                        "authority": {"approval_handle": "forged2"},
                    },
                    "request_id": "req-1",
                },
            )
        self.assertEqual(response.status_code, 403)
        body = response.get_json()
        self.assertEqual(body["error_code"], "APPROVAL_REQUIRED")
        self.assertEqual(body["approval_challenge"]["handle"], "apr-abc")
        forwarded = seen["payload"]
        self.assertEqual(forwarded["tool_name"], "git.commit")
        self.assertNotIn("authority", forwarded)
        self.assertNotIn("approval", forwarded["payload"])
        self.assertNotIn("approval_handle", forwarded["payload"])
        self.assertNotIn("authority", forwarded["payload"])

    def test_exact_explicit_authority_envelope_is_forwarded_separately(self) -> None:
        seen = {}

        def receiver_request(path, method="GET", payload=None, timeout=5.0):
            seen["payload"] = payload
            return 200, {
                "ok": True,
                "approved": True,
                "approval_mode": "bound_challenge",
                "approval_handle": "apr-abc",
                "result": {"done": True},
            }

        authority = {
            "approval_handle": "apr-abc",
            "permit": True,
            "operator_id": "local-hud-operator",
            "provenance": "pcmmad-local-hud:req-1",
        }
        with patch.object(self.hud, "receiver_request", side_effect=receiver_request):
            response = self.client.post(
                "/api/dispatch",
                json={
                    "tool_name": "git.commit",
                    "payload": {"project_id": "alpha", "message": "m"},
                    "authority": authority,
                    "request_id": "req-2",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(seen["payload"]["authority"], authority)
        self.assertEqual(
            seen["payload"]["payload"],
            {"project_id": "alpha", "message": "m"},
        )

    def test_legacy_approve_bit_is_rejected_before_receiver_call(self) -> None:
        with patch.object(self.hud, "receiver_request") as receiver:
            response = self.client.post(
                "/api/dispatch",
                json={
                    "tool_name": "git.commit",
                    "payload": {"project_id": "alpha", "message": "m"},
                    "approve": True,
                },
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["error_code"], "HUD_LEGACY_APPROVAL_DISABLED")
        receiver.assert_not_called()

    def test_authority_must_be_object(self) -> None:
        response = self.client.post(
            "/api/dispatch",
            json={"tool_name": "x", "payload": {}, "authority": "apr-bad"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error_code"], "BAD_REQUEST")

    def test_batch_uses_effective_approval_and_strips_nested_authority(self) -> None:
        catalog = {
            "ok": True,
            "tools": [
                {
                    "name": "sop.ingest.next_chunk",
                    "approval_required": False,
                    "effective_approval_required": True,
                    "danger_tier": "medium",
                    "contract_digest": "d" * 64,
                }
            ],
        }

        def receiver_request(path, method="GET", payload=None, timeout=5.0):
            if path == "/lab/tools":
                return 200, catalog
            raise AssertionError("approval-gated batch must not be dispatched")

        with patch.object(self.hud, "receiver_request", side_effect=receiver_request):
            response = self.client.post(
                "/api/batch",
                json={
                    "steps": [
                        {
                            "tool_name": "sop.ingest.next_chunk",
                            "payload": {
                                "project_id": "alpha",
                                "approval": {"permit": True},
                            },
                            "authority": {"approval_handle": "apr-smuggle", "permit": True},
                        }
                    ]
                },
            )
        self.assertEqual(response.status_code, 403)
        body = response.get_json()
        self.assertEqual(body["error_code"], "HUD_BATCH_APPROVAL_REQUIRED")
        self.assertTrue(body["gated_steps"][0]["effective_approval_required"])
        self.assertEqual(body["gated_steps"][0]["contract_digest"], "d" * 64)

    def test_batch_unknown_tool_fails_closed(self) -> None:
        with patch.object(
            self.hud,
            "receiver_request",
            return_value=(200, {"ok": True, "tools": []}),
        ):
            response = self.client.post(
                "/api/batch",
                json={"steps": [{"tool_name": "unknown.tool", "payload": {}}]},
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["error_code"], "HUD_BATCH_TOOL_UNKNOWN")

    def test_meta_advertises_runtime_bound_challenge_model(self) -> None:
        response = self.client.get("/api/meta")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIn("target/argument/contract-bound challenge", body["approval_model"])
        self.assertEqual(body["ui_version"], "ops-hud-20260909-observability-v1")
        self.assertEqual(body["telemetry_model"], "receiver-owned RED+USE+scheduler projection")

    def test_frontend_uses_effective_approval_and_runtime_challenge_not_local_approve_bit(self) -> None:
        js = (HUD_ROOT / "static" / "app.js").read_text(encoding="utf-8")
        html = (HUD_ROOT / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn("effective_approval_required", js)
        self.assertIn("approval_challenge", js)
        self.assertIn("approval_handle:challenge.handle", js)
        self.assertIn("Approve exact challenge", js)
        self.assertNotIn("sendDispatch(t,payload,true)", js)
        self.assertNotIn("approve,request_id", js)
        self.assertIn("Exact Runtime Challenge + Payload", html)
        self.assertIn("single-use handle", html)


if __name__ == "__main__":
    unittest.main()
