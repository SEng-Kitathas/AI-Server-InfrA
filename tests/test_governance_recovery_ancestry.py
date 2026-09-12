from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import governance_witness as w

def rec(project='A',kind='registry',ancestor='x',valid=True):return {'project_id':project,'authority_kind':kind,'ancestor_id':ancestor,'integrity_valid':valid}
def tgt(project='A',kind='registry',ancestor='x'):return {'project_id':project,'authority_kind':kind,'expected_ancestor_id':ancestor}
def test_clean_wrong_ancestor_is_rejected():
 r=w.verify_recovery_ancestry(rec(ancestor='old-clean'),tgt(ancestor='actual-parent'));assert r['status']=='WRONG_ANCESTOR'
def test_clean_other_project_is_rejected():
 assert w.verify_recovery_ancestry(rec(project='B'),tgt(project='A'))['status']=='WRONG_SCOPE'
def test_clean_wrong_authority_kind_is_rejected():
 assert w.verify_recovery_ancestry(rec(kind='ucm'),tgt(kind='registry'))['status']=='WRONG_SCOPE'
def test_integrity_invalid_rejected_before_ancestry():
 assert w.verify_recovery_ancestry(rec(valid=False),tgt())['status']=='INVALID'
def test_missing_ancestry_is_unknown_not_best_effort():
 x=rec();x.pop('ancestor_id');assert w.verify_recovery_ancestry(x,tgt())['status']=='UNKNOWN'
def test_matching_integrity_scope_and_ancestry_qualifies():
 assert w.verify_recovery_ancestry(rec(),tgt())['status']=='QUALIFIED_RECOVERY_SOURCE'
