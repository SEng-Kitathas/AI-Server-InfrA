"""Non-authoritative architectural consistency verifier."""
from __future__ import annotations
from typing import Any,Mapping
SCHEMA='pcmmad.governance-kernel.v0'
REQUIRED=('subject','question','authoritative_owner','projections','admission_rule','recovery_source','retirement_condition')
def evaluate_relation(relation:Mapping[str,Any],observed:Mapping[str,Any]|None=None)->dict[str,Any]:
 observed=dict(observed or {});issues=[]
 for key in REQUIRED:
  if key not in relation:issues.append({'code':'MISSING_RELATION_FIELD','field':key})
 owner=str(relation.get('authoritative_owner') or '').strip()
 if not owner:issues.append({'code':'MISSING_AUTHORITY_OWNER'})
 projections=relation.get('projections') or []
 if not isinstance(projections,list):issues.append({'code':'PROJECTIONS_NOT_LIST'});projections=[]
 for p in projections:
  if isinstance(p,Mapping) and p.get('claims_authority') is True:issues.append({'code':'PROJECTION_CLAIMS_AUTHORITY','projection':p.get('name')})
 currentness=relation.get('currentness_witness')
 if relation.get('currentness_required') and not currentness:issues.append({'code':'CURRENTNESS_WITNESS_MISSING'})
 if observed.get('authority_owner') and owner and observed['authority_owner']!=owner:issues.append({'code':'AUTHORITY_OWNER_CONTRADICTION','declared':owner,'observed':observed['authority_owner']})
 if observed.get('candidate_promoted_without_gate'):issues.append({'code':'ADMISSION_GATE_BYPASS'})
 if observed.get('derived_mutated_authority'):issues.append({'code':'DERIVED_STATE_AUTHORITY_ESCAPE'})
 return {'schema':SCHEMA,'status':'CONSISTENT' if not issues else 'CONTRADICTION','authority':'NONE','subject':relation.get('subject'),'question':relation.get('question'),'issues':issues,'issue_count':len(issues)}
def evaluate_manifest(manifest:Mapping[str,Any],observations:Mapping[str,Any]|None=None)->dict[str,Any]:
 obs=dict(observations or {});rels=manifest.get('relations') or []
 if not isinstance(rels,list):raise ValueError('relations must be an array')
 rows=[evaluate_relation(r,obs.get(str(r.get('subject')),{})) for r in rels if isinstance(r,Mapping)];issues=sum(x['issue_count'] for x in rows)
 return {'schema':SCHEMA,'status':'CONSISTENT' if issues==0 else 'CONTRADICTION','authority':'NONE','relations':rows,'relation_count':len(rows),'issue_count':issues}


KNOWN_RELATIONS={
 'capability.contract':{'subject':'capability.contract','question':'what invocation grammar is authoritative?','authoritative_owner':'lab_tools.registry','currentness_required':True,'currentness_witness':'catalog_digest + contract_digest','projections':[{'name':'orientCapabilities','claims_authority':False},{'name':'tool harness','claims_authority':False}],'admission_rule':'register_tool contract construction','recovery_source':'registered ToolSpec definitions','retirement_condition':'no legacy opaque/fallback contract consumers'},
 'global.doctrine':{'subject':'global.doctrine','question':'what global engineering law is promoted?','authoritative_owner':'global_doctrine.current','currentness_required':True,'currentness_witness':'version + canonical digest','projections':[{'name':'bootstrap','claims_authority':False},{'name':'HUD','claims_authority':False}],'admission_rule':'explicit operator doctrine.global.promote','recovery_source':'versioned doctrine history','retirement_condition':'superseded version retained as history only'},
 'mutation.generation':{'subject':'mutation.generation','question':'who owns project mutation now?','authoritative_owner':'project_mutation_authority.lease','currentness_required':True,'currentness_witness':'generation + lease expiry + consequence holder','projections':[{'name':'HUD authority panel','claims_authority':False}],'admission_rule':'project.mutation.acquire/renew/release','recovery_source':'persisted mutation authority state','retirement_condition':'expired/released generation cannot authorize mutation'},
 'migration.receipt':{'subject':'migration.receipt','question':'has a migration consequence been verified?','authoritative_owner':'migration_runtime.receipt','currentness_required':True,'currentness_witness':'plan identity + verification receipt','projections':[{'name':'migration HUD','claims_authority':False}],'admission_rule':'inspect -> plan -> execute -> verify -> receipt','recovery_source':'authoritative preimage + migration receipt','retirement_condition':'legacy migrator removable after qualified consumer count reaches zero'},
 'receiver.restart':{'subject':'receiver.restart','question':'did the receiver restart into the intended source?','authoritative_owner':'restart_control.receipt','currentness_required':True,'currentness_witness':'restart receipt + health + source/head witness','projections':[{'name':'HUD receiver status','claims_authority':False}],'admission_rule':'out-of-process restart/supervisor verification','recovery_source':'supervisor restart receipt','retirement_condition':'self-observed restart path no longer relied upon'},
}

def evaluate_known(subject:str,observed:Mapping[str,Any]|None=None)->dict[str,Any]:
 relation=KNOWN_RELATIONS.get(subject)
 if relation is None:return {'schema':SCHEMA,'status':'UNKNOWN_RELATION','authority':'NONE','subject':subject,'issues':[{'code':'UNKNOWN_RELATION'}],'issue_count':1}
 return evaluate_relation(relation,observed)
