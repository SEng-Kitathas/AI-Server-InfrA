from __future__ import annotations
from typing import Any,Mapping
def reopen_scan(*,arm_results:Mapping[str,Mapping[str,Any]],blockers:list[Mapping[str,Any]])->dict[str,Any]:
 facts=set()
 for arm,r in arm_results.items():
  for f in r.get('earned_facts',[]):facts.add(str(f))
 reopened=[];still=[]
 for b in blockers:
  requires={str(x) for x in b.get('reopen_requires',[])}
  item={**dict(b),'satisfied_by':sorted(requires & facts),'missing':sorted(requires-facts)}
  (reopened if requires and requires<=facts else still).append(item)
 return {'authority':'NONE','reopened':reopened,'still_blocked':still,'shared_facts':sorted(facts)}
def project_result(result:Mapping[str,Any],targets:list[str])->dict[str,Any]:
 return {'authority':'NONE','source_arm':result.get('arm'),'projections':{t:{'new_facts':list(result.get('earned_facts',[])),'new_scars':list(result.get('scars',[]))} for t in targets if t!=result.get('arm')}}
