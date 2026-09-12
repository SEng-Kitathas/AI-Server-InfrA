from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import governance_witness as w

def test_identical_hash_generation_from_other_project_is_rejected():
 e={'scope':{'project_id':'A'},'generation':5,'digest':'same'};r=w.verify_scope_binding(e,{'project_id':'B'});assert r['status']=='SCOPE_MISMATCH'
def test_same_project_matches():
 assert w.verify_scope_binding({'scope':{'project_id':'A'}},{'project_id':'A'})['usable']
def test_missing_scope_is_unknown_not_universal():
 assert w.verify_scope_binding({}, {'project_id':'A'})['status']=='UNKNOWN'
def test_missing_requested_identity_is_unknown():
 assert w.verify_scope_binding({'scope':{'project_id':'A'}},{})['status']=='UNKNOWN'
def test_composite_scope_can_bind_project_and_profile():
 e={'scope':{'project_id':'A','profile_id':'private'}};assert w.verify_scope_binding(e,{'project_id':'A','profile_id':'private'},fields=('project_id','profile_id'))['usable'];assert not w.verify_scope_binding(e,{'project_id':'A','profile_id':'other'},fields=('project_id','profile_id'))['usable']
