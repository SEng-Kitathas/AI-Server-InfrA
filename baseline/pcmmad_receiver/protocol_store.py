"""Append-only PCMMAD runtime-protocol ledger and derived state projection.

The event ledger is authoritative.  ``state.json`` is a rebuildable projection.
All mutation occurs by appending a typed event whose hash commits to the prior
head, making silent history edits detectable without pretending the filesystem
is magically immutable.
"""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from .protocol_models import (
    AdjudicationDecision,
    ClaimKind,
    ConstraintStrength,
    ContinuityKind,
    EvidenceRef,
    EvidenceStatus,
    MutationDomain,
    ProtocolEvent,
    ProtocolEventKind,
    ProtocolSnapshot,
    ProtocolValidationError,
    RigorLevel,
    RuntimeMode,
    WaiverStatus,
)
from .shared_core import (
    get_project_root,
    init_project_layout,
    render_jsonl_boundary,
    save_json_atomic,
    sha256_file,
    sha256_text,
    utc_now,
    validate_project_id,
)

_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")
_LOCKS_GUARD = threading.RLock()
_PROJECT_LOCKS: dict[str, threading.RLock] = {}
_SNAPSHOT_CACHE_GUARD = threading.RLock()
PROTOCOL_SNAPSHOT_CHECKPOINT_INTERVAL = 128


@dataclass
class _SnapshotCacheEntry:
    snapshot: ProtocolSnapshot
    ledger_fingerprint: tuple[int, int, int]


_SNAPSHOT_CACHE: dict[str, _SnapshotCacheEntry] = {}

PROTOCOL_METHOD_VERSION = "2.0"
PROTOCOL_BUILD_METABOLISM = (
    "FIX_INTENDED_OUTCOME -> INSPECT_REALITY_ANCESTRY_CONSTRAINTS -> "
    "COMPOSE_BEFORE_INVENTION -> PROBE -> DERIVE -> VERIFY -> "
    "BUILD_SMALLEST_JUSTIFIED_CHANGE -> ATTACK -> ISOLATE_FAILURE -> "
    "STRIP_MUTATE -> EMBODY -> RECURSE -> CSC_SEMANTIC_GATE_RELEASE_QUALIFICATION"
)
PROTOCOL_PRIMARY_AXIOM = "INTENT IS A CONSTRAINT, NOT A CEILING."


class ProtocolConflictError(RuntimeError):
    """Optimistic state expectation did not match current protocol state."""


class ProtocolLedgerError(RuntimeError):
    """The append-only ledger is malformed or its hash chain is invalid."""


@dataclass(frozen=True)
class ProtocolPaths:
    root: Path
    events: Path
    snapshot: Path


def _lock_for(project_id: str) -> threading.RLock:
    with _LOCKS_GUARD:
        return _PROJECT_LOCKS.setdefault(project_id, threading.RLock())


def _paths(project_id: str) -> ProtocolPaths:
    validate_project_id(project_id)
    root = get_project_root(project_id) / "system" / "protocol"
    return ProtocolPaths(root=root, events=root / "events.jsonl", snapshot=root / "state.json")


def _safe_id(value: object, field_name: str) -> str:
    text = str(value or "").strip()
    if not _SAFE_ID.fullmatch(text):
        raise ProtocolValidationError(
            f"{field_name} must match {_SAFE_ID.pattern}"
        )
    return text


def _required_text(value: object, field_name: str, *, max_length: int = 20000) -> str:
    text = str(value or "").strip()
    if not text:
        raise ProtocolValidationError(f"{field_name} is required")
    if len(text) > max_length:
        raise ProtocolValidationError(f"{field_name} exceeds {max_length} characters")
    return text


def _optional_text(value: object, *, max_length: int = 20000) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) > max_length:
        raise ProtocolValidationError(f"text exceeds {max_length} characters")
    return text


def _enum(enum_type: type[Any], value: object, field_name: str) -> Any:
    try:
        return enum_type(str(value).strip().upper())
    except ValueError as exc:
        allowed = ", ".join(item.value for item in enum_type)
        raise ProtocolValidationError(f"{field_name} must be one of: {allowed}") from exc


def _canonical_event_hash(event_without_hash: dict[str, Any]) -> str:
    return sha256_text(render_jsonl_boundary(event_without_hash))


