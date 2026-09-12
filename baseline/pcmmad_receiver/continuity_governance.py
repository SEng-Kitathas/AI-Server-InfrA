"""Non-authoritative readiness checks for doctrine/context/continuity consistency."""
from __future__ import annotations
from typing import Any,Mapping

def evaluate(packet:Mapping[str,Any])->dict[str,Any]:
 issues=[];unknown=[]
 doctrine=packet.get('doctrine')
 if not isinstance(doctrine,Mapping):unknown.append('doctrine')
 elif doctrine.get('current') is not True or not doctrine.get('digest'):issues.append({'code':'DOCTRINE_NOT_CURRENT'})
 pair=packet.get('continuity_pair')
 if not isinstance(pair,Mapping):unknown.append('continuity_pair')
 else:
  if not pair.get('live_shadow_current'):issues.append({'code':'LIVE_SHADOW_NOT_CURRENT'})
  if not pair.get('design_thread_current'):issues.append({'code':'DESIGN_THREAD_NOT_CURRENT'})
  if pair.get('lineage_consistent') is not True:issues.append({'code':'CONTINUITY_PAIR_CONTRADICTION'})
 ingress=packet.get('icf_ingress')
 if not isinstance(ingress,Mapping):unknown.append('icf_ingress')
 elif ingress.get('before_witness')!=ingress.get('after_witness'):issues.append({'code':'ICF_CURRENTNESS_CHANGED_DURING_REHYDRATION'})
 context=packet.get('context')
 if not isinstance(context,Mapping):unknown.append('context')
 elif context.get('provenance_complete') is not True:issues.append({'code':'CONTEXT_PROVENANCE_INCOMPLETE'})
 research=packet.get('research_process')
 if packet.get('non_trivial') is True:
  if not isinstance(research,Mapping) or research.get('qualified') is not True:issues.append({'code':'RESEARCH_PROCESS_UNQUALIFIED'})
 if unknown:return {'schema':'pcmmad.continuity-governance.v0','status':'UNKNOWN','ready':False,'authority':'NONE','unknown':unknown,'issues':issues}
 if issues:return {'schema':'pcmmad.continuity-governance.v0','status':'NOT_READY','ready':False,'authority':'NONE','unknown':[],'issues':issues}
 return {'schema':'pcmmad.continuity-governance.v0','status':'READY','ready':True,'authority':'NONE','unknown':[],'issues':[]}
