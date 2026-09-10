from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baseline"))

from pcmmad_receiver import approval_authority as aa
from pcmmad_receiver import lab_routes
from pcmmad_receiver import lab_tools
from pcmmad_receiver import schema_vnext_runtime as vnext
from pcmmad_receiver import shared_core
from pcmmad_receiver.control_plane_models import ToolSpec
from pcmmad_receiver.lab_results import store_result
from pcmmad_receiver import scheduler_effect_profile as effect_profile


class SchemaVNextFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="pcmmad-schema-vnext-")
        self.root = Path(self.temp.name)
        self.old_projects = shared_core.PROJECTS_ROOT
        shared_core.PROJECTS_ROOT = self.root / "projects"
        self.approval_patch = patch.object(aa, "SYSTEM_ROOT", self.root / "system")
        self.approval_patch.start()
        self.env_patch = patch.dict(
            os.environ,
            {"PCMMAD_LAB_POLICY_MODE": "strict", "PCMMAD_ALLOW_LEGACY_INLINE_APPROVAL": "0"},
            clear=False,
        )
        self.env_patch.start()
        self.original_registry = dict(lab_tools._TOOL_REGISTRY)
        self.calls: list[tuple[str, dict]] = []
        self._install("test.echo", side_effect_class="read", handler=lambda p: {"echo": dict(p), "value": p.get("value")})
        self._install("test.producer", side_effect_class="read", handler=lambda p: {"value": int(p.get("value", 7))})
        self._install("test.consumer", side_effect_class="read", handler=lambda p: {"got": p.get("x")})
        self._install("test.unsafe.a", side_effect_class="mutation", handler=self._logged("unsafe.a"))
        self._install("test.unsafe.b", side_effect_class="mutation", handler=self._logged("unsafe.b"))
        self._install(
            "test.approved",
            side_effect_class="mutation",
            danger_tier="high",
            approval_required=True,
            handler=self._logged("approved"),
        )
        self.effect_profile_patch = patch.object(vnext, "_current_scheduler_profile", side_effect=self._test_effect_profile)
        self.effect_profile_patch.start()

    def tearDown(self) -> None:
        with lab_tools._REGISTRY_LOCK:
            lab_tools._TOOL_REGISTRY.clear()
            lab_tools._TOOL_REGISTRY.update(self.original_registry)
        self.effect_profile_patch.stop()
        self.env_patch.stop()
        self.approval_patch.stop()
        shared_core.PROJECTS_ROOT = self.old_projects
        self.temp.cleanup()

    def _logged(self, name: str):
        def handler(payload):
            self.calls.append((name, dict(payload)))
            return {"name": name, "payload": dict(payload)}
        return handler

    def _install(
        self,
        name: str,
        *,
        version: str = "1",
        side_effect_class: str = "read",
        danger_tier: str = "low",
        approval_required: bool = False,
        handler=None,
        effect_traits=None,
    ) -> ToolSpec:
        spec = ToolSpec(
            name=name,
            description=f"synthetic {name}",
            danger_tier=danger_tier,
            category="test",
            tags=["synthetic", "schema-vnext"],
            approval_required=approval_required,
            mutating=False,
            input_schema={"type": "object", "additionalProperties": True},
            output_schema={"type": "object", "additionalProperties": True},
            capability_version=version,
            schema_version="1",
            side_effect_class=side_effect_class,
            effect_traits=list(effect_traits or ["test_only"]),
            handler=handler or (lambda p: dict(p)),
        )
        with lab_tools._REGISTRY_LOCK:
            lab_tools._TOOL_REGISTRY[name] = spec
        return spec

    def _test_effect_profile(self):
        cards = vnext._cards()
        profile = effect_profile.build_profile(cards)
        verification = effect_profile.verify_profile(profile, cards)
        return profile, verification, effect_profile.entry_map(profile)

    def lease(self, *names: str) -> dict:
        return vnext.orient({"capabilities": list(names), "detail": "compact", "ttl_seconds": 300})["lease"]

    def plan(self, nodes, **extra):
        return vnext.compose({"project_id": "p", "nodes": nodes, **extra})["plan"]


