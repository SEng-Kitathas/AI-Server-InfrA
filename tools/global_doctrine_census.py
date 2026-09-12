#!/usr/bin/env python3
from __future__ import annotations
import argparse, concurrent.futures, hashlib, json, os, re
from collections import defaultdict
from pathlib import Path

TEXT_EXT={'.md','.txt','.json','.yaml','.yml','.toml','.py','.ps1','.ini','.cfg','.conf','.html','.htm','.mht','.xml','.rst'}
SKIP_DIRS={'.git','node_modules','build','dist','.venv','venv','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','vendor','target','.pcmmad_sync_runs','qualification_logs','qualification_runs','logs','archive','archives','releases','data','research_cache','tmp','staging','source_bundle','third_party'}
SEED_PATH_TOKENS={'scar','warfort','sop','law','doctrine','postmortem','lesson','failure','runbook','incident','invariant','checklist','rules','continuity','methodology','lineage','governance','handoff','decision_ledger','commanders_intent','locked_invariants','policy'}
SEED_HEADINGS={'operating rules','failure boundary','failure boundaries','locked invariants','commander’s intent','commanders intent','donor ingress policy','engineering decision ledger','what hostile os is becoming','methodology','rules','laws','invariants','scars','lessons learned','recovery'}
SEED_KEYS={'descriptor','law','laws','rule','rules','invariant','invariants','scar','scars','failure_boundary','failure_boundaries','authority','currentness','verification','recovery','donor','quarry','constraint','constraints'}
HIGH_NAME=re.compile(r'(scar|warfort|sop|law|doctrine|postmortem|lesson|failure|runbook|incident|invariant|checklist|rules)',re.I)
DESCRIPTOR=re.compile(r'(?i)descriptor\s*=\s*!')
RULE=re.compile(r'\b(must(?: not)?|never|do not|shall(?: not)?|should not|required|only if|invariant|law|rule|scar|failure boundary|fail[- ]closed|authority|currentness|readback|verify|verification|recovery|quarry|donor|compose|composition|counterexample|provenance)\b',re.I)
HEADING=re.compile(r'^\s{0,3}#{1,6}\s+(.+?)\s*$')
KVKEY=re.compile(r'^\s*["\']?([A-Za-z_][A-Za-z0-9_. -]{1,80})["\']?\s*[:=]')
INEQUALITY=re.compile(r'\b[A-Z][A-Z0-9_ -]{2,}\s*!=\s*[A-Z][A-Z0-9_ -]{2,}\b')

def family(name:str)->str:
 x=name.lower()
 if x.startswith(('pcmmad','receiver-lab')) or x=='pcmmad': return 'PCMMAD'
 if x.startswith(('protoagi_microseed','microseed')): return 'MICROSEED'
 if x=='cfe': return 'CFE'
 if x.startswith(('hsp','rahl-')): return 'HSP_RAHL'
 if x.startswith(('singularity-works','monster-standard','chimera_')): return 'FORGE_CHIMERA'
 if x.startswith('ergo_'): return 'ERGO'
 if x.startswith('aedifex'): return 'AEDIFEX'
 if x.startswith('classicboy'): return 'CLASSICBOY'
 if x.startswith('tq2') or x.startswith('pcmmad_tq2'): return 'TQ2'
 if x.startswith('cto-'): return 'CTO'
 return name.upper()

def norm(text:str)->str:
 x=text.lower().strip();x=re.sub(r'^\s*[-*+>#\d.()\[\]:]+\s*','',x);x=re.sub(r'`[^`]+`','<code>',x);x=re.sub(r'\b[0-9a-f]{40,64}\b','<hash>',x);x=re.sub(r'\b\d+\b','<n>',x);x=re.sub(r'\s+',' ',x);return x[:500]

def slug(text:str)->str:
 return re.sub(r'[^a-z0-9_]+','_',text.lower()).strip('_')[:80]

def safe_text(path:Path,max_bytes:int):
 try:
  if path.stat().st_size>max_bytes:return None
  data=path.read_bytes()
 except OSError:return None
 if b'\x00' in data[:4096]: return None
 for enc in ('utf-8','cp1252'):
  try:return data.decode(enc)
  except UnicodeDecodeError: pass
 return None

def _relevant_dir_name(name:str,tokens:set[str])->bool:
 parts=set(re.split(r'[/_. -]+',name.lower()))
 return bool(parts & tokens) or any(tok in name.lower() for tok in tokens if len(tok)>=5)

