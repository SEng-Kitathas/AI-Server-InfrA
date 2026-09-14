from __future__ import annotations
import re
from pathlib import Path
SAFE=re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$')
def plan(*,project_id:str,projects_root:Path,source_epoch:str|None=None)->dict:
 if not SAFE.fullmatch(project_id):return {'ok':False,'status':'INVALID_PROJECT_ID','authority':'NONE'}
 root=(projects_root/project_id).resolve();base=projects_root.resolve()
 try:root.relative_to(base)
 except ValueError:return {'ok':False,'status':'ROOT_ESCAPE','authority':'NONE'}
 if root.exists():return {'ok':False,'status':'ALREADY_EXISTS','authority':'NONE','root':str(root)}
 return {'ok':True,'status':'PROVISION_PLAN','authority':'NONE','project_id':project_id,'root':str(root),'source_epoch':source_epoch,'initial_generation':0,'writes':False}
def verify_isolation(a:dict,b:dict)->dict:
 if not a.get('ok') or not b.get('ok'):return {'isolated':False,'status':'UNKNOWN','authority':'NONE'}
 isolated=Path(a['root']).resolve()!=Path(b['root']).resolve() and a['project_id']!=b['project_id']
 return {'isolated':isolated,'status':'ISOLATED' if isolated else 'COLLISION','authority':'NONE'}


def commit(*,plan_record:dict,receipt_dir:Path)->dict:
 import json,os,secrets
 if not plan_record.get('ok') or plan_record.get('status')!='PROVISION_PLAN' or plan_record.get('writes') is not False: return {'ok':False,'status':'PLAN_NOT_ADMISSIBLE','authority':'NONE'}
 root=Path(plan_record['root']);receipt_dir=receipt_dir.resolve();receipt_dir.mkdir(parents=True,exist_ok=True)
 try:root.mkdir(parents=False,exist_ok=False)
 except FileExistsError:return {'ok':False,'status':'RACE_ALREADY_EXISTS','authority':'NONE'}
 try:
  marker=root/'.pcmmad_project_identity.json';identity={'project_id':plan_record['project_id'],'source_epoch':plan_record.get('source_epoch'),'initial_generation':0};marker.write_text(json.dumps(identity,sort_keys=True)+'\n',encoding='utf-8')
  rid='provision-'+secrets.token_hex(8);receipt=receipt_dir/(rid+'.json');payload={'ok':True,'status':'PROVISIONED','authority':'NONE','receipt_id':rid,'project_id':identity['project_id'],'root':str(root),'identity_marker':str(marker),'initial_generation':0};receipt.write_text(json.dumps(payload,sort_keys=True)+'\n',encoding='utf-8');return payload
 except Exception:
  try:
   for x in root.iterdir():x.unlink()
   root.rmdir()
  except Exception:pass
  raise


def commit_registered(*,plan_record:dict,receipt_dir:Path,registry_path:Path,fault_at:str|None=None)->dict:
 import json,secrets,os
 if not plan_record.get('ok') or plan_record.get('status')!='PROVISION_PLAN':return {'ok':False,'status':'PLAN_NOT_ADMISSIBLE','authority':'NONE'}
 root=Path(plan_record['root']);created=False
 def atomic(path:Path,obj:dict):
  path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp-'+secrets.token_hex(4));tmp.write_text(json.dumps(obj,sort_keys=True)+'\n',encoding='utf-8');os.replace(tmp,path)
 try:
  root.mkdir(parents=False,exist_ok=False);created=True
  if fault_at=='after_root':raise RuntimeError('INJECTED_AFTER_ROOT')
  ident={'project_id':plan_record['project_id'],'source_epoch':plan_record.get('source_epoch'),'initial_generation':0};atomic(root/'.pcmmad_project_identity.json',ident)
  if fault_at=='after_identity':raise RuntimeError('INJECTED_AFTER_IDENTITY')
  registry={}
  if registry_path.is_file():registry=json.loads(registry_path.read_text(encoding='utf-8'))
  if ident['project_id'] in registry:raise RuntimeError('REGISTRY_COLLISION')
  registry[ident['project_id']]={'root':str(root),'source_epoch':ident['source_epoch'],'generation':0};atomic(registry_path,registry)
  if fault_at=='after_registry':raise RuntimeError('INJECTED_AFTER_REGISTRY')
  rid='provision-'+secrets.token_hex(8);receipt={'ok':True,'status':'PROVISIONED_REGISTERED','authority':'NONE','receipt_id':rid,**registry[ident['project_id']],'project_id':ident['project_id']};atomic(receipt_dir/(rid+'.json'),receipt);return receipt
 except Exception as exc:
  # Compensating rollback is bounded to this newly-created identity; registry entry removed only if it points at this root.
  try:
   if registry_path.is_file():
    reg=json.loads(registry_path.read_text(encoding='utf-8'));ent=reg.get(plan_record.get('project_id'))
    if isinstance(ent,dict) and ent.get('root')==str(root):reg.pop(plan_record['project_id'],None);atomic(registry_path,reg)
   if created and root.exists():
    for x in list(root.iterdir()):x.unlink()
    root.rmdir()
  except Exception:return {'ok':False,'status':'ROLLBACK_FAILED','authority':'NONE','error':str(exc)}
  return {'ok':False,'status':'ROLLED_BACK','authority':'NONE','error':str(exc)}
