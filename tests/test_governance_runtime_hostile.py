from __future__ import annotations
import copy,hashlib,tempfile,unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'baseline'/'pcmmad_receiver'))
import governance_runtime as gr


def p(x): return {"semantic_id":x,"label":x,"provenance":"fixture","description":x}
def e(x): return {"semantic_id":x,"label":x,"provenance":"fixture"}

class GrammarHostile(unittest.TestCase):
    def boolean(self): return {"grammar_mode":gr.GRAMMAR_BOOLEAN,"pressures":[p("A"),p("B")],"basis_justification":"independent","basis_evidence_digest":"evidence","all_subsets_lawful":True}
    def constrained(self): return {"grammar_mode":gr.GRAMMAR_CONSTRAINED,"pressures":[p("BASE"),p("REC")],"lawful_state_mode":"EXPLICIT_FINITE_SET","lawful_state_spec":[[],["BASE"],["BASE","REC"]],"relations":[{"type":"IMPLICATION","if":"REC","then":"BASE"}]}
    def reject(self,grammar,envs=None,compat=None,budget=None):
        with self.assertRaises(gr.GovernanceError): gr.enumerate_lawful_frame(grammar,envs or [e("E")],compatibility=compat,budget=budget)
    def test_duplicate_semantic_id(self):
        g=self.boolean(); g["pressures"][1]["semantic_id"]="A"; self.reject(g,compat={"compatibility_mode":gr.COMPAT_CROSS})
    def test_duplicate_label(self):
        g=self.boolean(); g["pressures"][1]["label"]="A"; self.reject(g,compat={"compatibility_mode":gr.COMPAT_CROSS})
    def test_missing_basis_justification(self):
        g=self.boolean(); g["basis_justification"]=""; self.reject(g,compat={"compatibility_mode":gr.COMPAT_CROSS})
    def test_missing_basis_evidence(self):
        g=self.boolean(); g["basis_evidence_digest"]=""; self.reject(g,compat={"compatibility_mode":gr.COMPAT_CROSS})
    def test_all_subsets_not_lawful(self):
        g=self.boolean(); g["all_subsets_lawful"]=False; self.reject(g,compat={"compatibility_mode":gr.COMPAT_CROSS})
    def test_constrained_raw_cross_product_rejected(self): self.reject(self.constrained(),compat={"compatibility_mode":gr.COMPAT_CROSS})
    def test_duplicate_lawful_state(self):
        g=self.constrained(); g["lawful_state_spec"].append(["BASE"]); self.reject(g,compat={"compatibility_mode":gr.COMPAT_EXPLICIT,"lawful_joint_spec":[]})
    def test_unknown_pressure_in_state(self):
        g=self.constrained(); g["lawful_state_spec"].append(["UNKNOWN"]); self.reject(g,compat={"compatibility_mode":gr.COMPAT_EXPLICIT,"lawful_joint_spec":[]})
    def test_unknown_relation(self):
        g=self.constrained(); g["relations"]=[{"type":"MAGIC"}]; self.reject(g,compat={"compatibility_mode":gr.COMPAT_EXPLICIT,"lawful_joint_spec":[]})
    def test_duplicate_joint(self):
        c={"compatibility_mode":gr.COMPAT_EXPLICIT,"lawful_joint_spec":[["E",[]],["E",[]]]}; self.reject(self.constrained(),compat=c)
    def test_unlawful_joint(self):
        c={"compatibility_mode":gr.COMPAT_EXPLICIT,"lawful_joint_spec":[["E",["REC"]]]}; self.reject(self.constrained(),compat=c)
    def test_zero_partial_on_budget_shortfall(self):
        out=gr.enumerate_lawful_frame(self.boolean(),[e("E0"),e("E1")],compatibility={"compatibility_mode":gr.COMPAT_CROSS},budget=0); self.assertEqual(out["evaluations"],0)

