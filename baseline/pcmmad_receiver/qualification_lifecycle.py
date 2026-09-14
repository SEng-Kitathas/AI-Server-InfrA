"""Non-authoritative qualification lifecycle calculus."""
from __future__ import annotations
from typing import Any,Mapping

def requalification_debt(qualification:Mapping[str,Any],current_bindings:Mapping[str,Any])->dict[str,Any]:
 bound=qualification.get('bindings')
 if not isinstance(bound,Mapping):return {'status':'UNKNOWN','debt':True,'authority':'NONE','reason':'QUALIFICATION_BINDINGS_MISSING'}
 changed=[]
 for key,old in bound.items():
  if key not in current_bindings:return {'status':'UNKNOWN','debt':True,'authority':'NONE','reason':'CURRENT_BINDING_MISSING','field':key}
  if current_bindings[key]!=old:changed.append({'field':key,'qualified_under':old,'current':current_bindings[key]})
 if not changed:return {'status':'QUALIFIED','debt':False,'authority':'NONE','changes':[]}
 relevant=set(qualification.get('load_bearing_bindings') or bound.keys());load=[x for x in changed if x['field'] in relevant]
 if not load:return {'status':'QUALIFIED_WITH_IRRELEVANT_CHANGE','debt':False,'authority':'NONE','changes':changed}
 return {'status':'REQUALIFICATION_REQUIRED','debt':True,'authority':'NONE','changes':load,'evidence_invalidated':False}

def query_admission(evidence:Mapping[str,Any],query:Mapping[str,Any])->dict[str,Any]:
 grants=evidence.get('admission_grants') or []
 wanted=(query.get('question_class'),query.get('consequence_class'),query.get('scope'))
 for g in grants:
  if (g.get('question_class'),g.get('consequence_class'),g.get('scope'))==wanted:
   return {'status':'ADMITTED','admitted':True,'authority':'NONE','grant':dict(g)}
 return {'status':'NOT_ADMITTED_FOR_QUERY','admitted':False,'authority':'NONE','query':dict(query)}

def scaffolding_class(evidence:Mapping[str,Any])->dict[str,Any]:
 layers=[]
 for key,label in [('server_enforced','SERVER_ENFORCED'),('server_projected','SERVER_PROJECTED'),('client_cooperative','CLIENT_COOPERATIVE'),('thread_scaffolded','THREAD_SCAFFOLDED'),('manual_operator','MANUAL_OPERATOR')]:
  if evidence.get(key):layers.append(label)
 strongest=layers[0] if layers else 'UNKNOWN'
 endogenous=strongest=='SERVER_ENFORCED'
 return {'status':'CLASSIFIED' if layers else 'UNKNOWN','layers':layers,'strongest':strongest,'endogenous_enforcement':endogenous,'authority':'NONE'}


def process_effect(receipt:Mapping[str,Any])->dict[str,Any]:
 effects={
  'loop_plus':bool((receipt.get('loop_plus') or {}).get('rivals') or (receipt.get('loop_plus') or {}).get('open')),
  'oarr':bool((receipt.get('oarr') or {}).get('attacks')) and bool((receipt.get('oarr') or {}).get('result')),
  'csc':(receipt.get('csc') or {}).get('authority') in {'audit_only','AUDIT_ONLY'} and bool((receipt.get('csc') or {}).get('finding') or (receipt.get('csc') or {}).get('questions')),
  'attention_reservoir':bool((receipt.get('attention_reservoir') or {}).get('selected')) and bool((receipt.get('attention_reservoir') or {}).get('reason')),
  'helix':bool((receipt.get('helix') or {}).get('next') or receipt.get('helix_next')),
 }
 missing=[k for k,v in effects.items() if not v]
 return {'status':'PROCESS_EFFECT_WITNESSED' if not missing else 'PROCESS_EFFECT_UNVERIFIED','effect_verified':not missing,'effects':effects,'missing':missing,'authority':'NONE'}

