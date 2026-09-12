#!/usr/bin/env python3
from __future__ import annotations
import copy,json,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import lab_tools,schema_vnext_runtime as runtime,governance_observers as obs

def h(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
 names=['fs.glob','execution.run','project.files.read','transfer.meta','doctrine.global.status'];cards={c['name']:c for c in lab_tools.list_tools() if c['name'] in names};before=h(cards)
 oriented=runtime.orient({'goal':'governance live contract observation','project_id':'RECEIVER-LAB','capabilities':names,'detail':'full','max_capabilities':len(names),'ttl_seconds':60});projection={c['name']:c for c in oriented['capabilities']}
 clean=obs.govern_observation('capability.contract',obs.observe_contract(cards,projection))
 corrupted=copy.deepcopy(projection);corrupted['fs.glob']['input_schema']={'type':'object'}
 attacked=obs.govern_observation('capability.contract',obs.observe_contract(cards,corrupted));after=h(cards)
 report={'schema':'pcmmad.governance-live-contract-probe.v1','clean_status':clean['status'],'corrupted_status':attacked['status'],'corrupted_issues':attacked['issues'],'owner_digest_before':before,'owner_digest_after':after,'owner_unchanged':before==after,'governance_authority':attacked['authority'],'pass':clean['status']=='CONSISTENT' and attacked['status']=='CONTRADICTION' and before==after and attacked['authority']=='NONE'}
 q=ROOT/'qualification'/'governance_live_contract_probe.json';q.parent.mkdir(exist_ok=True);q.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps(report,sort_keys=True));raise SystemExit(0 if report['pass'] else 2)
if __name__=='__main__':main()
