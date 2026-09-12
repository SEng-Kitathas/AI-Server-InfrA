from __future__ import annotations

from pathlib import Path
import json
from typing import Any

from . import ucm_v1_runtime as ucm
from . import user_continuity_store as backend

JsonObject = dict[str, Any]


def audit_ucm(profile_id: str) -> JsonObject:
    paths = backend._paths(profile_id)
    ledger_exists = paths.ledger.is_file()
    try:
        authoritative = backend.ledger_head(profile_id)
    except backend.UserContinuityLedgerError as exc:
        return {
            "schema": "pcmmad.derived-state-audit.v1",
            "kind": "ucm",
            "profile_id": profile_id,
            "authoritative": {"ledger_exists": ledger_exists, "error_code": exc.error_code, "message": exc.message},
            "derived": {"current_exists": paths.current.is_file(), "snapshot_files": sorted(item.name for item in paths.snapshots.glob("*.json")) if paths.snapshots.is_dir() else []},
            "status": "AUTHORITATIVE_CORRUPT",
            "repair": None,
        }
    seq = int(authoritative.get("event_seq") or 0)
    head_hash = authoritative.get("event_hash")
    snapshot_files = sorted(item.name for item in paths.snapshots.glob("*.json")) if paths.snapshots.is_dir() else []
    current_exists = paths.current.is_file()
    current = None
    derived_error = None
    if current_exists:
        try:
            current = backend._load_current_manifest(profile_id)
        except backend.UserContinuityLedgerError as exc:
            derived_error = {"error_code": exc.error_code, "message": exc.message}
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            derived_error = {"error_code": "MEMORY_SNAPSHOT_CORRUPT", "message": str(exc)}
    snap = int((current or {}).get("snapshot_from_seq") or 0)
    snapshot_current = bool(
        current is not None
        and int(current.get("snapshot_from_seq") or -1) == seq
        and int(current.get("ledger_head_seq") or -1) == seq
        and current.get("ledger_head_hash") == head_hash
    )
    if derived_error is not None:
        status = "CORRUPT_DERIVED"
    elif seq == 0 and (current_exists or snapshot_files):
        status = "ORPHAN_DERIVED"
    elif seq == 0:
        status = "EMPTY"
        snapshot_current = True
    elif snapshot_current:
        status = "CURRENT"
    else:
        status = "STALE_DERIVED"
    return {
        "schema": "pcmmad.derived-state-audit.v1",
        "kind": "ucm",
        "profile_id": profile_id,
        "authoritative": {"ledger_exists": ledger_exists, "head_seq": seq, "head_hash": head_hash},
        "derived": {"current_exists": current_exists, "snapshot_from_seq": snap, "snapshot_current": snapshot_current, "snapshot_files": snapshot_files, "error": derived_error},
        "status": status,
        "repair": None if status in {"CURRENT", "EMPTY", "AUTHORITATIVE_CORRUPT"} else "derived_state.rebuild",
    }


def rebuild_ucm(profile_id: str, expected_head_seq: int, expected_head_hash: str | None) -> JsonObject:
    before = audit_ucm(profile_id)
    actual_seq = int(before["authoritative"]["head_seq"])
    actual_hash = before["authoritative"]["head_hash"]
    if actual_seq != int(expected_head_seq) or actual_hash != expected_head_hash:
        raise ucm.UcmError(
            "UCM_HEAD_MISMATCH",
            "derived-state rebuild CAS does not match authoritative UCM head",
            409,
            expected_head_seq=expected_head_seq,
            expected_head_hash=expected_head_hash,
            actual_head_seq=actual_seq,
            actual_head_hash=actual_hash,
        )
    paths = backend._paths(profile_id)
    if actual_seq == 0:
        if paths.ledger.is_file():
            raise ucm.UcmError("UCM_DERIVED_REBUILD_UNSAFE", "head is zero but authoritative ledger exists", 409)
        paths.current.unlink(missing_ok=True)
        if paths.snapshots.is_dir():
            for item in paths.snapshots.glob("*.json"):
                item.unlink(missing_ok=True)
        with backend._CACHE_GUARD:
            backend._STATE_CACHE.pop(profile_id, None)
        action = "ORPHAN_DERIVED_CLEARED"
        result = {"ok": True, "profile_id": profile_id, "ledger_head_seq": 0, "ledger_head_hash": None}
    else:
        result = ucm.materialize({"profile_id": profile_id, "expected_head_seq": actual_seq, "expected_head_hash": actual_hash})
        action = "MATERIALIZED_FROM_LEDGER"
    after = audit_ucm(profile_id)
    return {"ok": True, "kind": "ucm", "profile_id": profile_id, "action": action, "before": before, "result": result, "after": after}
