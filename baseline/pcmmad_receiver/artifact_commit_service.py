from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .control_plane_models import CommitLedgerRecord, ManifestDocument, ManifestEntryRecord
from .shared_core import (
    ALLOWED_OPERATIONS, APPEND_ALLOWED_CLASSES, append_jsonl, commits_ledger_path_for,
    ensure_parent, ensure_safe_mutation_target_identity, get_project_root, idempotency_path_for,
    init_project_layout, load_json, manifest_path_for, resolve_target, save_json_atomic, sha256_file, utc_now,
)

JsonObject = dict[str, Any]


class ArtifactCommitError(RuntimeError):
    def __init__(self, error_code: str, message: str, status: int = 409, **extra: Any):
        super().__init__(message);self.error_code=error_code;self.message=message;self.status=status;self.extra=extra


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode('utf-8')).hexdigest()


def _render(content: str, mode: str) -> bytes:
    if mode == 'utf8_exact':
        return content.encode('utf-8')
    if mode == 'platform_text':
        rendered=content.replace('\n',os.linesep) if os.linesep!='\n' else content
        return rendered.encode('utf-8')
    raise ArtifactCommitError('BAD_REQUEST','unsupported render_mode',400,render_mode=mode)


def _manifest_update(project_id: str, target: Path, artifact_class: str, sha: str, size: int) -> None:
    path=manifest_path_for(project_id);raw=load_json(path,{"updated_at":None,"files":{}});manifest=ManifestDocument.from_dict(raw if isinstance(raw,dict) else {})
    rel=str(target.relative_to(get_project_root(project_id)))
    manifest.files[rel]=ManifestEntryRecord(artifact_class=artifact_class,sha256=sha,bytes=size,updated_at=utc_now());manifest.updated_at=utc_now();save_json_atomic(path,manifest.to_dict())


def _idem(project_id: str) -> dict[str,Any]:
    raw=load_json(idempotency_path_for(project_id),{});return dict(raw) if isinstance(raw,dict) else {}


def _request_digest(payload: Mapping[str,Any]) -> str:
    keys=['project_id','artifact_class','logical_name','operation','content','content_sha256','expected_previous_sha256','session_id','commit_id','idempotency_key','render_mode']
    return _hash({k:payload.get(k) for k in keys})


def _write_bytes(target: Path, operation: str, incoming: bytes) -> None:
    ensure_parent(target)
    if operation == 'append':
        with target.open('ab') as handle: handle.write(incoming)
        return
    fd,tmp=tempfile.mkstemp(prefix=target.name+'.',suffix='.tmp',dir=target.parent)
    try:
        with os.fdopen(fd,'wb') as handle: handle.write(incoming)
        os.replace(tmp,target)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def _find_commit(project_id: str, commit_id: str) -> JsonObject | None:
    ledger=commits_ledger_path_for(project_id)
    if not ledger.is_file(): return None
    for line in ledger.read_text(encoding='utf-8').splitlines():
        try: row=json.loads(line)
        except json.JSONDecodeError: continue
        if row.get('commit_id')==commit_id: return row
    return None


