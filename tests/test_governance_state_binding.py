from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import governance_witness as w

def test_unchanged_valid_evidence_can_be_stale_when_bound_generation_advances():
 e={'integrity_valid':True,'bindings':{'project_generation':5,'catalog_digest':'A'}};r=w.verify_state_binding(e,{'project_generation':6,'catalog_digest':'A'});assert r['status']=='STALE' and not r['usable']
def test_wall_clock_age_alone_is_not_staleness():
 e={'created_at':'1999-01-01','bindings':{'generation':5}};r=w.verify_state_binding(e,{'generation':5});assert r['status']=='CURRENT'
def test_missing_current_witness_is_unknown_not_stale():
 e={'bindings':{'generation':5,'head':'abc'}};r=w.verify_state_binding(e,{'generation':5});assert r['status']=='UNKNOWN'
def test_no_binding_cannot_claim_currentness():
 r=w.verify_state_binding({'integrity_valid':True},{'generation':99});assert r['status']=='UNKNOWN'
def test_multiple_bindings_require_all_to_match():
 e={'bindings':{'generation':5,'head':'abc','catalog':'x'}};assert w.verify_state_binding(e,dict(e['bindings']))['status']=='CURRENT';r=w.verify_state_binding(e,{'generation':5,'head':'def','catalog':'x'});assert r['status']=='STALE'
