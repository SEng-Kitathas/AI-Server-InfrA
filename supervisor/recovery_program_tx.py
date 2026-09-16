#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,os,shutil,tempfile,uuid,stat
from pathlib import Path
MANIFEST_NAME='installed_program_manifest.json';SCHEMA='pcmmad.recovery-installed-program.v2'
SUPPORT_FILES=('RecoverySecret.psm1','breakglass_restore.ps1','receiver_supervisor.py','ngrok_supervisor.py','recovery_program_tx.py','rollback_unattended_recovery.ps1')
EXCLUDED_PARTS={'.git','.pytest_cache','.heat_runtime','__pycache__','build'}
class ProgramTxError(RuntimeError):pass
def _rooted(root:Path,rel:str)->Path:
 root=root.resolve();candidate=(root/rel).resolve()
 try:candidate.relative_to(root)
 except ValueError as exc:raise ProgramTxError(f'PROGRAM_PATH_ESCAPE:{rel}') from exc
 return candidate
def _sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def _atomic_json(path:Path,obj):
 path.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent);tp=Path(tmp)
 try:
  with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as h:json.dump(obj,h,indent=2,sort_keys=True);h.write('\n');h.flush();os.fsync(h.fileno())
  os.replace(tp,path)
 finally:tp.unlink(missing_ok=True)
def _excluded(rel:Path)->bool:
 return any(part in EXCLUDED_PARTS or part.endswith('.egg-info') for part in rel.parts) or rel.suffix=='.pyc'
def _safe_unlink(path:Path):
 try:path.unlink()
 except PermissionError:
  os.chmod(path,stat.S_IREAD|stat.S_IWRITE);path.unlink()
def _collect(bundle:Path,support:Path,daemon:Path)->dict[str,Path]:
 out={}
 for src in sorted(bundle.rglob('*')):
  rel=src.relative_to(bundle)
  if src.is_file() and not _excluded(rel):out[rel.as_posix()]=src
 for name in SUPPORT_FILES:
  src=support/name
  if not src.is_file():raise ProgramTxError(f'SUPPORT_FILE_MISSING:{name}')
  out[name]=src
 if not daemon.is_dir():raise ProgramTxError('DAEMON_SOURCE_MISSING')
 for src in sorted(daemon.rglob('*')):
  if src.is_file() and '__pycache__' not in src.parts and src.suffix!='.pyc':out[f'daemon_runtime/mvf_resident/{src.relative_to(daemon).as_posix()}']=src
 return out
def _load_manifest(path:Path):
 if not path.exists():return None
 try:obj=json.loads(path.read_text(encoding='utf-8-sig'))
 except Exception as exc:raise ProgramTxError('INSTALLED_PROGRAM_MANIFEST_CORRUPT') from exc
 if obj.get('schema') not in {SCHEMA,'pcmmad.recovery-installed-program.v1'}:raise ProgramTxError('INSTALLED_PROGRAM_MANIFEST_SCHEMA')
 files=obj.get('files')
 if not isinstance(files,(list,dict)):raise ProgramTxError('INSTALLED_PROGRAM_MANIFEST_FILES')
 return obj
def _manifest_files(obj):
 if not obj:return []
 raw=obj.get('files',[]);return list(raw.keys()) if isinstance(raw,dict) else [str(x) for x in raw]
def rollback(tx:Path,*,install_root:Path|None=None,ignore_missing_meta:bool=False):
 tx=tx.resolve();meta_path=tx/'tx.json'
 if not meta_path.exists():
  if ignore_missing_meta:return
  raise ProgramTxError('PROGRAM_TX_METADATA_MISSING')
 meta=json.loads(meta_path.read_text(encoding='utf-8'));root=install_root.resolve() if install_root else tx.parent.parent.resolve();manifest=root/MANIFEST_NAME;phase=str(meta.get('phase') or '')
 # PREPARED means backup did not complete, therefore old installation bytes were never lawfully eligible for replacement.
 if phase=='PREPARED':
  meta['phase']='ROLLED_BACK_UNTOUCHED';_atomic_json(meta_path,meta);return
 for rel in meta.get('new_files',[]):
  p=_rooted(root,str(rel))
  if p.is_file():_safe_unlink(p)
 backup=tx/'backup';old=meta.get('old_manifest')
 if old:
  missing=[rel for rel in _manifest_files(old) if not (backup/rel).is_file()]
  if missing:raise ProgramTxError('PROGRAM_TX_BACKUP_INCOMPLETE:'+','.join(missing[:10]))
  for rel in _manifest_files(old):
   src=backup/rel;dst=_rooted(root,rel);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
  _atomic_json(manifest,old)
 else:manifest.unlink(missing_ok=True)
 meta['phase']='ROLLED_BACK';_atomic_json(meta_path,meta)
