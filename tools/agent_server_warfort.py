#!/usr/bin/env python3
"""In-process emulation of fresh agent <-> schema-vNext server interaction."""
from __future__ import annotations
import copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import lab_tools,schema_vnext_runtime as rt

def main():
 cards={c['name']:c for c in lab_tools.list_tools()};checks=[]
 def ck(name,ok,detail=None):checks.append({'name':name,'ok':bool(ok),'detail':detail});
 # Fresh agent knows names only; full orient must return every explicitly requested contract, not silently cap.
 names=['maintenance.status','maintenance.acquire','maintenance.release','maintenance.authority.reconcile','fs.glob','execution.run','project.mutation.inspect','protocol.status','doctrine.global.status']
 o=rt.orient({'goal':'fresh agent maintenance/recovery','project_id':'RECEIVER-LAB','capabilities':names,'detail':'full','max_capabilities':len(names),'ttl_seconds':60});got={x['name']:x for x in o['capabilities']};ck('explicit_orient_complete',set(names)==set(got),sorted(got))
 ck('no_opaque_contracts',all(x.get('input_schema')!={'type':'object'} for x in got.values()))
 # Lease must survive JSON round trip exactly.
 lease=json.loads(json.dumps(o['lease']));
 try:rt.validate_lease(lease);ck('lease_json_roundtrip',True)
 except Exception as exc:ck('lease_json_roundtrip',False,str(exc))
 # Every returned contract digest must match authoritative catalog card.
 ck('contract_digest_parity',all(got[n]['contract_digest']==cards[n]['contract_digest'] for n in names))
 # Stale digest must fail, not execute.
 try:lab_tools.dispatch_tool('maintenance.status',{},expected_contract_digest='0'*64);ck('stale_contract_fails_closed',False,'accepted stale digest')
 except Exception as exc:ck('stale_contract_fails_closed',('STALE' in str(exc).upper() or 'digest' in str(exc).lower() or 'changed after client discovery' in str(exc).lower()),f'{type(exc).__name__}:{exc}')
 # Read-only maintenance status through actual dispatch contract.
 try:r=lab_tools.dispatch_tool('maintenance.status',{},expected_contract_digest=cards['maintenance.status']['contract_digest']);ck('maintenance_status_dispatch',bool(r.get('ok')),r)
 except Exception as exc:ck('maintenance_status_dispatch',False,str(exc))
 report={'schema':'pcmmad.agent-server-warfort.v1','catalog_count':len(cards),'checks':checks,'pass':all(x['ok'] for x in checks)};q=ROOT/'qualification'/'agent_server_warfort.json';q.parent.mkdir(exist_ok=True);q.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n');print(json.dumps(report,sort_keys=True,default=str));raise SystemExit(0 if report['pass'] else 2)
if __name__=='__main__':main()
