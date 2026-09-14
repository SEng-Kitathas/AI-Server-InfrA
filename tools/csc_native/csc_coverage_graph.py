"""CSC doctrine coverage graph: declarations are claims, not authority."""
from __future__ import annotations
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCES=[ROOT/'docs/universal_invariants/UNIVERSAL_CSC_DOCTRINE_CODE_STYLE_GUIDE.md',ROOT/'docs/ergo_foundations/UNIFIED_CODE_STANDARDS_DOCTRINE_v1.2.md',ROOT/'docs/ergo_foundations/UNIFIED_CODE_STANDARDS_AGNOSTIC_2026-04-11.md',ROOT/'docs/architecture/INVARIANTS.md',ROOT/'docs/verification/RELEASE_CONTRACT.md']+sorted((ROOT/'docs/csc_sop').glob('*.md'))
CONSUMERS={'CSC_DECLARATION_BINDING':ROOT/'tools/csc_native/csc_declaration_binding_gate.py','CSC_CODE_HEALTH':ROOT/'tools/csc_native/csc_code_health_gate.py','FINAL_POLISH':ROOT/'tools/final_polish_gate.py','MVF_PROMOTION':ROOT/'baseline/pcmmad_receiver/mvf_promotion_gate.py','RELEASE_VERIFY':ROOT/'tools/verify_release.py','CI':ROOT/'.github/workflows/ci.yml'}
def declarations():
 rows=[]
 for p in SOURCES:
  if not p.is_file():continue
  for i,line in enumerate(p.read_text(errors='replace').splitlines(),1):
   text=line.strip()
   if text and (re.search(r'\b(SHALL|MUST|REQUIRED|NEVER)\b',text,re.I) or '!=' in text):rows.append({'source':str(p.relative_to(ROOT)),'line':i,'text':text[:500]})
 return rows
def run():
 dec=declarations();cons={k:{'path':str(v.relative_to(ROOT)),'current':v.is_file()} for k,v in CONSUMERS.items()};return {'schema':'pcmmad.csc-coverage-graph.v1','authority':'NONE','declaration_count':len(dec),'sources':[str(x.relative_to(ROOT)) for x in SOURCES if x.is_file()],'consumers':cons,'declarations':dec,'coverage_classes':['STATIC','SCHEMA_TYPE','RUNTIME','HOSTILE','INTEGRATION','ORDINARY_PATH','MANUAL_SEMANTIC','GAP','NOT_APPLICABLE'],'claim_ceiling':'inventory/coverage topology only; declaration extraction does not prove applicability or enforcement correctness'}
if __name__=='__main__':print(json.dumps(run(),indent=2))
