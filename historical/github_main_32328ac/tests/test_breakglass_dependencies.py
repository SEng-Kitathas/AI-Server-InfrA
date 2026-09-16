from __future__ import annotations
import importlib.util,json,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('bg',ROOT/'supervisor/breakglass_core.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);manifest=json.loads((ROOT/'supervisor/breakglass_dependency_manifest.json').read_text())
def allgood():
 ids=[x['id'] for x in manifest['core_operation']]+[x['id'] for x in manifest['guarantee_dependencies']];return {x:{'functional':True} for x in ids}
def test_all_hard_functions_required_for_core():assert m.evaluate(manifest,allgood())['core_operational']
def test_one_hard_function_missing_blocks_core():
 p=allgood();p['persistent_state']={'functional':False};assert not m.evaluate(manifest,p)['core_operational']
def test_unknown_hard_dependency_never_inferred_green():
 p=allgood();p.pop('loopback_network');r=m.evaluate(manifest,p);assert not r['core_operational'] and next(x for x in r['core'] if x['id']=='loopback_network')['status']=='UNKNOWN'
def test_optional_browser_absence_does_not_block_core():
 p=allgood();p['browser_bridge']={'functional':False};r=m.evaluate(manifest,p);assert r['core_operational'] and next(x for x in r['guarantees'] if x['id']=='browser_bridge')['status']=='CORE_READY_OPTIONAL_DEGRADED'
def test_remote_ingress_absence_does_not_lie_about_remote():
 p=allgood();p['remote_ingress']={'functional':False};r=m.evaluate(manifest,p);assert r['core_operational'] and next(x for x in r['guarantees'] if x['id']=='remote_ingress')['status']=='LOCAL_CORE_READY_REMOTE_DEGRADED'
def test_known_good_material_hash_mismatch_fails():
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'x';p.write_bytes(b'a');assert not m.verify_known_good(p,'0'*64)['functional']
def test_breakglass_core_has_no_receiver_or_third_party_imports():
 import ast;tree=ast.parse((ROOT/'supervisor/breakglass_core.py').read_text());mods=[]
 for n in ast.walk(tree):
  if isinstance(n,ast.Import):mods.extend(a.name.split('.')[0] for a in n.names)
  elif isinstance(n,ast.ImportFrom):mods.append((n.module or '').split('.')[0])
 assert set(mods)<= {'__future__','hashlib','json','pathlib'}
