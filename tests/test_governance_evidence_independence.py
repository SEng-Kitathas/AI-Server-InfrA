from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import governance_witness as w

def e(name,lineage,domain):return {'name':name,'lineage_id':lineage,'failure_domain':domain}
def test_three_surfaces_same_lineage_domain_are_one_vote():
 r=w.assess_evidence_independence([e('owner','runtime-A','process-A'),e('hud','runtime-A','process-A'),e('agent','runtime-A','process-A')]);assert r['status']=='CORRELATED' and r['independent_count']==1
def test_reexpression_same_lineage_different_file_is_not_automatically_independent_if_failure_domain_same_lineage_differs():
 # Different lineage ids but same failure domain are still correlated in reality; this test exposes whether pair grouping is too weak.
 r=w.assess_evidence_independence([e('a','line-A','process-A'),e('b','line-B','process-A')]);assert r['status']=='CORRELATED'
def test_out_of_domain_and_lineage_witness_can_supply_second_vote():
 r=w.assess_evidence_independence([e('owner','runtime-A','process-A'),e('supervisor','supervisor-B','process-B')]);assert r['status']=='INDEPENDENT_ENOUGH'
def test_missing_provenance_is_unknown():
 r=w.assess_evidence_independence([{'name':'mystery'}]);assert r['status']=='UNKNOWN'
