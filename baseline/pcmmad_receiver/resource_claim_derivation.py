from __future__ import annotations
from typing import Any,Mapping
def derive(spec:Mapping[str,Any],payload:Mapping[str,Any])->dict[str,Any]:
 name=str(spec.get('name') or '');traits={str(x) for x in spec.get('effect_traits') or []};project=str(payload.get('project_id') or '')
 claims=[]
 if 'mutates_project_authority' in traits:claims.append({'domain':'project_authority','resource':project,'mode':'WRITE','project_id':project})
 if 'project_mutation_fenced' in traits:claims.append({'domain':'project','resource':project,'mode':'WRITE','project_id':project})
 if any(x in traits for x in {'git_mutation','mutates_git','git_index_mutation'}):claims.append({'domain':'git_index','resource':str(payload.get('worktree') or project),'mode':'WRITE','project_id':project})
 if 'durable_mutation' in traits and not claims:claims.append({'domain':'project','resource':project,'mode':'WRITE','project_id':project})
 if 'project_registry_mutation' in traits:claims.append({'domain':'project_registry','resource':'GLOBAL_PROJECT_REGISTRY','mode':'WRITE','project_id':project})
 return {'authority':'NONE','source':'SERVER_CAPABILITY_CONTRACT','capability':name,'claims':claims,'complete':bool(claims) or not bool(traits),'unknown_traits':sorted(x for x in traits if x not in {'mutates_project_authority','project_mutation_fenced','git_mutation','mutates_git','git_index_mutation','durable_mutation','bounded_ttl','cross_process_exclusion','generation_fence','spawns_process','executes_code','arbitrary_process_side_effects'})}


def witness(predicted:dict,observed:list[dict])->dict:
 pred={(x.get('domain'),x.get('resource'),x.get('mode')) for x in predicted.get('claims',[])};obs={(x.get('domain'),x.get('resource'),x.get('mode')) for x in observed};missing=sorted(obs-pred,key=str);extra=sorted(pred-obs,key=str);unknown=bool(predicted.get('unknown_traits'))
 ok=not missing and not unknown
 return {'status':'EFFECT_TRUTH_MATCH' if ok else 'EFFECT_TRUTH_UNVERIFIED','verified':ok,'authority':'NONE','unpredicted_effects':missing,'predicted_not_observed':extra,'unknown_traits':predicted.get('unknown_traits',[])}


READ_PREFIXES=('reads_','probes_','bounded_','not_','no_','authority_neutral','project_scope_enforced','local_only','deterministic','idempotent','health_probe','availability_probe')
WRITE_HINTS=('mutat','write','delete','create','append','replace','commit','queue','spawn','execute','network','external','registry','state','process','service','cache')
def classify_unmapped_traits(traits:list[str])->dict:
 safe=[];hazard=[]
 for t in traits:
  low=t.lower()
  if low.startswith(READ_PREFIXES):safe.append(t)
  elif any(h in low for h in WRITE_HINTS):hazard.append(t)
  else:hazard.append(t)
 return {'descriptive_or_read':safe,'unqualified_effect':hazard,'parallel_admissible':not hazard,'authority':'NONE'}
