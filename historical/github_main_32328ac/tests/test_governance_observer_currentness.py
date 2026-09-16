from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import governance_witness as w

def test_observer_bound_to_current_owner_contracts_is_usable():
 o={'owner_contract_digests':{'capability.registry':'A','doctrine':'B'}};assert w.verify_observer_contract(o,{'capability.registry':'A','doctrine':'B'})['status']=='CURRENT'
def test_owner_contract_change_makes_observer_stale_even_if_observer_code_unchanged():
 o={'owner_contract_digests':{'capability.registry':'A'}};r=w.verify_observer_contract(o,{'capability.registry':'NEW'});assert r['status']=='STALE' and not r['usable']
def test_unbound_observer_cannot_claim_currentness():
 assert w.verify_observer_contract({}, {'x':'A'})['status']=='UNKNOWN'
def test_missing_owner_contract_is_unknown():
 o={'owner_contract_digests':{'x':'A','y':'B'}};assert w.verify_observer_contract(o,{'x':'A'})['status']=='UNKNOWN'
def test_extra_unbound_owner_contract_does_not_invalidate_observer_scope():
 o={'owner_contract_digests':{'x':'A'}};assert w.verify_observer_contract(o,{'x':'A','unrelated':'Z'})['status']=='CURRENT'
