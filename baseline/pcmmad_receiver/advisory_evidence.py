from __future__ import annotations
from pathlib import Path
from typing import Any
SURFACES=('LIVE_SHADOW.md','CURRENT_STATE.md','NEXT_STEPS.md','REVISIT_LEDGER.md','TRACE_MATRIX.md')
def gather(*,handoff_root:Path,issue:str,max_chars_per_surface:int=6000)->dict[str,Any]:
 terms={x.lower() for x in issue.replace('`',' ').replace('_',' ').split() if len(x)>=4};rows=[]
 for name in SURFACES:
  p=handoff_root/name
  if not p.is_file():rows.append({'surface':name,'status':'MISSING'});continue
  text=p.read_text(encoding='utf-8',errors='replace')[:max_chars_per_surface];lines=[ln for ln in text.splitlines() if any(t in ln.lower() for t in terms)][:12]
  rows.append({'surface':name,'status':'OBSERVED','path':str(p),'matches':lines})
 return {'schema':'pcmmad.advisory-evidence.v1','authority':'NONE','issue':issue,'observations':rows,'missing':[r['surface'] for r in rows if r['status']=='MISSING'],'may_mutate':False}


def gather_and_advise(*,handoff_root:Path,issue:str):
 from .agent_advisory import advise
 g=gather(handoff_root=handoff_root,issue=issue);obs=[]
 for row in g['observations']:
  if row['status']=='MISSING':obs.append({'status':'UNKNOWN','surface':row['surface'],'detail':'rollover surface missing'})
  elif row.get('matches'):obs.append({'status':'OBSERVED','surface':row['surface'],'matches':row['matches'],'evidence':{'server_projected':True}})
 return {'gather':g,'advisory':advise(issue=issue,observations=obs)}


def gather_extended(*,handoff_root:Path,project_root:Path,issue:str,max_bytes:int=12000):
 base=gather(handoff_root=handoff_root,issue=issue);terms={x.lower() for x in issue.replace('_',' ').split() if len(x)>=4};extra=[]
 candidates=[('RES',project_root/'continuity'/'research_epistemic_shadow'/'RESEARCH_EPISTEMIC_SHADOW.md'),('RESULT_INDEX',project_root/'system'/'lab'/'results'/'index.json')]
 for label,p in candidates:
  if not p.is_file():extra.append({'source':label,'status':'MISSING','provenance':str(p)});continue
  raw=p.read_bytes()[:max_bytes];text=raw.decode('utf-8','replace');hits=[ln for ln in text.splitlines() if any(t in ln.lower() for t in terms)][:12];extra.append({'source':label,'status':'OBSERVED','provenance':str(p),'matches':hits,'bytes_read':len(raw)})
 return {**base,'extended':extra}
def infer_candidates(evidence:dict)->dict:
 # deliberately weak symbolic inference: candidate only, never evidence.
 text=' '.join(str(x) for x in evidence.get('observations',[])+evidence.get('extended',[])).lower();out=[]
 if 'missing' in text:out.append({'hypothesis':'required evidence surface may be absent','epistemic_class':'INFERRED_CANDIDATE','authority':'NONE'})
 if 'stale' in text:out.append({'hypothesis':'currentness/requalification may discriminate the issue','epistemic_class':'INFERRED_CANDIDATE','authority':'NONE'})
 return {'authority':'NONE','candidates':out,'may_promote':False}


def gather_result_handle(*,project_id:str,handle:str,max_bytes:int=8192):
 from .lab_results import result_metadata,read_result_range
 meta=result_metadata(project_id,handle);data=read_result_range(project_id,handle,offset_bytes=0,length_bytes=min(max_bytes,8192));return {'source':'RESULT_HANDLE','status':'OBSERVED','provenance':handle,'metadata':meta,'preview':data,'authority':'NONE'}
def gather_runtime_source(*,runtime_root:Path,relative_path:str,max_bytes:int=8192):
 allowed=('baseline/pcmmad_receiver/','handoff/current/');rel=relative_path.replace('\\','/')
 if not any(rel.startswith(x) for x in allowed):return {'source':'RUNTIME_SOURCE','status':'NOT_ADMITTED','authority':'NONE'}
 p=(runtime_root/rel).resolve();base=runtime_root.resolve()
 try:p.relative_to(base)
 except ValueError:return {'source':'RUNTIME_SOURCE','status':'NOT_ADMITTED','authority':'NONE'}
 if not p.is_file():return {'source':'RUNTIME_SOURCE','status':'MISSING','provenance':str(p),'authority':'NONE'}
 raw=p.read_bytes()[:max_bytes];return {'source':'RUNTIME_SOURCE','status':'OBSERVED','provenance':str(p),'sha256_prefix':__import__('hashlib').sha256(raw).hexdigest(),'text':raw.decode('utf-8','replace'),'bytes_read':len(raw),'authority':'NONE'}
