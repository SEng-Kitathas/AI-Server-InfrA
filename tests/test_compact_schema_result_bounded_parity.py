from __future__ import annotations

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
sys.path.insert(0, str(RUNTIME_ROOT))

from lab_results import (  # noqa: E402
    RESULT_INLINE_SAFE_BYTES,
    RESULT_PREVIEW_MAX_CHARS,
    RESULT_RANGE_MAX_BYTES,
)


class CompactSchemaResultBoundedParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.request = cls.schema["components"]["schemas"]["ResultHandleRequest"]
        cls.operation = cls.schema["paths"]["/lab/results/get"]["post"]

    def test_actions_request_exposes_native_bounded_retrieval_modes(self) -> None:
        mode = self.request["properties"]["mode"]
        self.assertEqual(
            mode["enum"], ["auto", "full", "metadata", "preview", "range"]
        )
        self.assertEqual(mode["default"], "auto")
        self.assertIn("safely inline", mode["description"])
        self.assertIn("full explicitly", mode["description"])

    def test_range_and_preview_bounds_match_runtime_constants(self) -> None:
        props = self.request["properties"]
        offset = props["offset_bytes"]
        length = props["length_bytes"]
        preview = props["preview_chars"]

        self.assertEqual(offset["minimum"], 0)
        self.assertEqual(offset["default"], 0)

        self.assertEqual(length["minimum"], 1)
        self.assertEqual(length["maximum"], RESULT_RANGE_MAX_BYTES)
        self.assertEqual(length["default"], 32768)

        self.assertEqual(preview["minimum"], 200)
        self.assertEqual(preview["maximum"], RESULT_PREVIEW_MAX_CHARS)
        self.assertEqual(preview["default"], 1200)

        self.assertEqual(RESULT_INLINE_SAFE_BYTES, 12000)
        self.assertGreater(RESULT_RANGE_MAX_BYTES, RESULT_INLINE_SAFE_BYTES)

    def test_legacy_summary_only_remains_explicit_preview_alias(self) -> None:
        alias = self.request["properties"]["summary_only"]
        self.assertEqual(alias["type"], "boolean")
        self.assertFalse(alias["default"])
        self.assertIn("Historical compatibility alias", alias["description"])
        self.assertIn("forces preview mode", alias["description"])
        self.assertIn("prefer mode=preview", alias["description"])

    def test_request_remains_closed_and_requires_only_identity(self) -> None:
        self.assertFalse(self.request["additionalProperties"])
        self.assertEqual(self.request["required"], ["project_id", "handle"])
        self.assertEqual(
            set(self.request["properties"]),
            {
                "project_id",
                "handle",
                "mode",
                "offset_bytes",
                "length_bytes",
                "preview_chars",
                "summary_only",
            },
        )

    def test_operation_teaches_bounded_context_and_explicit_full_opt_in(self) -> None:
        description = self.operation["description"]
        self.assertIn("bounded model context", description)
        self.assertIn("full is explicit opt-in", description)
        self.assertIn("summary_only=true", description)
        self.assertIn("metadata", self.operation["summary"])
        self.assertIn("byte range", self.operation["summary"])

    def test_compact_surface_stays_at_thirty_operations(self) -> None:
        operations = []
        for path, item in self.schema["paths"].items():
            for method, spec in item.items():
                if method.lower() in {"get", "post", "put", "patch", "delete"}:
                    operations.append((path, method.upper(), spec.get("operationId")))
        self.assertEqual(len(operations), 30)
        self.assertEqual(len({op_id for _, _, op_id in operations}), 30)


if __name__ == "__main__":
    unittest.main()
