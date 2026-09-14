import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'));sys.path.insert(0,str(ROOT/'tools/csc_native'))
from csc_coverage_graph import run
from pcmmad_receiver.mvf_promotion_gate import from_csc
def test_graph_has_declarations_consumers_and_claim_ceiling():
 g=run();assert g['declaration_count']>0 and g['consumers'] and 'does not prove' in g['claim_ceiling']
def test_mvf_requires_coverage_graph_current_consumers():
 g=run();r=from_csc(declaration_binding={'qualified':True},final_polish={'qualified':True},coverage_graph=g);assert r['promotion_admissible'] and r['authority']=='NONE'
 g['consumers']['CI']['current']=False;r=from_csc(declaration_binding={'qualified':True},final_polish={'qualified':True},coverage_graph=g);assert not r['promotion_admissible']
