#!/usr/bin/env python3
from __future__ import annotations
import copy,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import lab_tools,schema_vnext_runtime as runtime,governance_observers as obs,governance_witness as w

def sha(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
 cards={c['name']:c for c in lab_tools.list_tools()};names=['fs.glob','execution.run','project.files.read','transfer.meta','doctrine.global.status'];authority={n:cards[n] for n in names};owner_before=sha(authority)
 oriented=runtime.orient({'goal':'anti-toy governance qualification','project_id':'RECEIVER-LAB','capabilities':names,'detail':'full','max_capabilities':10,'ttl_seconds':60});projection={c['name']:c for c in oriented['capabilities']}
 clean=obs.govern_observation('capability.contract',obs.observe_contract(authority,projection))
 stale=copy.deepcopy(projection);stale['execution.run']['contract_digest']='0'*64;stale_eval=obs.govern_observation('capability.contract',obs.observe_contract(authority,stale))
 scope=w.verify_scope_binding({'scope':{'project_id':'RECEIVER-LAB'}},{'project_id':'OTHER'})
 interval=w.verify_use_interval({'catalog_digest':runtime._catalog_digest(cards),'project_id':'RECEIVER-LAB'},{'catalog_digest':'changed','project_id':'RECEIVER-LAB'},['catalog_digest','project_id'])
 owner_after=sha(authority)
 report={'schema':'pcmmad.governance-anti-toy.v1','real_catalog_size':len(cards),'clean':clean['status'],'stale_projection':stale_eval['status'],'cross_project':scope['status'],'toctou_catalog_change':interval['status'],'owner_unchanged':owner_before==owner_after,'authority':'NONE','pass':clean['status']=='CONSISTENT' and stale_eval['status']=='CONTRADICTION' and scope['status']=='SCOPE_MISMATCH' and interval['status']=='STALE_DURING_USE' and owner_before==owner_after}
 q=ROOT/'qualification'/'governance_anti_toy_probe.json';q.parent.mkdir(exist_ok=True);q.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps(report,sort_keys=True));raise SystemExit(0 if report['pass'] else 2)
if __name__=='__main__':main()
