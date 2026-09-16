from __future__ import annotations

import json, os, shutil, sqlite3, tempfile, hashlib, contextlib, threading
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping

DAEMON_PLANE_SCHEMA = 1
RESERVED_SIBLING_PLANES = {"state", "continuity", "data", "handoff"}

class DaemonPlaneError(RuntimeError): pass
class DaemonPlaneBusy(DaemonPlaneError): pass
class DaemonPlaneCorrupt(DaemonPlaneError): pass
class DaemonPlaneMigrationError(DaemonPlaneError): pass

_SERVICE_LOCAL_GUARD = threading.RLock()
_SERVICE_LOCAL_HELD: set[str] = set()

@dataclass(frozen=True)
class DaemonPlanePaths:
    root: Path
    identity: Path
    current_state: Path
    evidence_db: Path
    biography_db: Path
    lock: Path
    checkpoints: Path
    migrations: Path
    quarantine: Path
    status_current: Path
    status_timeline: Path
    status_alerts: Path
    service_lock: Path

@dataclass(frozen=True)
class DaemonPlaneAudit:
    status: str
    schema_version: int | None
    missing: tuple[str,...] = ()
    corrupt: tuple[str,...] = ()
    mutation_authority: bool = False
    def to_dict(self) -> dict[str,Any]: return asdict(self)

def paths(root: Path) -> DaemonPlanePaths:
    return DaemonPlanePaths(root,root/'identity'/'daemon_identity.json',root/'state'/'current.json',root/'evidence'/'evidence.sqlite',root/'biography'/'biography.sqlite',root/'runtime'/'locks'/'plane.lock',root/'runtime'/'checkpoints',root/'migrations',root/'quarantine',root/'status'/'current.json',root/'status'/'timeline.jsonl',root/'status'/'alerts.jsonl',root/'runtime'/'locks'/'service.lock')

def qualify_root(root: Path, *, project_root: Path | None=None) -> None:
    root=root.resolve()
    if root.name.casefold() in RESERVED_SIBLING_PLANES:
        raise DaemonPlaneError('DAEMON_PLANE_COLLIDES_WITH_EXISTING_PLANE')
    if project_root is not None:
        pr=project_root.resolve()
        if root.parent != pr or root.name.casefold() != 'daemon':
            raise DaemonPlaneError('DAEMON_PLANE_MUST_BE_FIRST_CLASS_PROJECT_SIBLING')

def _fsync_dir(path: Path) -> None:
    if os.name == 'nt': return
    fd=os.open(str(path),os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)

def atomic_json(path: Path, payload: Any, *, before_replace: Callable[[Path],None] | None=None) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    tp=Path(tmp)
    try:
        with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as h:
            json.dump(payload,h,sort_keys=True,indent=2);h.write('\n');h.flush();os.fsync(h.fileno())
        if before_replace is not None: before_replace(tp)
        os.replace(tp,path);_fsync_dir(path.parent)
    finally:
        if tp.exists(): tp.unlink(missing_ok=True)

def _lock(handle,blocking:bool) -> None:
    handle.seek(0)
    if os.name=='nt':
        import msvcrt;msvcrt.locking(handle.fileno(),msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK,1)
    else:
        import fcntl;fcntl.flock(handle.fileno(),fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))

def _unlock(handle) -> None:
    handle.seek(0)
    if os.name=='nt':
        import msvcrt;msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
    else:
        import fcntl;fcntl.flock(handle.fileno(),fcntl.LOCK_UN)

@contextlib.contextmanager
def plane_lock(path: Path, *, blocking: bool=True) -> Iterator[None]:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as h:
        h.seek(0,os.SEEK_END)
        if h.tell()==0: h.write(b'0');h.flush();os.fsync(h.fileno())
        try:_lock(h,blocking)
        except (OSError,BlockingIOError) as exc: raise DaemonPlaneBusy('DAEMON_PLANE_BUSY') from exc
        try: yield
        finally: _unlock(h)