class EvaluatorHostile(unittest.TestCase):
    def binding(self): return {"grammar_digest":"g","environment_digest":"e","evaluator_digest":"v","baseline_id":"b","baseline_version":"1","baseline_digest":"d","baseline_current":True}
    def test_missing_binding(self):
        b=self.binding(); del b["evaluator_digest"]
        with self.assertRaises(gr.GovernanceError): gr.evaluate_effect_table(frame=["x"],baseline={"x":0},baseline_binding=b,case_effects=[],expected_case_digests=[])
    def test_stale_baseline(self):
        b=self.binding(); b["baseline_current"]=False
        with self.assertRaises(gr.GovernanceError): gr.evaluate_effect_table(frame=["x"],baseline={"x":0},baseline_binding=b,case_effects=[],expected_case_digests=[])
    def test_missing_baseline(self):
        with self.assertRaises(gr.GovernanceError): gr.evaluate_effect_table(frame=["x"],baseline=None,baseline_binding=self.binding(),case_effects=[],expected_case_digests=[])
    def test_case_count_mismatch(self):
        with self.assertRaises(gr.GovernanceError): gr.evaluate_effect_table(frame=["x"],baseline={"x":0},baseline_binding=self.binding(),case_effects=[],expected_case_digests=["c"])
    def test_duplicate_case_identity_rejected(self):
        rows=[{"case_digest":"c","status":"EVALUATED","effects":{"x":0}},{"case_digest":"c","status":"EVALUATED","effects":{"x":0}}]
        with self.assertRaises(gr.GovernanceError): gr.evaluate_effect_table(frame=["x"],baseline={"x":0},baseline_binding=self.binding(),case_effects=rows,expected_case_digests=["c","d"])
    def test_failure_not_coerced_to_unchanged(self):
        with self.assertRaises(gr.GovernanceError) as ctx: gr.evaluate_effect_table(frame=["x"],baseline={"x":0},baseline_binding=self.binding(),case_effects=[{"case_digest":"c","status":"FAILED"}],expected_case_digests=["c"])
        self.assertEqual(ctx.exception.code,"EVALUATOR_FAILURE")
    def test_missing_coordinate_rejected(self):
        with self.assertRaises(gr.GovernanceError): gr.evaluate_effect_table(frame=["x","y"],baseline={"x":0,"y":0},baseline_binding=self.binding(),case_effects=[{"case_digest":"c","status":"EVALUATED","effects":{"x":1}}],expected_case_digests=["c"])
    def test_tradeoff_not_boolean_collapsed(self):
        out=gr.evaluate_effect_table(frame=["x","y"],baseline={"x":0,"y":0},baseline_binding=self.binding(),case_effects=[{"case_digest":"c","status":"EVALUATED","effects":{"x":-1,"y":1}}],expected_case_digests=["c"]); self.assertTrue(out["results"][0]["changed"]); self.assertEqual(out["results"][0]["pareto_relation"],"TRADEOFF")

class WitnessHostile(unittest.TestCase):
    def cases(self): return [{"case_digest":"a","environment_id":"E","pressure_state":["A"]},{"case_digest":"ab","environment_id":"E","pressure_state":["A","B"]}]
    def test_outside_frame_rejected(self):
        with self.assertRaises(gr.GovernanceError): gr.compress_minimal_witnesses(cases=self.cases(),witness_case_digests=["x"])
    def test_inheritance_without_monotonicity_rejected(self):
        with self.assertRaises(gr.GovernanceError): gr.compress_minimal_witnesses(cases=self.cases(),witness_case_digests=["a"],inherit_supersets=True)
    def test_incomplete_monotonicity_rejected(self):
        with self.assertRaises(gr.GovernanceError): gr.compress_minimal_witnesses(cases=self.cases(),witness_case_digests=["a"],inherit_supersets=True,monotonicity_evidence={"property_id":"p"})

