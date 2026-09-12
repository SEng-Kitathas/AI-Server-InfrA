from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import governance_witness as w

def e(n=0,complete=True,method='m',scope='s',probe=True):return {'observed_consumers':n,'coverage':{'complete':complete,'method_digest':method,'scope_digest':scope},'fallback_probe_passed':probe}
def test_zero_observed_with_open_coverage_is_not_removal_evidence():
 assert w.verify_retirement_evidence(e(0,complete=False))['status']=='UNKNOWN'
def test_live_consumer_forces_retain():
 assert w.verify_retirement_evidence(e(1))['status']=='RETAIN'
def test_unbound_coverage_cannot_qualify_retirement():
 assert w.verify_retirement_evidence(e(method=''))['status']=='UNKNOWN'
def test_zero_closed_coverage_but_removal_probe_failure_retains():
 assert w.verify_retirement_evidence(e(probe=False))['status']=='RETAIN'
def test_only_closed_bound_zero_consumer_with_removal_probe_qualifies():
 r=w.verify_retirement_evidence(e());assert r['status']=='RETIREMENT_QUALIFIED' and r['removable']