def reauthorize_campaign(original:Mapping[str,Any],current:Mapping[str,Any],load_bearing:list[str])->dict[str,Any]:
 missing=[k for k in load_bearing if k not in original or k not in current]
 if missing:return {'status':'UNKNOWN','promotion_eligible':False,'missing':missing,'authority':'NONE'}
 changed=[{'field':k,'original':original[k],'current':current[k]} for k in load_bearing if original[k]!=current[k]]
 if changed:return {'status':'REQUALIFICATION_REQUIRED','promotion_eligible':False,'changes':changed,'authority':'NONE'}
 return {'status':'REAUTHORIZED','promotion_eligible':True,'changes':[],'authority':'NONE'}

def doctrine_challenge(observation:Mapping[str,Any])->dict[str,Any]:
 if observation.get('contradicts_doctrine') is not True:return {'status':'NO_CHALLENGE','authority':'NONE'}
 if observation.get('evidence_integrity') is not True or observation.get('provenance_current') is not True:return {'status':'UNQUALIFIED_NONCOMPLIANCE','authority':'NONE'}
 return {'status':'DOCTRINE_CHALLENGE','authority':'NONE','promotion_blocked':True,'preserve_evidence':True,'requires_review':True}


def negative_evidence(record:Mapping[str,Any])->dict[str,Any]:
 required=('claim','attack','outcome','scope','reopen_condition')
 missing=[k for k in required if not record.get(k)]
 return {'status':'NEGATIVE_EVIDENCE_RECORDED' if not missing else 'UNQUALIFIED_NEGATIVE_EVIDENCE','qualified':not missing,'missing':missing,'authority':'NONE','record':dict(record) if not missing else None}

def semantic_delta(previous:Mapping[str,Any],current:Mapping[str,Any],load_bearing:list[str])->dict[str,Any]:
 changes=[]
 for k in load_bearing:
  if k not in previous or k not in current:changes.append({'field':k,'kind':'UNKNOWN_ENDPOINT','before':previous.get(k),'after':current.get(k)})
  elif previous[k]!=current[k]:changes.append({'field':k,'kind':'CHANGED','before':previous[k],'after':current[k]})
 return {'status':'NO_LOAD_BEARING_CHANGE' if not changes else 'SEMANTIC_DELTA','changes':changes,'authority':'NONE'}

def closure_escape(history:list[Mapping[str,Any]])->dict[str,Any]:
 if len(history)<3:return {'status':'INSUFFICIENT_PRESSURE','escape_search_justified':False,'authority':'NONE'}
 recent=history[-3:];same=all(x.get('primitive_closure')==recent[0].get('primitive_closure') for x in recent);unresolved=all(x.get('resolved') is False for x in recent);distinct=len({str(x.get('discriminator')) for x in recent})==3
 justified=same and unresolved and distinct
 return {'status':'CLOSURE_ESCAPE_CANDIDATE' if justified else 'CONTINUE_COMPOSITION','escape_search_justified':justified,'authority':'NONE'}

def research_depth(task:Mapping[str,Any])->dict[str,Any]:
 severity=int(task.get('consequence_severity',0));rivals=int(task.get('live_rivals',0));uncertainty=int(task.get('uncertainty',0));reserve=int(task.get('reserve',0));score=severity*2+rivals+uncertainty
 if reserve<=0:return {'depth':'HARD_STOP','reason':'NO_RESERVE','authority':'NONE'}
 if score>=10:return {'depth':'CAMPAIGN','reason':'HIGH_DISCRIMINATOR_LOAD','authority':'NONE'}
 if score>=5:return {'depth':'BOUNDED_OARR','reason':'MEDIUM_DISCRIMINATOR_LOAD','authority':'NONE'}
 return {'depth':'SINGLE_HOSTILE_CHECK','reason':'LOW_DISCRIMINATOR_LOAD','authority':'NONE'}