def _event_body(
    *,
    sequence: int,
    event_id: str,
    event_kind: ProtocolEventKind,
    project_id: str,
    recorded_at: str,
    actor: str,
    payload: dict[str, Any],
    previous_hash: str | None,
) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "event_id": event_id,
        "event_kind": event_kind.value,
        "project_id": project_id,
        "recorded_at": recorded_at,
        "actor": actor,
        "payload": payload,
        "previous_hash": previous_hash,
    }


def _parse_event(raw: object, *, line_number: int) -> ProtocolEvent:
    if not isinstance(raw, dict):
        raise ProtocolLedgerError(f"ledger line {line_number} is not an object")
    try:
        return ProtocolEvent(
            sequence=int(raw["sequence"]),
            event_id=str(raw["event_id"]),
            event_kind=ProtocolEventKind(str(raw["event_kind"])),
            project_id=str(raw["project_id"]),
            recorded_at=str(raw["recorded_at"]),
            actor=str(raw["actor"]),
            payload=dict(raw["payload"]),
            previous_hash=(str(raw["previous_hash"]) if raw.get("previous_hash") else None),
            event_hash=str(raw["event_hash"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ProtocolLedgerError(f"ledger line {line_number} is malformed: {exc}") from exc


def _snapshot_cache_key(project_id: str) -> str:
    return str(_paths(project_id).events.resolve())


def _ledger_fingerprint(path: Path) -> tuple[int, int, int]:
    stat = path.stat()
    return (int(stat.st_size), int(stat.st_mtime_ns), int(stat.st_ctime_ns))


def _invalidate_snapshot_cache(project_id: str) -> None:
    key = _snapshot_cache_key(project_id)
    with _SNAPSHOT_CACHE_GUARD:
        _SNAPSHOT_CACHE.pop(key, None)


def _cache_snapshot(project_id: str, snapshot: ProtocolSnapshot) -> ProtocolSnapshot:
    paths = _paths(project_id)
    if not paths.events.is_file():
        return snapshot
    entry = _SnapshotCacheEntry(
        snapshot=snapshot, ledger_fingerprint=_ledger_fingerprint(paths.events)
    )
    with _SNAPSHOT_CACHE_GUARD:
        _SNAPSHOT_CACHE[_snapshot_cache_key(project_id)] = entry
    return snapshot


def _cached_snapshot_if_current(project_id: str) -> ProtocolSnapshot | None:
    paths = _paths(project_id)
    if not paths.events.is_file():
        _invalidate_snapshot_cache(project_id)
        return None
    key = _snapshot_cache_key(project_id)
    with _SNAPSHOT_CACHE_GUARD:
        entry = _SNAPSHOT_CACHE.get(key)
    if entry is None:
        return None
    try:
        current = _ledger_fingerprint(paths.events)
    except OSError:
        _invalidate_snapshot_cache(project_id)
        return None
    if current != entry.ledger_fingerprint:
        _invalidate_snapshot_cache(project_id)
        return None
    return entry.snapshot


def _load_verified_snapshot_locked(project_id: str) -> ProtocolSnapshot:
    """Use a current verified fold or rebuild the authoritative ledger once.

    The healthy mutation path extends the in-memory fold.  A cache miss, restart,
    or external ledger fingerprint change falls back to the existing full hash-chain
    verification and fold before another append is allowed.
    """
    cached = _cached_snapshot_if_current(project_id)
    if cached is not None:
        return cached
    paths = _paths(project_id)
    if not paths.events.is_file():
        return ProtocolSnapshot(project_id=project_id)
    snapshot = build_snapshot(project_id)
    _write_snapshot(project_id, snapshot)
    return _cache_snapshot(project_id, snapshot)


def _checkpoint_due(sequence: int) -> bool:
    return sequence == 1 or sequence % PROTOCOL_SNAPSHOT_CHECKPOINT_INTERVAL == 0


def read_events(project_id: str) -> list[ProtocolEvent]:
    path = _paths(project_id).events
    if not path.exists():
        return []
    events: list[ProtocolEvent] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ProtocolLedgerError(
                    f"ledger line {line_number} is not valid JSON: {exc}"
                ) from exc
            events.append(_parse_event(raw, line_number=line_number))
    return events


def verify_events(project_id: str, events: Iterable[ProtocolEvent] | None = None) -> dict[str, Any]:
    materialized = list(read_events(project_id) if events is None else events)
    expected_previous: str | None = None
    failures: list[dict[str, Any]] = []
    for index, event in enumerate(materialized, start=1):
        if event.sequence != index:
            failures.append(
                {"sequence": index, "error": "sequence_mismatch", "actual": event.sequence}
            )
        if event.project_id != project_id:
            failures.append(
                {"sequence": index, "error": "project_id_mismatch", "actual": event.project_id}
            )
        if event.previous_hash != expected_previous:
            failures.append(
                {
                    "sequence": index,
                    "error": "previous_hash_mismatch",
                    "expected": expected_previous,
                    "actual": event.previous_hash,
                }
            )
        body = _event_body(
            sequence=event.sequence,
            event_id=event.event_id,
            event_kind=event.event_kind,
            project_id=event.project_id,
            recorded_at=event.recorded_at,
            actor=event.actor,
            payload=event.payload,
            previous_hash=event.previous_hash,
        )
        computed = _canonical_event_hash(body)
        if event.event_hash != computed:
            failures.append(
                {
                    "sequence": index,
                    "error": "event_hash_mismatch",
                    "expected": computed,
                    "actual": event.event_hash,
                }
            )
        expected_previous = event.event_hash
    return {
        "ok": not failures,
        "project_id": project_id,
        "event_count": len(materialized),
        "head_hash": materialized[-1].event_hash if materialized else None,
        "failures": failures,
    }


def _apply_event(snapshot: ProtocolSnapshot, event: ProtocolEvent) -> None:
    payload = dict(event.payload)
    if event.event_kind is ProtocolEventKind.GENESIS:
        snapshot.rigor_level = RigorLevel(str(payload["rigor_level"]))
        snapshot.current_mode = RuntimeMode(str(payload["initial_mode"]))
    elif event.event_kind is ProtocolEventKind.MODE_TRANSITION:
        snapshot.current_mode = RuntimeMode(str(payload["to_mode"]))
    elif event.event_kind is ProtocolEventKind.OBJECTIVE_SET:
        snapshot.objective = payload
    elif event.event_kind is ProtocolEventKind.CONSTRAINT_RECORDED:
        snapshot.constraints[str(payload["constraint_id"])] = payload
    elif event.event_kind is ProtocolEventKind.CONTINUITY_RECORDED:
        snapshot.continuity.append(payload)
    elif event.event_kind is ProtocolEventKind.CLAIM_RECORDED:
        snapshot.claims[str(payload["claim_id"])] = payload
    elif event.event_kind is ProtocolEventKind.ARTIFACT_REGISTERED:
        snapshot.artifacts[str(payload["artifact_id"])] = payload
    elif event.event_kind is ProtocolEventKind.PROMOTION_RECORDED:
        key = f"{payload['target_type']}:{payload['target_id']}"
        snapshot.promotions[key] = payload
    elif event.event_kind is ProtocolEventKind.WAIVER_RECORDED:
        snapshot.waivers[str(payload["waiver_id"])] = payload
    snapshot.event_count = event.sequence
    snapshot.head_hash = event.event_hash
    snapshot.updated_at = event.recorded_at


def build_snapshot(project_id: str, events: Iterable[ProtocolEvent] | None = None) -> ProtocolSnapshot:
    materialized = list(read_events(project_id) if events is None else events)
    verification = verify_events(project_id, materialized)
    if not verification["ok"]:
        raise ProtocolLedgerError(
            f"protocol ledger failed verification: {verification['failures']}"
        )
    snapshot = ProtocolSnapshot(project_id=project_id)
    for event in materialized:
        _apply_event(snapshot, event)
    return snapshot


def _write_snapshot(project_id: str, snapshot: ProtocolSnapshot) -> None:
    save_json_atomic(_paths(project_id).snapshot, snapshot.to_dict())


def _append_event_locked(
    project_id: str,
    event_kind: ProtocolEventKind,
    payload: dict[str, Any],
    *,
    actor: str,
    snapshot: ProtocolSnapshot | None = None,
) -> ProtocolEvent:
    paths = _paths(project_id)
    paths.root.mkdir(parents=True, exist_ok=True)

    if snapshot is None:
        snapshot = _load_verified_snapshot_locked(project_id)
    elif paths.events.is_file():
        cached = _cached_snapshot_if_current(project_id)
        if cached is not snapshot:
            snapshot = _load_verified_snapshot_locked(project_id)

    sequence = int(snapshot.event_count) + 1
    previous_hash = snapshot.head_hash
    body = _event_body(
        sequence=sequence,
        event_id=str(uuid.uuid4()),
        event_kind=event_kind,
        project_id=project_id,
        recorded_at=utc_now(),
        actor=_required_text(actor, "actor", max_length=256),
        payload=payload,
        previous_hash=previous_hash,
    )
    event = ProtocolEvent(
        sequence=sequence,
        event_id=str(body["event_id"]),
        event_kind=event_kind,
        project_id=project_id,
        recorded_at=str(body["recorded_at"]),
        actor=str(body["actor"]),
        payload=dict(payload),
        previous_hash=previous_hash,
        event_hash=_canonical_event_hash(body),
    )

    # Authoritative durability boundary is unchanged: append then flush+fsync.
    with paths.events.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(render_jsonl_boundary(event.to_dict()) + "\n")
        handle.flush()
        os.fsync(handle.fileno())

    try:
        # Healthy steady state is one fold step, not a history rebuild.
        _apply_event(snapshot, event)
        _cache_snapshot(project_id, snapshot)
        # state.json is rebuildable derived state. Publish periodic checkpoints
        # rather than rewriting a history-sized projection on every WAL append.
        if _checkpoint_due(event.sequence):
            _write_snapshot(project_id, snapshot)
    except Exception:
        # The ledger append may already be durable.  Never leave cache claiming
        # currentness after a projection/checkpoint failure; recovery must rebuild.
        _invalidate_snapshot_cache(project_id)
        raise
    return event


def ensure_protocol(
    project_id: str,
    *,
    actor: str = "system",
    rigor_level: str | RigorLevel = RigorLevel.STANDARD,
    initial_mode: str | RuntimeMode = RuntimeMode.DISCUSSION,
) -> ProtocolSnapshot:
    project_id = validate_project_id(project_id)
    init_project_layout(project_id)
    rigor = rigor_level if isinstance(rigor_level, RigorLevel) else _enum(
        RigorLevel, rigor_level, "rigor_level"
    )
    mode = initial_mode if isinstance(initial_mode, RuntimeMode) else _enum(
        RuntimeMode, initial_mode, "initial_mode"
    )
    with _lock_for(project_id):
        snapshot = _load_verified_snapshot_locked(project_id)
        if snapshot.event_count == 0:
            _append_event_locked(
                project_id,
                ProtocolEventKind.GENESIS,
                {
                    "protocol_version": "1.1",
                    "method_version": PROTOCOL_METHOD_VERSION,
                    "rigor_level": rigor.value,
                    "initial_mode": mode.value,
                    "method": PROTOCOL_BUILD_METABOLISM,
                    "primary_axiom": PROTOCOL_PRIMARY_AXIOM,
                },
                actor=actor,
                snapshot=snapshot,
            )
        return snapshot


def protocol_is_initialized(project_id: str) -> bool:
    project_id = validate_project_id(project_id)
    return _paths(project_id).events.is_file()


def protocol_status(
    project_id: str, *, initialize: bool = False, actor: str = "system"
) -> dict[str, Any]:
    project_id = validate_project_id(project_id)
    initialized = protocol_is_initialized(project_id)
    if not initialized:
        if initialize:
            snapshot = ensure_protocol(project_id, actor=actor)
            initialized = True
        else:
            return {
                "ok": True,
                "initialized": False,
                "ledger": {
                    "ok": True,
                    "project_id": project_id,
                    "present": False,
                    "event_count": 0,
                    "head_hash": None,
                    "failures": [],
                },
                "state": None,
                "active_waiver_ids": [],
                "expired_waiver_ids": [],
            }
    if initialize and 'snapshot' in locals():
        pass
    else:
        snapshot = build_snapshot(project_id)
    verification = verify_events(project_id)
    now = datetime.now(timezone.utc)
    active_waivers: list[str] = []
    expired_waivers: list[str] = []
    for waiver_id, waiver in snapshot.waivers.items():
        if waiver.get("status") != WaiverStatus.ACTIVE.value:
            continue
        expires_at = waiver.get("expires_at")
        if expires_at:
            try:
                expiry = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            except ValueError:
                expired_waivers.append(waiver_id)
                continue
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry.astimezone(timezone.utc) <= now:
                expired_waivers.append(waiver_id)
                continue
        active_waivers.append(waiver_id)
    return {
        "ok": verification["ok"],
        "initialized": True,
        "ledger": {**verification, "present": True},
        "state": snapshot.to_dict(),
        "active_waiver_ids": active_waivers,
        "expired_waiver_ids": expired_waivers,
    }


def evaluate_mode_gate(
    project_id: str,
    mutation_domain: str | MutationDomain,
    *,
    actor: str = "system",
) -> dict[str, Any]:
    """Evaluate the discourse/build boundary without mutating protocol state."""

    project_id = validate_project_id(project_id)
    domain = (
        mutation_domain
        if isinstance(mutation_domain, MutationDomain)
        else _enum(MutationDomain, mutation_domain, "mutation_domain")
    )
    allowed_modes = {
        MutationDomain.READ: set(RuntimeMode),
        MutationDomain.GOVERNANCE: set(RuntimeMode),
        MutationDomain.SPECIMEN: {
            RuntimeMode.BUILD_COMMIT,
            RuntimeMode.RECOVERY,
            RuntimeMode.MERGE,
        },
        MutationDomain.PROMOTION: {RuntimeMode.PROMOTION},
    }[domain]
    if not protocol_is_initialized(project_id):
        return {
            "ok": True,
            "allowed": True,
            "initialized": False,
            "project_id": project_id,
            "mutation_domain": domain.value,
            "current_mode": None,
            "allowed_modes": sorted(mode.value for mode in allowed_modes),
            "reason": "project has no initialized protocol ledger; mode gate is not active",
            "ledger_head_hash": None,
        }
    snapshot = build_snapshot(project_id)
    allowed = snapshot.current_mode in allowed_modes
    return {
        "ok": True,
        "allowed": allowed,
        "initialized": True,
        "project_id": project_id,
        "mutation_domain": domain.value,
        "current_mode": snapshot.current_mode.value,
        "allowed_modes": sorted(mode.value for mode in allowed_modes),
        "reason": (
            "current mode permits this domain"
            if allowed
            else "explicit mode transition is required before this domain may mutate"
        ),
        "ledger_head_hash": snapshot.head_hash,
    }


def transition_mode(
    project_id: str,
    *,
    to_mode: str | RuntimeMode,
    reason: str,
    actor: str,
    expected_mode: str | RuntimeMode | None = None,
) -> ProtocolEvent:
    target = to_mode if isinstance(to_mode, RuntimeMode) else _enum(RuntimeMode, to_mode, "to_mode")
    with _lock_for(project_id):
        snapshot = ensure_protocol(project_id, actor=actor)
        if expected_mode is not None:
            expected = (
                expected_mode
                if isinstance(expected_mode, RuntimeMode)
                else _enum(RuntimeMode, expected_mode, "expected_mode")
            )
            if snapshot.current_mode is not expected:
                raise ProtocolConflictError(
                    f"expected mode {expected.value}, current mode is {snapshot.current_mode.value}"
                )
        if snapshot.current_mode is target:
            raise ProtocolConflictError(f"protocol is already in {target.value} mode")
        return _append_event_locked(
            project_id,
            ProtocolEventKind.MODE_TRANSITION,
            {
                "from_mode": snapshot.current_mode.value,
                "to_mode": target.value,
                "reason": _required_text(reason, "reason"),
            },
            actor=actor,
            snapshot=snapshot,
        )


def set_objective(
    project_id: str,
    *,
    objective_id: str,
    statement: str,
    actor: str,
    success_criteria: list[str] | None = None,
    scope: str | None = None,
) -> ProtocolEvent:
    with _lock_for(project_id):
        snapshot = ensure_protocol(project_id, actor=actor)
        prior = snapshot.objective
        return _append_event_locked(
            project_id,
            ProtocolEventKind.OBJECTIVE_SET,
            {
                "objective_id": _safe_id(objective_id, "objective_id"),
                "statement": _required_text(statement, "statement"),
                "success_criteria": [
                    _required_text(item, "success_criterion", max_length=2000)
                    for item in (success_criteria or [])
                ],
                "scope": _optional_text(scope, max_length=4000),
                "supersedes_objective_id": prior.get("objective_id") if prior else None,
            },
            actor=actor,
            snapshot=snapshot,
        )


def record_constraint(
    project_id: str,
    *,
    constraint_id: str,
    statement: str,
    strength: str | ConstraintStrength,
    actor: str,
    source: str | None = None,
    active: bool = True,
) -> ProtocolEvent:
    strength_value = (
        strength
        if isinstance(strength, ConstraintStrength)
        else _enum(ConstraintStrength, strength, "strength")
    )
    cid = _safe_id(constraint_id, "constraint_id")
    with _lock_for(project_id):
        snapshot = ensure_protocol(project_id, actor=actor)
        prior = snapshot.constraints.get(cid)
        return _append_event_locked(
            project_id,
            ProtocolEventKind.CONSTRAINT_RECORDED,
            {
                "constraint_id": cid,
                "statement": _required_text(statement, "statement"),
                "strength": strength_value.value,
                "source": _optional_text(source, max_length=4000),
                "active": bool(active),
                "revision": int(prior.get("revision", 0)) + 1 if prior else 1,
            },
            actor=actor,
            snapshot=snapshot,
        )


def record_continuity(
    project_id: str,
    *,
    continuity_id: str,
    kind: str | ContinuityKind,
    summary: str,
    actor: str,
    artifact_ref: str | None = None,
    open_loops: list[str] | None = None,
) -> ProtocolEvent:
    kind_value = kind if isinstance(kind, ContinuityKind) else _enum(
        ContinuityKind, kind, "kind"
    )
    return _append_protocol_event(
        project_id,
        ProtocolEventKind.CONTINUITY_RECORDED,
        {
            "continuity_id": _safe_id(continuity_id, "continuity_id"),
            "kind": kind_value.value,
            "summary": _required_text(summary, "summary"),
            "artifact_ref": _optional_text(artifact_ref, max_length=4000),
            "open_loops": [
                _required_text(item, "open_loop", max_length=4000)
                for item in (open_loops or [])
            ],
        },
        actor=actor,
    )


def record_claim(
    project_id: str,
    *,
    claim_id: str,
    kind: str | ClaimKind,
    statement: str,
    actor: str,
    evidence: Iterable[object] = (),
    confidence: float | None = None,
) -> ProtocolEvent:
    kind_value = kind if isinstance(kind, ClaimKind) else _enum(ClaimKind, kind, "kind")
    cid = _safe_id(claim_id, "claim_id")
    if confidence is not None:
        confidence = float(confidence)
        if not 0.0 <= confidence <= 1.0:
            raise ProtocolValidationError("confidence must be between 0.0 and 1.0")
    evidence_refs = [EvidenceRef.from_dict(item).to_dict() for item in evidence]
    with _lock_for(project_id):
        snapshot = ensure_protocol(project_id, actor=actor)
        prior = snapshot.claims.get(cid)
        return _append_event_locked(
            project_id,
            ProtocolEventKind.CLAIM_RECORDED,
            {
                "claim_id": cid,
                "kind": kind_value.value,
                "statement": _required_text(statement, "statement"),
                "confidence": confidence,
                "evidence": evidence_refs,
                "revision": int(prior.get("revision", 0)) + 1 if prior else 1,
            },
            actor=actor,
            snapshot=snapshot,
        )


def _safe_project_relative_path(project_id: str, raw_path: object) -> tuple[str, Path]:
    text = _required_text(raw_path, "path", max_length=4000).replace("\\", "/")
    pure = PurePosixPath(text)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise ProtocolValidationError("path must be a project-relative non-traversing path")
    project_root = get_project_root(project_id).resolve()
    resolved = (project_root / Path(*pure.parts)).resolve()
    if project_root not in [resolved, *resolved.parents]:
        raise ProtocolValidationError("path escaped the project root")
    return pure.as_posix(), resolved


def register_artifact(
    project_id: str,
    *,
    artifact_id: str,
    artifact_class: str,
    actor: str,
    path: str | None = None,
    sha256: str | None = None,
    sealed: bool = False,
    provenance: list[str] | None = None,
) -> ProtocolEvent:
    aid = _safe_id(artifact_id, "artifact_id")
    artifact_class = _required_text(artifact_class, "artifact_class", max_length=256)
    normalized_path: str | None = None
    resolved_path: Path | None = None
    if path is not None:
        normalized_path, resolved_path = _safe_project_relative_path(project_id, path)
    digest = str(sha256).strip().lower() if sha256 else None
    if digest is None and resolved_path is not None and resolved_path.is_file():
        digest = sha256_file(resolved_path)
    if digest is not None and (
        len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest)
    ):
        raise ProtocolValidationError("sha256 must be a 64-character hex digest")
    if sealed and digest is None:
        raise ProtocolValidationError("sealed artifacts require a sha256 digest")
    with _lock_for(project_id):
        snapshot = ensure_protocol(project_id, actor=actor)
        prior = snapshot.artifacts.get(aid)
        if prior and prior.get("sealed") and prior.get("sha256") != digest:
            raise ProtocolConflictError(
                "sealed artifact identity cannot be rewritten; register a new artifact and supersede it"
            )
        return _append_event_locked(
            project_id,
            ProtocolEventKind.ARTIFACT_REGISTERED,
            {
                "artifact_id": aid,
                "artifact_class": artifact_class,
                "path": normalized_path,
                "sha256": digest,
                "sealed": bool(sealed),
                "provenance": [
                    _required_text(item, "provenance_ref", max_length=4000)
                    for item in (provenance or [])
                ],
                "revision": int(prior.get("revision", 0)) + 1 if prior else 1,
            },
            actor=actor,
            snapshot=snapshot,
        )


def record_promotion(
    project_id: str,
    *,
    target_type: str,
    target_id: str,
    decision: str | AdjudicationDecision,
    rationale: str,
    actor: str,
    evidence: Iterable[object] = (),
    waiver_ids: list[str] | None = None,
) -> ProtocolEvent:
    target_type = str(target_type).strip().lower()
    if target_type not in {"claim", "artifact"}:
        raise ProtocolValidationError("target_type must be claim or artifact")
    target_id = _safe_id(target_id, "target_id")
    decision_value = (
        decision
        if isinstance(decision, AdjudicationDecision)
        else _enum(AdjudicationDecision, decision, "decision")
    )
    evidence_records = [EvidenceRef.from_dict(item) for item in evidence]
    identities = [item.identity for item in evidence_records]
    if len(identities) != len(set(identities)):
        raise ProtocolValidationError("promotion evidence refs must be distinct")
    now = datetime.now(timezone.utc)
    expired = [item.ref for item in evidence_records if item.is_expired(now=now)]
    failed = [item.ref for item in evidence_records if item.status is EvidenceStatus.FAILED]
    if expired:
        raise ProtocolValidationError(f"expired promotion evidence refs: {expired}")
    if failed:
        raise ProtocolValidationError(f"failed promotion evidence refs: {failed}")
    evidence_refs = [item.to_dict() for item in evidence_records]
    with _lock_for(project_id):
        snapshot = ensure_protocol(project_id, actor=actor)
        if snapshot.current_mode is not RuntimeMode.PROMOTION:
            raise ProtocolConflictError(
                "promotion records require PROMOTION mode; transition explicitly first"
            )
        target_map = snapshot.claims if target_type == "claim" else snapshot.artifacts
        if target_id not in target_map:
            raise ProtocolValidationError(f"unknown {target_type}: {target_id}")
        if decision_value is AdjudicationDecision.RATIFIED:
            minimum = snapshot.rigor_level.minimum_ratification_evidence
            minimum_verified = snapshot.rigor_level.minimum_verified_evidence
            verified_count = sum(
                item.status is EvidenceStatus.VERIFIED for item in evidence_records
            )
            if len(evidence_refs) < minimum:
                raise ProtocolValidationError(
                    f"{snapshot.rigor_level.value} rigor requires at least {minimum} evidence refs"
                )
            if verified_count < minimum_verified:
                raise ProtocolValidationError(
                    f"{snapshot.rigor_level.value} rigor requires at least "
                    f"{minimum_verified} VERIFIED evidence refs"
                )
            if target_type == "claim" and target_map[target_id].get("kind") == ClaimKind.UNKNOWN.value:
                raise ProtocolValidationError("UNKNOWN claims cannot be ratified")
        supplied_waivers = [_safe_id(item, "waiver_id") for item in (waiver_ids or [])]
        missing_waivers = sorted(set(supplied_waivers) - set(snapshot.waivers))
        if missing_waivers:
            raise ProtocolValidationError(f"unknown waiver ids: {missing_waivers}")
        unusable_waivers: list[str] = []
        for waiver_id in supplied_waivers:
            waiver = snapshot.waivers[waiver_id]
            if waiver.get("status") != WaiverStatus.ACTIVE.value:
                unusable_waivers.append(waiver_id)
                continue
            expires_at = waiver.get("expires_at")
            if expires_at and datetime.fromisoformat(str(expires_at)) <= now:
                unusable_waivers.append(waiver_id)
        if unusable_waivers:
            raise ProtocolValidationError(
                f"inactive or expired waiver ids cannot authorize promotion: {unusable_waivers}"
            )
        return _append_event_locked(
            project_id,
            ProtocolEventKind.PROMOTION_RECORDED,
            {
                "target_type": target_type,
                "target_id": target_id,
                "decision": decision_value.value,
                "rationale": _required_text(rationale, "rationale"),
                "evidence": evidence_refs,
                "waiver_ids": supplied_waivers,
                "rigor_level": snapshot.rigor_level.value,
            },
            actor=actor,
            snapshot=snapshot,
        )


def record_waiver(
    project_id: str,
    *,
    waiver_id: str,
    scope: str,
    reason: str,
    doctrine_basis: str,
    owner: str,
    actor: str,
    status: str | WaiverStatus = WaiverStatus.ACTIVE,
    expires_at: str | None = None,
    affected_claims: list[str] | None = None,
) -> ProtocolEvent:
    status_value = status if isinstance(status, WaiverStatus) else _enum(
        WaiverStatus, status, "status"
    )
    wid = _safe_id(waiver_id, "waiver_id")
    normalized_expiry: str | None = None
    if expires_at:
        try:
            parsed = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
        except ValueError as exc:
            raise ProtocolValidationError("expires_at must be ISO-8601") from exc
        if parsed.tzinfo is None:
            raise ProtocolValidationError("expires_at must include a timezone")
        parsed = parsed.astimezone(timezone.utc)
        if status_value is WaiverStatus.ACTIVE and parsed <= datetime.now(timezone.utc):
            raise ProtocolValidationError("active waivers must expire in the future")
        normalized_expiry = parsed.isoformat()
    with _lock_for(project_id):
        snapshot = ensure_protocol(project_id, actor=actor)
        prior = snapshot.waivers.get(wid)
        claims = [_safe_id(item, "affected_claim_id") for item in (affected_claims or [])]
        missing_claims = sorted(set(claims) - set(snapshot.claims))
        if missing_claims:
            raise ProtocolValidationError(f"unknown affected claim ids: {missing_claims}")
        return _append_event_locked(
            project_id,
            ProtocolEventKind.WAIVER_RECORDED,
            {
                "waiver_id": wid,
                "scope": _required_text(scope, "scope"),
                "reason": _required_text(reason, "reason"),
                "doctrine_basis": _required_text(doctrine_basis, "doctrine_basis"),
                "owner": _required_text(owner, "owner", max_length=256),
                "status": status_value.value,
                "expires_at": normalized_expiry,
                "affected_claims": claims,
                "revision": int(prior.get("revision", 0)) + 1 if prior else 1,
            },
            actor=actor,
            snapshot=snapshot,
        )


def _append_protocol_event(
    project_id: str,
    event_kind: ProtocolEventKind,
    payload: dict[str, Any],
    *,
    actor: str,
) -> ProtocolEvent:
    with _lock_for(project_id):
        snapshot = ensure_protocol(project_id, actor=actor)
        return _append_event_locked(
            project_id, event_kind, payload, actor=actor, snapshot=snapshot
        )
