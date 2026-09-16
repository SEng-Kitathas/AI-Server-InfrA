from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "baseline" / "pcmmad_receiver" / "pcmmad_lab_action_schema_v11_0_actions_compat_8.json"
GENERATOR = ROOT / "tools" / "generate_schema_v11_actions_compat.py"


class ActionsCompatSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    def test_editor_requires_openapi_31(self) -> None:
        self.assertIn(self.schema["openapi"], {"3.1.0", "3.1.1"})

    def test_components_schemas_is_an_object(self) -> None:
        self.assertIsInstance(self.schema.get("components"), dict)
        self.assertIsInstance(self.schema["components"].get("schemas"), dict)

    def test_exactly_eight_unique_actions(self) -> None:
        operations = [
            spec[method]["operationId"]
            for spec in self.schema["paths"].values()
            for method in spec
            if method.lower() in {"get", "post", "put", "patch", "delete"}
        ]
        self.assertEqual(len(operations), 8)
        self.assertEqual(len(set(operations)), 8)

    def test_every_object_schema_has_properties_object(self) -> None:
        missing: list[str] = []

        def walk(value: object, path: str) -> None:
            if isinstance(value, dict):
                if value.get("type") == "object":
                    if "properties" not in value or not isinstance(value.get("properties"), dict):
                        missing.append(path)
                for key, child in value.items():
                    walk(child, f"{path}.{key}")
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    walk(child, f"{path}[{index}]")

        walk(self.schema, "$")
        self.assertEqual(missing, [])

    def test_response_object_schemas_have_properties(self) -> None:
        bad: list[str] = []
        for path, item in self.schema["paths"].items():
            for method, operation in item.items():
                if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                    continue
                for status, response in operation.get("responses", {}).items():
                    schema = (
                        response.get("content", {})
                        .get("application/json", {})
                        .get("schema")
                    )
                    if isinstance(schema, dict) and schema.get("type") == "object":
                        if not isinstance(schema.get("properties"), dict):
                            bad.append(f"{path}:{method}:{status}")
        self.assertEqual(bad, [])

    def test_importer_projection_stays_flat(self) -> None:
        text = SCHEMA.read_text(encoding="utf-8")
        self.assertNotIn('"$ref"', text)
        self.assertNotIn('"nullable"', text)

    def test_generator_is_byte_deterministic(self) -> None:
        before = SCHEMA.read_bytes()
        cp = subprocess.run(
            [sys.executable, str(GENERATOR)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertEqual(SCHEMA.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
