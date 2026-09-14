"""Principal/epoch/session-bound operator grants. No ambient project authority can mint machine authority."""
from __future__ import annotations
import hashlib,hmac,json,secrets,time
from typing import Any,Mapping

def _canon(x:Mapping[str,Any])->bytes:return json.dumps(dict(x),sort_keys=True,separators=(',',':')).encode()
def issue(*,principal_id:str,principal_epoch:int,session_id:str,scope:str,ttl_seconds:int,issuer_class:str,signing_key:bytes)->dict[str,Any]:
 if issuer_class!='LOCAL_OPERATOR_ROOT':raise ValueError('only LOCAL_OPERATOR_ROOT may issue operator grants')
 if scope not in {'PROJECT','MACHINE'}:raise ValueError('scope must be PROJECT or MACHINE')
 if not principal_id or not session_id:raise ValueError('principal_id and session_id required')
 now=int(time.time());body={'schema':'pcmmad.operator-grant.v1','grant_id':'opg-'+secrets.token_hex(12),'principal_id':principal_id,'principal_epoch':int(principal_epoch),'session_id':session_id,'scope':scope,'issued_at_epoch':now,'expires_at_epoch':now+max(30,min(int(ttl_seconds),86400)),'authority':'OPERATOR_EXPLICIT'};body['mac']=hmac.new(signing_key,_canon(body),hashlib.sha256).hexdigest();return body
def validate(grant:Mapping[str,Any],*,principal_id:str,principal_epoch:int,session_id:str,required_scope:str,signing_key:bytes,now_epoch:int|None=None)->dict[str,Any]:
 body={k:v for k,v in grant.items() if k!='mac'};mac=str(grant.get('mac') or '');expected=hmac.new(signing_key,_canon(body),hashlib.sha256).hexdigest()
 if not hmac.compare_digest(mac,expected):return {'valid':False,'reason':'GRANT_INTEGRITY_INVALID','authority':'NONE'}
 checks=[('principal_id',principal_id,'PRINCIPAL_MISMATCH'),('principal_epoch',int(principal_epoch),'PRINCIPAL_EPOCH_STALE'),('session_id',session_id,'SESSION_MISMATCH'),('scope',required_scope,'SCOPE_NOT_ADMITTED')]
 for key,want,reason in checks:
  if grant.get(key)!=want:return {'valid':False,'reason':reason,'authority':'NONE'}
 now=int(time.time()) if now_epoch is None else int(now_epoch)
 if int(grant.get('expires_at_epoch') or 0)<=now:return {'valid':False,'reason':'GRANT_EXPIRED','authority':'NONE'}
 return {'valid':True,'reason':'ADMITTED','scope':required_scope,'grant_id':grant.get('grant_id'),'authority':'OPERATOR_EXPLICIT'}
def project_authority_can_compose_machine(*_args,**_kwargs)->bool:return False
