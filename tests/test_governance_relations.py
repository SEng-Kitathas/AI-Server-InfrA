from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'));from pcmmad_receiver import governance_relations as g
def test_binding_missing_is_unknown_not_current():assert g.binding_witness({'epoch':1},{},['epoch'])['status']=='UNKNOWN'
def test_binding_change_is_stale_without_authority():
 r=g.binding_witness({'epoch':1},{'epoch':2},['epoch']);assert r['status']=='STALE' and r['authority']=='NONE'
def test_query_relative_admission_does_not_generalize():
 grants=[{'question_class':'history','consequence_class':'read','scope':'P'}];assert not g.admission_witness(grants,{'question_class':'mutation','consequence_class':'write','scope':'P'})['admitted']
def test_binding_change_creates_debt_not_evidence_destruction():
 r=g.qualification_debt({'bindings':{'doctrine':'D1'},'load_bearing_bindings':['doctrine']},{'doctrine':'D2'});assert r['debt'] and r['evidence_invalidated'] is False
def test_thread_scaffold_not_endogenous():assert not g.evidence_class({'thread_scaffolded':True})['endogenous']
def test_server_enforced_is_endogenous():assert g.evidence_class({'server_enforced':True})['endogenous']
def test_scar_requires_reopen_condition():assert not g.scar_record(claim='x',attack='a',outcome='killed',scope='p',reopen_condition='')['qualified']
def test_transition_missing_endpoint_unknown():assert g.transition_witness({'x':1},{'x':2},{},['x'])['status']=='UNKNOWN'
def test_transition_contradiction_detected():assert g.transition_witness({'x':1},{'x':2},{'x':3},['x'])['status']=='CONTRADICTION'
def test_relations_never_expose_mutation_or_authority_grant_functions():
 import inspect;names=[n for n,v in inspect.getmembers(g,inspect.isfunction)];assert not any(x in n for n in names for x in ('write','save','commit','grant','authorize','promote'))
