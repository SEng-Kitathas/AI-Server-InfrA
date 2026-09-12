#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures,json,os,sys,time,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import lab_tools
from pcmmad_receiver import schema_vnext_runtime as runtime

def proc_metrics():
 try:
  import psutil;p=psutil.Process();return {'rss':p.memory_info().rss,'threads':p.num_threads(),'handles':p.num_handles() if hasattr(p,'num_handles') else None}
 except Exception:return {'rss':None,'threads':threading.active_count(),'handles':None}
def main():
 # Warm lazy imports/registry machinery before the resource baseline so one-time initialization is not misclassified as a leak.
 proc_metrics();lab_tools.list_tools();runtime.orient({'goal':'warm','project_id':'RECEIVER-LAB','capabilities':['protocol.status'],'detail':'full','ttl_seconds':10});import gc;gc.collect();time.sleep(0.1);before=proc_metrics();cards={c['name']:c for c in lab_tools.list_tools()};cases=[('protocol.status',{'project_id':'RECEIVER-LAB'}),('protocol.merkle.root',{'project_id':'RECEIVER-LAB'}),('architecture.registry.inspect',{'project_id':'RECEIVER-LAB','artifact':{'artifact_class':'state.current','logical_name':'CURRENT_STATE.md'}})]
 failures=[];t=time.perf_counter()
 def one(i):
  name,payload=cases[i%len(cases)]
  try:return lab_tools.dispatch_tool(name,payload,expected_contract_digest=cards[name]['contract_digest'])['ok']
  except Exception as exc:failures.append(f'{type(exc).__name__}:{exc}');return False
 with concurrent.futures.ThreadPoolExecutor(max_workers=24) as ex:results=list(ex.map(one,range(1200)))
 for _ in range(100):
  o=runtime.orient({'goal':'soak discovery','project_id':'RECEIVER-LAB','capabilities':['fs.glob','project.files.list','protocol.status'],'detail':'full','max_capabilities':8,'ttl_seconds':10});runtime.validate_lease(json.loads(json.dumps(o['lease'])))
 import gc;gc.collect();time.sleep(0.25);mid=proc_metrics();
 # A second identical pressure wave distinguishes persistent one-time runtime allocation from continuing growth.
 with concurrent.futures.ThreadPoolExecutor(max_workers=24) as ex:list(ex.map(one,range(1200,2400)))
 for _ in range(100):
  o=runtime.orient({'goal':'soak discovery','project_id':'RECEIVER-LAB','capabilities':['fs.glob','project.files.list','protocol.status'],'detail':'full','max_capabilities':8,'ttl_seconds':10});runtime.validate_lease(json.loads(json.dumps(o['lease'])))
 gc.collect();time.sleep(0.25);after=proc_metrics();report={'schema':'pcmmad.local-warfort-soak.v1','calls':1200,'orient_cycles':100,'failures':failures[:20],'failure_count':len(failures),'all_calls_ok':all(results),'seconds':round(time.perf_counter()-t,3),'before':before,'mid':mid,'after':after,'rss_growth':None if before['rss'] is None else after['rss']-before['rss'],'second_wave_rss_growth':None if mid['rss'] is None else after['rss']-mid['rss'],'thread_growth':after['threads']-before['threads'],'handle_growth':None if before['handles'] is None else after['handles']-before['handles'],'second_wave_handle_growth':None if mid['handles'] is None else after['handles']-mid['handles']};report['pass']=report['failure_count']==0 and report['all_calls_ok'] and report['thread_growth']<=4 and (report['second_wave_handle_growth'] is None or report['second_wave_handle_growth']<=4) and (report['second_wave_rss_growth'] is None or report['second_wave_rss_growth']<=4194304);q=ROOT/'qualification'/'warfort_soak.json';q.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps(report,sort_keys=True));raise SystemExit(0 if report['pass'] else 2)
if __name__=='__main__':main()
