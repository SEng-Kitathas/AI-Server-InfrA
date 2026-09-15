"""Operator-local maintenance authority for repairing the control plane itself.

Separate from project mutation authority. Maintenance never fabricates missing authority.
"""
from __future__ import annotations
import hashlib,json,secrets
from datetime import datetime,timezone,timedelta
from pathlib import Path
from typing import Any,Mapping
from .shared_core import SYSTEM_ROOT,save_json_atomic,load_json,append_jsonl,utc_now
ROOT=SYSTEM_ROOT/'maintenance';STATE=ROOT/'authority.json';RECEIPTS=ROOT/'receipts.jsonl'
def _digest(x:Mapping[str,Any])->str:return hashlib.sha256(json.dumps(dict(x),sort_keys=True,separators=(',',':')).encode()).hexdigest()
def inspect()->dict[str,Any]:
 d=load_json(STATE,default={});return dict(d) if isinstance(d,dict) and d else {'schema':'pcmmad.maintenance-authority.v1','status':'INACTIVE','generation':0,'authority':'NONE'}
def acquire(*,operator_id:str,reason:str,ttl_seconds:int=900)->dict[str,Any]:
 if not operator_id.strip() or not reason.strip():raise ValueError('operator_id and reason are required')
 now=datetime.now(timezone.utc);prior=inspect();active=prior.get('status')=='ACTIVE' and str(prior.get('expires_at') or '')>now.isoformat()
 if active:raise ValueError('maintenance authority already active')
 generation=int(prior.get('generation') or 0)+1;token='pmm-'+secrets.token_hex(12);d={'schema':'pcmmad.maintenance-authority.v1','status':'ACTIVE','generation':generation,'token':token,'operator_id':operator_id,'reason':reason,'issued_at':now.isoformat(),'expires_at':(now+timedelta(seconds=max(30,min(int(ttl_seconds),3600)))).isoformat(),'authority':'MAINTENANCE_ONLY'};d['integrity']=_digest(d);ROOT.mkdir(parents=True,exist_ok=True);save_json_atomic(STATE,d);return d
def validate(token:str,generation:int,operator_id:str)->dict[str,Any]:
 d=inspect();now=utc_now()
 if d.get('status')!='ACTIVE':raise ValueError('maintenance authority not active')
 if d.get('token')!=token or int(d.get('generation') or -1)!=int(generation) or d.get('operator_id')!=operator_id:raise ValueError('maintenance authority fenced')
 if str(d.get('expires_at') or '')<=now:raise ValueError('maintenance authority expired')
 expected=_digest({k:v for k,v in d.items() if k!='integrity'})
 if d.get('integrity')!=expected:raise ValueError('maintenance authority integrity invalid')
 return d
def release(*,token:str,generation:int,operator_id:str)->dict[str,Any]:
 d=validate(token,generation,operator_id);d={**d,'status':'RELEASED','released_at':utc_now(),'token':None};d['integrity']=_digest({k:v for k,v in d.items() if k!='integrity'});save_json_atomic(STATE,d);return d
def reconcile_authority_state(*,token:str,generation:int,operator_id:str,project_id:str,state_path:Path,reason:str)->dict[str,Any]:
 validate(token,generation,operator_id)
 # The repair target is derived internally from project identity. Caller-supplied arbitrary paths are forbidden.
 from .project_mutation_authority import _state_path as project_authority_state_path
 expected=project_authority_state_path(project_id).resolve();supplied=state_path.resolve()
 if supplied!=expected:raise ValueError('state_path does not match canonical project mutation authority state path')
 before=load_json(expected,default=None)
 if not isinstance(before,dict):raise ValueError('project authority state missing/corrupt')
 impossible=before.get('status')=='ACTIVE' and not str(before.get('lease_id') or '').strip()
 if not impossible:raise ValueError('state is not a recognized impossible authority state; maintenance refuses speculative repair')
 after=dict(before);after['status']='RECONCILED_INVALID';after['released_at']=utc_now();after['maintenance_reconciled']=True;after['maintenance_reason']=reason
 # Preserve generation; never invent a lease/token or rewind authority.
 save_json_atomic(expected,after);receipt={'schema':'pcmmad.maintenance-receipt.v1','action':'authority.reconcile','project_id':project_id,'operator_id':operator_id,'maintenance_generation':generation,'reason':reason,'before_sha256':_digest(before),'after_sha256':_digest(after),'before':before,'after':after,'time':utc_now(),'law':'REPAIR_IMPOSSIBLE_AUTHORITY; DO_NOT INVENT MISSING_AUTHORITY'};ROOT.mkdir(parents=True,exist_ok=True);append_jsonl(RECEIPTS,receipt);return receipt
