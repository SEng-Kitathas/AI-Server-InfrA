from __future__ import annotations

import dataclasses
import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
SCHEMA_PATH = (
    RUNTIME_ROOT
    / "pcmmad_lab_action_schema_v10_3_pcmmad_native_protocol_compact_30_router.json"
)
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import lab_tools


class CompactSchemaFamilyAuthorityParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.family_schema = cls.schema["components"]["schemas"]["CapabilityFamilyCard"]
        cls.families = [dataclasses.asdict(row) for row in lab_tools.capability_families()]

    def test_closed_family_schema_matches_native_serialized_key_set(self) -> None:
        self.assertFalse(self.family_schema["additionalProperties"])
        schema_keys = set(self.family_schema["properties"])
        required = set(self.family_schema["required"])
        self.assertEqual(required, schema_keys)
        for family in self.families:
            self.assertEqual(set(family), schema_keys, family["name"])

    def test_effective_approval_count_is_explicit_and_semantically_distinct(self) -> None:
        field = self.family_schema["properties"]["effective_approval_required_tools"]
        self.assertEqual(field["type"], "integer")
        self.assertEqual(field["minimum"], 0)
        self.assertIn("effective runtime policy", field["description"])

        strict_difference = []
        for family in self.families:
            declared = family["approval_required_tools"]
            effective = family["effective_approval_required_tools"]
            self.assertLessEqual(declared, effective, family["name"])
            if effective > declared:
                strict_difference.append(family["name"])
        self.assertTrue(strict_difference)
        self.assertIn("browser", strict_difference)

    def test_compact_action_surface_remains_exactly_thirty_operations(self) -> None:
        operations = []
        for path, item in self.schema["paths"].items():
            for method, spec in item.items():
                if method.lower() in {"get", "post", "put", "patch", "delete"}:
                    operations.append((path, method.upper(), spec.get("operationId")))
        self.assertEqual(len(operations), 30)
        self.assertEqual(len({op_id for _, _, op_id in operations}), 30)


if __name__ == "__main__":
    unittest.main()
