"""Cross-plane non-authoritative governance relations harvested from Microseed/Veya mechanisms."""
from __future__ import annotations
from typing import Any,Mapping

def binding_witness(bound:Mapping[str,Any],current:Mapping[str,Any],load_bearing:list[str])->dict[str,Any]:
 missing=[k for k in load_bearing if k not in bound or k not in current]
 if missing:return {'status':'UNKNOWN','authority':'NONE','missing':missing,'current':False}
 changed=[{'field':k,'bound':bound[k],'current':current[k]} for k in load_bearing if bound[k]!=current[k]]
 return {'status':'CURRENT' if not changed else 'STALE','authority':'NONE','current':not changed,'changes':changed}
def admission_witness(grants:list[Mapping[str,Any]],query:Mapping[str,Any])->dict[str,Any]:
 keys=('question_class','consequence_class','scope')
 for g in grants:
  if all(g.get(k)==query.get(k) for k in keys):return {'status':'ADMITTED','authority':'NONE','admitted':True,'grant':dict(g)}
 return {'status':'NOT_ADMITTED','authority':'NONE','admitted':False,'query':dict(query)}
def qualification_debt(qualification:Mapping[str,Any],current:Mapping[str,Any])->dict[str,Any]:
 b=qualification.get('bindings');lb=qualification.get('load_bearing_bindings')
 if not isinstance(b,Mapping):return {'status':'UNKNOWN','authority':'NONE','debt':True,'reason':'BINDINGS_MISSING'}
 if not isinstance(lb,list):lb=list(b.keys())
 w=binding_witness(b,current,lb)
 if w['status']=='UNKNOWN':return {'status':'UNKNOWN','authority':'NONE','debt':True,'witness':w}
 return {'status':'QUALIFIED' if w['current'] else 'REQUALIFICATION_REQUIRED','authority':'NONE','debt':not w['current'],'evidence_invalidated':False,'witness':w}
def evidence_class(e:Mapping[str,Any])->dict[str,Any]:
 order=(('server_enforced','SERVER_ENFORCED'),('server_projected','SERVER_PROJECTED'),('client_cooperative','CLIENT_COOPERATIVE'),('thread_scaffolded','THREAD_SCAFFOLDED'),('manual_operator','MANUAL_OPERATOR'))
 layers=[label for key,label in order if e.get(key) is True]
 return {'status':'CLASSIFIED' if layers else 'UNKNOWN','authority':'NONE','layers':layers,'strongest':layers[0] if layers else 'UNKNOWN','endogenous':bool(layers and layers[0]=='SERVER_ENFORCED')}
def scar_record(*,claim:str,attack:str,outcome:str,scope:str,reopen_condition:str,provenance:Mapping[str,Any]|None=None)->dict[str,Any]:
 vals=(claim,attack,outcome,scope,reopen_condition)
 if not all(isinstance(x,str) and x.strip() for x in vals):return {'status':'UNQUALIFIED','authority':'NONE','qualified':False}
 return {'status':'SCAR_QUALIFIED','authority':'NONE','qualified':True,'claim':claim,'attack':attack,'outcome':outcome,'scope':scope,'reopen_condition':reopen_condition,'provenance':dict(provenance or {})}
def transition_witness(previous:Mapping[str,Any],delta:Mapping[str,Any],current:Mapping[str,Any],fields:list[str])->dict[str,Any]:
 unknown=[k for k in fields if k not in previous or k not in current]
 if unknown:return {'status':'UNKNOWN','authority':'NONE','consistent':False,'unknown':unknown}
 expected=dict(previous);expected.update({k:v for k,v in delta.items() if k in fields});bad=[k for k in fields if expected.get(k)!=current.get(k)]
 return {'status':'CONSISTENT' if not bad else 'CONTRADICTION','authority':'NONE','consistent':not bad,'fields':bad}
