"""Lab session, reflexion, and andon state persistence boundary."""

from __future__ import annotations
from collections.abc import MutableMapping

import uuid
from pathlib import Path
from typing import Any

from control_plane_models import (
    AndonEventRecord,
    LabSessionRecord,
    ReflexionRecord,
    SessionNoteRecord,
)
from server_hardening import safe_json_dumps, safe_json_loads
from shared_core import ensure_parent, get_project_root, utc_now

JsonObject = MutableMapping[str, Any]


def _lab_root(project_id: str) -> Path:
    root = get_project_root(project_id) / "system" / "lab"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _sessions_root(project_id: str) -> Path:
    root = _lab_root(project_id) / "sessions"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _reflexion_path(project_id: str) -> Path:
    path = _lab_root(project_id) / "reflexion" / "reflexion.jsonl"
    ensure_parent(path)
    return path


def _andon_path(project_id: str) -> Path:
    path = _lab_root(project_id) / "andon" / "events.jsonl"
    ensure_parent(path)
    return path


def _session_path(project_id: str, session_id: str) -> Path:
    return _sessions_root(project_id) / f"{session_id}.json"


def start_session(
    project_id: str, title: str = "", meta: JsonObject | None = None
) -> LabSessionRecord:
    session_id = f"lab-{uuid.uuid4().hex[:12]}"
    now = utc_now()
    record = LabSessionRecord(
        project_id=project_id,
        session_id=session_id,
        title=title,
        status="active",
        created_at=now,
        updated_at=now,
        meta=meta or {},
        notes=[],
        andon_events=[],
    )
    path = _session_path(project_id, session_id)
    path.write_text(safe_json_dumps(record.to_dict()), encoding="utf-8")
    return record


def get_session(project_id: str, session_id: str) -> LabSessionRecord:
    path = _session_path(project_id, session_id)
    if not path.exists():
        raise FileNotFoundError("session not found")
    return LabSessionRecord.from_dict(safe_json_loads(path.read_text(encoding="utf-8")))


def save_session(project_id: str, session_id: str, record: LabSessionRecord) -> LabSessionRecord:
    record.updated_at = utc_now()
    path = _session_path(project_id, session_id)
    path.write_text(safe_json_dumps(record.to_dict()), encoding="utf-8")
    return record


def append_session_note(
    project_id: str, session_id: str, note: str, note_type: str = "note"
) -> LabSessionRecord:
    record = get_session(project_id, session_id)
    record.notes.append(SessionNoteRecord(time=utc_now(), type=note_type, note=note))
    return save_session(project_id, session_id, record)


def end_session(project_id: str, session_id: str, status: str = "closed") -> LabSessionRecord:
    record = get_session(project_id, session_id)
    record.status = status
    return save_session(project_id, session_id, record)


def append_jsonl(path: Path, record: JsonObject) -> None:
    ensure_parent(path)
    with path.open("a", encoding="utf-8") as f:
        f.write(safe_json_dumps(record) + "\n")


def append_reflexion(project_id: str, record: JsonObject) -> ReflexionRecord:
    row = ReflexionRecord(
        time=utc_now(),
        session_id=str(record.get("session_id")) if record.get("session_id") is not None else None,
        title=str(record.get("title", "")),
        content=str(record.get("content", "")),
        tags=(
            [str(x) for x in (record.get("tags") or [])]
            if isinstance(record.get("tags") or [], list)
            else []
        ),
    )
    append_jsonl(_reflexion_path(project_id), row)
    return row


def read_reflexion(project_id: str, limit: int = 50) -> list[ReflexionRecord]:
    path = _reflexion_path(project_id)
    if not path.exists():
        return []
    out: list[ReflexionRecord] = []
    recent_lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
    for line in recent_lines:
        try:
            out.append(ReflexionRecord.from_dict(safe_json_loads(line)))
        except (TypeError, ValueError, KeyError):
            continue
    return out


def pull_andon(project_id: str, record: JsonObject) -> AndonEventRecord:
    row = AndonEventRecord(
        time=utc_now(),
        session_id=str(record.get("session_id")) if record.get("session_id") is not None else None,
        reason=str(record.get("reason", "")),
        details=str(record.get("details", "")),
    )
    append_jsonl(_andon_path(project_id), row)
    session_id = row.session_id
    if session_id:
        try:
            session = get_session(project_id, str(session_id))
            session.andon_events.append(row)
            session.status = "paused"
            save_session(project_id, str(session_id), session)
        except (OSError, ValueError, KeyError, TypeError):
            row.payload["session_update_error"] = "session andon propagation failed"
    return row