@contextlib.contextmanager
def service_lease(root: Path, *, blocking: bool=False) -> Iterator[None]:
    p=paths(root);key=str(p.service_lock.resolve()).casefold()
    with _SERVICE_LOCAL_GUARD:
        if key in _SERVICE_LOCAL_HELD:
            raise DaemonPlaneBusy('DAEMON_SERVICE_ALREADY_ACTIVE')
        _SERVICE_LOCAL_HELD.add(key)
    ctx=plane_lock(p.service_lock,blocking=blocking)
    try:
        ctx.__enter__()
    except Exception:
        with _SERVICE_LOCAL_GUARD:_SERVICE_LOCAL_HELD.discard(key)
        raise
    try:
        yield
    finally:
        try:ctx.__exit__(None,None,None)
        finally:
            with _SERVICE_LOCAL_GUARD:_SERVICE_LOCAL_HELD.discard(key)

def open_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=5.0,isolation_level=None)
    db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL');db.execute('PRAGMA foreign_keys=ON')
    db.execute('CREATE TABLE IF NOT EXISTS daemon_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
    db.execute("INSERT OR IGNORE INTO daemon_meta(key,value) VALUES ('schema_version',?)",(str(DAEMON_PLANE_SCHEMA),))
    return db

def initialize(root: Path, *, daemon_id: str, project_id: str) -> DaemonPlanePaths:
    qualify_root(root); p=paths(root)
    for d in [p.identity.parent,p.current_state.parent,p.evidence_db.parent,p.biography_db.parent,p.lock.parent,p.checkpoints,p.migrations,p.quarantine,p.status_current.parent]: d.mkdir(parents=True,exist_ok=True)
    with plane_lock(p.lock):
        if p.identity.exists():
            try: ident=json.loads(p.identity.read_text(encoding='utf-8'))
            except Exception as exc: raise DaemonPlaneCorrupt('DAEMON_IDENTITY_CORRUPT') from exc
            if int(ident.get('schema_version',-1))!=DAEMON_PLANE_SCHEMA: raise DaemonPlaneCorrupt('DAEMON_IDENTITY_SCHEMA_MISMATCH')
            if str(ident.get('daemon_id') or '')!=str(daemon_id): raise DaemonPlaneCorrupt('DAEMON_IDENTITY_MISMATCH')
            if str(ident.get('project_id') or '')!=str(project_id): raise DaemonPlaneCorrupt('DAEMON_PROJECT_MISMATCH')
            if ident.get('authority')!='COGNITIVE_PLANE_ONLY': raise DaemonPlaneCorrupt('DAEMON_AUTHORITY_IDENTITY_INVALID')
        else:
            atomic_json(p.identity,{'schema_version':DAEMON_PLANE_SCHEMA,'daemon_id':daemon_id,'project_id':project_id,'authority':'COGNITIVE_PLANE_ONLY'})
        if p.current_state.exists():
            try: cur=json.loads(p.current_state.read_text(encoding='utf-8'))
            except Exception as exc: raise DaemonPlaneCorrupt('DAEMON_CURRENT_STATE_CORRUPT') from exc
            if str(cur.get('daemon_id') or '')!=str(daemon_id): raise DaemonPlaneCorrupt('CURRENT_STATE_DAEMON_IDENTITY_MISMATCH')
        else:
            atomic_json(p.current_state,{'schema_version':DAEMON_PLANE_SCHEMA,'daemon_id':daemon_id,'state':{},'generation':0})
        for dbp in [p.evidence_db,p.biography_db]:
            db=open_db(dbp);db.close()
    return p

def audit(root: Path) -> DaemonPlaneAudit:
    p=paths(root);missing=[];corrupt=[];schema=None
    for name,path in [('identity',p.identity),('current_state',p.current_state),('evidence_db',p.evidence_db),('biography_db',p.biography_db)]:
        if not path.exists(): missing.append(name)
    if missing:return DaemonPlaneAudit('UNKNOWN_INCOMPLETE',None,tuple(missing),())
    for name,path in [('identity',p.identity),('current_state',p.current_state)]:
        try:
            obj=json.loads(path.read_text(encoding='utf-8'));v=int(obj.get('schema_version',-1));schema=v if schema is None else schema
            if v!=DAEMON_PLANE_SCHEMA: corrupt.append(name+':schema')
        except Exception: corrupt.append(name)
    for name,path in [('evidence_db',p.evidence_db),('biography_db',p.biography_db)]:
        try:
            db=sqlite3.connect(f'file:{path.as_posix()}?mode=ro&immutable=1',uri=True);row=db.execute('PRAGMA integrity_check').fetchone();db.close()
            if not row or row[0]!='ok': corrupt.append(name)
        except Exception: corrupt.append(name)
    return DaemonPlaneAudit('CORRUPT' if corrupt else 'CURRENT',schema,(),tuple(corrupt))

def write_current_unlocked(root: Path, state: Mapping[str,Any], *, before_replace: Callable[[Path],None] | None=None) -> dict[str,Any]:
    p=paths(root);old=json.loads(p.current_state.read_text(encoding='utf-8'));new={'schema_version':DAEMON_PLANE_SCHEMA,'daemon_id':old['daemon_id'],'generation':int(old.get('generation',0))+1,'state':dict(state)}
    atomic_json(p.current_state,new,before_replace=before_replace);return new

def write_current(root: Path, state: Mapping[str,Any], *, before_replace: Callable[[Path],None] | None=None) -> dict[str,Any]:
    with plane_lock(paths(root).lock):
        return write_current_unlocked(root,state,before_replace=before_replace)

def checkpoint(root: Path, checkpoint_id: str) -> Path:
    p=paths(root);dest=p.checkpoints/checkpoint_id
    with plane_lock(p.lock):
        if dest.exists(): raise DaemonPlaneError('CHECKPOINT_EXISTS')
        dest.mkdir(parents=True)
        shutil.copy2(p.identity,dest/'daemon_identity.json');shutil.copy2(p.current_state,dest/'current.json')
        for src,name in [(p.evidence_db,'evidence.sqlite'),(p.biography_db,'biography.sqlite')]:
            srcdb=sqlite3.connect(src);dstdb=sqlite3.connect(dest/name);srcdb.backup(dstdb);dstdb.close();srcdb.close()
        manifest={}
        for f in sorted(dest.iterdir()): manifest[f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
        atomic_json(dest/'manifest.json',{'schema_version':DAEMON_PLANE_SCHEMA,'files':manifest})
    return dest

def _recover_unchecked(root: Path, checkpoint_id: str) -> None:
    p=paths(root);src=p.checkpoints/checkpoint_id;mf=src/'manifest.json'
    if not mf.exists(): raise DaemonPlaneCorrupt('CHECKPOINT_MANIFEST_MISSING')
    data=json.loads(mf.read_text(encoding='utf-8'))
    for name,sha in data.get('files',{}).items():
        f=src/name
        if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest()!=sha: raise DaemonPlaneCorrupt('CHECKPOINT_HASH_MISMATCH')
    with plane_lock(p.lock):
        atomic_json(p.identity,json.loads((src/'daemon_identity.json').read_text(encoding='utf-8')));atomic_json(p.current_state,json.loads((src/'current.json').read_text(encoding='utf-8')))
        shutil.copy2(src/'evidence.sqlite',p.evidence_db);shutil.copy2(src/'biography.sqlite',p.biography_db)

def recover(root: Path, checkpoint_id: str) -> None:
    with service_lease(root,blocking=False):
        _recover_unchecked(root,checkpoint_id)

def migrate(root: Path, target_version: int, migration: Callable[[Path],None]) -> None:
    if target_version<=DAEMON_PLANE_SCHEMA: raise DaemonPlaneMigrationError('TARGET_VERSION_NOT_FORWARD')
    with service_lease(root,blocking=False):
        backup=checkpoint(root,f'pre-migrate-v{target_version}')
        try:
            with plane_lock(paths(root).lock): migration(root)
        except Exception as exc:
            _recover_unchecked(root,backup.name);raise DaemonPlaneMigrationError('MIGRATION_FAILED_ROLLED_BACK') from exc
