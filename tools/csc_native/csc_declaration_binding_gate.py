"""CSC declaration-binding compiler gate.

Static/deterministic only. It proves narrow bindings and reports its blind spots.
CSC_PASS != CODE_IS_GOOD.
"""
from __future__ import annotations
import ast,hashlib,json,re,subprocess,sys,tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
LIVE=('baseline','tools','supervisor','system','tests')
STD={'flask':'flask','requests':'requests','bs4':'beautifulsoup4','psutil':'psutil','prometheus_client':'prometheus-client','waitress':'waitress','hypothesis':'hypothesis','pytest':'pytest'}
def pyfiles():
 for base in LIVE:
  for p in (ROOT/base).rglob('*.py'):
   if not any(x in p.parts for x in ('build','__pycache__','.venv')):yield p
def imports():
 out={}
 for p in pyfiles():
  try:t=ast.parse(p.read_text(encoding='utf-8',errors='replace'))
  except SyntaxError:continue
  for n in ast.walk(t):
   if isinstance(n,ast.Import):names=[a.name.split('.')[0] for a in n.names]
   elif isinstance(n,ast.ImportFrom) and n.level==0 and n.module:names=[n.module.split('.')[0]]
   else:continue
   for x in names:out.setdefault(x,set()).add(str(p.relative_to(ROOT)))
 return out
def declared_deps():
 pj=tomllib.loads((ROOT/'pyproject.toml').read_text());vals=list(pj.get('project',{}).get('dependencies',[]));
 for v in pj.get('project',{}).get('optional-dependencies',{}).values():vals+=v
 vals+=(ROOT/'requirements-dev.txt').read_text().splitlines();names=set()
 for v in vals:
  x=re.split(r'[<>=!~\[; ]',v.strip(),1)[0].lower().replace('_','-')
  if x:names.add(x)
 return names
def d1():
 pj=(ROOT/'pyproject.toml').read_text();decl=[];missing=[]
 if '[tool.ruff' in pj:decl.append('ruff');
 consumers=' '.join(p.read_text(errors='ignore') for p in [ROOT/'.github/workflows/ci.yml',ROOT/'tools/csc_native/csc_code_health_gate.py',ROOT/'tools/final_polish_gate.py'])
 for x in decl:
  if x not in consumers.lower():missing.append(x)
 return {'rule':'D1','ok':not missing,'declared':decl,'missing_consumers':missing,'does_not_catch':'consumer correctness'}
def d3():
 im=imports();deps=declared_deps();stdlib=set(getattr(sys,'stdlib_module_names',()));undeclared=[]
 for mod,paths in sorted(im.items()):
  if mod in stdlib or mod.startswith('pcmmad_receiver') or mod in {'csc_doctrine_manifest','csc_runtime_bindings','csc_doctrine_passes'}:continue
  pkg=STD.get(mod,mod.lower().replace('_','-'))
  local=any(p.stem==mod for p in pyfiles())
  if pkg not in deps and not local and not (ROOT/(mod+'.py')).exists() and not (ROOT/mod).exists():undeclared.append({'import':mod,'expected_package':pkg,'paths':sorted(paths)[:8]})
 return {'rule':'D3','ok':not undeclared,'undeclared':undeclared,'does_not_catch':'dynamic imports or package/import-name mappings not represented in CSC map'}
def d35():
 im=imports();deps=declared_deps();used={STD.get(x,x.lower().replace('_','-')) for x in im};ignore={'ruff','pytest-xdist','py-spy'};ghost=sorted(x for x in deps if x not in used and x not in ignore)
 return {'rule':'D3.5','ok':not ghost,'ghost_dependencies':ghost,'report_only':True,'does_not_catch':'CLI-only/plugins/native transitive uses; allowlist requires review'}
def d4():
 m=ROOT/'handoff/current/SNAPSHOT_MANIFEST_SHA256.json';d=json.loads(m.read_text());bad=[]
 for name,row in d['files'].items():
  p=m.parent/name
  if not p.is_file():bad.append({'path':name,'reason':'missing'});continue
  raw=p.read_bytes();
  if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:bad.append({'path':name,'reason':'digest_or_size'})
 return {'rule':'D4','ok':not bad,'mismatches':bad,'does_not_catch':'semantic correctness of manifested content'}