class ContactHostile(unittest.TestCase):
    def specimen(self,root:Path):
        src=root/'intent.md'; src.write_text('intent',encoding='utf-8'); h=hashlib.sha256(src.read_bytes()).hexdigest()
        task={"task_id":"t","project_scopes":["demo"],"mutation_class":"PROJECT_STATE","consequence_classes":["state"],"mechanism_tags":["CURRENTNESS_GUARD"],"touched_paths":["state/x"],"capabilities":["project.write"]}
        contact={"contact_id":"intent","locator":str(src),"authority_class":"COMMANDERS_INTENT","semantic_extent":"FULL_ARTIFACT","currentness_required":True,"commit_recheck":"LOCAL_FILE_SHA256","expected_sha256":h,"reason":"intent"}
        sidecar={"sidecar_id":"intent-current","project_scope":"demo","subject":{"locator":str(src),"sha256":h},"authority_class":"COMMANDERS_INTENT","currentness":{"status":"CURRENT","basis":"fixture"},"contact_rules":[{"rule_id":"r","selectors":{"mutation_classes":["PROJECT_STATE"]},"contact":contact}]}
        profile={"profile_id":"demo-current","project_scope":"demo","currentness":{"status":"CURRENT","basis":"fixture"},"rules":[{"rule_id":"o","selectors":{"mutation_classes":["PROJECT_STATE"]},"required_authority_classes":["COMMANDERS_INTENT"],"required_sidecar_ids":["intent-current"]}]}
        return {"project_profiles":[profile],"sidecars":[sidecar]},task,src,h
    def receipt(self,cs,src,h): return {"contact_set_digest":cs["contact_set_digest"],"contact_id":"intent","locator":str(src),"observed_sha256":h,"semantic_extent":"FULL_ARTIFACT","governing_scope":"demo|t","currentness_basis":"current fixture","read_note":"complete semantic contact on exact current bytes"}
    def test_missing_profile_rejected(self):
        task={"task_id":"t","project_scopes":["demo"],"mutation_class":"PROJECT_STATE","consequence_classes":[],"mechanism_tags":[],"touched_paths":[],"capabilities":[]}; out=gr.derive_contact_set({"project_profiles":[],"sidecars":[]},task); self.assertEqual(out["state"],"CONTACT_SET_REJECTED")
    def test_duplicate_current_profiles_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            cat,task,_,_=self.specimen(Path(td)); cat["project_profiles"].append(copy.deepcopy(cat["project_profiles"][0])); cat["project_profiles"][1]["profile_id"]="other"
            with self.assertRaises(gr.GovernanceError): gr.derive_contact_set(cat,task)
    def test_contradictory_current_subject_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            cat,task,_,_=self.specimen(Path(td)); other=copy.deepcopy(cat["sidecars"][0]); other["sidecar_id"]="other"; other["subject"]["sha256"]="0"*64; cat["sidecars"].append(other)
            with self.assertRaises(gr.GovernanceError): gr.derive_contact_set(cat,task)
    def test_historical_required_sidecar_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            cat,task,_,_=self.specimen(Path(td)); cat["sidecars"][0]["currentness"]["status"]="HISTORICAL_SUPERSEDED"; out=gr.derive_contact_set(cat,task); self.assertEqual(out["state"],"CONTACT_SET_REJECTED")
    def test_unknown_currentness_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            cat,task,_,_=self.specimen(Path(td)); cat["sidecars"][0]["currentness"]["status"]="UNKNOWN"; out=gr.derive_contact_set(cat,task); self.assertEqual(out["state"],"CONTACT_SET_REJECTED")
    def test_missing_receipt_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); cat,task,_,_=self.specimen(root); cs=gr.derive_contact_set(cat,task); out=gr.admit_contact_set(cs,[],catalog=cat,task=task,project_root=root); self.assertEqual(out["state"],"CONTACT_SET_REJECTED")
    def test_wrong_scope_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); cat,task,src,h=self.specimen(root); cs=gr.derive_contact_set(cat,task); r=self.receipt(cs,src,h); r["governing_scope"]="wrong"; out=gr.admit_contact_set(cs,[r],catalog=cat,task=task,project_root=root); self.assertIn("WRONG_GOVERNING_SCOPE",{x["error"] for x in out["errors"]})
    def test_wrong_hash_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); cat,task,src,h=self.specimen(root); cs=gr.derive_contact_set(cat,task); r=self.receipt(cs,src,h); r["observed_sha256"]="0"*64; out=gr.admit_contact_set(cs,[r],catalog=cat,task=task,project_root=root); self.assertIn("WRONG_HASH",{x["error"] for x in out["errors"]})
    def test_ack_only_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); cat,task,src,h=self.specimen(root); cs=gr.derive_contact_set(cat,task); r=self.receipt(cs,src,h); r["read_note"]="ACK"; out=gr.admit_contact_set(cs,[r],catalog=cat,task=task,project_root=root); self.assertIn("NON_SUBSTANTIVE_ACKNOWLEDGEMENT_NOTE",{x["error"] for x in out["errors"]})
    def test_local_drift_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); cat,task,src,h=self.specimen(root); cs=gr.derive_contact_set(cat,task); r=self.receipt(cs,src,h); src.write_text('drift',encoding='utf-8'); out=gr.admit_contact_set(cs,[r],catalog=cat,task=task,project_root=root); self.assertIn("LOCAL_SOURCE_DRIFT_AT_ADMISSION",{x["error"] for x in out["errors"]})
    def test_self_deleted_resigned_contact_set_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); cat,task,_,_=self.specimen(root); cs=gr.derive_contact_set(cat,task); forged=copy.deepcopy(cs); forged["entries"]=[]; forged["contact_set_digest"]=gr.digest({k:v for k,v in forged.items() if k!="contact_set_digest"})
            with self.assertRaises(gr.GovernanceError) as ctx: gr.admit_contact_set(forged,[],catalog=cat,task=task,project_root=root)
            self.assertEqual(ctx.exception.code,"GOVERNANCE_CONTACT_SET_STALE")
    def test_catalog_drift_after_resolve_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); cat,task,_,_=self.specimen(root); cs=gr.derive_contact_set(cat,task); cat2=copy.deepcopy(cat); cat2["project_profiles"][0]["currentness"]["basis"]="new"
            with self.assertRaises(gr.GovernanceError): gr.admit_contact_set(cs,[],catalog=cat2,task=task,project_root=root)
    def test_task_expansion_after_resolve_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); cat,task,_,_=self.specimen(root); cs=gr.derive_contact_set(cat,task); task2=copy.deepcopy(task); task2["capabilities"].append("git.push")
            with self.assertRaises(gr.GovernanceError): gr.admit_contact_set(cs,[],catalog=cat,task=task2,project_root=root)

if __name__=='__main__': unittest.main()
