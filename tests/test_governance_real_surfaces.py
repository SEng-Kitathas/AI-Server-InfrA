from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import governance_kernel as g

def codes(r):return {x['code'] for x in r['issues']}
def test_contract_projection_cannot_replace_registry_authority():
 r=g.evaluate_known('capability.contract',{'authority_owner':'orientCapabilities'});assert 'AUTHORITY_OWNER_CONTRADICTION' in codes(r);assert r['authority']=='NONE'
def test_global_doctrine_candidate_cannot_self_promote():
 r=g.evaluate_known('global.doctrine',{'candidate_promoted_without_gate':True});assert 'ADMISSION_GATE_BYPASS' in codes(r);assert r['authority']=='NONE'
def test_mutation_hud_cannot_become_mutation_owner():
 r=g.evaluate_known('mutation.generation',{'authority_owner':'HUD authority panel'});assert 'AUTHORITY_OWNER_CONTRADICTION' in codes(r)
def test_migration_projection_cannot_write_authority():
 r=g.evaluate_known('migration.receipt',{'derived_mutated_authority':True});assert 'DERIVED_STATE_AUTHORITY_ESCAPE' in codes(r)
def test_restart_hud_cannot_substitute_for_restart_receipt():
 r=g.evaluate_known('receiver.restart',{'authority_owner':'HUD receiver status'});assert 'AUTHORITY_OWNER_CONTRADICTION' in codes(r)
def test_unknown_relation_fails_unknown_not_coherent():
 r=g.evaluate_known('invented.manager');assert r['status']=='UNKNOWN_RELATION' and r['authority']=='NONE'
