from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

import approval_authority as aa
import lab_tools
from control_plane_models import ToolSpec


class BoundApprovalDispatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root_patch = patch.object(aa, "SYSTEM_ROOT", Path(self.temp.name))
        self.root_patch.start()
        self.env_patch = patch.dict(
            os.environ,
            {
                "PCMMAD_LAB_POLICY_MODE": "strict",
                "PCMMAD_ALLOW_LEGACY_INLINE_APPROVAL": "1",
            },
            clear=False,
        )
        self.env_patch.start()
        self.original_registry = dict(lab_tools._TOOL_REGISTRY)
        self.calls: list[dict] = []
        self._install("test.approved", version="1")

    def tearDown(self) -> None:
        lab_tools._TOOL_REGISTRY.clear()
        lab_tools._TOOL_REGISTRY.update(self.original_registry)
        self.env_patch.stop()
        self.root_patch.stop()
        self.temp.cleanup()

    def _install(self, name: str, *, version: str = "1") -> None:
        def handler(payload):
            self.calls.append(dict(payload))
            return {"received": dict(payload)}

        lab_tools._TOOL_REGISTRY[name] = ToolSpec(
            name=name,
            description="approval test",
            danger_tier="high",
            category="test",
            approval_required=True,
            mutating=False,
            capability_version=version,
            input_schema={
                "type": "object",
                "properties": {
                    "target": {"type": "string"},
                    "value": {"type": "integer"},
                },
                "required": ["target"],
                "additionalProperties": False,
            },
            output_schema={"type": "object"},
            side_effect_class="mutation",
            effect_traits=["test_mutation"],
            handler=handler,
        )

    def _challenge(self, args: dict) -> dict:
        with self.assertRaises(lab_tools.LabToolError) as caught:
            lab_tools.dispatch_tool("test.approved", args)
        self.assertEqual(caught.exception.error_code, "APPROVAL_REQUIRED")
        self.assertEqual(self.calls, [])
        challenge = caught.exception.extra["approval_challenge"]
        self.assertEqual(challenge["capability_id"], "test.approved")
        self.assertEqual(challenge["target"], {"target": args["target"]})
        return challenge

    def test_missing_authority_returns_bound_challenge_without_execution(self) -> None:
        challenge = self._challenge({"target": "A", "value": 1})
        self.assertEqual(challenge["status"], "ACTIVE")
        self.assertEqual(len(challenge["contract_digest"]), 64)
        self.assertEqual(len(challenge["arguments_digest"]), 64)

    def test_exact_challenge_executes_once_and_reports_bound_mode(self) -> None:
        args = {"target": "A", "value": 1}
        challenge = self._challenge(args)
        result = lab_tools.dispatch_tool(
            "test.approved",
            args,
            authority={
                "approval_handle": challenge["handle"],
                "permit": True,
                "operator_id": "operator",
                "provenance": "hud",
            },
        )
        self.assertTrue(result["ok"])
        self.assertTrue(result["approved"])
        self.assertEqual(result["approval_mode"], "bound_challenge")
        self.assertEqual(result["approval_handle"], challenge["handle"])
        self.assertEqual(self.calls, [args])

        with self.assertRaises(lab_tools.LabToolError) as replay:
            lab_tools.dispatch_tool(
                "test.approved",
                args,
                authority={"approval_handle": challenge["handle"], "permit": True},
            )
        self.assertEqual(replay.exception.error_code, "APPROVAL_ALREADY_CONSUMED")
        self.assertEqual(len(self.calls), 1)

    def test_changed_arguments_do_not_consume_or_execute(self) -> None:
        challenge = self._challenge({"target": "A", "value": 1})
        with self.assertRaises(lab_tools.LabToolError) as caught:
            lab_tools.dispatch_tool(
                "test.approved",
                {"target": "B", "value": 1},
                authority={"approval_handle": challenge["handle"], "permit": True},
            )
        self.assertEqual(caught.exception.error_code, "APPROVAL_ARGUMENTS_MISMATCH")
        self.assertEqual(self.calls, [])
        self.assertEqual(aa.inspect_challenge(challenge["handle"])["status"], "ACTIVE")

    def test_contract_change_invalidates_existing_challenge(self) -> None:
        args = {"target": "A", "value": 1}
        challenge = self._challenge(args)
        self._install("test.approved", version="2")
        with self.assertRaises(lab_tools.LabToolError) as caught:
            lab_tools.dispatch_tool(
                "test.approved",
                args,
                authority={"approval_handle": challenge["handle"], "permit": True},
            )
        self.assertEqual(caught.exception.error_code, "APPROVAL_CONTRACT_STALE")
        self.assertEqual(self.calls, [])

    def test_challenge_for_one_capability_cannot_authorize_another(self) -> None:
        args = {"target": "A", "value": 1}
        challenge = self._challenge(args)
        self._install("test.other", version="1")
        with self.assertRaises(lab_tools.LabToolError) as caught:
            lab_tools.dispatch_tool(
                "test.other",
                args,
                authority={"approval_handle": challenge["handle"], "permit": True},
            )
        self.assertEqual(caught.exception.error_code, "APPROVAL_CAPABILITY_MISMATCH")

    def test_legacy_inline_approval_is_stripped_before_schema_and_handler(self) -> None:
        result = lab_tools.dispatch_tool(
            "test.approved",
            {
                "target": "A",
                "value": 1,
                "approval": {"permit": True},
            },
        )
        self.assertTrue(result["approved"])
        self.assertEqual(result["approval_mode"], "legacy_inline")
        self.assertIn("legacy inline approval is unbound", result["warning"])
        self.assertEqual(self.calls, [{"target": "A", "value": 1}])
        self.assertNotIn("approval", result["result"]["received"])

    def test_legacy_inline_can_be_disabled_without_breaking_bound_flow(self) -> None:
        with patch.dict(os.environ, {"PCMMAD_ALLOW_LEGACY_INLINE_APPROVAL": "0"}, clear=False):
            with self.assertRaises(lab_tools.LabToolError) as caught:
                lab_tools.dispatch_tool(
                    "test.approved",
                    {"target": "A", "approval": {"permit": True}},
                )
            self.assertEqual(caught.exception.error_code, "LEGACY_APPROVAL_DISABLED")


if __name__ == "__main__":
    unittest.main()
