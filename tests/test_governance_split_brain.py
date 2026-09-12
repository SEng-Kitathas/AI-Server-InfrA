from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import governance_witness as w

def c(identity,generation):return {'identity':identity,'generation':generation,'integrity_valid':True}
def test_newer_integrity_valid_candidate_does_not_win_without_external_generation():
 r=w.resolve_monotonic_currentness([c('old',4),c('new',5)],None);assert r['status']=='UNKNOWN'
def test_external_generation_selects_current_without_governance_inventing_order():
 r=w.resolve_monotonic_currentness([c('old',4),c('new',5)],5);assert r['status']=='CURRENT' and r['current']['identity']=='new'
def test_two_distinct_valid_owners_same_current_generation_is_split_brain():
 r=w.resolve_monotonic_currentness([c('A',5),c('B',5)],5);assert r['status']=='CONTRADICTION' and r['reason']=='SPLIT_BRAIN_SAME_GENERATION'
def test_duplicate_same_identity_is_not_false_split_brain():
 r=w.resolve_monotonic_currentness([c('A',5),c('A',5)],5);assert r['status']=='CURRENT'
def test_stale_external_generation_that_matches_neither_fails_closed():
 r=w.resolve_monotonic_currentness([c('A',5),c('B',6)],7);assert r['status']=='CONTRADICTION'
def test_invalid_candidate_cannot_win_even_if_generation_matches():
 bad={'identity':'B','generation':6,'integrity_valid':False};r=w.resolve_monotonic_currentness([c('A',5),bad],6);assert r['status']=='CONTRADICTION'
