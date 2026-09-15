from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME))

import approval_authority as aa
import lab_routes
import lab_tools
from control_plane_models import ToolSpec


class ApprovalContinuationHttpTests(unittest.TestCase):
    TOOL = "test.http.approval.continuation"

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root_patch = patch.object(aa, "SYSTEM_ROOT", Path(self.temp.name))
        self.root_patch.start()
        self.env_patch = patch.dict(os.environ, {"PCMMAD_LAB_POLICY_MODE": "strict", "PCMMAD_ALLOW_LEGACY_INLINE_APPROVAL": "0"}, clear=False)
        self.env_patch.start()
        self.calls = []
        self.spec = ToolSpec(
            name=self.TOOL, description="http approval continuation", danger_tier="high", category="test",
            approval_required=True, mutating=False, capability_version="1",
            input_schema={"type": "object", "properties": {"target": {"type": "string"}, "value": {"type": "integer"}}, "required": ["target"], "additionalProperties": False},
            output_schema={"type": "object"}, side_effect_class="mutation", effect_traits=["test_mutation"],
            handler=lambda payload: self.calls.append(dict(payload)) or {"received": dict(payload)},
        )
        with lab_tools._REGISTRY_LOCK:
            self.previous = lab_tools._TOOL_REGISTRY.get(self.TOOL)
            lab_tools._TOOL_REGISTRY[self.TOOL] = self.spec
        app = Flask(__name__)
        app.register_blueprint(lab_routes.lab_bp)
        self.client = app.test_client()
        self.auth_patch = patch.object(lab_routes, "require_valid_api_key", return_value=None)
        self.auth_patch.start()

    def tearDown(self) -> None:
        self.auth_patch.stop()
        with lab_tools._REGISTRY_LOCK:
            if self.previous is None:
                lab_tools._TOOL_REGISTRY.pop(self.TOOL, None)
            else:
                lab_tools._TOOL_REGISTRY[self.TOOL] = self.previous
        self.env_patch.stop()
        self.root_patch.stop()
        self.temp.cleanup()

    def _post(self, body):
        return self.client.post("/lab/dispatch", json=body)

    def test_http_transports_safe_continuation_and_exact_resubmit_executes_once(self) -> None:
        args = {"target": "A", "value": 7}
        first = self._post({"tool_name": self.TOOL, "payload": args})
        self.assertEqual(first.status_code, 403)
        challenge_body = first.get_json()
        self.assertEqual(challenge_body["error_code"], "APPROVAL_REQUIRED")
        cont = challenge_body["continuation"]
        challenge = challenge_body["approval_challenge"]
        self.assertEqual(cont["tool"], self.TOOL)
        self.assertEqual(cont["arguments"], args)
        self.assertEqual(cont["expected_contract_digest"], self.spec.contract_digest)
        self.assertEqual(cont["authority_template"], {"approval_handle": challenge["handle"], "permit": False})
        self.assertEqual(self.calls, [])

        denied = self._post({"tool_name": cont["tool"], "payload": cont["arguments"], "authority": cont["authority_template"], "expected_contract_digest": cont["expected_contract_digest"]})
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.get_json()["error_code"], "APPROVAL_CONFIRMATION_REQUIRED")
        self.assertEqual(self.calls, [])
        self.assertEqual(aa.inspect_challenge(challenge["handle"])["status"], "ACTIVE")

        authority = dict(cont["authority_template"]); authority["permit"] = True
        approved = self._post({"tool_name": cont["tool"], "payload": cont["arguments"], "authority": authority, "expected_contract_digest": cont["expected_contract_digest"]})
        self.assertEqual(approved.status_code, 200)
        self.assertTrue(approved.get_json()["ok"])
        self.assertEqual(self.calls, [args])

        replay = self._post({"tool_name": cont["tool"], "payload": cont["arguments"], "authority": authority, "expected_contract_digest": cont["expected_contract_digest"]})
        self.assertEqual(replay.status_code, 403)
        self.assertEqual(replay.get_json()["error_code"], "APPROVAL_ALREADY_CONSUMED")
        self.assertEqual(len(self.calls), 1)

    def test_http_changed_arguments_do_not_consume_continuation(self) -> None:
        args = {"target": "A", "value": 1}
        body = self._post({"tool_name": self.TOOL, "payload": args}).get_json()
        cont = body["continuation"]
        authority = dict(cont["authority_template"]); authority["permit"] = True
        changed = dict(cont["arguments"]); changed["target"] = "B"
        denied = self._post({"tool_name": cont["tool"], "payload": changed, "authority": authority, "expected_contract_digest": cont["expected_contract_digest"]})
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.get_json()["error_code"], "APPROVAL_ARGUMENTS_MISMATCH")
        self.assertEqual(self.calls, [])
        self.assertEqual(aa.inspect_challenge(body["approval_challenge"]["handle"])["status"], "ACTIVE")


if __name__ == "__main__":
    unittest.main()
