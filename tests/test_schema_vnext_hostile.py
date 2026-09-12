from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baseline"))

from pcmmad_receiver import approval_authority as aa
from pcmmad_receiver import lab_tools
from pcmmad_receiver import schema_vnext_runtime as vnext
from pcmmad_receiver import shared_core
from pcmmad_receiver.control_plane_models import ToolSpec
from pcmmad_receiver import scheduler_effect_profile as effect_profile


class HostileFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pcmmad-schema-hostile-")
        self.root = Path(self.temp.name)
        self.old_projects = shared_core.PROJECTS_ROOT
        shared_core.PROJECTS_ROOT = self.root / "projects"
        self.approval_patch = patch.object(aa, "SYSTEM_ROOT", self.root / "system")
        self.approval_patch.start()
        self.env_patch = patch.dict(os.environ, {"PCMMAD_LAB_POLICY_MODE":"strict","PCMMAD_ALLOW_LEGACY_INLINE_APPROVAL":"0"}, clear=False)
        self.env_patch.start()
        self.original_registry = dict(lab_tools._TOOL_REGISTRY)
        self.effects = []
        self.install("h.read", effect="read", handler=lambda p: {"value": p.get("value", 1)})
        self.install("h.mutate", effect="mutation", approval=True, danger="high", handler=self.logged("mutate"))
        self.install("h.cache", effect="read_cache", handler=self.logged("cache"), traits=["writes_ephemeral_cache"])
        self.install("h.unknown", effect="read_cache", handler=self.logged("unknown"))
        self.install("h.big", effect="read", handler=lambda p: {"blob":"x"*30000})
        self.read_counter = {"value": 0}
        def changing_read(_payload):
            self.read_counter["value"] += 1
            return {"value": self.read_counter["value"]}
        self.install("h.changing_read", effect="read", handler=changing_read)
        self.install("h.cache_effect", effect="read_cache", handler=self.logged("cache-effect"), traits=["writes_ephemeral_cache"])
        self.effect_profile_patch = patch.object(vnext, "_current_scheduler_profile", side_effect=self._test_effect_profile)
        self.effect_profile_patch.start()

    def tearDown(self):
        with lab_tools._REGISTRY_LOCK:
            lab_tools._TOOL_REGISTRY.clear(); lab_tools._TOOL_REGISTRY.update(self.original_registry)
        self.effect_profile_patch.stop(); self.env_patch.stop(); self.approval_patch.stop(); shared_core.PROJECTS_ROOT=self.old_projects
        self.temp.cleanup()

    def logged(self, name):
        def fn(payload):
            self.effects.append((name, dict(payload)))
            return {"name":name,"payload":dict(payload)}
        return fn

    def install(self,name,*,version="1",effect="read",approval=False,danger="low",handler=None,traits=None):
        spec=ToolSpec(name=name,description=name,danger_tier=danger,category="hostile",approval_required=approval,mutating=False,input_schema={"type":"object","additionalProperties":True},output_schema={"type":"object","additionalProperties":True},capability_version=version,schema_version="1",side_effect_class=effect,effect_traits=list(traits or ["hostile_test"]),handler=handler or (lambda p:dict(p)))
        with lab_tools._REGISTRY_LOCK: lab_tools._TOOL_REGISTRY[name]=spec
        return spec

    def _test_effect_profile(self):
        cards = vnext._cards()
        profile = effect_profile.build_profile(cards)
        verification = effect_profile.verify_profile(profile, cards)
        return profile, verification, effect_profile.entry_map(profile)

    def compose(self,nodes,**extra):
        return vnext.compose({"project_id":"p","nodes":nodes,**extra})["plan"]

    def resign(self,plan):
        core=dict(plan); core.pop("plan_digest",None); plan["plan_digest"]=vnext._hash_json(core); return plan


