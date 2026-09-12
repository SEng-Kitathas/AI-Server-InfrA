from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import governance_kernel as g
BASE={'subject':'artifact.currentness','question':'which artifact is current?','authoritative_owner':'architecture.registry','currentness_required':True,'currentness_witness':'registry generation/hash','projections':[{'name':'HUD','claims_authority':False},{'name':'agent contract','claims_authority':False}],'admission_rule':'registry commit/adopt','recovery_source':'authoritative registry+bytes','retirement_condition':'legacy projection has zero qualified consumers'}
def test_clean_relation_is_non_authoritative_and_consistent():
 r=g.evaluate_relation(BASE);assert r['status']=='CONSISTENT' and r['authority']=='NONE'
def test_projection_cannot_claim_authority():
 x={**BASE,'projections':[{'name':'HUD','claims_authority':True}]};r=g.evaluate_relation(x);assert r['status']=='CONTRADICTION';assert 'PROJECTION_CLAIMS_AUTHORITY' in [i['code'] for i in r['issues']]
def test_missing_currentness_is_detected():
 x={**BASE};x.pop('currentness_witness');r=g.evaluate_relation(x);assert 'CURRENTNESS_WITNESS_MISSING' in [i['code'] for i in r['issues']]
def test_observed_owner_contradiction_is_detected():
 r=g.evaluate_relation(BASE,{'authority_owner':'filesystem'});assert 'AUTHORITY_OWNER_CONTRADICTION' in [i['code'] for i in r['issues']]
def test_admission_and_derived_authority_escape_are_detected():
 r=g.evaluate_relation(BASE,{'candidate_promoted_without_gate':True,'derived_mutated_authority':True});codes=[i['code'] for i in r['issues']];assert 'ADMISSION_GATE_BYPASS' in codes and 'DERIVED_STATE_AUTHORITY_ESCAPE' in codes