def d7():
 refs={}
 for p in pyfiles():
  s=p.read_text(errors='ignore')
  for x in re.findall(r'(?:os\.environ\.get|os\.getenv)\(\s*[\'\"]([A-Z][A-Z0-9_]*)',s):refs.setdefault(x,set()).add(str(p.relative_to(ROOT)))
 schema=ROOT/'docs/verification/ENV_SCHEMA.md';decl=set(re.findall(r'`([A-Z][A-Z0-9_]*)`',schema.read_text(errors='ignore'))) if schema.exists() else set();missing=sorted(set(refs)-decl)
 return {'rule':'D7','ok':not missing,'referenced':len(refs),'undeclared_environment':missing,'schema':str(schema.relative_to(ROOT)),'report_only':True,'does_not_catch':'environment reads hidden behind arbitrary helper APIs'}

def d2():
 # Effect vocabulary: count declarations and exact-string reader references outside catalog declaration sites.
 vals=set();readers=set()
 for p in pyfiles():
  text=p.read_text(errors='ignore')
  for m in re.finditer(r'["\']effect_traits["\']\s*:\s*\[([^\]]*)\]',text,re.S):vals.update(re.findall(r'["\']([^"\']+)["\']',m.group(1)))
 for trait in vals:
  for p in pyfiles():
   text=p.read_text(errors='ignore')
   if trait in text and 'effect_traits' not in text:readers.add(trait);break
 return {'rule':'D2','ok':len(readers)==len(vals),'declared_metadata':len(vals),'consumed_metadata':len(readers),'ratio':f'{len(readers)}/{len(vals)}','report_only':True,'does_not_catch':'dynamic/indirect readers or semantic correctness of consumption'}
def d5():
 broken=[];checked=0
 for p in [ROOT/'README.md',ROOT/'EXTERNAL_EVALUATION.md',ROOT/'docs/verification/RELEASE_CONTRACT.md']:
  if not p.is_file():continue
  for ref in re.findall(r'`([^`]+(?:\.md|\.json|\.py|\.yml|\.yaml|\.toml))`',p.read_text(errors='ignore')):
   if '://' in ref or any(x in ref for x in '<>*'):continue
   checked+=1;candidates=[ROOT/ref,p.parent/ref]
   if not any(x.exists() for x in candidates):broken.append({'source':str(p.relative_to(ROOT)),'reference':ref})
 return {'rule':'D5','ok':not broken,'checked':checked,'broken':broken,'report_only':True,'does_not_catch':'prose references without path-like markup or semantic target correctness'}
def d6():
 p=ROOT/'docs/architecture/INVARIANTS.md';text=p.read_text(errors='ignore') if p.exists() else '';items=[x.strip() for x in text.splitlines() if x.strip().startswith(('-', '*'))];marked=sum('ENFORCEMENT:' in x.upper() for x in items)
 return {'rule':'D6','ok':marked==len(items) if items else True,'invariant_entries':len(items),'explicit_enforcement_markers':marked,'report_only':True,'does_not_catch':'whether mapped tests actually discriminate the invariant'}
def d8():
 bad=[];checked=0
 for p in pyfiles():
  for i,line in enumerate(p.read_text(errors='ignore').splitlines(),1):
   if p.name == 'csc_declaration_binding_gate.py': continue
   if '# noqa' in line or '# type: ignore' in line or '# csc: disable' in line:
    checked+=1;tail=line.split('#',1)[1]
    if not any(x in tail.lower() for x in ('because','reason:','justification:','compat','generated','optional','typing')):bad.append({'path':str(p.relative_to(ROOT)),'line':i,'text':line.strip()[:300]})
 return {'rule':'D8','ok':not bad,'overrides':checked,'unjustified':bad,'report_only':True,'does_not_catch':'whether stated justification is true'}

def tier1():
 cmd=[sys.executable,'-m','ruff','check','--select','F821,F403,F405,B023,B006','baseline','tools','supervisor','system','tests','--output-format','concise'];r=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
 return {'rule':'TIER1','ok':r.returncode==0,'return_code':r.returncode,'output':r.stdout[-16000:],'does_not_catch':'resource lifetime and async semantic defects beyond selected static rules'}
def run():
 rules=[d1(),d2(),d3(),d35(),d4(),d5(),d6(),d7(),d8(),tier1()];blocking={'D1','D3','D4','TIER1'};ok=all(x['ok'] for x in rules if x['rule'] in blocking);return {'schema':'pcmmad.csc-declaration-binding.v1','law':'DECLARED != BOUND != CONSUMED != CURRENT != EVICTED','history_law':'EVICTED != DELETED; CLAIM_SUPERSEDED != HISTORY_REWRITTEN','csc_pass_claim_ceiling':'narrow static bindings only; CSC_PASS != CODE_IS_GOOD','deterministic_static_gate':True,'qualified':ok,'rules':rules,'unverified_claims':[x for x in rules if not x['ok']]}
if __name__=='__main__':
 r=run();print(json.dumps(r,indent=2));raise SystemExit(0 if r['qualified'] else 1)
