from __future__ import annotations

import hashlib, json, sqlite3
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from .daemon_plane import audit, paths, DAEMON_PLANE_SCHEMA, DaemonPlaneCorrupt

@dataclass(frozen=True)
class DaemonBootstrapState:
    daemon_id: str
    project_id: str
    schema_version: int
    generation: int
    current_state: dict[str,Any]
    evidence_count: int
    biography_event_count: int
    biography_graph_digest: str
    authority: str
    mutation_authority: bool = False
    def to_dict(self) -> dict[str,Any]: return asdict(self)

def _readonly_db(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f'file:{path.as_posix()}?mode=ro&immutable=1',uri=True)

def _biography_digest(db: sqlite3.Connection) -> tuple[int,str]:
    ids=sorted(str(r[0]) for r in db.execute('select event_id from biography_events').fetchall())
    raw=json.dumps(ids,sort_keys=True,separators=(',',':')).encode('utf-8')
    return len(ids),hashlib.sha256(raw).hexdigest()

def rehydrate(root: Path, *, expected_daemon_id: str | None=None, expected_project_id: str | None=None) -> DaemonBootstrapState:
    a=audit(root)
    if a.status!='CURRENT': raise DaemonPlaneCorrupt(f'DAEMON_PLANE_NOT_CURRENT:{a.status}')
    p=paths(root)
    identity=json.loads(p.identity.read_text(encoding='utf-8'));current=json.loads(p.current_state.read_text(encoding='utf-8'))
    if int(identity.get('schema_version',-1))!=DAEMON_PLANE_SCHEMA or int(current.get('schema_version',-1))!=DAEMON_PLANE_SCHEMA: raise DaemonPlaneCorrupt('DAEMON_SCHEMA_MISMATCH')
    if identity.get('authority')!='COGNITIVE_PLANE_ONLY': raise DaemonPlaneCorrupt('DAEMON_AUTHORITY_IDENTITY_INVALID')
    daemon_id=str(identity.get('daemon_id') or '');project_id=str(identity.get('project_id') or '')
    if not daemon_id or not project_id: raise DaemonPlaneCorrupt('DAEMON_IDENTITY_INCOMPLETE')
    if expected_daemon_id is not None and daemon_id!=expected_daemon_id: raise DaemonPlaneCorrupt('DAEMON_IDENTITY_MISMATCH')
    if expected_project_id is not None and project_id!=expected_project_id: raise DaemonPlaneCorrupt('DAEMON_PROJECT_MISMATCH')
    if str(current.get('daemon_id') or '')!=daemon_id: raise DaemonPlaneCorrupt('CURRENT_STATE_DAEMON_IDENTITY_MISMATCH')
    edb=_readonly_db(p.evidence_db);bdb=_readonly_db(p.biography_db)
    try:
        evidence_count=int(edb.execute('select count(*) from evidence').fetchone()[0]) if edb.execute("select count(*) from sqlite_master where type='table' and name='evidence'").fetchone()[0] else 0
        biography_event_count,biography_graph_digest=_biography_digest(bdb) if bdb.execute("select count(*) from sqlite_master where type='table' and name='biography_events'").fetchone()[0] else (0,hashlib.sha256(b'[]').hexdigest())
    finally:
        edb.close();bdb.close()
    return DaemonBootstrapState(daemon_id,project_id,DAEMON_PLANE_SCHEMA,int(current.get('generation',0)),dict(current.get('state') or {}),evidence_count,biography_event_count,biography_graph_digest,'COGNITIVE_PLANE_ONLY',False)
