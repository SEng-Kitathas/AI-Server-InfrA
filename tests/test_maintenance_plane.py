from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import maintenance_plane as m

def env(td):
 r=Path(td);return patch.multiple(m,ROOT=r,STATE=r/'authority.json',RECEIPTS=r/'receipts.jsonl')
def test_maintenance_is_separate_bounded_authority():
 with tempfile.TemporaryDirectory() as td,env(td):
  a=m.acquire(operator_id='op',reason='repair',ttl_seconds=60);assert a['authority']=='MAINTENANCE_ONLY' and a['token'].startswith('pmm-');assert m.validate(a['token'],a['generation'],'op')['status']=='ACTIVE'
def test_wrong_token_is_fenced():
 with tempfile.TemporaryDirectory() as td,env(td):
  a=m.acquire(operator_id='op',reason='repair',ttl_seconds=60)
  try:m.validate('wrong',a['generation'],'op')
  except ValueError:pass
  else:raise AssertionError('wrong token accepted')
def test_reconcile_impossible_active_null_lease_preserves_generation_and_never_invents_token():
 with tempfile.TemporaryDirectory() as td,env(td),patch('pcmmad_receiver.project_mutation_authority._state_path',return_value=Path(td)/'project.json'):
  a=m.acquire(operator_id='op',reason='repair',ttl_seconds=60);state=Path(td)/'project.json';before={'project_id':'P','status':'ACTIVE','generation':34,'lease_id':None,'owner_id':'x'};state.write_text(json.dumps(before))
  r=m.reconcile_authority_state(token=a['token'],generation=a['generation'],operator_id='op',project_id='P',state_path=state,reason='active null lease impossible');after=json.loads(state.read_text());assert after['generation']==34 and after['lease_id'] is None and after['status']=='RECONCILED_INVALID';assert r['before_sha256']!=r['after_sha256'];assert Path(td,'receipts.jsonl').is_file()
def test_reconcile_refuses_healthy_active_authority():
 with tempfile.TemporaryDirectory() as td,env(td),patch('pcmmad_receiver.project_mutation_authority._state_path',return_value=Path(td)/'project.json'):
  a=m.acquire(operator_id='op',reason='repair',ttl_seconds=60);state=Path(td)/'project.json';state.write_text(json.dumps({'status':'ACTIVE','generation':1,'lease_id':'real'}))
  try:m.reconcile_authority_state(token=a['token'],generation=a['generation'],operator_id='op',project_id='P',state_path=state,reason='no')
  except ValueError:pass
  else:raise AssertionError('healthy authority was rewritten')
def test_release_destroys_maintenance_token():
 with tempfile.TemporaryDirectory() as td,env(td):
  a=m.acquire(operator_id='op',reason='repair',ttl_seconds=60);r=m.release(token=a['token'],generation=a['generation'],operator_id='op');assert r['status']=='RELEASED' and r['token'] is None


def test_reconcile_refuses_arbitrary_state_path_even_with_maintenance_authority():
 with tempfile.TemporaryDirectory() as td,env(td),patch('pcmmad_receiver.project_mutation_authority._state_path',return_value=Path(td)/'canonical.json'):
  a=m.acquire(operator_id='op',reason='repair',ttl_seconds=60);bad=Path(td)/'other.json';bad.write_text(json.dumps({'status':'ACTIVE','generation':1,'lease_id':None}))
  try:m.reconcile_authority_state(token=a['token'],generation=a['generation'],operator_id='op',project_id='P',state_path=bad,reason='no')
  except ValueError as exc:assert 'canonical' in str(exc)
  else:raise AssertionError('maintenance accepted arbitrary authority path')