class OrientLeaseTests(SchemaVNextFixture):
    def test_task_relative_orientation_returns_bounded_lease(self):
        out = vnext.orient({"goal": "synthetic echo", "categories": ["test"], "max_capabilities": 3})
        self.assertTrue(out["ok"])
        self.assertLessEqual(out["count"], 3)
        self.assertEqual(out["lease"]["authority_effect"], "NONE")
        self.assertTrue(vnext.validate_lease(out["lease"])["current"])

    def test_explicit_orientation_returns_exact_requested_capability(self):
        out = vnext.orient({"capabilities": ["test.echo"], "detail": "full"})
        self.assertEqual([row["name"] for row in out["capabilities"]], ["test.echo"])
        self.assertIn("output_schema", out["capabilities"][0])

    def test_lease_content_tamper_rejected(self):
        lease = self.lease("test.echo")
        lease["selected"][0]["name"] = "test.consumer"
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            vnext.validate_lease(lease)
        self.assertEqual(ctx.exception.error_code, "CAPABILITY_LEASE_INVALID")

    def test_expired_lease_rejected(self):
        lease = self.lease("test.echo")
        lease["expires_at_epoch"] = 1
        core = dict(lease); core.pop("lease_digest")
        lease["lease_digest"] = vnext._hash_json(core)
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            vnext.validate_lease(lease)
        self.assertEqual(ctx.exception.error_code, "CAPABILITY_LEASE_EXPIRED")

    def test_lease_stale_when_selected_contract_changes(self):
        lease = self.lease("test.echo")
        self._install("test.echo", version="2", side_effect_class="read", handler=lambda p: dict(p))
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            vnext.validate_lease(lease)
        self.assertEqual(ctx.exception.error_code, "CAPABILITY_LEASE_STALE")

    def test_unrelated_capability_change_does_not_stale_selected_lease(self):
        lease = self.lease("test.echo")
        self._install("test.consumer", version="2", side_effect_class="read", handler=lambda p: dict(p))
        out = vnext.validate_lease(lease)
        self.assertTrue(out["current"])
        self.assertNotEqual(out["catalog_digest_current"], out["catalog_digest_at_issue"])


class InvokeTests(SchemaVNextFixture):
    def test_vnext_invoke_requires_currentness_binding(self):
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            vnext.invoke({"capability": "test.echo", "arguments": {"value": 1}})
        self.assertEqual(ctx.exception.error_code, "EXPECTED_CONTRACT_REQUIRED")

    def test_lease_bound_invoke_executes(self):
        lease = self.lease("test.echo")
        out = vnext.invoke({"capability": "test.echo", "arguments": {"value": 4}, "lease": lease})
        self.assertTrue(out["ok"])
        self.assertEqual(out["result"]["value"], 4)

    def test_invoke_rejects_explicit_project_context_mismatch_with_lease(self):
        lease=vnext.orient({"project_id":"alpha","capabilities":["test.echo"]})["lease"]
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            vnext.invoke({"capability":"test.echo","arguments":{"project_id":"beta"},"lease":lease})
        self.assertEqual(ctx.exception.error_code,"CAPABILITY_LEASE_PROJECT_MISMATCH")

    def test_capability_outside_lease_rejected(self):
        lease = self.lease("test.echo")
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            vnext.invoke({"capability": "test.consumer", "arguments": {}, "lease": lease})
        self.assertEqual(ctx.exception.error_code, "CAPABILITY_NOT_IN_LEASE")

    def test_explicit_digest_conflicting_with_lease_rejected_before_dispatch(self):
        lease = self.lease("test.echo")
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            vnext.invoke({"capability": "test.echo", "arguments": {}, "lease": lease, "expected_contract_digest": "0" * 64})
        self.assertEqual(ctx.exception.error_code, "CAPABILITY_LEASE_CONTRACT_CONFLICT")


