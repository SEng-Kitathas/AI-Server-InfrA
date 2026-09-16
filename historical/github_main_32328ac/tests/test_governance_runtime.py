from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'baseline'))

import governance_runtime as gr
import lab_tools


def pressure(pid): return {"semantic_id":pid,"label":pid,"provenance":"fixture","description":pid}
def env(eid): return {"semantic_id":eid,"label":eid,"provenance":"fixture"}


class FiniteExhaustionTests(unittest.TestCase):
    def boolean(self):
        return {"grammar_mode":gr.GRAMMAR_BOOLEAN,"pressures":[pressure("A"),pressure("B")],"basis_justification":"fixture independent basis","basis_evidence_digest":"sha:fixture","all_subsets_lawful":True}
    def constrained(self):
        return {"grammar_mode":gr.GRAMMAR_CONSTRAINED,"pressures":[pressure("BASE"),pressure("REC")],"lawful_state_mode":"EXPLICIT_FINITE_SET","lawful_state_spec":[[],["BASE"],["BASE","REC"]],"relations":[{"type":"IMPLICATION","if":"REC","then":"BASE"}]}
    def test_boolean_reference_is_4_pressure_8_joint(self):
        out=gr.enumerate_lawful_frame(self.boolean(),[env("E0"),env("E1")],compatibility={"compatibility_mode":gr.COMPAT_CROSS})
        self.assertEqual(out["required_case_count"],8); self.assertEqual(out["evaluations"],8)
    def test_constrained_reference_is_3_pressure_5_joint(self):
        compat={"compatibility_mode":gr.COMPAT_EXPLICIT,"lawful_joint_spec":[["T",[]],["T",["BASE"]],["U",[]],["U",["BASE"]],["U",["BASE","REC"]]]}
        out=gr.enumerate_lawful_frame(self.constrained(),[env("T"),env("U")],compatibility=compat)
        self.assertEqual(out["required_case_count"],5)
    def test_insufficient_budget_performs_zero_evaluations(self):
        out=gr.enumerate_lawful_frame(self.boolean(),[env("E0"),env("E1")],compatibility={"compatibility_mode":gr.COMPAT_CROSS},budget=7)
        self.assertEqual(out["state"],"DEFER_UNKNOWN_INSUFFICIENT_BUDGET"); self.assertEqual(out["evaluations"],0)
    def test_unique_labels_do_not_mint_boolean_basis(self):
        bad=self.boolean(); bad["basis_evidence_digest"]=""
        with self.assertRaisesRegex(gr.GovernanceError,"Boolean basis"): gr.enumerate_lawful_frame(bad,[env("E")],compatibility={"compatibility_mode":gr.COMPAT_CROSS})
    def test_constrained_does_not_inherit_unconditional_cross_product(self):
        with self.assertRaises(gr.GovernanceError) as ctx: gr.enumerate_lawful_frame(self.constrained(),[env("T")],compatibility={"compatibility_mode":gr.COMPAT_CROSS})
        self.assertEqual(ctx.exception.code,"ENVIRONMENT_COMPATIBILITY_UNPROVEN")
    def test_unlawful_joint_rejected(self):
        compat={"compatibility_mode":gr.COMPAT_EXPLICIT,"lawful_joint_spec":[["T",["REC"]]]}
        with self.assertRaises(gr.GovernanceError): gr.enumerate_lawful_frame(self.constrained(),[env("T")],compatibility=compat)
    def test_pareto_preserves_tradeoff_vs_improvement(self):
        frame=["safety","latency"]; base={"safety":0,"latency":0}
        self.assertEqual(gr.pareto_relation(frame,{"safety":-1,"latency":1},base),"TRADEOFF")
        self.assertEqual(gr.pareto_relation(frame,{"safety":1,"latency":1},base),"STRICT_IMPROVEMENT")
    def test_incomplete_frame_fails_closed(self):
        with self.assertRaises(gr.GovernanceError) as ctx: gr.pareto_relation(["safety","latency"],{"latency":1},{"safety":0,"latency":0})
        self.assertEqual(ctx.exception.code,"INCOMPLETE_RESPONSIBILITY_FRAME")
    def test_failure_is_not_unchanged(self):
        bind={"grammar_digest":"g","environment_digest":"e","evaluator_digest":"v","baseline_id":"b","baseline_version":"1","baseline_digest":"d","baseline_current":True}
        with self.assertRaises(gr.GovernanceError) as ctx: gr.evaluate_effect_table(frame=["x"],baseline={"x":0},baseline_binding=bind,case_effects=[{"case_digest":"c","status":"FAILED"}],expected_case_digests=["c"])
        self.assertEqual(ctx.exception.code,"EVALUATOR_FAILURE")
    def test_stale_baseline_fails_closed(self):
        bind={"grammar_digest":"g","environment_digest":"e","evaluator_digest":"v","baseline_id":"b","baseline_version":"1","baseline_digest":"d","baseline_current":False}
        with self.assertRaises(gr.GovernanceError) as ctx: gr.evaluate_effect_table(frame=["x"],baseline={"x":0},baseline_binding=bind,case_effects=[],expected_case_digests=[])
        self.assertEqual(ctx.exception.code,"BASELINE_NOT_CURRENT")
    def test_witness_antichain_uses_lawful_state_order(self):
        cases=[{"case_digest":"a","environment_id":"E","pressure_state":["A"]},{"case_digest":"ab","environment_id":"E","pressure_state":["A","B"]},{"case_digest":"b","environment_id":"E","pressure_state":["B"]}]
        out=gr.compress_minimal_witnesses(cases=cases,witness_case_digests=["a","ab","b"]); self.assertEqual(set(out["minimal_case_digests"]),{"a","b"})
    def test_superset_inheritance_requires_monotonicity_evidence(self):
        cases=[{"case_digest":"a","environment_id":"E","pressure_state":["A"]}]
        with self.assertRaises(gr.GovernanceError) as ctx: gr.compress_minimal_witnesses(cases=cases,witness_case_digests=["a"],inherit_supersets=True)
        self.assertEqual(ctx.exception.code,"MONOTONICITY_EVIDENCE_REQUIRED")