def stage(bundle_source:Path,support_root:Path,daemon_source:Path,install_root:Path)->Path:
 bundle_source=bundle_source.resolve();support_root=support_root.resolve();daemon_source=daemon_source.resolve();install_root.mkdir(parents=True,exist_ok=True);install_root=install_root.resolve();mapping=_collect(bundle_source,support_root,daemon_source);manifest_path=install_root/MANIFEST_NAME;old=_load_manifest(manifest_path)
 tx=install_root/'.program_tx'/uuid.uuid4().hex;backup=tx/'backup';backup.mkdir(parents=True);meta={'schema':'pcmmad.recovery-program-tx.v1','old_manifest':old,'new_files':sorted(mapping),'phase':'PREPARED'};_atomic_json(tx/'tx.json',meta)
 try:
  for rel in _manifest_files(old):
   src=_rooted(install_root,rel)
   if src.is_file():
    dst=backup/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
   elif src.exists():raise ProgramTxError(f'PRIOR_PROGRAM_PATH_NOT_FILE:{rel}')
  meta['phase']='BACKED_UP';_atomic_json(tx/'tx.json',meta)
  for rel in _manifest_files(old):
   target=_rooted(install_root,rel)
   if target.exists():_safe_unlink(target)
  for rel,src in mapping.items():
   dst=_rooted(install_root,rel);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
  new={'schema':SCHEMA,'files':{rel:{'sha256':_sha(_rooted(install_root,rel)),'bytes':_rooted(install_root,rel).stat().st_size} for rel in sorted(mapping)}};_atomic_json(manifest_path,new);meta['phase']='STAGED';_atomic_json(tx/'tx.json',meta);return tx
 except Exception:
  rollback(tx,install_root=install_root);raise
def commit(tx:Path,*,archive_root:Path|None=None):
 tx=tx.resolve();meta=json.loads((tx/'tx.json').read_text(encoding='utf-8'));meta['phase']='COMMITTED';_atomic_json(tx/'tx.json',meta)
 if archive_root is None:shutil.rmtree(tx);return None
 archive_root=archive_root.resolve();archive_root.mkdir(parents=True,exist_ok=True);dest=archive_root/tx.name
 if dest.exists():raise ProgramTxError('PROGRAM_TX_ARCHIVE_COLLISION')
 os.replace(tx,dest);return dest
def main(argv=None):
 ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='cmd',required=True);st=sub.add_parser('stage');st.add_argument('--bundle-source',required=True);st.add_argument('--support-root',required=True);st.add_argument('--daemon-source',required=True);st.add_argument('--install-root',required=True);rb=sub.add_parser('rollback');rb.add_argument('--tx',required=True);rb.add_argument('--install-root',required=True);co=sub.add_parser('commit');co.add_argument('--tx',required=True);co.add_argument('--archive-root');a=ap.parse_args(argv)
 if a.cmd=='stage':print(stage(Path(a.bundle_source),Path(a.support_root),Path(a.daemon_source),Path(a.install_root)));return 0
 if a.cmd=='rollback':rollback(Path(a.tx),install_root=Path(a.install_root));return 0
 dest=commit(Path(a.tx),archive_root=Path(a.archive_root) if a.archive_root else None);print(str(dest) if dest else 'COMMITTED');return 0
if __name__=='__main__':raise SystemExit(main())
