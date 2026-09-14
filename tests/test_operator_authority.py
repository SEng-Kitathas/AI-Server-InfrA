from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'));from pcmmad_receiver import operator_authority as o
K=b'warfort-secret-key';BASE=dict(principal_id='tommy',principal_epoch=7,session_id='s1',scope='MACHINE',ttl_seconds=600,issuer_class='LOCAL_OPERATOR_ROOT',signing_key=K)
def grant():return o.issue(**BASE)
def val(g,**kw):return o.validate(g,principal_id=kw.get('principal_id','tommy'),principal_epoch=kw.get('principal_epoch',7),session_id=kw.get('session_id','s1'),required_scope=kw.get('required_scope','MACHINE'),signing_key=K,now_epoch=kw.get('now_epoch',g['issued_at_epoch']+1))
def test_exact_bound_grant_admits():assert val(grant())['valid']
def test_stolen_grant_wrong_principal_rejected():assert val(grant(),principal_id='attacker')['reason']=='PRINCIPAL_MISMATCH'
def test_replay_after_principal_epoch_rotation_rejected():assert val(grant(),principal_epoch=8)['reason']=='PRINCIPAL_EPOCH_STALE'
def test_session_substitution_rejected():assert val(grant(),session_id='evil')['reason']=='SESSION_MISMATCH'
def test_project_grant_cannot_satisfy_machine_scope():
 g=o.issue(**{**BASE,'scope':'PROJECT'});assert val(g)['reason']=='SCOPE_NOT_ADMITTED'
def test_payload_scope_tamper_breaks_integrity():
 g=grant();g['scope']='PROJECT';assert val(g)['reason']=='GRANT_INTEGRITY_INVALID'
def test_expired_grant_rejected():
 g=grant();assert val(g,now_epoch=g['expires_at_epoch'])['reason']=='GRANT_EXPIRED'
def test_project_authority_never_composes_machine():assert o.project_authority_can_compose_machine(project_lease='x',standing='allow_all') is False
def test_nonlocal_issuer_cannot_mint_machine_or_project_operator_grant():
 try:o.issue(**{**BASE,'issuer_class':'PROJECT_AUTHORITY'})
 except ValueError:pass
 else:raise AssertionError('project authority minted operator grant')
