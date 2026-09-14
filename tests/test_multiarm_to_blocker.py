from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'));from pcmmad_receiver.principal_auth import derive_request_principal,admits_scope;from pcmmad_receiver.project_provisioning import plan,commit_registered;from pcmmad_receiver.resource_claim_derivation import derive,witness;from pcmmad_receiver.advisory_evidence import gather_extended,infer_candidates
def test_request_principal_is_derived_from_server_env_not_claimed_json():
 env={'GITHOME_API_KEY':'a','PCMMAD_OPERATOR_API_KEY':'o','PCMMAD_OPERATOR_EPOCH':'4'};p=derive_request_principal({'X-GitHome-Key':'a','X-Claimed-Principal':'OPERATOR'},env);assert p['principal_class']=='REMOTE_AGENT' and not admits_scope(p,'MACHINE')
def test_operator_request_derives_machine_ceiling():
 p=derive_request_principal({'X-PCMMAD-Operator-Key':'o'},{'GITHOME_API_KEY':'a','PCMMAD_OPERATOR_API_KEY':'o','PCMMAD_OPERATOR_EPOCH':'4'});assert p['principal_epoch']==4 and admits_scope(p,'MACHINE')
def test_registered_provision_rolls_back_after_each_injected_boundary():
 for fault in ('after_root','after_identity','after_registry'):
  with tempfile.TemporaryDirectory() as td:
   b=Path(td)/'projects';b.mkdir();reg=Path(td)/'registry.json';r=commit_registered(plan_record=plan(project_id='P',projects_root=b),receipt_dir=Path(td)/'receipts',registry_path=reg,fault_at=fault);assert r['status']=='ROLLED_BACK' and not (b/'P').exists();data=json.loads(reg.read_text()) if reg.exists() else {};assert 'P' not in data
def test_registered_provision_success_readback():
 with tempfile.TemporaryDirectory() as td:
  b=Path(td)/'projects';b.mkdir();reg=Path(td)/'registry.json';r=commit_registered(plan_record=plan(project_id='P',projects_root=b,source_epoch='e1'),receipt_dir=Path(td)/'receipts',registry_path=reg);assert r['ok'] and json.loads(reg.read_text())['P']['source_epoch']=='e1'
def test_unpredicted_observed_effect_fails_truth():
 p=derive({'name':'x','effect_traits':['project_mutation_fenced']},{'project_id':'P'});r=witness(p,[{'domain':'project','resource':'P','mode':'WRITE'},{'domain':'git_index','resource':'P','mode':'WRITE'}]);assert not r['verified'] and r['unpredicted_effects']
def test_exact_observed_effect_can_match_but_does_not_grant_authority():
 p=derive({'name':'x','effect_traits':['project_mutation_fenced']},{'project_id':'P'});r=witness(p,p['claims']);assert r['verified'] and r['authority']=='NONE'
def test_extended_gather_is_bounded_and_provenance_bearing():
 with tempfile.TemporaryDirectory() as td:
  r=Path(td);h=r/'handoff';h.mkdir();(h/'LIVE_SHADOW.md').write_text('stale qualification');pr=r/'project';(pr/'continuity/research_epistemic_shadow').mkdir(parents=True);(pr/'continuity/research_epistemic_shadow/RESEARCH_EPISTEMIC_SHADOW.md').write_text('stale research evidence');e=gather_extended(handoff_root=h,project_root=pr,issue='stale evidence',max_bytes=64);res=next(x for x in e['extended'] if x['source']=='RES');assert res['status']=='OBSERVED' and res['bytes_read']<=64 and res['provenance']
def test_inference_is_explicit_candidate_not_evidence_or_authority():
 x=infer_candidates({'observations':[{'status':'MISSING'}],'extended':[]});assert x['candidates'][0]['epistemic_class']=='INFERRED_CANDIDATE' and x['authority']=='NONE' and not x['may_promote']
