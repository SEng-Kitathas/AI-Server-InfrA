"""Read-only governance observations composed from existing owner APIs."""
from __future__ import annotations
from typing import Any,Callable,Mapping
from . import governance_kernel as kernel

def observe_contract(cards:Mapping[str,Mapping[str,Any]], projection:Mapping[str,Mapping[str,Any]])->dict[str,Any]:
 mismatches=[]
 for name,card in cards.items():
  projected=projection.get(name)
  if projected is None:mismatches.append({'name':name,'code':'PROJECTION_MISSING'});continue
  for field in ('contract_digest','schema_hash','input_schema'):
   if projected.get(field)!=card.get(field):mismatches.append({'name':name,'code':'PROJECTION_MISMATCH','field':field})
 return {'authority_available':True,'authority_owner':'lab_tools.registry','projection_mismatches':mismatches}

def observe_doctrine(owner_read:Callable[[],Mapping[str,Any]], projection:Mapping[str,Any]|None)->dict[str,Any]:
 try:owner=dict(owner_read())
 except Exception as exc:return {'authority_available':False,'error':f'{type(exc).__name__}: {exc}'}
 if owner.get('authority')!='GLOBAL_DOCTRINE':return {'authority_available':False,'owner_state':owner.get('status')}
 if owner.get('status')!='CURRENT' or owner.get('digest_valid') is not True:return {'authority_available':False,'owner_state':owner.get('status'),'integrity_valid':owner.get('digest_valid')}
 doc=owner.get('document') or {};mismatch=bool(projection is not None and (projection.get('digest')!=doc.get('digest') or projection.get('version')!=doc.get('version')))
 return {'authority_available':True,'authority_owner':'global_doctrine.current','projection_mismatches':[{'code':'PROJECTION_MISMATCH'}] if mismatch else []}

def govern_observation(subject:str,observation:Mapping[str,Any])->dict[str,Any]:
 if not observation.get('authority_available'):
  return {'schema':kernel.SCHEMA,'status':'UNKNOWN','authority':'NONE','subject':subject,'issues':[{'code':'AUTHORITATIVE_EVIDENCE_UNAVAILABLE'}],'issue_count':1}
 base=kernel.evaluate_known(subject,{'authority_owner':observation.get('authority_owner')});issues=list(base['issues'])
 for item in observation.get('projection_mismatches') or []:
  detail=dict(item);detail['source_code']=detail.pop('code',None);issues.append({'code':'PROJECTION_CONTRADICTION',**detail})
 return {**base,'status':'CONSISTENT' if not issues else 'CONTRADICTION','issues':issues,'issue_count':len(issues),'authority':'NONE'}
