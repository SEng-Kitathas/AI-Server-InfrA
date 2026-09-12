#!/usr/bin/env python3
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import lab_tools
from pcmmad_receiver.lab_schema_validation import validate_payload_schema

def sample_value(spec):
 if 'enum' in spec:return spec['enum'][0]
 typ=spec.get('type')
 if isinstance(typ,list):
  if 'null' in typ:return None
  typ=typ[0] if typ else None
 if typ=='string':
  pat=spec.get('pattern','')
  if '0-9a-f' in pat and '64' in pat:return '0'*64
  return 'x'
 if typ=='integer':return max(1,int(spec.get('minimum',1)))
 if typ=='number':return max(1,float(spec.get('minimum',1)))
 if typ=='boolean':return False
 if typ=='array':
  n=max(0,int(spec.get('minItems',0)));return [sample_value(spec.get('items',{})) for _ in range(n)]
 if typ=='object':
  return {k:sample_value(spec.get('properties',{}).get(k,{})) for k in spec.get('required',[])}
 return 'x'

def sample_for(schema):
 return {key:sample_value(schema.get('properties',{}).get(key,{})) for key in schema.get('required',[])}

def main():
 cards=lab_tools.list_tools();rows=[];fail=[]
 for c in cards:
  s=c['input_schema'];name=c['name'];sample=sample_for(s)
  try:validate_payload_schema(name,s,sample,raise_error=lambda code,msg,status,**extra: (_ for _ in ()).throw(ValueError(f'{code}: {msg}')));sample_ok=True
  except Exception as exc:sample_ok=False;fail.append({'name':name,'kind':'SCHEMA_SELF_SAMPLE_REJECTED','error':str(exc),'sample':sample})
  required=[]
  for key in s.get('required',[]):
   trial=dict(sample);trial.pop(key,None)
   try:validate_payload_schema(name,s,trial,raise_error=lambda code,msg,status,**extra: (_ for _ in ()).throw(ValueError(f'{code}: {msg}')));fail.append({'name':name,'kind':'MISSING_REQUIRED_ACCEPTED','field':key});required.append((key,False))
   except Exception:required.append((key,True))
  extra=dict(sample);extra['__unknown_contract_probe__']=1
  try:validate_payload_schema(name,s,extra,raise_error=lambda code,msg,status,**extra: (_ for _ in ()).throw(ValueError(f'{code}: {msg}')));extra_rejected=False
  except Exception:extra_rejected=True
  if s.get('additionalProperties') is False and not extra_rejected:fail.append({'name':name,'kind':'UNKNOWN_FIELD_ACCEPTED'})
  rows.append({'name':name,'sample_ok':sample_ok,'required_checks':required,'unknown_rejected':extra_rejected if s.get('additionalProperties') is False else None})
 report={'schema':'pcmmad.contract-parity-warfort.v1','capabilities':len(cards),'failures':fail,'failure_count':len(fail),'pass':not fail,'rows':rows}
 out=ROOT/'qualification'/'contract_parity_warfort.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8');print(json.dumps({'capabilities':len(cards),'failures':len(fail),'pass':not fail,'out':str(out)},sort_keys=True));raise SystemExit(0 if not fail else 2)
if __name__=='__main__':main()