class ComposeTests(SchemaVNextFixture):
    def test_identical_compose_inputs_produce_identical_sealed_plan_digest(self):
        nodes=[{"id":"a","capability":"test.echo","arguments":{"value":1}}]
        first=vnext.compose({"project_id":"p","goal":"inspect","nodes":nodes})
        time.sleep(0.01)
        second=vnext.compose({"project_id":"p","goal":"inspect","nodes":nodes})
        self.assertEqual(first["plan"],second["plan"])
        self.assertEqual(first["plan_digest"],second["plan_digest"])
        self.assertNotEqual(first["composed_at"],second["composed_at"])

    def test_goal_is_sealed_metadata_but_does_not_synthesize_or_change_execution_shape(self):
        nodes=[{"id":"a","capability":"test.echo","arguments":{"value":1}}]
        first=vnext.compose({"project_id":"p","goal":"alpha", "nodes":nodes})["plan"]
        second=vnext.compose({"project_id":"p","goal":"beta", "nodes":nodes})["plan"]
        self.assertEqual(first["nodes"],second["nodes"])
        self.assertEqual(first["stages"],second["stages"])
        self.assertEqual(first["static_cost_units"],second["static_cost_units"])
        self.assertNotEqual(first["plan_digest"],second["plan_digest"])

    def test_dataflow_ref_derives_dependency_and_digest(self):
        plan = self.plan([
            {"id": "a", "capability": "test.producer", "arguments": {"value": 9}},
            {"id": "b", "capability": "test.consumer", "arguments": {"x": {"$ref": "a.result.value"}}},
        ])
        b = next(node for node in plan["nodes"] if node["id"] == "b")
        self.assertEqual(b["depends_on"], ["a"])
        self.assertEqual(len(plan["plan_digest"]), 64)
        self.assertEqual(plan["authority_effect"], "NONE")

    def test_cycle_rejected(self):
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            self.plan([
                {"id": "a", "capability": "test.echo", "depends_on": ["b"]},
                {"id": "b", "capability": "test.echo", "depends_on": ["a"]},
            ])
        self.assertEqual(ctx.exception.error_code, "PLAN_CYCLE")

    def test_authority_inside_plan_node_is_forbidden(self):
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            self.plan([{"id": "a", "capability": "test.echo", "authority": {"permit": True}}])
        self.assertEqual(ctx.exception.error_code, "AUTHORITY_IN_PLAN_FORBIDDEN")

    def test_compose_with_lease_rejects_capability_outside_advisory_scope(self):
        lease=self.lease("test.echo")
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            vnext.compose({"project_id":"p","lease":lease,"nodes":[{"id":"a","capability":"test.consumer"}]})
        self.assertEqual(ctx.exception.error_code,"CAPABILITY_NOT_IN_LEASE")

    def test_compose_rejects_lease_project_context_mismatch(self):
        lease=vnext.orient({"project_id":"alpha","capabilities":["test.echo"]})["lease"]
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            vnext.compose({"project_id":"beta","lease":lease,"nodes":[{"id":"a","capability":"test.echo"}]})
        self.assertEqual(ctx.exception.error_code,"CAPABILITY_LEASE_PROJECT_MISMATCH")

    def test_plan_contract_stales_when_native_capability_changes(self):
        plan = self.plan([{"id": "a", "capability": "test.echo", "arguments": {}}])
        self._install("test.echo", version="2", side_effect_class="read", handler=lambda p: dict(p))
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            vnext.execute({"project_id": "p", "plan": plan, "expected_plan_digest": plan["plan_digest"]})
        self.assertEqual(ctx.exception.error_code, "PLAN_CAPABILITY_STALE")

    def test_plan_tamper_rejected(self):
        plan = self.plan([{"id": "a", "capability": "test.echo", "arguments": {"value": 1}}])
        plan["nodes"][0]["arguments"]["value"] = 2
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            vnext.execute({"project_id": "p", "plan": plan, "expected_plan_digest": plan["plan_digest"]})
        self.assertEqual(ctx.exception.error_code, "PLAN_INVALID")


