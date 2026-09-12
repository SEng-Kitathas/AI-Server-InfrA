from __future__ import annotations
import copy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import governance_observers as o

def naive_projection_consensus(a,b):return a==b
def test_two_wrong_projections_do_not_outvote_authority():
 authority={'fs.glob':{'contract_digest':'AUTH','schema_hash':'S','input_schema':{'type':'object','required':['pattern']}}}
 wrong={'fs.glob':{'contract_digest':'OLD','schema_hash':'OLD-S','input_schema':{'type':'object'}}}
 hud=copy.deepcopy(wrong);agent=copy.deepcopy(wrong)
 assert naive_projection_consensus(hud,agent) is True
 rh=o.govern_observation('capability.contract',o.observe_contract(authority,hud));ra=o.govern_observation('capability.contract',o.observe_contract(authority,agent))
 assert rh['status']=='CONTRADICTION' and ra['status']=='CONTRADICTION';assert rh['authority']=='NONE' and ra['authority']=='NONE'
def test_projection_consensus_cannot_create_truth_when_owner_unavailable():
 wrong={'version':99,'digest':'same-wrong'};assert naive_projection_consensus(wrong,copy.deepcopy(wrong))
 obs={'authority_available':False,'projection_mismatches':[]};r=o.govern_observation('global.doctrine',obs);assert r['status']=='UNKNOWN' and r['authority']=='NONE'