class PlanDerivationHostiles(HostileFixture):
    def test_forged_parallel_safe_flag_rejected_even_with_recomputed_plan_digest(self):
        plan=self.compose([{"id":"x","capability":"h.cache"}])
        plan["nodes"][0]["parallel_safe"]=True; self.resign(plan)
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            vnext.execute({"project_id":"p","plan":plan,"expected_plan_digest":plan["plan_digest"]})
        self.assertEqual(ctx.exception.error_code,"PLAN_DERIVATION_TAMPERED")
        self.assertEqual(self.effects,[])

    def test_forged_effect_metadata_rejected_even_with_recomputed_digest(self):
        plan=self.compose([{"id":"x","capability":"h.unknown"}])
        plan["nodes"][0]["effect"]["side_effect_class"]="read"; self.resign(plan)
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            vnext.execute({"project_id":"p","plan":plan,"expected_plan_digest":plan["plan_digest"]})
        self.assertEqual(ctx.exception.error_code,"PLAN_DERIVATION_TAMPERED")

    def test_forged_stages_rejected_even_with_recomputed_digest(self):
        plan=self.compose([{"id":"a","capability":"h.read"},{"id":"b","capability":"h.read","depends_on":["a"]}])
        plan["stages"]=[["a","b"]]; self.resign(plan)
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            vnext.execute({"project_id":"p","plan":plan,"expected_plan_digest":plan["plan_digest"]})
        self.assertEqual(ctx.exception.error_code,"PLAN_DERIVATION_TAMPERED")

    def test_ref_dependency_removed_after_compose_rejected(self):
        plan=self.compose([{"id":"a","capability":"h.read"},{"id":"b","capability":"h.read","arguments":{"value":{"$ref":"a.result.value"}}}])
        plan["nodes"][1]["depends_on"]=[]; plan["stages"]=[["a","b"]]; self.resign(plan)
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            vnext.execute({"project_id":"p","plan":plan,"expected_plan_digest":plan["plan_digest"]})
        self.assertEqual(ctx.exception.error_code,"PLAN_INVALID")

    def test_execute_project_mismatch_rejected(self):
        plan=self.compose([{"id":"a","capability":"h.read"}])
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            vnext.execute({"project_id":"other","plan":plan,"expected_plan_digest":plan["plan_digest"]})
        self.assertEqual(ctx.exception.error_code,"PLAN_PROJECT_MISMATCH")

    def test_33_nodes_rejected(self):
        nodes=[{"id":f"n{i}","capability":"h.read"} for i in range(33)]
        with self.assertRaises(lab_tools.LabToolError) as ctx: self.compose(nodes)
        self.assertEqual(ctx.exception.error_code,"PLAN_LIMIT_EXCEEDED")

    def test_unknown_assertion_ref_rejected_at_compose(self):
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            self.compose([{"id":"a","capability":"h.read"}], assertions=[{"ref":"missing.result.x","op":"eq","value":1}])
        self.assertEqual(ctx.exception.error_code,"BAD_PLAN")

    def test_plan_size_bound_rejects_huge_arguments(self):
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            self.compose([{"id":"a","capability":"h.read","arguments":{"blob":"x"*70000}}])
        self.assertEqual(ctx.exception.error_code,"PLAN_TOO_LARGE")


