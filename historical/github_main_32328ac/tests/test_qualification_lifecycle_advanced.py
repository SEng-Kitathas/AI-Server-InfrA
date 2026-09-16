from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import qualification_lifecycle as q

def test_negative_evidence_requires_reopen_condition():
 r=q.negative_evidence({'claim':'X','attack':'A','outcome':'killed','scope':'P'});assert not r['qualified']
def test_complete_negative_evidence_preserves_killed_path():
 r=q.negative_evidence({'claim':'X','attack':'A','outcome':'killed','scope':'P','reopen_condition':'new evidence'});assert r['qualified']
def test_semantic_delta_only_tracks_load_bearing_fields():
 r=q.semantic_delta({'frontier':'A','telemetry':1},{'frontier':'B','telemetry':2},['frontier']);assert len(r['changes'])==1 and r['changes'][0]['field']=='frontier'
def test_missing_delta_endpoint_is_not_silently_equal():
 r=q.semantic_delta({'frontier':'A'},{},['frontier']);assert r['changes'][0]['kind']=='UNKNOWN_ENDPOINT'
def test_three_distinct_failed_discriminators_inside_same_closure_justify_escape_search_not_new_primitive():
 h=[{'primitive_closure':'C','resolved':False,'discriminator':x} for x in ['a','b','c']];r=q.closure_escape(h);assert r['status']=='CLOSURE_ESCAPE_CANDIDATE' and r['authority']=='NONE'
def test_repeated_same_discriminator_does_not_fake_closure_escape():
 h=[{'primitive_closure':'C','resolved':False,'discriminator':'a'}]*3;assert not q.closure_escape(h)['escape_search_justified']
def test_research_depth_is_resource_and_consequence_relative():
 assert q.research_depth({'consequence_severity':4,'live_rivals':2,'uncertainty':2,'reserve':5})['depth']=='CAMPAIGN';assert q.research_depth({'consequence_severity':1,'live_rivals':1,'uncertainty':1,'reserve':5})['depth']=='SINGLE_HOSTILE_CHECK'
def test_no_reserve_is_hard_stop_not_method_waiver():
 assert q.research_depth({'consequence_severity':5,'reserve':0})['depth']=='HARD_STOP'
