import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver.mvf_promotion_gate import evaluate
def test_all_applicable_current_green_is_admissible_but_no_authority():
 r=evaluate(consumers=[{'id':'CSC','current':True,'qualified':True},{'id':'FINAL_QC','current':True,'qualified':True}],applicable_doctrine=['CSC','FINAL_QC']);assert r['promotion_admissible'] and r['authority']=='NONE'
def test_missing_consumer_blocks():assert not evaluate(consumers=[],applicable_doctrine=['CSC'])['promotion_admissible']
def test_stale_consumer_blocks():assert not evaluate(consumers=[{'id':'CSC','current':False,'qualified':True}],applicable_doctrine=['CSC'])['promotion_admissible']
def test_failed_consumer_blocks():assert not evaluate(consumers=[{'id':'CSC','current':True,'qualified':False}],applicable_doctrine=['CSC'])['promotion_admissible']
