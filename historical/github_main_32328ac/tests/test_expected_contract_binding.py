from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import lab_routes
import lab_tools
from control_plane_models import ToolSpec


class ExpectedContractBindingTests(unittest.TestCase):
    TOOL = "test.contract.binding"

    def setUp(self) -> None:
        self.effects: list[dict] = []
        self.spec = ToolSpec(
            name=self.TOOL,
            description="contract binding test",
            danger_tier="low",
            category="general",
            input_schema={"type": "object", "additionalProperties": True},
            output_schema={"type": "object"},
            side_effect_class="read",
            effect_traits=["test_only"],
            handler=lambda payload: self.effects.append(dict(payload)) or {"value": payload.get("value")},
        )
        with lab_tools._REGISTRY_LOCK:
            self.previous = lab_tools._TOOL_REGISTRY.get(self.TOOL)
            lab_tools._TOOL_REGISTRY[self.TOOL] = self.spec

    def tearDown(self) -> None:
        with lab_tools._REGISTRY_LOCK:
            if self.previous is None:
                lab_tools._TOOL_REGISTRY.pop(self.TOOL, None)
            else:
                lab_tools._TOOL_REGISTRY[self.TOOL] = self.previous

    def test_legacy_omission_remains_compatible(self) -> None:
        result = lab_tools.dispatch_tool(self.TOOL, {"value": 1})
        self.assertTrue(result["ok"])
        self.assertEqual(len(self.effects), 1)

    def test_matching_digest_executes(self) -> None:
        result = lab_tools.dispatch_tool(
            self.TOOL,
            {"value": 2},
            expected_contract_digest=self.spec.contract_digest,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(self.effects, [{"value": 2}])

    def test_malformed_digest_fails_before_effect(self) -> None:
        with self.assertRaises(lab_tools.LabToolError) as caught:
            lab_tools.dispatch_tool(self.TOOL, {}, expected_contract_digest="not-a-digest")
        self.assertEqual(caught.exception.error_code, "BAD_EXPECTED_CONTRACT_DIGEST")
        self.assertEqual(caught.exception.status, 400)
        self.assertEqual(self.effects, [])

    def test_stale_digest_fails_before_any_downstream_dispatch_work(self) -> None:
        stale = "0" * 64 if self.spec.contract_digest != "0" * 64 else "1" * 64
        with patch.object(lab_tools, "_tool_router_validation_state") as router, patch.object(
            lab_tools, "_validate_payload_schema"
        ) as schema, patch.object(lab_tools, "_dispatch_protocol_decision") as protocol, patch.object(
            lab_tools, "_dispatch_decision"
        ) as approval:
            with self.assertRaises(lab_tools.LabToolError) as caught:
                lab_tools.dispatch_tool(self.TOOL, {}, expected_contract_digest=stale)
        self.assertEqual(caught.exception.error_code, "CAPABILITY_CONTRACT_STALE")
        self.assertEqual(caught.exception.status, 409)
        self.assertEqual(caught.exception.extra["current_contract_digest"], self.spec.contract_digest)
        router.assert_not_called()
        schema.assert_not_called()
        protocol.assert_not_called()
        approval.assert_not_called()
        self.assertEqual(self.effects, [])

    def test_http_dispatch_propagates_expected_digest(self) -> None:
        app = Flask(__name__)
        app.register_blueprint(lab_routes.lab_bp)
        with app.test_client() as client, patch.object(
            lab_routes, "require_valid_api_key", return_value=None
        ), patch.object(lab_routes, "dispatch_tool", return_value={"ok": True}) as dispatch:
            response = client.post(
                "/lab/dispatch",
                json={
                    "tool_name": self.TOOL,
                    "payload": {},
                    "expected_contract_digest": "a" * 64,
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(dispatch.call_args.kwargs["expected_contract_digest"], "a" * 64)

    def test_batch_step_propagates_expected_digest(self) -> None:
        with patch.object(lab_routes, "dispatch_tool", return_value={"ok": True}) as dispatch:
            result = lab_routes._batch_step_result(
                0,
                {
                    "tool_name": self.TOOL,
                    "payload": {},
                    "expected_contract_digest": "b" * 64,
                },
            )
        self.assertTrue(result["ok"])
        self.assertEqual(dispatch.call_args.kwargs["expected_contract_digest"], "b" * 64)


if __name__ == "__main__":
    unittest.main()
