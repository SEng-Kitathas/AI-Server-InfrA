#!/usr/bin/env python3
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import lab_tools
from pcmmad_receiver import schema_vnext_runtime as runtime
FAMILIES=['fs.glob','project.files.list','git.status','execution.status','transfer.meta','sop.ingest.status','research.hunt','migration.inspect','control.hud.status','protocol.status']
def main():
 cards={c['name']:c for c in lab_tools.list_tools()};out=runtime.orient({'goal':'fresh agent representative workflow contract dogfood','project_id':'RECEIVER-LAB','capabilities':FAMILIES,'detail':'full','max_capabilities':20,'ttl_seconds':60});seen={c['name']:c for c in out['capabilities']};rows=[];fail=[]
 for name in FAMILIES:
  c=seen.get(name);ok=bool(c and c.get('input_schema')==cards[name]['input_schema'] and c.get('schema_hash')==cards[name]['schema_hash'] and c.get('contract_digest')==cards[name]['contract_digest']);rows.append({'name':name,'ok':ok,'schema':c.get('input_schema') if c else None});
  if not ok:fail.append(name)
 lease=json.loads(json.dumps(out['lease'],sort_keys=True));lease_ok=runtime.validate_lease(lease)['current'] is True
 report={'schema':'pcmmad.fresh-agent-contract-dogfood.v1','families':rows,'failures':fail,'lease_json_roundtrip':lease_ok,'pass':not fail and lease_ok};q=ROOT/'qualification'/'fresh_agent_contract_dogfood.json';q.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8');print(json.dumps({'families':len(rows),'failures':fail,'lease':lease_ok,'pass':report['pass']},sort_keys=True));raise SystemExit(0 if report['pass'] else 2)
if __name__=='__main__':main()
