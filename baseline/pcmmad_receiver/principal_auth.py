from __future__ import annotations
import hashlib,hmac
from typing import Mapping,Any
def _eq(a:str,b:str)->bool:return bool(a) and bool(b) and hmac.compare_digest(a.encode(),b.encode())
def authenticate(headers:Mapping[str,Any],*,agent_secret:str,operator_secret:str,operator_epoch:int)->dict:
 agent=str(headers.get('X-GitHome-Key') or '');op=str(headers.get('X-PCMMAD-Operator-Key') or '')
 if _eq(op,operator_secret):return {'authenticated':True,'principal_class':'OPERATOR','principal_id':'local-operator','principal_epoch':int(operator_epoch),'max_scope':'MACHINE','authority':'AUTHENTICATION_ONLY'}
 if _eq(agent,agent_secret):return {'authenticated':True,'principal_class':'REMOTE_AGENT','principal_id':'remote-agent','principal_epoch':0,'max_scope':'PROJECT','authority':'AUTHENTICATION_ONLY'}
 return {'authenticated':False,'principal_class':'NONE','principal_id':None,'principal_epoch':None,'max_scope':'NONE','authority':'NONE'}
def admits_scope(principal:Mapping[str,Any],scope:str)->bool:
 return bool(principal.get('authenticated')) and (scope=='PROJECT' or principal.get('max_scope')=='MACHINE')


def derive_request_principal(headers,env):
 return authenticate(headers,agent_secret=str(env.get('GITHOME_API_KEY') or ''),operator_secret=str(env.get('PCMMAD_OPERATOR_API_KEY') or ''),operator_epoch=int(env.get('PCMMAD_OPERATOR_EPOCH') or 0))
