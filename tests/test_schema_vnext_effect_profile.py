from __future__ import annotations

import ast, copy, json, unittest
from pathlib import Path
from unittest.mock import patch
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"baseline"))
from pcmmad_receiver import lab_tools
from pcmmad_receiver import scheduler_effect_profile as effect
from pcmmad_receiver import schema_vnext_runtime as vnext
from pcmmad_receiver.control_plane_models import ToolSpec

class ProductionEffectProfileTests(unittest.TestCase):
    def setUp(self):
        self.cards={row["name"]:row for row in lab_tools.list_tools()}
        self.profile=effect.load_profile()
    def test_profile_exactly_covers_live_159_capability_catalog(self):
        r=effect.verify_profile(self.profile,self.cards); self.assertTrue(r["current"]); self.assertEqual(r["capability_count"],159); self.assertEqual(set(x["name"] for x in self.profile["entries"]),set(self.cards)); self.assertEqual(lab_tools._PLUGIN_ERRORS,[])
    def test_closed_vocabularies_are_exact(self):
        self.assertEqual(self.profile["effect_kinds"],sorted(effect.EFFECT_KINDS)); self.assertEqual(self.profile["schedule_classes"],sorted(effect.SCHEDULE_CLASSES)); self.assertEqual(self.profile["resume_replay_classes"],sorted(effect.RESUME_REPLAY_CLASSES)); self.assertEqual(self.profile["retry_classes"],sorted(effect.RETRY_CLASSES)); self.assertEqual(self.profile["freshness_classes"],sorted(effect.FRESHNESS_CLASSES)); self.assertFalse(self.profile["descriptive_effect_traits_are_scheduler_authority"])
    def test_default_profile_has_zero_unearned_parallel_capabilities(self):
        r=effect.verify_profile(self.profile,self.cards); self.assertEqual(r["effect_truth_verified_count"],0); self.assertEqual(r["parallel_verified_count"],0); self.assertEqual(r["resume_replay_verified_count"],0); self.assertTrue(all(x["effect_kind"]=="UNVERIFIED" and x["static_cost_units"]==10 and x["schedule_class"]=="SERIAL" and x["resume_replay_class"]=="RECOMPOSE_REQUIRED" for x in self.profile["entries"]))
    def test_rehashed_parallel_tamper_is_rejected(self):
        f=copy.deepcopy(self.profile); f["entries"][0]["schedule_class"]="PARALLEL_READ_VERIFIED"; c=dict(f); c.pop("profile_digest",None); f["profile_digest"]=effect._hash_json(c)
        with self.assertRaises(lab_tools.LabToolError) as x: effect.verify_profile(f,self.cards)
        self.assertEqual(x.exception.error_code,"EFFECT_PROFILE_STALE")
    def test_rehashed_resume_replay_tamper_is_rejected(self):
        f=copy.deepcopy(self.profile); f["entries"][0]["resume_replay_class"]="REEXECUTE_READ_VERIFIED"; c=dict(f); c.pop("profile_digest",None); f["profile_digest"]=effect._hash_json(c)
        with self.assertRaises(lab_tools.LabToolError) as x: effect.verify_profile(f,self.cards)
        self.assertEqual(x.exception.error_code,"EFFECT_PROFILE_STALE")

    def test_removed_capability_is_rejected_even_with_rehash(self):
        f=copy.deepcopy(self.profile); f["entries"]=f["entries"][:-1]; f["capability_count"]=len(f["entries"]); c=dict(f); c.pop("profile_digest",None); f["profile_digest"]=effect._hash_json(c)
        with self.assertRaises(lab_tools.LabToolError) as x: effect.verify_profile(f,self.cards)
        self.assertEqual(x.exception.error_code,"EFFECT_PROFILE_INVALID")
    def test_catalog_contract_change_stales_profile(self):
        name=sorted(self.cards)[0]; changed=copy.deepcopy(self.cards); changed[name]=dict(changed[name]); changed[name]["contract_digest"]="0"*64
        with self.assertRaises(lab_tools.LabToolError) as x: effect.verify_profile(self.profile,changed)
        self.assertEqual(x.exception.error_code,"EFFECT_PROFILE_STALE")
    def test_descriptive_traits_never_choose_schedule_class(self):
        card=dict(next(iter(self.cards.values()))); card.update(name="synthetic.safe",side_effect_class="read",contract_digest="a"*64,effect_traits=["mutation","parallel_please"]); row=effect.derive_entry(card); self.assertEqual(row["declared_effect_kind"],"READ_LOCAL"); self.assertEqual(row["effect_kind"],"UNVERIFIED"); self.assertFalse(row["effect_truth_verified"]); self.assertEqual(row["static_cost_units"],10); self.assertEqual(row["schedule_class"],"SERIAL"); self.assertNotIn("effect_traits",row)
    def test_parallel_witness_without_effect_truth_witness_is_rejected(self):
        card=dict(next(iter(self.cards.values()))); card.update(name="synthetic.parallel",side_effect_class="read",contract_digest="b"*64)
        with patch.dict(effect.PARALLEL_VERIFICATION_WITNESSES,{"synthetic.parallel":{"contract_digest":"b"*64,"evidence":"parallel"}},clear=True):
            with self.assertRaises(lab_tools.LabToolError) as x: effect.derive_entry(card)
        self.assertEqual(x.exception.error_code,"EFFECT_PROFILE_INVALID")

    def test_effect_truth_witness_must_match_declared_effect_class(self):
        card=dict(next(iter(self.cards.values()))); card.update(name="synthetic.mismatch",side_effect_class="read",contract_digest="c"*64)
        with patch.dict(effect.EFFECT_TRUTH_VERIFICATION_WITNESSES,{"synthetic.mismatch":{"contract_digest":"c"*64,"effect_kind":"EXECUTION","evidence":"hostile"}},clear=True):
            with self.assertRaises(lab_tools.LabToolError) as x: effect.derive_entry(card)
        self.assertEqual(x.exception.error_code,"EFFECT_PROFILE_DECLARATION_MISMATCH")

    def test_verified_effect_truth_can_lower_cost_but_does_not_enable_parallel_by_itself(self):
        card=dict(next(iter(self.cards.values()))); card.update(name="synthetic.truth",side_effect_class="read",contract_digest="d"*64,idempotency_semantics="safe_repeat")
        truth={"synthetic.truth":{"contract_digest":"d"*64,"effect_kind":"READ_LOCAL","evidence":"effect-truth"}}
        with patch.dict(effect.EFFECT_TRUTH_VERIFICATION_WITNESSES,truth,clear=True):
            row=effect.derive_entry(card)
        self.assertTrue(row["effect_truth_verified"]); self.assertEqual(row["effect_kind"],"READ_LOCAL"); self.assertEqual(row["static_cost_units"],1); self.assertEqual(row["schedule_class"],"SERIAL"); self.assertEqual(row["resume_replay_class"],"RECOMPOSE_REQUIRED")

    def test_unknown_side_effect_class_cannot_enter_profile(self):
        card={"name":"bad.effect","contract_digest":"a"*64,"side_effect_class":"telepathy","category":"test","mutating":False,"effective_approval_required":False,"idempotency_semantics":"safe_repeat"}
        with self.assertRaises(lab_tools.LabToolError) as x: effect.derive_entry(card)
        self.assertEqual(x.exception.error_code,"EFFECT_PROFILE_UNCLASSIFIED")
    def test_static_cost_positive_and_closed(self):
        for row in self.profile["entries"]: self.assertIn(row["effect_kind"],effect.EFFECT_KINDS); self.assertGreater(row["static_cost_units"],0); self.assertEqual(row["static_cost_units"],effect.STATIC_COST_UNITS[row["effect_kind"]])

