"""Additive Research OS qualification gate for non-trivial work. Non-authoritative."""
from __future__ import annotations
from typing import Any,Mapping
NONTRIVIAL_KINDS={'architecture','design','research_claim','mutation_plan','migration','promotion','cross_plane_inference','persistent_state_change','multi_hypothesis_diagnostic'}
REQUIRED_RECEIPT=('loop_plus','oarr','csc','attention_reservoir','helix')
def classify(task:Mapping[str,Any])->dict[str,Any]:
 explicit=task.get('trivial')
 if explicit is True:return {'classification':'TRIVIAL','reason':'EXPLICIT_OPERATOR_TRIVIAL'}
 kind=str(task.get('kind') or '').strip()
 if kind in NONTRIVIAL_KINDS:return {'classification':'NON_TRIVIAL','reason':f'CONSEQUENCE_KIND:{kind}'}
 if task.get('persistent') or task.get('mutating') or task.get('competing_hypotheses') or task.get('cross_plane'):return {'classification':'NON_TRIVIAL','reason':'CONSEQUENCE_FLAGS'}
 return {'classification':'NON_TRIVIAL','reason':'AMBIGUOUS_FAILS_TO_PROCESS_QUALIFICATION'}
def verify_receipt(task:Mapping[str,Any],receipt:Mapping[str,Any]|None)->dict[str,Any]:
 c=classify(task)
 if c['classification']=='TRIVIAL':return {'status':'PROCESS_NOT_REQUIRED','qualified':True,'authority':'NONE','classification':c}
 if not isinstance(receipt,Mapping):return {'status':'PROCESS_UNQUALIFIED','qualified':False,'authority':'NONE','classification':c,'missing':list(REQUIRED_RECEIPT)}
 missing=[k for k in REQUIRED_RECEIPT if not receipt.get(k)]
 if missing:return {'status':'PROCESS_UNQUALIFIED','qualified':False,'authority':'NONE','classification':c,'missing':missing}
 if not receipt.get('additive') is True:return {'status':'PROCESS_UNQUALIFIED','qualified':False,'authority':'NONE','classification':c,'missing':['additive=true']}
 if receipt.get('csc',{}).get('authority') not in {'audit_only','AUDIT_ONLY'}:return {'status':'PROCESS_UNQUALIFIED','qualified':False,'authority':'NONE','classification':c,'missing':['csc.audit_only']}
 return {'status':'PROCESS_QUALIFIED','qualified':True,'authority':'NONE','classification':c}
