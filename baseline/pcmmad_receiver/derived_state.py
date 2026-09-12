from __future__ import annotations

from pathlib import Path
from typing import Any

from . import ucm_v1_runtime as ucm
from . import user_continuity_store as backend

JsonObject = dict[str, Any]


def audit_ucm(profile_id: str) -> JsonObject:
    head = ucm.head(profile_id)
    paths = backend._paths(profile_id)
    snapshot_files = sorted(item.name for item in paths.snapshots.glob("*.json")) if paths.snapshots.is_dir() else []
    ledger_exists = paths.ledger.is_file()
    current_exists = paths.current.is_file()
    seq = int(head.get("ledger_head_seq") or 0)
    snap = int(head.get("snapshot_from_seq") or 0)
    if seq == 0 and (current_exists or snapshot_files):
        status = "ORPHAN_DERIVED"
    elif seq == 0:
        status = "EMPTY"
    elif bool(head.get("snapshot_current")) and snap == seq:
        status = "CURRENT"
    else:
        status = "STALE_DERIVED"
    return {
        "schema": "pcmmad.derived-state-audit.v1",
        "kind": "ucm",
        "profile_id": profile_id,
        "authoritative": {"ledger_exists": ledger_exists, "head_seq": seq, "head_hash": head.get("ledger_head_hash")},
        "derived": {"current_exists": current_exists, "snapshot_from_seq": snap, "snapshot_current": bool(head.get("snapshot_current")), "snapshot_files": snapshot_files},
        "status": status,
        "repair": None if status in {"CURRENT", "EMPTY"} else "derived_state.rebuild",
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
