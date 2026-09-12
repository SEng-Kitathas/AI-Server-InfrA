"""Independent witness verification primitives for governance research."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any,Mapping

def canonical_digest(doc:Mapping[str,Any],exclude=('digest',))->str:
 body={k:v for k,v in doc.items() if k not in exclude};return hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def verify_json_document(path:Path,claimed_digest:str|None=None)->dict[str,Any]:
 try:raw=path.read_bytes();doc=json.loads(raw.decode('utf-8'))
 except Exception as exc:return {'available':False,'valid':False,'error':f'{type(exc).__name__}: {exc}'}
 if not isinstance(doc,dict):return {'available':True,'valid':False,'error':'document not object'}
 recomputed=canonical_digest(doc);stored=str(doc.get('digest') or '');claim=str(claimed_digest or stored)
 return {'available':True,'valid':bool(stored and recomputed==stored and claim==stored),'stored_digest':stored,'recomputed_digest':recomputed,'claimed_digest':claim,'raw_sha256':hashlib.sha256(raw).hexdigest()}
def combine_owner_and_witness(owner:Mapping[str,Any],witness:Mapping[str,Any])->dict[str,Any]:
 if not witness.get('available'):return {'usable':False,'status':'UNKNOWN','reason':'WITNESS_UNAVAILABLE'}
 if not witness.get('valid'):return {'usable':False,'status':'CONTRADICTION','reason':'INDEPENDENT_WITNESS_INVALID'}
 if owner.get('digest_valid') is not True:return {'usable':False,'status':'CONTRADICTION','reason':'OWNER_WITNESS_DISAGREES'}
 return {'usable':True,'status':'CURRENT','reason':'OWNER_AND_INDEPENDENT_WITNESS_AGREE'}


def resolve_monotonic_currentness(candidates:list[Mapping[str,Any]], external_generation:int|None)->dict[str,Any]:
 valid=[dict(c) for c in candidates if c.get('integrity_valid') is True]
 if external_generation is None:return {'status':'UNKNOWN','current':None,'reason':'MONOTONIC_WITNESS_UNAVAILABLE'}
 matches=[c for c in valid if c.get('generation')==external_generation]
 if len(matches)==1:return {'status':'CURRENT','current':matches[0],'reason':'EXTERNAL_GENERATION_MATCH'}
 if len(matches)>1:
  ids={str(c.get('identity')) for c in matches}
  if len(ids)==1:return {'status':'CURRENT','current':matches[0],'reason':'DUPLICATE_SAME_IDENTITY'}
  return {'status':'CONTRADICTION','current':None,'reason':'SPLIT_BRAIN_SAME_GENERATION'}
 return {'status':'CONTRADICTION','current':None,'reason':'NO_CANDIDATE_MATCHES_EXTERNAL_GENERATION'}


def verify_state_binding(evidence:Mapping[str,Any],current_state:Mapping[str,Any])->dict[str,Any]:
 bindings=evidence.get('bindings')
 if not isinstance(bindings,Mapping) or not bindings:return {'status':'UNKNOWN','usable':False,'reason':'NO_STATE_BINDING'}
 mismatches=[]
 for key,expected in bindings.items():
  if key not in current_state:return {'status':'UNKNOWN','usable':False,'reason':'CURRENT_STATE_WITNESS_MISSING','field':key}
  if current_state.get(key)!=expected:mismatches.append({'field':key,'bound':expected,'current':current_state.get(key)})
 if mismatches:return {'status':'STALE','usable':False,'reason':'BOUND_STATE_ADVANCED','mismatches':mismatches}
 return {'status':'CURRENT','usable':True,'reason':'BOUND_STATE_MATCH'}


def verify_use_interval(before:Mapping[str,Any],after:Mapping[str,Any],required_fields:list[str])->dict[str,Any]:
 missing=[k for k in required_fields if k not in before or k not in after]
 if missing:return {'status':'UNKNOWN','usable':False,'reason':'INTERVAL_WITNESS_MISSING','fields':missing}
 changed=[{'field':k,'before':before.get(k),'after':after.get(k)} for k in required_fields if before.get(k)!=after.get(k)]
 if changed:return {'status':'STALE_DURING_USE','usable':False,'reason':'TOCTOU_CURRENTNESS_CHANGED','changes':changed}
 return {'status':'CURRENT_THROUGH_USE','usable':True,'reason':'INTERVAL_WITNESS_STABLE'}


def assess_evidence_independence(evidence:list[Mapping[str,Any]],minimum_independent:int=2)->dict[str,Any]:
 rows=[dict(x) for x in evidence]
 for item in rows:
  if not str(item.get('lineage_id') or '').strip() or not str(item.get('failure_domain') or '').strip():return {'status':'UNKNOWN','independent_count':0,'reason':'PROVENANCE_OR_FAILURE_DOMAIN_MISSING'}
 # Independence requires both lineage and failure-domain separation. Any shared failure domain or shared lineage correlates the connected component.
 parent=list(range(len(rows)))
 def find(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 def union(a,b):
  a,b=find(a),find(b)
  if a!=b:parent[b]=a
 for i in range(len(rows)):
  for j in range(i+1,len(rows)):
   if rows[i]['lineage_id']==rows[j]['lineage_id'] or rows[i]['failure_domain']==rows[j]['failure_domain']:union(i,j)
 groups={}
 for i,item in enumerate(rows):groups.setdefault(find(i),[]).append(item)
 independent=len(groups)
 return {'status':'INDEPENDENT_ENOUGH' if independent>=minimum_independent else 'CORRELATED','independent_count':independent,'required':minimum_independent,'groups':[{'lineages':sorted({str(x['lineage_id']) for x in v}),'failure_domains':sorted({str(x['failure_domain']) for x in v}),'count':len(v)} for v in groups.values()]}


def verify_observer_contract(observer:Mapping[str,Any],owner_contracts:Mapping[str,str])->dict[str,Any]:
 bound=observer.get('owner_contract_digests')
 if not isinstance(bound,Mapping) or not bound:return {'status':'UNKNOWN','usable':False,'reason':'OBSERVER_BINDING_MISSING'}
 missing=[k for k in bound if k not in owner_contracts]
 if missing:return {'status':'UNKNOWN','usable':False,'reason':'OWNER_CONTRACT_UNAVAILABLE','owners':missing}
 stale=[{'owner':k,'bound':v,'current':owner_contracts[k]} for k,v in bound.items() if owner_contracts[k]!=v]
 if stale:return {'status':'STALE','usable':False,'reason':'OBSERVER_CONTRACT_STALE','mismatches':stale}
 return {'status':'CURRENT','usable':True,'reason':'OBSERVER_OWNER_CONTRACTS_MATCH'}


def verify_scope_binding(evidence:Mapping[str,Any],requested_scope:Mapping[str,Any],fields=('project_id',))->dict[str,Any]:
 bound=evidence.get('scope')
 if not isinstance(bound,Mapping):return {'status':'UNKNOWN','usable':False,'reason':'SCOPE_BINDING_MISSING'}
 missing=[k for k in fields if k not in bound or k not in requested_scope]
 if missing:return {'status':'UNKNOWN','usable':False,'reason':'SCOPE_FIELD_MISSING','fields':missing}
 mismatches=[{'field':k,'bound':bound[k],'requested':requested_scope[k]} for k in fields if bound[k]!=requested_scope[k]]
 if mismatches:return {'status':'SCOPE_MISMATCH','usable':False,'reason':'CROSS_SCOPE_EVIDENCE_REJECTED','mismatches':mismatches}
 return {'status':'SCOPE_MATCH','usable':True,'reason':'SCOPE_IDENTITY_MATCH'}


def verify_recovery_ancestry(recovery:Mapping[str,Any],target:Mapping[str,Any])->dict[str,Any]:
 if recovery.get('integrity_valid') is not True:return {'status':'INVALID','usable':False,'reason':'RECOVERY_INTEGRITY_INVALID'}
 required=('project_id','authority_kind','ancestor_id')
 if any(not recovery.get(k) for k in required) or any(not target.get(k) for k in ('project_id','authority_kind','expected_ancestor_id')):return {'status':'UNKNOWN','usable':False,'reason':'ANCESTRY_BINDING_MISSING'}
 if recovery['project_id']!=target['project_id'] or recovery['authority_kind']!=target['authority_kind']:return {'status':'WRONG_SCOPE','usable':False,'reason':'RECOVERY_SCOPE_MISMATCH'}
 if recovery['ancestor_id']!=target['expected_ancestor_id']:return {'status':'WRONG_ANCESTOR','usable':False,'reason':'RECOVERY_CAUSAL_ANCESTRY_MISMATCH'}
 return {'status':'QUALIFIED_RECOVERY_SOURCE','usable':True,'reason':'INTEGRITY_SCOPE_AND_ANCESTRY_MATCH'}


def verify_retirement_evidence(evidence:Mapping[str,Any])->dict[str,Any]:
 observed=int(evidence.get('observed_consumers',-1))
 coverage=evidence.get('coverage')
 if observed<0 or not isinstance(coverage,Mapping):return {'status':'UNKNOWN','removable':False,'reason':'RETIREMENT_EVIDENCE_INCOMPLETE'}
 if observed>0:return {'status':'RETAIN','removable':False,'reason':'LIVE_CONSUMERS_OBSERVED'}
 if coverage.get('complete') is not True:return {'status':'UNKNOWN','removable':False,'reason':'CONSUMER_SPACE_NOT_CLOSED','coverage':dict(coverage)}
 if not coverage.get('method_digest') or not coverage.get('scope_digest'):return {'status':'UNKNOWN','removable':False,'reason':'COVERAGE_NOT_IDENTITY_BOUND'}
 if evidence.get('fallback_probe_passed') is not True:return {'status':'RETAIN','removable':False,'reason':'FALLBACK_REMOVAL_PROBE_FAILED'}
 return {'status':'RETIREMENT_QUALIFIED','removable':True,'reason':'ZERO_CONSUMERS_WITH_CLOSED_BOUND_COVERAGE_AND_REMOVAL_PROBE'}
