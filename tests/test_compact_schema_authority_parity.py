from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
SCHEMA_PATH = RUNTIME_ROOT / "pcmmad_lab_action_schema_v10_3_pcmmad_native_protocol_compact_30_router.json"
RESTART_SCRIPT = PROJECT_ROOT / "RESTART_RECEIVER_AND_NGROK.ps1"


class CompactSchemaAuthorityParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.schemas = cls.schema["components"]["schemas"]

    def test_compact_projection_remains_exactly_thirty_operations(self) -> None:
        operations = []
        for path, item in self.schema.get("paths", {}).items():
            for method, spec in item.items():
                if method.lower() in {"get", "post", "put", "patch", "delete"}:
                    operations.append((path, method.upper(), spec.get("operationId")))
        self.assertEqual(len(operations), 30)
        self.assertEqual(len({op_id for _, _, op_id in operations}), 30)

    def test_dispatch_projects_authority_separately_from_capability_payload(self) -> None:
        request = self.schemas["LabDispatchRequest"]
        props = request["properties"]
        self.assertEqual(props["authority"], {"$ref": "#/components/schemas/RuntimeAuthorityEnvelope"})
        self.assertIn("arguments only", props["payload"]["description"])
        self.assertIn("does not belong inside payload", props["payload"]["description"])
        self.assertFalse(request["additionalProperties"])
        self.assertNotIn("approval", props)
        self.assertNotIn("approval_handle", props)

    def test_batch_projects_bound_authority_per_step_not_in_payload(self) -> None:
        step = self.schemas["LabBatchRequest"]["properties"]["steps"]["items"]
        props = step["properties"]
        self.assertEqual(props["authority"], {"$ref": "#/components/schemas/RuntimeAuthorityEnvelope"})
        self.assertIn("arguments only", props["payload"]["description"])
        self.assertIn("separately per step", props["payload"]["description"])
        self.assertFalse(step["additionalProperties"])
        self.assertNotIn("approval", props)
        self.assertNotIn("approval_handle", props)

    def test_runtime_authority_envelope_separates_approval_and_project_mutation(self) -> None:
        envelope = self.schemas["RuntimeAuthorityEnvelope"]
        self.assertFalse(envelope["additionalProperties"])
        props = envelope["properties"]
        approval = self.schemas["BoundApprovalAuthority"]["properties"]
        for key in ("approval_handle", "permit", "operator_id", "provenance"):
            self.assertEqual(props[key]["type"], approval[key]["type"])
            if "minLength" in approval[key]:
                self.assertEqual(props[key].get("minLength"), approval[key]["minLength"])
        self.assertEqual(
            props["project_mutation"],
            {"$ref": "#/components/schemas/ProjectMutationAuthority"},
        )
        self.assertNotIn("project_mutation", self.schemas["BoundApprovalAuthority"]["properties"])

    def test_bound_authority_contract_matches_runtime_retry_shape(self) -> None:
        authority = self.schemas["BoundApprovalAuthority"]
        self.assertEqual(authority["required"], ["approval_handle", "permit"])
        self.assertFalse(authority["additionalProperties"])
        props = authority["properties"]
        self.assertEqual(props["approval_handle"]["type"], "string")
        self.assertEqual(props["permit"]["type"], "boolean")
        self.assertIn("operator_id", props)
        self.assertIn("provenance", props)

    def test_schema_no_longer_teaches_legacy_inline_boolean_approval(self) -> None:
        text = SCHEMA_PATH.read_text(encoding="utf-8")
        forbidden = [
            r'"approval"\s*:\s*\{\s*"permit"',
            r'approval\s*:\s*\{\s*permit',
            r'payload[^\n]{0,180}approval[^\n]{0,80}permit',
        ]
        for pattern in forbidden:
            self.assertIsNone(re.search(pattern, text, flags=re.IGNORECASE), pattern)
        self.assertEqual(
            self.schema["info"]["x-pcmmad-authority-model"],
            "runtime-authority-envelope-v1",
        )

    def test_dispatch_and_batch_descriptions_explain_separate_bound_authority(self) -> None:
        dispatch = self.schema["paths"]["/lab/dispatch"]["post"]["description"].lower()
        batch = self.schema["paths"]["/lab/batch"]["post"]["description"].lower()
        self.assertIn("separate top-level authority envelope", dispatch)
        self.assertIn("do not embed approval inside payload", dispatch)
        self.assertIn("separate runtime authority envelope", batch)
        self.assertIn("does not imply transaction", batch)

    def test_restart_controller_still_publishes_this_compact_template(self) -> None:
        text = RESTART_SCRIPT.read_text(encoding="utf-8-sig")
        self.assertIn(SCHEMA_PATH.name, text)
        self.assertIn("pcmmad_lab_action_schema_ACTIVE.json", text)


if __name__ == "__main__":
    unittest.main()
