from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import research_process_gate as g

def receipt():return {'additive':True,'loop_plus':{'claims':['x']},'oarr':{'attacks':['a']},'csc':{'authority':'audit_only','findings':[]},'attention_reservoir':{'selected':'x'},'helix':{'next':'d'}}
def test_architecture_requires_research_process():
 r=g.verify_receipt({'kind':'architecture'},None);assert not r['qualified'] and r['status']=='PROCESS_UNQUALIFIED'
def test_mutation_plan_requires_research_process():
 assert not g.verify_receipt({'mutating':True},None)['qualified']
def test_ambiguous_defaults_to_nontrivial_for_qualification():
 assert g.classify({'description':'maybe complex'})['classification']=='NON_TRIVIAL'
def test_operator_explicit_trivial_skips_process():
 assert g.verify_receipt({'trivial':True},None)['status']=='PROCESS_NOT_REQUIRED'
def test_complete_additive_receipt_qualifies():
 r=g.verify_receipt({'kind':'research_claim'},receipt());assert r['qualified'] and r['authority']=='NONE'
def test_specialized_process_cannot_replace_additive_research_os():
 x=receipt();x['additive']=False;assert not g.verify_receipt({'kind':'design'},x)['qualified']
def test_csc_cannot_gain_veto_or_promotion_authority():
 x=receipt();x['csc']['authority']='veto';assert not g.verify_receipt({'kind':'design'},x)['qualified']