class SchedulerStructuralTests(unittest.TestCase):
    def test_critical_helpers_not_shadowed(self):
        tree=ast.parse(Path(vnext.__file__).read_text(encoding="utf-8")); names=[n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
        for n in ("_effect_snapshot","_current_scheduler_profile","_execute_plan_core","_store_continuation","compose","execute","resume"): self.assertEqual(names.count(n),1,n)
    def test_profile_file_content_addressable(self):
        v=json.loads(effect.PROFILE_PATH.read_text(encoding="utf-8")); self.assertEqual(v["schema"],effect.PROFILE_SCHEMA); self.assertEqual(len(v["profile_digest"]),64)

class StaticPlanCostTests(unittest.TestCase):
    def setUp(self):
        self.orig=dict(lab_tools._TOOL_REGISTRY)
        for name in ("cost.a","cost.b"): lab_tools._TOOL_REGISTRY[name]=ToolSpec(name=name,description=name,category="test",side_effect_class="execution",effect_traits=["synthetic"],input_schema={"type":"object"},output_schema={"type":"object"},handler=lambda p:{"ok":True})
        self.p=patch.object(vnext,"_current_scheduler_profile",side_effect=self.profile); self.p.start()
    def tearDown(self): self.p.stop(); lab_tools._TOOL_REGISTRY.clear(); lab_tools._TOOL_REGISTRY.update(self.orig)
    def profile(self):
        cards=vnext._cards(); p=effect.build_profile(cards); return p,effect.verify_profile(p,cards),effect.entry_map(p)
    def test_compose_refuses_plan_over_static_cost_budget(self):
        with self.assertRaises(lab_tools.LabToolError) as x: vnext.compose({"project_id":"p","max_cost_units":8,"nodes":[{"id":"a","capability":"cost.a"},{"id":"b","capability":"cost.b"}]})
        self.assertEqual(x.exception.error_code,"PLAN_COST_EXCEEDED")
    def test_rehashed_cost_tamper_rejected(self):
        plan=vnext.compose({"project_id":"p","max_cost_units":32,"nodes":[{"id":"a","capability":"cost.a"}]})["plan"]; plan["static_cost_units"]=1; c=dict(plan); c.pop("plan_digest",None); plan["plan_digest"]=vnext._hash_json(c)
        with self.assertRaises(lab_tools.LabToolError) as x: vnext.execute({"project_id":"p","plan":plan,"expected_plan_digest":plan["plan_digest"]})
        self.assertEqual(x.exception.error_code,"PLAN_DERIVATION_TAMPERED")

if __name__=="__main__": unittest.main()
