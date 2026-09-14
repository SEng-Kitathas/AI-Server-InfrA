"""Mandatory CSC code-health gate: correctness hazards block promotion."""
from __future__ import annotations
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SURFACES=('baseline','tools','supervisor','system','tests')
CORRECTNESS=('F821','B023')
def run()->dict:
 cmd=[sys.executable,'-m','ruff','check','--select',','.join(CORRECTNESS),*SURFACES,'--output-format','concise'];p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
 return {'schema':'pcmmad.csc-code-health.v1','clean':p.returncode==0,'authority':'AUDIT_ONLY','blocking_rules':list(CORRECTNESS),'command':cmd,'return_code':p.returncode,'stdout':p.stdout[-12000:],'stderr':p.stderr[-4000:]}
def main()->int:
 r=run();print(json.dumps(r,indent=2));return 0 if r['clean'] else 1
if __name__=='__main__':raise SystemExit(main())
