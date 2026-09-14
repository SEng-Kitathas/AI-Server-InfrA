"""Authority-neutral local AI-for-AI advisory synthesis.

This is a deterministic first responder. It compresses local evidence/scars into a
bounded advisory; it cannot grant authority, mutate owner state, or promote doctrine.
"""
from __future__ import annotations
from typing import Any,Iterable,Mapping
from .governance_relations import evidence_class

def advise(*,issue:str,observations:Iterable[Mapping[str,Any]],scars:Iterable[Mapping[str,Any]]=(),candidates:Iterable[Mapping[str,Any]]=(),max_items:int=8)->dict[str,Any]:
 obs=[dict(x) for x in observations][:max_items];scar=[dict(x) for x in scars][:max_items];cand=[dict(x) for x in candidates][:max_items]
 # HELIX-like successor: prefer candidate that discriminates most live hypotheses per declared cost; never manufacture score inputs.
 ranked=[]
 for c in cand:
  discriminates=c.get('discriminates');cost=c.get('cost')
  if isinstance(discriminates,list) and isinstance(cost,(int,float)) and cost>0:
   ranked.append((len(set(map(str,discriminates)))/float(cost),c))
 ranked.sort(key=lambda x:x[0],reverse=True)
 next_d=ranked[0][1] if ranked else None
 contradictions=[o for o in obs if str(o.get('status','')).upper() in {'CONTRADICTION','MISMATCH','STALE','UNKNOWN'}]
 reopened=[s for s in scar if s.get('reopen_condition')]
 layers=[]
 for o in obs:
  ev=o.get('evidence')
  if isinstance(ev,Mapping):layers.append(evidence_class(ev))
 return {'schema':'pcmmad.agent-advisory.v1','issue':issue,'authority':'NONE','claim_ceiling':'ADVISORY_ONLY; VERIFY BEFORE CONSEQUENCE','observations_considered':len(obs),'scar_count':len(scar),'contradictions':contradictions[:max_items],'reopen_conditions':[s.get('reopen_condition') for s in reopened[:max_items]],'next_discriminator':next_d,'evidence_classes':layers[:max_items],'requires_agent_judgment':True,'may_mutate':False,'may_promote':False}


def qualify_hypothesis_candidate(candidate:dict,tests:list[dict])->dict:
 cid=str(candidate.get('hypothesis') or '');relevant=[t for t in tests if cid in (t.get('targets') or [])];dist=[t for t in relevant if t.get('outcome') in {'SUPPORTED','REFUTED'}]
 return {'hypothesis':cid,'status':'DISCRIMINATED_CANDIDATE' if dist else 'UNQUALIFIED_CANDIDATE','epistemic_class':'INFERRED_CANDIDATE','authority':'NONE','tests':len(relevant),'discriminating_tests':len(dist),'truth_promoted':False}
