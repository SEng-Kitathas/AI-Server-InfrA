"""Versioned global engineering doctrine authority; candidate evidence never self-promotes."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any,Mapping
from .shared_core import SYSTEM_ROOT,save_json_atomic,load_json,utc_now
SCHEMA='pcmmad.global-doctrine.v1';ROOT=SYSTEM_ROOT/'doctrine'/'global';CURRENT=ROOT/'current.json';HISTORY=ROOT/'history'
def canonical_digest(doc:Mapping[str,Any])->str:
 body={k:v for k,v in doc.items() if k!='digest'};return hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def inspect()->dict[str,Any]:
 if not CURRENT.is_file():return {'schema':SCHEMA,'status':'UNINITIALIZED','authority':'NONE','path':str(CURRENT)}
 doc=load_json(CURRENT,default=None)
 if not isinstance(doc,dict):return {'schema':SCHEMA,'status':'CORRUPT','authority':'NONE','path':str(CURRENT)}
 expected=canonical_digest(doc);return {'schema':SCHEMA,'status':'CURRENT' if doc.get('digest')==expected else 'DIGEST_MISMATCH','authority':'GLOBAL_DOCTRINE' if doc.get('digest')==expected else 'NONE','path':str(CURRENT),'document':doc,'digest_valid':doc.get('digest')==expected}
def promote(payload:Mapping[str,Any])->dict[str,Any]:
 candidate=payload.get('candidate');
 if not isinstance(candidate,Mapping):raise ValueError('candidate object is required')
 laws=candidate.get('laws');
 if not isinstance(laws,list) or not laws:raise ValueError('candidate.laws must be a non-empty array')
 operator=str(payload.get('operator_id') or '').strip();provenance=str(payload.get('provenance') or '').strip();
 if not operator or not provenance:raise ValueError('operator_id and provenance are required')
 prior=inspect();version=int((prior.get('document') or {}).get('version') or 0)+1
 doc={'schema':SCHEMA,'version':version,'promoted_at':utc_now(),'operator_id':operator,'provenance':provenance,'source_candidate_sha256':str(payload.get('candidate_sha256') or ''),'laws':laws,'authority_law':'RECURRENCE != AUTHORITY; explicit operator promotion is required'};doc['digest']=canonical_digest(doc);ROOT.mkdir(parents=True,exist_ok=True);HISTORY.mkdir(parents=True,exist_ok=True);save_json_atomic(HISTORY/f'v{version:04d}-{doc["digest"][:12]}.json',doc);save_json_atomic(CURRENT,doc);return {'status':'PROMOTED','version':version,'digest':doc['digest'],'path':str(CURRENT),'law_count':len(laws)}