def candidate_paths(project:Path, learned:dict[str,set[str]], max_root_files:int=1500):
 tokens=SEED_PATH_TOKENS|learned['path_tokens'];paths=[];roots=[];unresolved=[]
 # Top-level authored files are always inspected.
 try: top=list(project.iterdir())
 except OSError: top=[]
 for item in top:
  if item.is_file() and item.suffix.lower() in TEXT_EXT: paths.append(item)
 # Shallow discovery (depth <= 3) finds authored roots without traversing bulk descendants.
 queue=[(item,1) for item in top if item.is_dir() and item.name not in SKIP_DIRS]
 while queue:
  directory,depth=queue.pop(0)
  rel=directory.relative_to(project).as_posix().lower()
  if _relevant_dir_name(rel,tokens):
   roots.append(directory);continue
  if depth>=3:continue
  try: kids=list(directory.iterdir())
  except OSError:continue
  for child in kids:
   if child.is_dir() and child.name not in SKIP_DIRS:queue.append((child,depth+1))
   elif child.is_file() and depth<=1 and child.suffix.lower() in TEXT_EXT and _relevant_dir_name(child.name,tokens):paths.append(child)
 # Recurse only inside earned authored roots.
 for root in roots:
  admitted=0;truncated=False
  for dp,dn,fn in os.walk(root):
   dn[:]=[d for d in dn if d not in SKIP_DIRS]
   for name in fn:
    path=Path(dp)/name
    if path.suffix.lower() not in TEXT_EXT:continue
    if admitted>=max_root_files:
     truncated=True;break
    paths.append(path);admitted+=1
   if truncated:break
  if truncated:unresolved.append({'root':root.relative_to(project).as_posix(),'reason':'ROOT_FILE_BUDGET','admitted_files':admitted,'max_root_files':max_root_files})
 # High-signal filenames visible in shallow levels are admitted even outside named roots.
 queue=[(project,0)]
 while queue:
  directory,depth=queue.pop(0)
  if depth>3:continue
  try:kids=list(directory.iterdir())
  except OSError:continue
  for child in kids:
   if child.is_dir() and child.name not in SKIP_DIRS:queue.append((child,depth+1))
   elif child.is_file() and child.suffix.lower() in TEXT_EXT and HIGH_NAME.search(child.name):paths.append(child)
 dedup={str(p).lower():p for p in paths}
 return list(dedup.values()),unresolved

def learn_from_text(project:Path,path:Path,text:str,pass_no:int,registry:list[dict],learned:dict[str,set[str]]):
 rel=path.relative_to(project).as_posix()
 for i,line in enumerate(text.splitlines(),1):
  m=HEADING.match(line)
  if m:
   heading=slug(m.group(1))
   if any(tok in heading for tok in ('rule','law','invariant','scar','failure','authority','doctrine','method','recovery','donor','quarry','intent','decision','lesson')) and heading not in learned['headings']:
    learned['headings'].add(heading);registry.append({'kind':'heading','value':heading,'learned_pass':pass_no,'project':project.name,'family':family(project.name),'file':rel,'line':i})
  m=KVKEY.match(line)
  if m:
   key=slug(m.group(1))
   if any(tok in key for tok in ('descriptor','rule','law','invariant','scar','failure','authority','currentness','verification','recovery','donor','quarry','constraint')) and key not in learned['keys']:
    learned['keys'].add(key);registry.append({'kind':'key','value':key,'learned_pass':pass_no,'project':project.name,'family':family(project.name),'file':rel,'line':i})
 for token in re.split(r'[/_. -]+',rel.lower()):
  if token and any(seed in token for seed in ('doctrine','method','lineage','govern','continuity','intent','decision','invariant','scar','sop','policy','lesson','recovery')) and token not in learned['path_tokens']:
   learned['path_tokens'].add(token);registry.append({'kind':'path_token','value':token,'learned_pass':pass_no,'project':project.name,'family':family(project.name),'file':rel,'line':None})

def extract_rows(project:Path,path:Path,text:str,pass_no:int,learned:dict[str,set[str]]):
 rel=path.relative_to(project).as_posix();rows=[];lines=text.splitlines();active_heading=None
 for i,line in enumerate(lines,1):
  t=line.strip();m=HEADING.match(line)
  if m: active_heading=slug(m.group(1))
  desc=bool(DESCRIPTOR.search(t));key=None;km=KVKEY.match(line)
  if km:key=slug(km.group(1))
  structural=desc or (active_heading in learned['headings']) or (key in learned['keys']) or bool(INEQUALITY.search(t))
  ruleish=18<=len(t)<=600 and RULE.search(t)
  if t and (desc or (structural and ruleish) or (ruleish and any(tok in rel.lower() for tok in SEED_PATH_TOKENS|learned['path_tokens']))):
   rows.append({'project':project.name,'family':family(project.name),'file':rel,'line':i,'pass':pass_no,'descriptor':desc,'heading':active_heading,'key':key,'text':t[:600],'normalized':norm(t)})
 return rows

