from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import governance_witness as w

def test_generation_change_during_use_invalidates_precheck():
 r=w.verify_use_interval({'generation':5,'head':'a'},{'generation':6,'head':'a'},['generation','head']);assert r['status']=='STALE_DURING_USE'
def test_head_change_during_use_invalidates_precheck():
 r=w.verify_use_interval({'generation':5,'head':'a'},{'generation':5,'head':'b'},['generation','head']);assert not r['usable']
def test_stable_interval_is_usable():
 x={'generation':5,'head':'a','catalog':'c'};r=w.verify_use_interval(x,dict(x),['generation','head','catalog']);assert r['status']=='CURRENT_THROUGH_USE'
def test_missing_after_witness_is_unknown():
 r=w.verify_use_interval({'generation':5},{},['generation']);assert r['status']=='UNKNOWN'
def test_irrelevant_field_change_does_not_invalidate_bound_interval():
 r=w.verify_use_interval({'generation':5,'telemetry':1},{'generation':5,'telemetry':2},['generation']);assert r['usable']
