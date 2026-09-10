"""Lab session, reflexion, and andon state persistence boundary."""

from __future__ import annotations
from collections.abc import MutableMapping

import uuid
from pathlib import Path
from typing import Any

from .control_plane_models import (
    AndonEventRecord,
    LabSessionRecord,
    ReflexionRecord,
    SessionNoteRecord,
)
from .server_hardening import safe_json_dumps, safe_json_loads
from .shared_core import append_jsonl, cross_process_file_guard, ensure_parent, get_project_root, save_json_atomic, utc_now

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


def _session_notes_path(project_id: str, session_id: str) -> Path:
    return _sessions_root(project_id) / f"{session_id}.notes.jsonl"


def _session_guard_path(project_id: str, session_id: str) -> Path:
    return _sessions_root(project_id) / f".{session_id}.state.guard"


def _load_session_snapshot(project_id: str, session_id: str) -> LabSessionRecord:
    path = _session_path(project_id, session_id)
    if not path.exists():
        raise FileNotFoundError("session not found")
    return LabSessionRecord.from_dict(safe_json_loads(path.read_text(encoding="utf-8")))


def _read_session_notes(project_id: str, session_id: str) -> list[SessionNoteRecord]:
    path = _session_notes_path(project_id, session_id)
    if not path.exists():
        return []
    notes: list[SessionNoteRecord] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            notes.append(SessionNoteRecord.from_dict(safe_json_loads(line)))
        except (TypeError, ValueError, KeyError) as exc:
            raise ValueError(f"session note journal corrupt at line {line_no}") from exc
    return notes


def _write_session_snapshot(
    project_id: str, session_id: str, record: LabSessionRecord
) -> LabSessionRecord:
    record.updated_at = utc_now()
    save_json_atomic(_session_path(project_id, session_id), record.to_dict())
    return record


def _mutate_session_snapshot(project_id: str, session_id: str, mutate) -> LabSessionRecord:
    with cross_process_file_guard(_session_guard_path(project_id, session_id), timeout_seconds=5.0):
        record = _load_session_snapshot(project_id, session_id)
        mutate(record)
        _write_session_snapshot(project_id, session_id, record)
    return get_session(project_id, session_id)


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
    with cross_process_file_guard(_session_guard_path(project_id, session_id), timeout_seconds=5.0):
        save_json_atomic(_session_path(project_id, session_id), record.to_dict())
    return record


def get_session(project_id: str, session_id: str) -> LabSessionRecord:
    record = _load_session_snapshot(project_id, session_id)
    journal_notes = _read_session_notes(project_id, session_id)
    if journal_notes:
        record.notes.extend(journal_notes)
        latest = journal_notes[-1].time
        if latest and latest > record.updated_at:
            record.updated_at = latest
    return record


def save_session(project_id: str, session_id: str, record: LabSessionRecord) -> LabSessionRecord:
    # Compatibility save: once a note journal exists, preserve only legacy embedded
    # notes in the snapshot so journal notes cannot be duplicated on the next read.
    with cross_process_file_guard(_session_guard_path(project_id, session_id), timeout_seconds=5.0):
        journal_exists = _session_notes_path(project_id, session_id).exists()
        if journal_exists:
            legacy = _load_session_snapshot(project_id, session_id)
            record.notes = list(legacy.notes)
        _write_session_snapshot(project_id, session_id, record)
    return get_session(project_id, session_id)


def append_session_note(
    project_id: str, session_id: str, note: str, note_type: str = "note"
) -> LabSessionRecord:
    # O(1) write path with respect to session history: append one durable journal row.
    row = SessionNoteRecord(time=utc_now(), type=note_type, note=note)
    with cross_process_file_guard(_session_guard_path(project_id, session_id), timeout_seconds=5.0):
        _load_session_snapshot(project_id, session_id)  # existence/current JSON check before append
        append_jsonl(_session_notes_path(project_id, session_id), row)
    return get_session(project_id, session_id)


def end_session(project_id: str, session_id: str, status: str = "closed") -> LabSessionRecord:
    def mutate(record: LabSessionRecord) -> None:
        record.status = status

    return _mutate_session_snapshot(project_id, session_id, mutate)


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
        stop_recorded=True,
        session_pause_projected=False,
        session_update_error=None,
    )
    append_jsonl(_andon_path(project_id), row)
    if not row.session_id:
        return row
    try:
        def pause(session: LabSessionRecord) -> None:
            session.andon_events.append(row)
            session.status = "paused"

        _mutate_session_snapshot(project_id, str(row.session_id), pause)
        return AndonEventRecord(
            time=row.time, session_id=row.session_id, reason=row.reason, details=row.details,
            stop_recorded=True, session_pause_projected=True, session_update_error=None,
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return AndonEventRecord(
            time=row.time, session_id=row.session_id, reason=row.reason, details=row.details,
            stop_recorded=True, session_pause_projected=False,
            session_update_error=f"{type(exc).__name__}: {exc}",
        )