def scan_project(project:Path,max_bytes:int,max_passes:int):
 learned={'path_tokens':set(),'headings':set(slug(x) for x in SEED_HEADINGS),'keys':set(SEED_KEYS)};registry=[];seen_files=set();rows=[];coverage=[]
 for pass_no in range(1,max_passes+1):
  paths,unresolved=candidate_paths(project,learned);new_paths=[p for p in paths if str(p).lower() not in seen_files];new_rows=0
  for path in new_paths:
   seen_files.add(str(path).lower());text=safe_text(path,max_bytes)
   if text is None:continue
   learn_from_text(project,path,text,pass_no,registry,learned);r=extract_rows(project,path,text,pass_no,learned);rows.extend(r);new_rows+=len(r)
  coverage.append({'pass':pass_no,'candidate_files':len(paths),'new_files':len(new_paths),'new_rows':new_rows,'learned_path_tokens':len(learned['path_tokens']),'learned_headings':len(learned['headings']),'learned_keys':len(learned['keys'])})
  if not new_paths:break
 # Descriptor hits discovered inside already-inspected authored files are retained here.
 descriptor_files=sorted({row["file"] for row in rows if row.get("descriptor")})
 return {'project':project.name,'family':family(project.name),'rows':rows,'descriptor_files':sorted(set(descriptor_files)),'locator_registry':registry,'coverage':coverage,'files_inspected':len(seen_files),'unresolved_roots':unresolved,'learned':{k:sorted(v) for k,v in learned.items()}}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--projects-root',required=True);ap.add_argument('--out',required=True);ap.add_argument('--max-file-bytes',type=int,default=750_000);ap.add_argument('--workers',type=int,default=12);ap.add_argument('--passes',type=int,default=3);args=ap.parse_args()
 root=Path(args.projects_root);projects=sorted([p for p in root.iterdir() if p.is_dir()],key=lambda p:p.name.lower())
 def guarded(p):
  try:return scan_project(p,args.max_file_bytes,args.passes)
  except Exception as exc:return {'project':p.name,'family':family(p.name),'rows':[],'descriptor_files':[],'locator_registry':[],'coverage':[],'files_inspected':0,'unresolved_roots':[{'root':'.','reason':'SCAN_EXCEPTION','error':f'{type(exc).__name__}: {exc}'}],'learned':{'path_tokens':[],'headings':[],'keys':[]}}
 with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex: results=list(ex.map(guarded,projects))
 all_rows=[row for r in results for row in r['rows']];clusters=defaultdict(list)
 for row in all_rows:clusters[row['normalized']].append(row)
 cross=[]
 for key,items in clusters.items():
  fams=sorted({x['family'] for x in items})
  if len(fams)>=2:
   examples=[];seen=set()
   for item in items:
    if item['family'] in seen:continue
    seen.add(item['family']);examples.append(item)
   cross.append({'normalized':key,'family_count':len(fams),'families':fams,'occurrences':len(items),'examples':examples[:8]})
 cross.sort(key=lambda x:(-x['family_count'],-x['occurrences'],x['normalized']))
 locator_rows=[x for r in results for x in r['locator_registry']]
 doc={'schema':'pcmmad.adaptive-global-doctrine-census.v3','projects_root':str(root),'project_count':len(results),'excluded_dir_names':sorted(SKIP_DIRS),'seed_locator':{'path_tokens':sorted(SEED_PATH_TOKENS),'headings':sorted(SEED_HEADINGS),'keys':sorted(SEED_KEYS),'special_content':['Descriptor=!… (fast pass only within selected authored files; exhaustive descriptor indexing is separate/resumable)','ALL_CAPS != ALL_CAPS']},'projects_with_descriptor_files':sum(bool(r['descriptor_files']) for r in results),'descriptor_file_count':sum(len(r['descriptor_files']) for r in results),'candidate_rule_rows':len(all_rows),'learned_locator_count':len(locator_rows),'locator_registry':locator_rows,'cross_family_exact_clusters':cross,'unresolved_root_count':sum(len(r.get('unresolved_roots',[])) for r in results),'projects':[{'project':r['project'],'family':r['family'],'files_inspected':r['files_inspected'],'descriptor_files':r['descriptor_files'],'coverage':r['coverage'],'unresolved_roots':r.get('unresolved_roots',[]),'learned':r['learned']} for r in results],'rows':all_rows}
 raw=json.dumps(doc,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode();doc['content_sha256']=hashlib.sha256(raw).hexdigest();out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(doc,indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf-8');print(json.dumps({'project_count':doc['project_count'],'descriptor_projects':doc['projects_with_descriptor_files'],'descriptor_files':doc['descriptor_file_count'],'candidate_rows':doc['candidate_rule_rows'],'learned_locators':doc['learned_locator_count'],'cross_family_clusters':len(cross),'content_sha256':doc['content_sha256'],'out':str(out)},sort_keys=True))
if __name__=='__main__':main()