class ExecuteTests(SchemaVNextFixture):
    def test_dataflow_executes_without_model_roundtrip(self):
        plan = self.plan([
            {"id": "a", "capability": "test.producer", "arguments": {"value": 11}},
            {"id": "b", "capability": "test.consumer", "arguments": {"x": {"$ref": "a.result.value"}}},
        ])
        out = vnext.execute({"project_id": "p", "plan": plan, "expected_plan_digest": plan["plan_digest"]})
        self.assertEqual(out["status"], "COMPLETED")
        self.assertEqual(out["results"]["b"]["result"]["got"], 11)

    def test_condition_skips_node(self):
        plan = self.plan([
            {"id": "a", "capability": "test.producer", "arguments": {"value": 0}},
            {"id": "b", "capability": "test.consumer", "arguments": {"x": 1}, "when": {"ref": "a.result.value", "equals": 1}},
        ])
        out = vnext.execute({"project_id": "p", "plan": plan, "expected_plan_digest": plan["plan_digest"]})
        self.assertEqual(out["results"]["b"]["status"], "SKIPPED")

    def test_plan_assertion_failure_is_exact(self):
        plan = self.plan(
            [{"id": "a", "capability": "test.producer", "arguments": {"value": 5}}],
            assertions=[{"ref": "a.result.value", "op": "eq", "value": 6}],
        )
        out = vnext.execute({"project_id": "p", "plan": plan, "expected_plan_digest": plan["plan_digest"]})
        self.assertFalse(out["ok"])
        self.assertEqual(out["status"], "POSTCONDITION_FAILED")
        self.assertEqual(out["failures"][0]["error_code"], "PLAN_ASSERTION_FAILED")
        self.assertEqual(out["results"]["a"]["result"]["value"], 5)
        self.assertIn("not transactional", out["warning"])

    def test_unwitnessed_reads_serialize_even_when_parallelism_requested(self):
        lock = threading.Lock(); active = {"count": 0, "peak": 0}
        def read_handler(payload):
            with lock:
                active["count"] += 1; active["peak"] = max(active["peak"], active["count"])
            time.sleep(0.02)
            with lock:
                active["count"] -= 1
            return {"ok": True}
        self._install("test.parallel.a", side_effect_class="read", handler=read_handler)
        self._install("test.parallel.b", side_effect_class="read", handler=read_handler)
        plan = self.plan([
            {"id": "a", "capability": "test.parallel.a"},
            {"id": "b", "capability": "test.parallel.b"},
        ], max_parallelism=2)
        out = vnext.execute({"project_id": "p", "plan": plan, "expected_plan_digest": plan["plan_digest"]})
        self.assertEqual(out["status"], "COMPLETED")
        self.assertEqual(active["peak"], 1)

    def test_exact_digest_parallel_witness_enables_independent_read_parallelism(self):
        barrier = threading.Barrier(2)
        def read_handler(payload):
            barrier.wait(timeout=2)
            return {"ok": True}
        a = self._install("test.parallel.a", side_effect_class="read", handler=read_handler)
        b = self._install("test.parallel.b", side_effect_class="read", handler=read_handler)
        truth = {
            "test.parallel.a": {"contract_digest": a.contract_digest, "effect_kind": "READ_LOCAL", "evidence": "test:effect-truth-a"},
            "test.parallel.b": {"contract_digest": b.contract_digest, "effect_kind": "READ_LOCAL", "evidence": "test:effect-truth-b"},
        }
        witnesses = {
            "test.parallel.a": {"contract_digest": a.contract_digest, "evidence": "test:parallel-a"},
            "test.parallel.b": {"contract_digest": b.contract_digest, "evidence": "test:parallel-b"},
        }
        with patch.dict(effect_profile.EFFECT_TRUTH_VERIFICATION_WITNESSES, truth, clear=True), patch.dict(effect_profile.PARALLEL_VERIFICATION_WITNESSES, witnesses, clear=True):
            plan = self.plan([
                {"id": "a", "capability": "test.parallel.a"},
                {"id": "b", "capability": "test.parallel.b"},
            ], max_parallelism=2)
            out = vnext.execute({"project_id": "p", "plan": plan, "expected_plan_digest": plan["plan_digest"]})
        self.assertEqual(out["status"], "COMPLETED")
        self.assertEqual(set(plan["stages"][0]), {"a", "b"})
        self.assertTrue(all(node["parallel_safe"] for node in plan["nodes"]))

    def test_unknown_or_mutating_effects_serialize(self):
        lock = threading.Lock(); active = {"count": 0, "peak": 0}
        def unsafe(name):
            def handler(payload):
                with lock:
                    active["count"] += 1; active["peak"] = max(active["peak"], active["count"])
                time.sleep(0.03)
                with lock:
                    active["count"] -= 1
                return {"name": name}
            return handler
        self._install("test.serial.a", side_effect_class="mutation", handler=unsafe("a"))
        self._install("test.serial.b", side_effect_class="mutation", handler=unsafe("b"))
        plan = self.plan([
            {"id": "a", "capability": "test.serial.a"},
            {"id": "b", "capability": "test.serial.b"},
        ], max_parallelism=16)
        out = vnext.execute({"project_id": "p", "plan": plan, "expected_plan_digest": plan["plan_digest"]})
        self.assertEqual(out["status"], "COMPLETED")
        self.assertEqual(active["peak"], 1)

    def test_approval_block_creates_authority_neutral_single_use_continuation(self):
        plan = self.plan([{"id": "write", "capability": "test.approved", "arguments": {"target": "A"}}])
        blocked = vnext.execute({"project_id": "p", "plan": plan, "expected_plan_digest": plan["plan_digest"]})
        self.assertEqual(blocked["status"], "BLOCKED")
        self.assertEqual(blocked["error_code"], "APPROVAL_REQUIRED")
        self.assertEqual(self.calls, [])
        continuation = blocked["continuation"]
        challenge = blocked["error"]["extra"]["approval_challenge"]
        resumed = vnext.resume({
            "project_id": "p",
            "continuation_handle": continuation["handle"],
            "resume_token": continuation["resume_token"],
            "expected_plan_digest": plan["plan_digest"],
            "authorities": {"write": {"approval_handle": challenge["handle"], "permit": True, "operator_id": "test"}},
        })
        self.assertEqual(resumed["status"], "COMPLETED")
        self.assertEqual(len(self.calls), 1)
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            vnext.resume({
                "project_id": "p",
                "continuation_handle": continuation["handle"],
                "resume_token": continuation["resume_token"],
                "expected_plan_digest": plan["plan_digest"],
                "authorities": {},
            })
        self.assertEqual(ctx.exception.error_code, "CONTINUATION_ALREADY_CONSUMED")