class AuthorityAndConsequenceHostiles(HostileFixture):
    def test_nested_inline_authority_in_arguments_does_not_bypass_native_policy(self):
        plan=self.compose([{"id":"m","capability":"h.mutate","arguments":{"target":"A","authority":{"permit":True}}}])
        out=vnext.execute({"project_id":"p","plan":plan,"expected_plan_digest":plan["plan_digest"]})
        self.assertEqual(out["status"],"BLOCKED")
        self.assertEqual(out["error_code"],"APPROVAL_REQUIRED")
        self.assertEqual(self.effects,[])

    def test_postcondition_failure_after_mutation_preserves_consequence_evidence(self):
        # Advisory mode is used only to isolate postcondition semantics from approval mechanics.
        plan=self.compose([{"id":"m","capability":"h.mutate","arguments":{"target":"A"}}], assertions=[{"ref":"m.result.name","op":"eq","value":"not-mutate"}])
        with patch.dict(os.environ,{"PCMMAD_LAB_POLICY_MODE":"advisory"},clear=False):
            out=vnext.execute({"project_id":"p","plan":plan,"expected_plan_digest":plan["plan_digest"]})
        self.assertEqual(out["status"],"POSTCONDITION_FAILED")
        self.assertEqual(len(self.effects),1)
        self.assertEqual(out["results"]["m"]["result"]["name"],"mutate")
        self.assertIn("not transactional",out["warning"])

    def test_bad_resume_token_fails_before_effect_and_does_not_consume(self):
        plan=self.compose([{"id":"m","capability":"h.mutate","arguments":{"target":"A"}}])
        blocked=vnext.execute({"project_id":"p","plan":plan,"expected_plan_digest":plan["plan_digest"]})
        cont=blocked["continuation"]; challenge=blocked["error"]["extra"]["approval_challenge"]
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            vnext.resume({"project_id":"p","continuation_handle":cont["handle"],"resume_token":"wrong-token-xxxxxxxx","expected_plan_digest":plan["plan_digest"],"authorities":{"m":{"approval_handle":challenge["handle"],"permit":True}}})
        self.assertEqual(ctx.exception.error_code,"CONTINUATION_TOKEN_INVALID")
        self.assertEqual(self.effects,[])
        good=vnext.resume({"project_id":"p","continuation_handle":cont["handle"],"resume_token":cont["resume_token"],"expected_plan_digest":plan["plan_digest"],"authorities":{"m":{"approval_handle":challenge["handle"],"permit":True}}})
        self.assertEqual(good["status"],"COMPLETED")

    def test_concurrent_resume_exactly_one_claims_continuation(self):
        plan=self.compose([{"id":"m","capability":"h.mutate","arguments":{"target":"A"}}])
        blocked=vnext.execute({"project_id":"p","plan":plan,"expected_plan_digest":plan["plan_digest"]})
        cont=blocked["continuation"]; challenge=blocked["error"]["extra"]["approval_challenge"]
        barrier=threading.Barrier(2); outcomes=[]; lock=threading.Lock()
        def worker():
            barrier.wait(timeout=3)
            try:
                row=vnext.resume({"project_id":"p","continuation_handle":cont["handle"],"resume_token":cont["resume_token"],"expected_plan_digest":plan["plan_digest"],"authorities":{"m":{"approval_handle":challenge["handle"],"permit":True}}})
                outcome=("ok",row.get("status"))
            except lab_tools.LabToolError as exc:
                outcome=("error",exc.error_code)
            with lock: outcomes.append(outcome)
        ts=[threading.Thread(target=worker) for _ in range(2)]
        [t.start() for t in ts]; [t.join(timeout=5) for t in ts]
        self.assertEqual(sum(x[0]=="ok" for x in outcomes),1)
        self.assertEqual(sum(x==( "error","CONTINUATION_ALREADY_CONSUMED") for x in outcomes),1)
        self.assertEqual(len(self.effects),1)

    def test_stale_capability_on_resume_does_not_consume_continuation(self):
        plan=self.compose([{"id":"m","capability":"h.mutate","arguments":{"target":"A"}}])
        blocked=vnext.execute({"project_id":"p","plan":plan,"expected_plan_digest":plan["plan_digest"]})
        cont=blocked["continuation"]
        self.install("h.mutate",version="2",effect="mutation",approval=True,danger="high",handler=self.logged("v2"))
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            vnext.resume({"project_id":"p","continuation_handle":cont["handle"],"resume_token":cont["resume_token"],"expected_plan_digest":plan["plan_digest"],"authorities":{}})
        self.assertEqual(ctx.exception.error_code,"PLAN_CAPABILITY_STALE")
        observed=vnext.observe({"kind":"continuation","project_id":"p","ref":cont["handle"]})
        self.assertFalse(observed["claimed"])


    def test_resume_reexecutes_completed_reads_instead_of_reusing_stale_evidence(self):
        spec=lab_tools._TOOL_REGISTRY["h.changing_read"]
        truth={"h.changing_read":{"contract_digest":spec.contract_digest,"effect_kind":"READ_LOCAL","evidence":"test:changing-read-truth"}}
        witness={"h.changing_read":{"contract_digest":spec.contract_digest,"evidence":"test:changing-read-replay"}}
        with patch.dict(effect_profile.EFFECT_TRUTH_VERIFICATION_WITNESSES,truth,clear=True), patch.dict(effect_profile.PARALLEL_VERIFICATION_WITNESSES,{},clear=True), patch.dict(effect_profile.RESUME_REPLAY_VERIFICATION_WITNESSES,witness,clear=True):
            plan=self.compose([
                {"id":"read","capability":"h.changing_read"},
                {"id":"write","capability":"h.mutate","arguments":{"target":{"$ref":"read.result.value"}}},
            ])
            blocked=vnext.execute({"project_id":"p","plan":plan,"expected_plan_digest":plan["plan_digest"]})
            self.assertEqual(blocked["status"],"BLOCKED")
            self.assertEqual(self.read_counter["value"],1)
            cont=blocked["continuation"]; challenge=blocked["error"]["extra"]["approval_challenge"]
            resumed=vnext.resume({
                "project_id":"p","continuation_handle":cont["handle"],"resume_token":cont["resume_token"],
                "expected_plan_digest":plan["plan_digest"],
                "authorities":{"write":{"approval_handle":challenge["handle"],"permit":True,"operator_id":"test"}},
            })
        self.assertEqual(self.read_counter["value"],2)
        self.assertEqual(resumed["status"],"FAILED")
        self.assertEqual(resumed["failures"][0]["error_code"],"APPROVAL_ARGUMENTS_MISMATCH")
        self.assertEqual(self.effects,[])

    def test_prior_unwitnessed_read_forces_recovery_not_automatic_continuation(self):
        plan=self.compose([
            {"id":"read","capability":"h.read"},
            {"id":"write","capability":"h.mutate","depends_on":["read"],"arguments":{"target":"A"}},
        ])
        blocked=vnext.execute({"project_id":"p","plan":plan,"expected_plan_digest":plan["plan_digest"]})
        self.assertEqual(blocked["status"],"BLOCKED_RECOVERY_REQUIRED")
        self.assertIsNone(blocked["continuation"])
        self.assertEqual(blocked["unsafe_completed_nodes"],["read"])

    def test_prior_cache_effect_forces_recovery_not_automatic_continuation(self):
        plan=self.compose([
            {"id":"cache","capability":"h.cache_effect"},
            {"id":"write","capability":"h.mutate","depends_on":["cache"],"arguments":{"target":"A"}},
        ])
        blocked=vnext.execute({"project_id":"p","plan":plan,"expected_plan_digest":plan["plan_digest"]})
        self.assertEqual(blocked["status"],"BLOCKED_RECOVERY_REQUIRED")
        self.assertIsNone(blocked["continuation"])
        self.assertEqual(blocked["unsafe_completed_nodes"],["cache"])
        self.assertEqual(blocked["law"],"CONTINUATION != CURRENTNESS")
        self.assertEqual([name for name,_ in self.effects],["cache-effect"])


    def test_compact_plan_cannot_expand_huge_dataflow_into_downstream_arguments(self):
        plan=self.compose([
            {"id":"a","capability":"h.big"},
            {"id":"b","capability":"h.read","arguments":{
                "x":{"$ref":"a.result.blob"},
                "y":{"$ref":"a.result.blob"},
                "z":{"$ref":"a.result.blob"},
            }},
        ])
        out=vnext.execute({"project_id":"p","plan":plan,"expected_plan_digest":plan["plan_digest"]})
        self.assertEqual(out["status"],"FAILED")
        self.assertEqual(out["failures"][0]["error_code"],"PLAN_DATAFLOW_ARGUMENT_TOO_LARGE")
        self.assertEqual([name for name,_ in self.effects],[])

    def test_rehashed_resolved_argument_ceiling_tamper_is_rejected(self):
        plan=self.compose([{"id":"a","capability":"h.read"}])
        plan["max_resolved_argument_bytes"]=10_000_000
        core=dict(plan); core.pop("plan_digest",None); plan["plan_digest"]=vnext._hash_json(core)
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            vnext.execute({"project_id":"p","plan":plan,"expected_plan_digest":plan["plan_digest"]})
        self.assertEqual(ctx.exception.error_code,"PLAN_DERIVATION_TAMPERED")


