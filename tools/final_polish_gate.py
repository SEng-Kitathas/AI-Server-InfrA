"""Microseed-derived final-polish gate. Evidence gates promotion; it grants no authority."""
from __future__ import annotations
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def _run(cmd):
 p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True);return {'command':cmd,'ok':p.returncode==0,'return_code':p.returncode,'stdout':p.stdout[-8000:],'stderr':p.stderr[-4000:]}
def main()->int:
 checks=[_run([sys.executable,'tools/csc_native/csc_declaration_binding_gate.py']),_run([sys.executable,'tools/csc_native/csc_code_health_gate.py']),_run([sys.executable,'-m','pytest','-q','tests/test_git_handoff_current.py','tests/test_runtime_observability.py'])]
 r={'schema':'pcmmad.final-polish.v1','qualified':all(x['ok'] for x in checks),'authority':'NONE','law':'CONFIGURED_STANDARD_REQUIRES_ENFORCING_CONSUMER','checks':checks};print(json.dumps(r,indent=2));return 0 if r['qualified'] else 1
if __name__=='__main__':raise SystemExit(main())
