#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, re, subprocess, time, hashlib
from pathlib import Path
TEXT_EXT={'.md','.txt','.json','.yaml','.yml','.toml','.py','.ps1','.ini','.cfg','.conf','.html','.htm','.mht','.xml','.rst'}
SKIP={'.git','node_modules','build','dist','.venv','venv','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','vendor','target','.pcmmad_sync_runs','qualification_logs','qualification_runs','logs','archive','archives','releases','data','research_cache','tmp','staging','source_bundle','third_party'}
PATTERN=r'descriptor\s*=\s*!'
def children(path:Path):
 try:return list(path.iterdir())
 except OSError:return []
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--projects-root',required=True);ap.add_argument('--state',required=True);ap.add_argument('--max-seconds',type=int,default=240);ap.add_argument('--per-node-timeout',type=int,default=5);ap.add_argument('--max-depth',type=int,default=5);args=ap.parse_args()
 root=Path(args.projects_root);state_path=Path(args.state)
 if state_path.is_file(): doc=json.loads(state_path.read_text(encoding='utf-8'))
 else:
  queue=[]
  for p in sorted([x for x in root.iterdir() if x.is_dir()],key=lambda x:x.name.lower()):queue.append({'project':p.name,'path':str(p),'depth':0})
  doc={'schema':'pcmmad.descriptor-index.v1','projects_root':str(root),'queue':queue,'hits':[],'completed_nodes':0,'timeouts':[],'errors':[]}
 rg=subprocess.run(['where','rg'],capture_output=True,text=True).stdout.splitlines()[0]
 deadline=time.monotonic()+args.max_seconds
 seen_hits={(h['project'],h['file'],h['line']) for h in doc['hits']}
 while doc['queue'] and time.monotonic()<deadline:
  item=doc['queue'].pop(0);p=Path(item['path']);depth=int(item['depth']);proj=item['project']
  if not p.exists():continue
  if p.is_dir() and p.name in SKIP:continue
  if p.is_file():
   if p.suffix.lower() not in TEXT_EXT:continue
   try:
    if p.stat().st_size>2_000_000:continue
    text=p.read_text(encoding='utf-8',errors='replace')
   except OSError:continue
   for i,line in enumerate(text.splitlines(),1):
    if re.search(PATTERN,line,re.I):
     rel=p.relative_to(root/proj).as_posix();key=(proj,rel,i)
     if key not in seen_hits:doc['hits'].append({'project':proj,'file':rel,'line':i,'text':line.strip()[:500]});seen_hits.add(key)
   doc['completed_nodes']+=1;continue
  cmd=[rg,'-i','-n','--max-filesize','2M']
  for ext in TEXT_EXT:cmd+=['--glob','*'+ext]
  for sk in SKIP:cmd+=['--glob',f'!**/{sk}/**']
  cmd += [PATTERN,str(p)]
  try:
   cp=subprocess.run(cmd,text=True,capture_output=True,timeout=args.per_node_timeout)
   if cp.returncode in (0,1):
    for raw in cp.stdout.splitlines():
     m=re.match(r'^(.*?):(\d+):(.*)$',raw)
     if not m:continue
     fp=Path(m.group(1));line=int(m.group(2));txt=m.group(3).strip()
     try:rel=fp.relative_to(root/proj).as_posix()
     except ValueError:rel=str(fp)
     key=(proj,rel,line)
     if key not in seen_hits:doc['hits'].append({'project':proj,'file':rel,'line':line,'text':txt[:500]});seen_hits.add(key)
    doc['completed_nodes']+=1
   else:doc['errors'].append({'project':proj,'path':str(p),'returncode':cp.returncode,'stderr':cp.stderr[-500:]})
  except subprocess.TimeoutExpired:
   if depth<args.max_depth:
    kids=[x for x in children(p) if not (x.is_dir() and x.name in SKIP)]
    if kids:doc['queue'][0:0]=[{'project':proj,'path':str(x),'depth':depth+1} for x in kids]
    else:doc['timeouts'].append({'project':proj,'path':str(p),'depth':depth})
   else:doc['timeouts'].append({'project':proj,'path':str(p),'depth':depth})
  if doc['completed_nodes']%25==0:
   state_path.parent.mkdir(parents=True,exist_ok=True);state_path.write_text(json.dumps(doc,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 doc['complete']=not bool(doc['queue']);doc['remaining_nodes']=len(doc['queue']);doc['hit_count']=len(doc['hits']);doc['project_hit_count']=len({h['project'] for h in doc['hits']});raw=json.dumps({k:v for k,v in doc.items() if k!='content_sha256'},sort_keys=True,separators=(',',':')).encode();doc['content_sha256']=hashlib.sha256(raw).hexdigest();state_path.parent.mkdir(parents=True,exist_ok=True);state_path.write_text(json.dumps(doc,indent=2,sort_keys=True)+'\n',encoding='utf-8');print(json.dumps({'complete':doc['complete'],'remaining_nodes':doc['remaining_nodes'],'hits':doc['hit_count'],'projects_with_hits':doc['project_hit_count'],'timeouts':len(doc['timeouts']),'errors':len(doc['errors']),'content_sha256':doc['content_sha256']},sort_keys=True))
if __name__=='__main__':main()