class BoundednessAndDiscoveryHostiles(HostileFixture):
    def test_completed_large_plan_result_materializes_to_existing_result_store(self):
        plan=self.compose([{"id":"big","capability":"h.big"}])
        out=vnext.execute({"project_id":"p","plan":plan,"expected_plan_digest":plan["plan_digest"]})
        self.assertEqual(out["status"],"COMPLETED")
        self.assertIn("result_handle",out)
        self.assertNotIn("results",out)
        meta=vnext.observe({"kind":"result","project_id":"p","ref":out["result_handle"]["handle"],"mode":"metadata"})
        self.assertGreater(meta["bytes"],vnext.PLAN_INLINE_SAFE_BYTES)

    def test_irrelevant_goal_does_not_return_arbitrary_alphabetical_capabilities(self):
        out=vnext.orient({"goal":"zzzzzzzzzzzzzzzzzz","categories":["hostile"]})
        self.assertEqual(out["count"],0)
        self.assertIsNone(out["lease"])

    def test_read_cache_and_unknown_are_never_parallel_safe(self):
        plan=self.compose([{"id":"cache","capability":"h.cache"},{"id":"unknown","capability":"h.unknown"}])
        flags={n["id"]:n["parallel_safe"] for n in plan["nodes"]}
        self.assertEqual(flags,{"cache":False,"unknown":False})

    def test_self_hashed_forged_lease_grants_no_approval_authority(self):
        base=vnext.orient({"capabilities":["h.read"]})["lease"]
        base["selected"]=[{"name":"h.mutate","contract_digest":lab_tools._TOOL_REGISTRY["h.mutate"].contract_digest}]
        core=dict(base); core.pop("lease_digest"); base["lease_digest"]=vnext._hash_json(core)
        # Lease is deliberately a self-consistency/currentness capsule, not a signature or authority token.
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            vnext.invoke({"capability":"h.mutate","arguments":{"target":"A"},"lease":base})
        self.assertEqual(ctx.exception.error_code,"APPROVAL_REQUIRED")
        self.assertEqual(self.effects,[])


if __name__ == "__main__":
    unittest.main()
