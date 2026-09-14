from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'));from pcmmad_receiver.principal_auth import *;from pcmmad_receiver.resource_claim_derivation import derive;from pcmmad_receiver.project_provisioning import plan,commit;from pcmmad_receiver.advisory_evidence import gather_and_advise
def test_stolen_agent_key_cannot_be_machine_principal():
 p=authenticate({'X-GitHome-Key':'agent'},agent_secret='agent',operator_secret='operator',operator_epoch=3);assert p['principal_class']=='REMOTE_AGENT' and not admits_scope(p,'MACHINE')
def test_operator_key_is_distinct_machine_principal():
 p=authenticate({'X-PCMMAD-Operator-Key':'operator'},agent_secret='agent',operator_secret='operator',operator_epoch=3);assert p['principal_class']=='OPERATOR' and admits_scope(p,'MACHINE') and p['principal_epoch']==3
def test_claims_derived_from_spec_ignore_payload_claim_forgery():
 spec={'name':'execution.run','effect_traits':['project_mutation_fenced','executes_code']};r=derive(spec,{'project_id':'P','claims':[{'domain':'none'}]});assert r['source']=='SERVER_CAPABILITY_CONTRACT' and r['claims'][0]['domain']=='project'
def test_unknown_effect_trait_creates_incomplete_derivation():
 r=derive({'name':'x','effect_traits':['teleports_state']},{'project_id':'P'});assert 'teleports_state' in r['unknown_traits'] and not r['complete']
def test_provision_commit_is_exclusive_and_receipted():
 with tempfile.TemporaryDirectory() as td:
  base=Path(td)/'projects';base.mkdir();receipts=Path(td)/'receipts';pl=plan(project_id='S',projects_root=base,source_epoch='abc');r=commit(plan_record=pl,receipt_dir=receipts);assert r['ok'] and Path(r['identity_marker']).is_file() and (receipts/(r['receipt_id']+'.json')).is_file();assert commit(plan_record=pl,receipt_dir=receipts)['status']=='RACE_ALREADY_EXISTS'
def test_issue_only_gather_and_advise_surfaces_missing_evidence():
 with tempfile.TemporaryDirectory() as td:
  r=Path(td);(r/'LIVE_SHADOW.md').write_text('lease token redaction means secret withheld');x=gather_and_advise(handoff_root=r,issue='lease token redaction');assert x['advisory']['authority']=='NONE' and x['advisory']['requires_agent_judgment'];assert x['gather']['missing']
