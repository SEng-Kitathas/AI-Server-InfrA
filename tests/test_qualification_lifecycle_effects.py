from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import qualification_lifecycle as q

def full():return {'loop_plus':{'rivals':['r']},'oarr':{'attacks':['a'],'result':'killed'},'csc':{'authority':'audit_only','finding':'f'},'attention_reservoir':{'selected':'x','reason':'breadth'},'helix_next':'next'}
def test_populated_labels_without_effect_are_unverified():
 x={'loop_plus':{},'oarr':{},'csc':{'authority':'audit_only'},'attention_reservoir':{},'helix_next':'next'};r=q.process_effect(x);assert not r['effect_verified'] and 'oarr' in r['missing']
def test_effectful_receipt_witnesses_process():assert q.process_effect(full())['effect_verified']
def test_campaign_binding_change_requires_requalification_before_promotion():
 r=q.reauthorize_campaign({'doctrine':'D1','head':'H1'},{'doctrine':'D2','head':'H1'},['doctrine','head']);assert r['status']=='REQUALIFICATION_REQUIRED' and not r['promotion_eligible']
def test_irrelevant_unbound_change_does_not_block_reauthorization():
 assert q.reauthorize_campaign({'doctrine':'D1'},{'doctrine':'D1','telemetry':2},['doctrine'])['promotion_eligible']
def test_credible_counterevidence_becomes_doctrine_challenge_not_violation_suppression():
 r=q.doctrine_challenge({'contradicts_doctrine':True,'evidence_integrity':True,'provenance_current':True});assert r['status']=='DOCTRINE_CHALLENGE' and r['preserve_evidence'] and r['promotion_blocked']
def test_unqualified_contradiction_does_not_challenge_doctrine():
 assert q.doctrine_challenge({'contradicts_doctrine':True,'evidence_integrity':False,'provenance_current':True})['status']=='UNQUALIFIED_NONCOMPLIANCE'
