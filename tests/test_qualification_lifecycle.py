from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import qualification_lifecycle as q

def test_load_bearing_authority_change_creates_debt_not_evidence_destruction():
 x={'bindings':{'doctrine':'D1','head':'H1'},'load_bearing_bindings':['doctrine']};r=q.requalification_debt(x,{'doctrine':'D2','head':'H1'});assert r['status']=='REQUALIFICATION_REQUIRED' and r['evidence_invalidated'] is False
def test_irrelevant_change_does_not_create_debt():
 x={'bindings':{'doctrine':'D1','telemetry':1},'load_bearing_bindings':['doctrine']};r=q.requalification_debt(x,{'doctrine':'D1','telemetry':2});assert not r['debt']
def test_missing_current_binding_is_unknown():
 assert q.requalification_debt({'bindings':{'doctrine':'D1'}},{})['status']=='UNKNOWN'
def test_historical_admission_does_not_authorize_mutation_query():
 e={'admission_grants':[{'question_class':'history','consequence_class':'read','scope':'P'}]};assert q.query_admission(e,{'question_class':'current_authority','consequence_class':'mutation','scope':'P'})['status']=='NOT_ADMITTED_FOR_QUERY'
def test_exact_query_consequence_scope_grant_admits():
 g={'question_class':'history','consequence_class':'read','scope':'P'};assert q.query_admission({'admission_grants':[g]},g)['admitted']
def test_thread_success_is_not_server_enforcement():
 r=q.scaffolding_class({'thread_scaffolded':True});assert not r['endogenous_enforcement'] and r['strongest']=='THREAD_SCAFFOLDED'
def test_server_enforcement_is_distinguished_from_projection():
 r=q.scaffolding_class({'server_enforced':True,'server_projected':True});assert r['endogenous_enforcement'] and r['strongest']=='SERVER_ENFORCED'