class GovernanceContactTests(unittest.TestCase):
    def specimen(self, locator: str, digest: str):
        task={"task_id":"t1","project_scopes":["demo"],"mutation_class":"PROJECT_STATE","consequence_classes":["state"],"mechanism_tags":["CURRENTNESS_GUARD"],"touched_paths":["state/x.md"],"capabilities":["project.write"]}
        contact={"contact_id":"intent","locator":locator,"authority_class":"COMMANDERS_INTENT","semantic_extent":"FULL_ARTIFACT","currentness_required":True,"commit_recheck":"LOCAL_FILE_SHA256","expected_sha256":digest,"reason":"current intent"}
        sidecar={"sidecar_id":"intent-current","project_scope":"demo","subject":{"locator":locator,"sha256":digest},"authority_class":"COMMANDERS_INTENT","currentness":{"status":"CURRENT","basis":"fixture"},"contact_rules":[{"rule_id":"all-state","selectors":{"mutation_classes":["PROJECT_STATE"]},"contact":contact}]}
        profile={"profile_id":"demo-current","project_scope":"demo","currentness":{"status":"CURRENT","basis":"fixture"},"rules":[{"rule_id":"orient","selectors":{"mutation_classes":["PROJECT_STATE"]},"required_authority_classes":["COMMANDERS_INTENT"],"required_sidecar_ids":["intent-current"]}]}
        return {"project_profiles":[profile],"sidecars":[sidecar]},task
    def test_missing_profile_rejects(self):
        catalog={"project_profiles":[],"sidecars":[]}; task={"task_id":"t","project_scopes":["x"],"mutation_class":"PROJECT_STATE","consequence_classes":[],"mechanism_tags":[],"touched_paths":[],"capabilities":[]}
        out=gr.derive_contact_set(catalog,task); self.assertEqual(out["state"],"CONTACT_SET_REJECTED")
    def test_ack_only_receipt_rejects(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'intent.md'; p.write_text('intent',encoding='utf-8'); h=hashlib.sha256(p.read_bytes()).hexdigest(); catalog,task=self.specimen(str(p),h); cs=gr.derive_contact_set(catalog,task)
            receipt={"contact_set_digest":cs["contact_set_digest"],"contact_id":"intent","locator":str(p),"observed_sha256":h,"semantic_extent":"FULL_ARTIFACT","governing_scope":"demo|t1","currentness_basis":"current","read_note":"ACK"}
            out=gr.admit_contact_set(cs,[receipt],catalog=catalog,task=task,project_root=Path(td)); self.assertEqual(out["state"],"CONTACT_SET_REJECTED"); self.assertEqual(out["errors"][0]["error"],"NON_SUBSTANTIVE_ACKNOWLEDGEMENT_NOTE")
    def test_local_drift_after_receipt_rejects(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'intent.md'; p.write_text('intent',encoding='utf-8'); h=hashlib.sha256(p.read_bytes()).hexdigest(); catalog,task=self.specimen(str(p),h); cs=gr.derive_contact_set(catalog,task)
            receipt={"contact_set_digest":cs["contact_set_digest"],"contact_id":"intent","locator":str(p),"observed_sha256":h,"semantic_extent":"FULL_ARTIFACT","governing_scope":"demo|t1","currentness_basis":"current","read_note":"read complete current intent"}
            p.write_text('drift',encoding='utf-8'); out=gr.admit_contact_set(cs,[receipt],catalog=catalog,task=task,project_root=Path(td)); self.assertEqual(out["state"],"CONTACT_SET_REJECTED"); self.assertIn("LOCAL_SOURCE_DRIFT_AT_ADMISSION",{e["error"] for e in out["errors"]})
    def test_contact_set_self_deletion_and_resign_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'intent.md'; p.write_text('intent',encoding='utf-8'); h=hashlib.sha256(p.read_bytes()).hexdigest(); catalog,task=self.specimen(str(p),h); cs=gr.derive_contact_set(catalog,task)
            forged=dict(cs); forged["entries"]=[]; forged["orientation_requirements"]=[]; forged["contact_set_digest"]=gr.digest({k:v for k,v in forged.items() if k!="contact_set_digest"})
            with self.assertRaises(gr.GovernanceError) as ctx: gr.admit_contact_set(forged,[],catalog=catalog,task=task,project_root=Path(td))
            self.assertEqual(ctx.exception.code,"GOVERNANCE_CONTACT_SET_STALE")
    def test_task_scope_change_after_resolve_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'intent.md'; p.write_text('intent',encoding='utf-8'); h=hashlib.sha256(p.read_bytes()).hexdigest(); catalog,task=self.specimen(str(p),h); cs=gr.derive_contact_set(catalog,task); changed=dict(task); changed["task_id"]="t2"
            with self.assertRaises(gr.GovernanceError) as ctx: gr.admit_contact_set(cs,[],catalog=catalog,task=changed,project_root=Path(td))
            self.assertEqual(ctx.exception.code,"GOVERNANCE_CONTACT_SET_STALE")
    def test_local_recheck_cannot_escape_project_scope(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as outside:
            p=Path(outside)/'intent.md'; p.write_text('intent',encoding='utf-8'); h=hashlib.sha256(p.read_bytes()).hexdigest(); catalog,task=self.specimen(str(p),h); cs=gr.derive_contact_set(catalog,task)
            receipt={"contact_set_digest":cs["contact_set_digest"],"contact_id":"intent","locator":str(p),"observed_sha256":h,"semantic_extent":"FULL_ARTIFACT","governing_scope":"demo|t1","currentness_basis":"current","read_note":"read complete current intent"}
            out=gr.admit_contact_set(cs,[receipt],catalog=catalog,task=task,project_root=Path(td)); self.assertIn("LOCAL_SOURCE_OUTSIDE_PROJECT_SCOPE",{e["error"] for e in out["errors"]})
    def test_valid_contact_is_satisfied_but_authority_none(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'intent.md'; p.write_text('intent',encoding='utf-8'); h=hashlib.sha256(p.read_bytes()).hexdigest(); catalog,task=self.specimen(str(p),h); cs=gr.derive_contact_set(catalog,task)
            receipt={"contact_set_digest":cs["contact_set_digest"],"contact_id":"intent","locator":str(p),"observed_sha256":h,"semantic_extent":"FULL_ARTIFACT","governing_scope":"demo|t1","currentness_basis":"current","read_note":"read complete current intent"}
            out=gr.admit_contact_set(cs,[receipt],catalog=catalog,task=task,project_root=Path(td)); self.assertEqual(out["state"],"CONTACT_SET_SATISFIED"); self.assertEqual(out["authority_effect"],"NONE")


class RuntimeProjectionTests(unittest.TestCase):
    def test_native_tools_are_registered_and_read_only(self):
        for name in ("governance.contacts.resolve","governance.contacts.admit","governance.exhaustion.enumerate","governance.exhaustion.evaluate_table","governance.exhaustion.compress_witnesses"):
            spec=lab_tools._TOOL_REGISTRY[name]; self.assertEqual(spec.side_effect_class,"read"); self.assertFalse(spec.mutating)
    def test_stale_contract_rejected_before_handler(self):
        name="governance.exhaustion.enumerate"; spec=lab_tools._TOOL_REGISTRY[name]
        with self.assertRaises(lab_tools.LabToolError) as ctx: lab_tools.dispatch_tool(name,{},expected_contract_digest="0"*64)
        self.assertEqual(ctx.exception.error_code,"CAPABILITY_CONTRACT_STALE")
        self.assertNotEqual(spec.contract_digest,"0"*64)


if __name__=='__main__': unittest.main()
