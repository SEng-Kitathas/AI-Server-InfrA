"""Dependency-light break-glass dependency evaluator. Stdlib only; no pcmmad_receiver imports."""
from __future__ import annotations
import hashlib,json
from pathlib import Path

def sha256_file(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def load_manifest(path:Path)->dict:return json.loads(path.read_text(encoding='utf-8'))
def evaluate(manifest:dict,probes:dict[str,dict])->dict:
 rows=[]
 for dep in manifest.get('core_operation',[]):
  r=probes.get(dep['id']);status='UNKNOWN' if not r else ('QUALIFIED' if r.get('functional') is True else 'MISSING_OR_FAILED');rows.append({'id':dep['id'],'required':True,'status':status,'evidence':r})
 core=all(x['status']=='QUALIFIED' for x in rows)
 guarantees=[]
 for dep in manifest.get('guarantee_dependencies',[]):
  r=probes.get(dep['id']);guarantees.append({'id':dep['id'],'status':'QUALIFIED' if r and r.get('functional') is True else dep['absence']})
 return {'schema':'pcmmad.breakglass-evaluation.v1','core_operational':core,'core':rows,'guarantees':guarantees,'authority':'NONE'}
def verify_known_good(path:Path,expected_sha256:str)->dict:
 if not path.is_file():return {'functional':False,'reason':'MISSING'}
 actual=sha256_file(path);return {'functional':actual==expected_sha256,'sha256':actual,'reason':'HASH_MATCH' if actual==expected_sha256 else 'HASH_MISMATCH'}
