#!/usr/bin/env python3
from __future__ import annotations
import sys,tempfile,time,json
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import project_mutation_authority as pma

def main():
 with tempfile.TemporaryDirectory() as td, patch.object(pma,'PROJECTS_ROOT',Path(td)/'projects'):
  project='PRESSURE';Path(td,'projects',project).mkdir(parents=True)
  rows=[]
  for i in range(100):
   t=time.perf_counter()
   with pma.consequence_guard(project,session_id='warfort',timeout_seconds=1.0):
    pass
   snap=pma._consequence_holder_snapshot(project);rows.append({'i':i,'active':snap['active'],'ms':round((time.perf_counter()-t)*1000,3)})
  stuck=[r for r in rows if r['active']]
  report={'schema':'pcmmad.mutation-guard-pressure.v1','cycles':100,'stuck':stuck,'max_cycle_ms':max(r['ms'] for r in rows),'pass':not stuck}
  q=ROOT/'qualification'/'mutation_guard_pressure.json';q.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps(report,sort_keys=True));raise SystemExit(0 if report['pass'] else 2)
if __name__=='__main__':main()
