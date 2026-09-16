from __future__ import annotations

import argparse, hashlib, json, os, shutil, tempfile, time
from pathlib import Path
from typing import Any

from .daemon_plane import atomic_json
from .surfaces import audit_continuity_surfaces

class ProjectHandoffError(RuntimeError): pass

def _sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()

def _manifest_sha(handoff_dir:Path)->str:return _sha(handoff_dir/'SNAPSHOT_MANIFEST_SHA256.json')

def publish(source_dir:Path, project_root:Path)->dict[str,Any]:
    source_dir=source_dir.resolve();project_root=project_root.resolve();audit=audit_continuity_surfaces(source_dir)
    if audit.status!='CURRENT':raise ProjectHandoffError(f'SOURCE_HANDOFF_NOT_CURRENT:{audit.status}')
    root=project_root/'handoff';gens=root/'generations';gens.mkdir(parents=True,exist_ok=True)
    manifest_sha=_manifest_sha(source_dir);generation=f'{time.time_ns()}-{manifest_sha[:16]}'
    temp=gens/(generation+'.tmp');final=gens/generation
    if temp.exists():shutil.rmtree(temp)
    temp.mkdir(parents=True)
    try:
        for src in sorted(source_dir.iterdir()):
            if src.is_file():shutil.copy2(src,temp/src.name)
        copied=audit_continuity_surfaces(temp)
        if copied.status!='CURRENT':raise ProjectHandoffError(f'COPIED_HANDOFF_NOT_CURRENT:{copied.status}')
        for src in source_dir.iterdir():
            if src.is_file() and _sha(src)!=_sha(temp/src.name):raise ProjectHandoffError(f'HANDOFF_COPY_HASH_MISMATCH:{src.name}')
        os.replace(temp,final)
        pointer={'schema':'pcmmad.project-handoff-pointer.v1','generation':generation,'relative_path':f'generations/{generation}','manifest_sha256':manifest_sha,'published_at_epoch':time.time()}
        atomic_json(root/'current.json',pointer)
    finally:
        if temp.exists():shutil.rmtree(temp,ignore_errors=True)
    return pointer

def resolve(handoff_root:Path)->Path:
    handoff_root=handoff_root.resolve();pointer_path=handoff_root/'current.json'
    if not pointer_path.exists():raise ProjectHandoffError('HANDOFF_POINTER_MISSING')
    try:pointer=json.loads(pointer_path.read_text(encoding='utf-8'))
    except Exception as exc:raise ProjectHandoffError('HANDOFF_POINTER_CORRUPT') from exc
    if pointer.get('schema')!='pcmmad.project-handoff-pointer.v1':raise ProjectHandoffError('HANDOFF_POINTER_SCHEMA_MISMATCH')
    candidate=(handoff_root/str(pointer.get('relative_path') or '')).resolve();gens=(handoff_root/'generations').resolve()
    try:candidate.relative_to(gens)
    except ValueError as exc:raise ProjectHandoffError('HANDOFF_POINTER_ESCAPE') from exc
    if not candidate.is_dir():raise ProjectHandoffError('HANDOFF_GENERATION_MISSING')
    a=audit_continuity_surfaces(candidate)
    if a.status!='CURRENT':raise ProjectHandoffError(f'HANDOFF_GENERATION_NOT_CURRENT:{a.status}')
    if _manifest_sha(candidate)!=str(pointer.get('manifest_sha256') or ''):raise ProjectHandoffError('HANDOFF_POINTER_MANIFEST_MISMATCH')
    return candidate

def main(argv=None)->int:
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--project-root',required=True);args=ap.parse_args(argv)
    print(json.dumps(publish(Path(args.source),Path(args.project_root)),sort_keys=True));return 0

if __name__=='__main__':raise SystemExit(main())
