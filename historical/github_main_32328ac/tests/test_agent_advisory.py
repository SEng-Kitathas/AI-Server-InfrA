from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'));from pcmmad_receiver.agent_advisory import advise
def test_advisory_has_zero_authority_and_no_mutation():
 r=advise(issue='x',observations=[]);assert r['authority']=='NONE' and not r['may_mutate'] and not r['may_promote']
def test_unknown_is_surfaced_not_smoothed():
 r=advise(issue='x',observations=[{'status':'UNKNOWN','detail':'missing witness'}]);assert r['contradictions'][0]['status']=='UNKNOWN'
def test_scar_reopen_condition_survives_compression():
 r=advise(issue='x',observations=[],scars=[{'claim':'dead','reopen_condition':'new independent witness'}]);assert r['reopen_conditions']==['new independent witness']
def test_helix_prefers_discrimination_per_declared_cost():
 cs=[{'id':'expensive','discriminates':['a','b','c'],'cost':3},{'id':'sharp','discriminates':['a','b'],'cost':1}];assert advise(issue='x',observations=[],candidates=cs)['next_discriminator']['id']=='sharp'
def test_missing_score_inputs_do_not_get_invented():
 assert advise(issue='x',observations=[],candidates=[{'id':'guess'}])['next_discriminator'] is None
def test_evidence_scaffolding_class_is_preserved():
 r=advise(issue='x',observations=[{'status':'OK','evidence':{'thread_scaffolded':True}}]);assert r['evidence_classes'][0]['strongest']=='THREAD_SCAFFOLDED'
def test_bounded_output_discards_excess_items():
 obs=[{'status':'UNKNOWN','n':i} for i in range(100)];r=advise(issue='x',observations=obs,max_items=5);assert r['observations_considered']==5 and len(r['contradictions'])==5
