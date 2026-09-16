from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baseline"))

from pcmmad_receiver import lab_routes, lab_tools, shared_core
from pcmmad_receiver.control_plane_models import ToolSpec


class BatchDataflowFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pcmmad-batch-dataflow-")
        self.old_projects = shared_core.PROJECTS_ROOT
        shared_core.PROJECTS_ROOT = Path(self.temp.name) / "projects"
        self.original = dict(lab_tools._TOOL_REGISTRY)
        self.install("df.producer", lambda p: {"value": int(p.get("value", 7)), "nested": {"x": "ok"}})
        self.install("df.consumer", lambda p: {"got": p.get("x")})
        self.install("df.big", lambda p: {"blob": "x" * 70000})

    def tearDown(self):
        with lab_tools._REGISTRY_LOCK:
            lab_tools._TOOL_REGISTRY.clear()
            lab_tools._TOOL_REGISTRY.update(self.original)
        shared_core.PROJECTS_ROOT = self.old_projects
        self.temp.cleanup()

    def install(self, name, handler):
        spec = ToolSpec(
            name=name,
            description=name,
            category="test",
            side_effect_class="read",
            effect_traits=["test_only"],
            input_schema={"type": "object", "additionalProperties": True},
            output_schema={"type": "object", "additionalProperties": True},
            handler=handler,
        )
        with lab_tools._REGISTRY_LOCK:
            lab_tools._TOOL_REGISTRY[name] = spec
        return spec

    def step(self, step_id, tool, payload=None):
        return {
            "id": step_id,
            "tool_name": tool,
            "payload": payload or {},
            "expected_contract_digest": lab_tools._TOOL_REGISTRY[tool].contract_digest,
        }


class BatchDataflowTests(BatchDataflowFixture):
    def test_output_flows_into_later_step_without_model_roundtrip(self):
        steps = [
            self.step("a", "df.producer", {"value": 11}),
            self.step("b", "df.consumer", {"x": {"$ref": "a.result.value"}}),
        ]
        results = lab_routes._execute_batch_steps(steps, True, 1)
        self.assertEqual(results[0]["id"], "a")
        self.assertEqual(results[1]["id"], "b")
        self.assertEqual(results[1]["result"]["got"], 11)

    def test_nested_and_list_reference_paths_resolve(self):
        steps = [
            self.step("a", "df.producer", {"value": 3}),
            self.step("b", "df.consumer", {"x": {"$ref": "a.result.nested.x"}}),
        ]
        results = lab_routes._execute_batch_steps(steps, True, 1)
        self.assertEqual(results[1]["result"]["got"], "ok")

    def test_forward_reference_rejected_before_any_dispatch(self):
        calls = []
        self.install("df.consumer", lambda p: calls.append(dict(p)) or {"got": p.get("x")})
        steps = [
            self.step("a", "df.consumer", {"x": {"$ref": "b.result.value"}}),
            self.step("b", "df.producer", {"value": 1}),
        ]
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            lab_routes._execute_batch_steps(steps, True, 1)
        self.assertEqual(ctx.exception.error_code, "BATCH_REF_FORWARD_OR_UNKNOWN")
        self.assertEqual(calls, [])

    def test_reference_requires_named_consumer_step(self):
        steps = [
            self.step("a", "df.producer", {"value": 1}),
            {"tool_name": "df.consumer", "payload": {"x": {"$ref": "a.result.value"}}},
        ]
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            lab_routes._execute_batch_steps(steps, True, 1)
        self.assertEqual(ctx.exception.error_code, "BATCH_REF_INVALID")

    def test_authority_dataflow_is_forbidden(self):
        steps = [
            self.step("a", "df.producer", {"value": 1}),
            {
                **self.step("b", "df.consumer", {"x": 1}),
                "authority": {"approval_handle": {"$ref": "a.result.value"}},
            },
        ]
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            lab_routes._execute_batch_steps(steps, True, 1)
        self.assertEqual(ctx.exception.error_code, "BATCH_AUTHORITY_REF_FORBIDDEN")

    def test_dataflow_parallelism_is_gated_until_effect_profile_is_qualified(self):
        steps = [
            self.step("a", "df.producer", {"value": 1}),
            self.step("b", "df.consumer", {"x": {"$ref": "a.result.value"}}),
        ]
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            lab_routes._execute_batch_steps(steps, False, 2)
        self.assertEqual(ctx.exception.error_code, "BATCH_DATAFLOW_REQUIRES_SEQUENTIAL")

    def test_unresolved_field_is_typed_failure(self):
        steps = [
            self.step("a", "df.producer", {"value": 1}),
            self.step("b", "df.consumer", {"x": {"$ref": "a.result.missing"}}),
        ]
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            lab_routes._execute_batch_steps(steps, True, 1)
        self.assertEqual(ctx.exception.error_code, "BATCH_REF_UNRESOLVED")

    def test_resolved_payload_amplification_is_bounded(self):
        steps = [
            self.step("a", "df.big"),
            self.step("b", "df.consumer", {"x": {"$ref": "a.result"}}),
        ]
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            lab_routes._execute_batch_steps(steps, True, 1)
        self.assertEqual(ctx.exception.error_code, "BATCH_DATAFLOW_PAYLOAD_TOO_LARGE")

    def test_legacy_parallel_batch_without_refs_remains_available(self):
        steps = [self.step("a", "df.producer", {"value": 1}), self.step("b", "df.producer", {"value": 2})]
        out = lab_routes._execute_batch_steps(steps, False, 2)
        self.assertEqual([row["result"]["value"] for row in out], [1, 2])

    def test_duplicate_step_ids_rejected(self):
        steps = [self.step("x", "df.producer"), self.step("x", "df.consumer")]
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            lab_routes._execute_batch_steps(steps, True, 1)
        self.assertEqual(ctx.exception.error_code, "BAD_REQUEST")


if __name__ == "__main__":
    unittest.main()