def commit_artifact(payload: Mapping[str,Any]) -> JsonObject:
    project_id=str(payload.get('project_id') or '').strip()
    artifact_class=str(payload.get('artifact_class') or '').strip()
    logical_name=str(payload.get('logical_name') or '').strip()
    operation=str(payload.get('operation') or '').strip()
    content=str(payload.get('content') or '')
    session_id=str(payload.get('session_id') or '').strip()
    commit_id=str(payload.get('commit_id') or '').strip()
    idem_key=str(payload.get('idempotency_key') or '').strip()
    render_mode=str(payload.get('render_mode') or 'utf8_exact')
    if not all([project_id,artifact_class,logical_name,operation,session_id,commit_id,idem_key]):
        raise ArtifactCommitError('BAD_REQUEST','missing required artifact commit identity fields',400)
    if operation not in ALLOWED_OPERATIONS:
        raise ArtifactCommitError('BAD_REQUEST',f'unsupported operation: {operation}',400)
    init_project_layout(project_id)
    target=resolve_target(project_id,artifact_class,logical_name)
    ensure_safe_mutation_target_identity(target)
    incoming=_render(content,render_mode)
    provided=payload.get('content_sha256')
    incoming_sha=hashlib.sha256(incoming).hexdigest()
    if provided and provided != incoming_sha:
        raise ArtifactCommitError('CONTENT_HASH_INVALID','content_sha256 did not match rendered incoming bytes',400,computed_content_sha256=incoming_sha)
    request_digest=_request_digest(payload)
    idem=_idem(project_id)
    existing=idem.get(idem_key)
    prior_commit=_find_commit(project_id,commit_id)
    if isinstance(existing,dict):
        if existing.get('request_digest') != request_digest:
            raise ArtifactCommitError('IDEMPOTENCY_KEY_CONFLICT','idempotency_key belongs to another request',409)
        record=existing.get('record')
        if existing.get('state')=='committed' and isinstance(record,dict):
            if prior_commit is not None and (prior_commit.get('idempotency_key')!=idem_key or prior_commit.get('sha256')!=record.get('sha256')):
                raise ArtifactCommitError('COMMIT_ID_CONFLICT','commit_id belongs to different result',409)
            return {"ok":True,"replayed":True,**record}
        if existing.get('state')!='prepared':
            raise ArtifactCommitError('IDEMPOTENCY_RECOVERY_CONFLICT','unknown idempotency state',409)
        prepared_before=existing.get('before_sha256')
        intended=str(existing.get('intended_final_sha256') or '')
        if len(intended)!=64:
            raise ArtifactCommitError('IDEMPOTENCY_RECOVERY_CONFLICT','prepared idempotency record lacks intended final SHA',409)
        if prior_commit is not None and prior_commit.get('idempotency_key')!=idem_key:
            raise ArtifactCommitError('COMMIT_ID_CONFLICT','commit_id belongs to different result',409)
        current=sha256_file(target) if target.is_file() else None
        if current==intended:
            final_sha=current;size=target.stat().st_size
        elif current==prepared_before:
            _write_bytes(target,operation,incoming);final_sha=sha256_file(target);size=target.stat().st_size
        else:
            raise ArtifactCommitError('IDEMPOTENCY_RECOVERY_CONFLICT','target is neither prepared before-state nor intended final state',409,before_sha256=prepared_before,current_sha256=current,intended_final_sha256=intended)
    else:
        if prior_commit is not None:
            raise ArtifactCommitError('COMMIT_ID_CONFLICT','commit_id already exists without matching idempotency state',409)
        exists=target.is_file();before_sha=sha256_file(target) if exists else None
        if operation=='create' and exists:
            raise ArtifactCommitError('OPERATION_CONFLICT','create target already exists',409)
        if operation in {'update','append'} and not exists:
            raise ArtifactCommitError('OPERATION_CONFLICT',f'{operation} target does not exist',409)
        if operation=='append' and artifact_class not in APPEND_ALLOWED_CLASSES:
            raise ArtifactCommitError('OPERATION_CONFLICT','append not allowed for artifact class',409)
        expected=payload.get('expected_previous_sha256')
        if expected is not None and before_sha != expected:
            raise ArtifactCommitError('HASH_MISMATCH','expected_previous_sha256 did not match existing file',409,expected_previous_sha256=expected,current_sha256=before_sha)
        before_bytes=target.read_bytes() if operation=='append' else b''
        intended=hashlib.sha256(before_bytes+incoming).hexdigest()
        idem[idem_key]={"version":2,"state":"prepared","request_digest":request_digest,"before_sha256":before_sha,"intended_final_sha256":intended,"prepared_at":utc_now()}
        save_json_atomic(idempotency_path_for(project_id),idem)
        _write_bytes(target,operation,incoming)
        final_sha=sha256_file(target);size=target.stat().st_size
    if final_sha != intended:
        raise ArtifactCommitError('FINAL_HASH_MISMATCH','written artifact bytes do not match intended final SHA',409,intended_sha256=intended,final_sha256=final_sha)
    _manifest_update(project_id,target,artifact_class,final_sha,size)
    record=_find_commit(project_id,commit_id)
    if record is not None:
        if record.get('idempotency_key')!=idem_key or record.get('sha256')!=final_sha:
            raise ArtifactCommitError('COMMIT_ID_CONFLICT','commit_id belongs to different result',409)
    else:
        ledger=commits_ledger_path_for(project_id)
        record=CommitLedgerRecord(project_id=project_id,session_id=session_id,commit_id=commit_id,idempotency_key=idem_key,artifact_class=artifact_class,logical_name=logical_name,operation=operation,path=str(target.relative_to(get_project_root(project_id))).replace('\\','/'),sha256=final_sha,bytes=size,time=utc_now()).to_dict()
        append_jsonl(ledger,CommitLedgerRecord.from_dict(record))
    idem=_idem(project_id)
    idem[idem_key]={"version":2,"state":"committed","request_digest":request_digest,"record":record,"committed_at":utc_now()}
    save_json_atomic(idempotency_path_for(project_id),idem)
    return {"ok":True,"replayed":False,**record}
