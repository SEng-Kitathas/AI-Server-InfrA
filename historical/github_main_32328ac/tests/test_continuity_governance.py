from __future__ import annotations
import copy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import continuity_governance as g

def good():return {'doctrine':{'current':True,'digest':'d'},'continuity_pair':{'live_shadow_current':True,'design_thread_current':True,'lineage_consistent':True},'icf_ingress':{'before_witness':'x','after_witness':'x'},'context':{'provenance_complete':True},'non_trivial':True,'research_process':{'qualified':True}}
def test_all_current_is_ready_non_authoritative():
 r=g.evaluate(good());assert r['status']=='READY' and r['authority']=='NONE'
def test_stale_doctrine_blocks_readiness_only():
 x=good();x['doctrine']['current']=False;r=g.evaluate(x);assert r['status']=='NOT_READY' and {i['code'] for i in r['issues']}=={'DOCTRINE_NOT_CURRENT'}
def test_continuity_contradiction_not_smoothed():
 x=good();x['continuity_pair']['lineage_consistent']=False;assert 'CONTINUITY_PAIR_CONTRADICTION' in {i['code'] for i in g.evaluate(x)['issues']}
def test_icf_toctou_blocks():
 x=good();x['icf_ingress']['after_witness']='changed';assert 'ICF_CURRENTNESS_CHANGED_DURING_REHYDRATION' in {i['code'] for i in g.evaluate(x)['issues']}
def test_context_without_provenance_does_not_become_authority():
 x=good();x['context']['provenance_complete']=False;assert g.evaluate(x)['status']=='NOT_READY'
def test_nontrivial_missing_research_process_blocks():
 x=good();x.pop('research_process');assert 'RESEARCH_PROCESS_UNQUALIFIED' in {i['code'] for i in g.evaluate(x)['issues']}
def test_missing_authoritative_component_is_unknown():
 x=good();x.pop('doctrine');assert g.evaluate(x)['status']=='UNKNOWN'
def test_fixing_only_broken_authoritative_component_restores_ready():
 x=good();x['doctrine']['current']=False;assert not g.evaluate(x)['ready'];x['doctrine']['current']=True;assert g.evaluate(x)['ready']