class ObserveTransferAndHttpTests(SchemaVNextFixture):
    def test_orient_reports_scheduler_gate_without_using_it_as_lease_authority(self):
        out = vnext.orient({"capabilities": ["test.echo"]})
        self.assertIn("scheduler_profile", out)
        self.assertEqual(out["lease"]["law"], "CAPABILITY_LEASE != CAPABILITY_GRANT")

    def test_observe_effect_profile_is_bounded_and_closed(self):
        out = vnext.observe({"kind": "effect_profile", "ref": "test.echo"})
        self.assertTrue(out["current"]); self.assertEqual(out["law"], "DESCRIPTIVE_EFFECT_TRAITS != SCHEDULER_AUTHORITY")
        self.assertEqual(out["capability"]["name"], "test.echo")
        self.assertNotIn("entries", out)

    def test_observe_validates_lease_plan_and_capability(self):
        lease = self.lease("test.echo")
        self.assertTrue(vnext.observe({"kind": "lease", "lease": lease})["validation"]["current"])
        plan = self.plan([{"id": "a", "capability": "test.echo"}])
        self.assertTrue(vnext.observe({"kind": "plan", "plan": plan, "expected_plan_digest": plan["plan_digest"]})["current"])
        card = vnext.observe({"kind": "capability", "ref": "test.echo"})
        self.assertEqual(card["capability"]["name"], "test.echo")

    def test_observe_result_preview_and_range_reuse_native_result_store(self):
        meta = store_result("p", {"blob": "x" * 20000}, label="large")
        preview = vnext.observe({"kind": "result", "project_id": "p", "ref": meta["handle"], "mode": "preview"})
        self.assertTrue(preview["summary"]["truncated"])
        ranged = vnext.observe({"kind": "result", "project_id": "p", "ref": meta["handle"], "mode": "range", "length_bytes": 1024})
        self.assertLessEqual(ranged["length_bytes"], 1024)
        self.assertEqual(ranged["sha256"], meta["sha256"])

    def test_transfer_maps_only_to_native_transfer_capabilities(self):
        card = {"contract_digest": "a" * 64}
        with patch.object(vnext, "_cards", return_value={"transfer.meta": card}), patch.object(vnext, "dispatch_tool", return_value={"ok": True}) as dispatch:
            out = vnext.transfer({"action": "meta", "arguments": {"ticket": "x"}})
        self.assertTrue(out["ok"])
        self.assertEqual(dispatch.call_args.args[0], "transfer.meta")
        self.assertEqual(dispatch.call_args.kwargs["expected_contract_digest"], "a" * 64)

    def test_all_eight_external_primitives_are_registered_and_orient_works(self):
        app = Flask(__name__)
        app.register_blueprint(lab_routes.lab_bp)
        rules = {rule.rule for rule in app.url_map.iter_rules()}
        expected = {
            "/lab/vnext/orient", "/lab/vnext/invoke", "/lab/batch", "/lab/vnext/compose",
            "/lab/vnext/execute", "/lab/vnext/observe", "/lab/vnext/resume", "/lab/vnext/transfer",
        }
        self.assertTrue(expected.issubset(rules))
        with app.test_client() as client, patch.object(lab_routes, "require_valid_api_key", return_value=None):
            response = client.post("/lab/vnext/orient", json={"capabilities": ["test.echo"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["count"], 1)

    def test_http_flow_resolves_backward_dataflow_without_model_roundtrip(self):
        app = Flask(__name__)
        app.register_blueprint(lab_routes.lab_bp)
        steps = [
            {
                "id": "producer",
                "tool_name": "test.producer",
                "payload": {"value": 17},
                "expected_contract_digest": lab_tools._TOOL_REGISTRY["test.producer"].contract_digest,
            },
            {
                "id": "consumer",
                "tool_name": "test.consumer",
                "payload": {"x": {"$ref": "producer.result.value"}},
                "expected_contract_digest": lab_tools._TOOL_REGISTRY["test.consumer"].contract_digest,
            },
        ]
        with app.test_client() as client, patch.object(lab_routes, "require_valid_api_key", return_value=None):
            response = client.post("/lab/batch", json={"steps": steps, "parallelism": 1, "stop_on_error": True})
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["results"][1]["id"], "consumer")
        self.assertEqual(body["results"][1]["result"]["got"], 17)

    def test_http_flow_rejects_ref_parallelism_before_dispatch(self):
        app = Flask(__name__)
        app.register_blueprint(lab_routes.lab_bp)
        steps = [
            {
                "id": "producer",
                "tool_name": "test.producer",
                "payload": {"value": 1},
                "expected_contract_digest": lab_tools._TOOL_REGISTRY["test.producer"].contract_digest,
            },
            {
                "id": "consumer",
                "tool_name": "test.consumer",
                "payload": {"x": {"$ref": "producer.result.value"}},
                "expected_contract_digest": lab_tools._TOOL_REGISTRY["test.consumer"].contract_digest,
            },
        ]
        with app.test_client() as client, patch.object(lab_routes, "require_valid_api_key", return_value=None):
            response = client.post("/lab/batch", json={"steps": steps, "parallelism": 2, "stop_on_error": False})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["error_code"], "BATCH_DATAFLOW_REQUIRES_SEQUENTIAL")

    def test_http_observe_effect_profile_returns_bounded_scheduler_truth(self):
        app = Flask(__name__)
        app.register_blueprint(lab_routes.lab_bp)
        with app.test_client() as client, patch.object(lab_routes, "require_valid_api_key", return_value=None):
            response = client.post("/lab/vnext/observe", json={"kind": "effect_profile", "ref": "test.echo"})
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["current"])
        self.assertEqual(body["capability"]["name"], "test.echo")
        self.assertNotIn("entries", body)


if __name__ == "__main__":
    unittest.main()
