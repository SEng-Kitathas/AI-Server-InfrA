"""User-owned continuity memory: append-only authority + addressable snapshots.

The ledger is authoritative. Materialized snapshots are bounded navigation aids,
not proof of project/live state. Healthy reads use an atomic manifest plus
content-addressed section objects and a bounded ledger-head read; full ledger
folds are recovery/audit work, not the ordinary hydration path.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from shared_core import SYSTEM_ROOT, save_json_atomic

SCHEMA_VERSION = "1.1"
LEDGER_SCHEMA = "pcmmad.user-continuity-ledger.v1.1"
SNAPSHOT_SCHEMA = "pcmmad.user-continuity-snapshot.v1.1"
OBJECT_SCHEMA = "pcmmad.user-continuity-object.v1.1"
DEFAULT_PROFILE_ID = "default"
CORE_MAX_BYTES = 32 * 1024
SECTION_MAX_BYTES = 2 * 1024 * 1024
TARGET_INDEX_MAX_BYTES = 2 * 1024 * 1024
MAX_SECTIONS = 512
MAX_SEARCH_SECTIONS = 128
MAX_EVENT_BYTES = 128 * 1024
MAX_VALUE_BYTES = 64 * 1024
MAX_EVIDENCE_ITEMS = 32
MAX_REVALIDATE_ITEMS = 32
MAX_READ_SECTIONS = 24
MAX_LEDGER_TAIL = 64
MAX_SEARCH_RESULTS = 100

MEMORY_ROOT = Path(
    os.environ.get("PCMMAD_USER_CONTINUITY_ROOT", str(SYSTEM_ROOT / "user_continuity"))
).resolve()

_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")
_SAFE_SECTION = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_SAFE_TARGET = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

MEMORY_CLASSES = frozenset(
    {
        "USER_STATED",
        "USER_PREFERENCE",
        "USER_CONSTRAINT",
        "PROJECT_STATE",
        "PROJECT_DOCTRINE",
        "OBSERVED",
        "ASSISTANT_INFERRED",
        "SESSION_METADATA",
        "UNKNOWN",
    }
)
MEMORY_STATUSES = frozenset(
    {
        "ACTIVE",
        "HISTORICAL",
        "SUPERSEDED",
        "DEFERRED",
        "REJECTED",
        "UNKNOWN_CURRENTNESS",
        "FORGET_REQUESTED",
    }
)
EXPORT_CLASSES = frozenset({"PORTABLE", "USER", "PROJECT", "DEPLOYMENT"})
SENSITIVITY = frozenset({"normal", "personal", "sensitive"})
CONFIDENCE = frozenset({"high", "medium", "low"})
ACTORS = frozenset({"user", "assistant", "server", "imported"})
OPERATIONS = frozenset({"ADD", "UPDATE", "SUPERSEDE", "VERIFY", "FORGET_REQUEST"})
_HIDDEN_DEFAULT_STATUSES = frozenset({"SUPERSEDED", "REJECTED", "FORGET_REQUESTED"})

_LOCKS_GUARD = threading.RLock()
_PROFILE_LOCKS: dict[str, threading.RLock] = {}
_CACHE_GUARD = threading.RLock()


class UserContinuityError(RuntimeError):
    def __init__(self, error_code: str, message: str, status: int = 400, **extra: Any) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status = status
        self.extra = extra


class UserContinuityLedgerError(UserContinuityError):
    pass


class UserContinuityConflict(UserContinuityError):
    pass


@dataclass(frozen=True)
class MemoryPaths:
    root: Path
    ledger: Path
    lock: Path
    objects: Path
    snapshots: Path
    current: Path


@dataclass
class _StateCacheEntry:
    state: dict[str, Any]
    ledger_fingerprint: tuple[int, int, int]


_STATE_CACHE: dict[str, _StateCacheEntry] = {}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(_canonical_bytes(value))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _profile_id(value: object | None) -> str:
    text = str(value or DEFAULT_PROFILE_ID).strip()
    if not _SAFE_ID.fullmatch(text):
        raise UserContinuityError("BAD_PROFILE_ID", "profile_id contains invalid characters", 400)
    return text


def _paths(profile_id: str) -> MemoryPaths:
    pid = _profile_id(profile_id)
    expected = (MEMORY_ROOT / "profiles").resolve()
    root = (expected / pid).resolve()
    try:
        root.relative_to(expected)
    except ValueError as exc:
        raise UserContinuityError("BAD_PROFILE_ID", "profile path escapes continuity root", 400) from exc
    return MemoryPaths(
        root=root,
        ledger=root / "events.jsonl",
        lock=root / "profile.lock",
        objects=root / "objects",
        snapshots=root / "snapshots",
        current=root / "current.json",
    )


def _thread_lock(profile_id: str) -> threading.RLock:
    with _LOCKS_GUARD:
        return _PROFILE_LOCKS.setdefault(profile_id, threading.RLock())


@contextmanager
def _cross_process_file_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
            os.fsync(handle.fileno())
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:  # pragma: no cover - Windows is the primary deployment
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def _profile_lock(profile_id: str) -> Iterator[None]:
    pid = _profile_id(profile_id)
    with _thread_lock(pid):
        with _cross_process_file_lock(_paths(pid).lock):
            yield


def _ledger_fingerprint(path: Path) -> tuple[int, int, int]:
    stat = path.stat()
    return (int(stat.st_size), int(stat.st_mtime_ns), int(stat.st_ctime_ns))


def _cache_key(profile_id: str) -> str:
    return str(_paths(profile_id).ledger.resolve())


def _cache_state(profile_id: str, state: dict[str, Any]) -> None:
    path = _paths(profile_id).ledger
    if not path.is_file():
        return
    entry = _StateCacheEntry(state=copy.deepcopy(state), ledger_fingerprint=_ledger_fingerprint(path))
    with _CACHE_GUARD:
        _STATE_CACHE[_cache_key(profile_id)] = entry


def _cached_state(profile_id: str) -> dict[str, Any] | None:
    path = _paths(profile_id).ledger
    if not path.is_file():
        return None
    key = _cache_key(profile_id)
    with _CACHE_GUARD:
        entry = _STATE_CACHE.get(key)
    if entry is None:
        return None
    try:
        current = _ledger_fingerprint(path)
    except OSError:
        return None
    if current != entry.ledger_fingerprint:
        with _CACHE_GUARD:
            _STATE_CACHE.pop(key, None)
        return None
    return copy.deepcopy(entry.state)


def _empty_state(profile_id: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "profile_id": profile_id,
        "event_count": 0,
        "head_hash": None,
        "updated_at": None,
        "facts": {},
        "targets": {},
        "idempotency": {},
    }


def _required_text(value: object, field: str, *, max_chars: int = 20000) -> str:
    text = str(value or "").strip()
    if not text:
        raise UserContinuityError("BAD_REQUEST", f"{field} is required", 400)
    if len(text) > max_chars:
        raise UserContinuityError("BAD_REQUEST", f"{field} exceeds {max_chars} characters", 400)
    return text


def _optional_text(value: object, field: str, *, max_chars: int = 20000) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) > max_chars:
        raise UserContinuityError("BAD_REQUEST", f"{field} exceeds {max_chars} characters", 400)
    return text


def _safe_token(value: object, field: str) -> str:
    text = _required_text(value, field, max_chars=160)
    if not _SAFE_ID.fullmatch(text):
        raise UserContinuityError("BAD_REQUEST", f"{field} contains invalid characters", 400)
    return text


def _section(value: object) -> str:
    text = _required_text(value, "section", max_chars=128)
    if not _SAFE_SECTION.fullmatch(text):
        raise UserContinuityError("BAD_REQUEST", "section contains invalid characters", 400)
    return text


def _target(value: object) -> str:
    text = _required_text(value, "target", max_chars=256)
    if not _SAFE_TARGET.fullmatch(text):
        raise UserContinuityError("BAD_REQUEST", "target must be a stable dotted/token path", 400)
    return text


def _enum(value: object, field: str, allowed: frozenset[str], *, lower: bool = False) -> str:
    text = _required_text(value, field, max_chars=128)
    normalized = text.lower() if lower else text.upper()
    expected = {item.lower() if lower else item.upper(): item for item in allowed}
    if normalized not in expected:
        raise UserContinuityError("BAD_REQUEST", f"{field} must be one of {sorted(allowed)}", 400)
    return expected[normalized]


def _json_value(value: Any) -> Any:
    try:
        encoded = _canonical_bytes(value)
    except (TypeError, ValueError) as exc:
        raise UserContinuityError("BAD_REQUEST", "value must be JSON-serializable", 400) from exc
    if len(encoded) > MAX_VALUE_BYTES:
        raise UserContinuityError("BAD_REQUEST", f"value exceeds {MAX_VALUE_BYTES} encoded bytes", 400)
    return copy.deepcopy(value)


def _iso8601(value: object | None, field: str) -> str | None:
    text = _optional_text(value, field, max_chars=80)
    if text is None:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise UserContinuityError("BAD_REQUEST", f"{field} must be ISO-8601", 400) from exc
    if parsed.tzinfo is None:
        raise UserContinuityError("BAD_REQUEST", f"{field} must include a timezone offset", 400)
    return text


def _string_list(value: object | None, field: str, *, limit: int = MAX_REVALIDATE_ITEMS) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, list) or len(value) > limit:
        raise UserContinuityError("BAD_REQUEST", f"{field} must be an array with at most {limit} items", 400)
    out: list[str] = []
    for item in value:
        text = _required_text(item, field, max_chars=200)
        out.append(text)
    return out


def _evidence_list(value: object | None, field: str, *, required: bool = False) -> list[dict[str, Any]]:
    if value in (None, ""):
        if required:
            raise UserContinuityError("BAD_REQUEST", f"{field} requires at least one evidence item", 400)
        return []
    if not isinstance(value, list) or not value or len(value) > MAX_EVIDENCE_ITEMS:
        raise UserContinuityError("BAD_REQUEST", f"{field} must contain 1-{MAX_EVIDENCE_ITEMS} objects", 400)
    out: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise UserContinuityError("BAD_REQUEST", f"{field}[{index}] must be an object", 400)
        ref_type = _safe_token(item.get("type"), f"{field}[{index}].type")
        ref = _required_text(item.get("ref"), f"{field}[{index}].ref", max_chars=2000)
        sha = _optional_text(item.get("sha256"), f"{field}[{index}].sha256", max_chars=64)
        if sha is not None and not _SHA256_RE.fullmatch(sha.lower()):
            raise UserContinuityError("BAD_REQUEST", f"{field}[{index}].sha256 must be 64 hex characters", 400)
        group = _optional_text(item.get("independence_group"), f"{field}[{index}].independence_group", max_chars=200)
        out.append(
            {
                "type": ref_type,
                "ref": ref,
                "sha256": sha.lower() if sha else None,
                "independence_group": group,
            }
        )
    return out


def _provenance(payload: dict[str, Any]) -> dict[str, Any]:
    actor = _enum(payload.get("actor"), "actor", ACTORS, lower=True)
    source_instance = _safe_token(payload.get("source_instance"), "source_instance")
    return {
        "actor": actor,
        "source_instance": source_instance,
        "source_thread": _optional_text(payload.get("source_thread"), "source_thread", max_chars=500),
        "source_event": _optional_text(payload.get("source_event"), "source_event", max_chars=500),
        "evidence_independence_group": _optional_text(
            payload.get("evidence_independence_group"), "evidence_independence_group", max_chars=200
        ),
    }


def _fact_payload(payload: dict[str, Any], *, memory_id: str | None = None) -> dict[str, Any]:
    status = _enum(payload.get("status", "ACTIVE"), "status", MEMORY_STATUSES)
    fact = {
        "memory_id": memory_id or f"MEM-{uuid.uuid4().hex}",
        "target": _target(payload.get("target")),
        "section": _section(payload.get("section")),
        "class": _enum(payload.get("class"), "class", MEMORY_CLASSES),
        "status": status,
        "value": _json_value(payload.get("value")),
        "reason": _required_text(payload.get("reason"), "reason", max_chars=8000),
        "provenance": _optional_text(payload.get("provenance"), "provenance", max_chars=16000),
        "confidence": _enum(payload.get("confidence", "medium"), "confidence", CONFIDENCE, lower=True),
        "requires_live_verification": bool(payload.get("requires_live_verification", False)),
        "sensitivity": _enum(payload.get("sensitivity", "normal"), "sensitivity", SENSITIVITY, lower=True),
        "export_class": _enum(payload.get("export_class"), "export_class", EXPORT_CLASSES),
        "always_load": bool(payload.get("always_load", False)),
        "hydration_priority": int(payload.get("hydration_priority", 100)),
        "last_verified_at": _iso8601(payload.get("last_verified_at"), "last_verified_at"),
        "revalidate_after": _iso8601(payload.get("revalidate_after"), "revalidate_after"),
        "revalidate_when": _string_list(payload.get("revalidate_when"), "revalidate_when"),
        "verification_summary": {
            "verification_count": 0,
            "evidence_independence_groups": [],
            "independent_evidence_count": 0,
            "last_verification": None,
        },
    }
    if fact["hydration_priority"] < 0 or fact["hydration_priority"] > 100000:
        raise UserContinuityError("BAD_REQUEST", "hydration_priority must be between 0 and 100000", 400)
    if fact["class"] == "PROJECT_STATE" and not fact["requires_live_verification"]:
        raise UserContinuityError(
            "PROJECT_STATE_REQUIRES_LIVE_VERIFICATION",
            "PROJECT_STATE facts must set requires_live_verification=true",
            400,
        )
    return fact


def _event_body(
    *,
    event_seq: int,
    event_id: str,
    timestamp: str,
    profile_id: str,
    operation: str,
    provenance: dict[str, Any],
    payload: dict[str, Any],
    previous_hash: str | None,
    idempotency_key: str,
    request_fingerprint: str,
) -> dict[str, Any]:
    return {
        "schema": LEDGER_SCHEMA,
        "event_seq": event_seq,
        "event_id": event_id,
        "timestamp": timestamp,
        "profile_id": profile_id,
        "actor": provenance["actor"],
        "source_instance": provenance["source_instance"],
        "source_thread": provenance.get("source_thread"),
        "source_event": provenance.get("source_event"),
        "evidence_independence_group": provenance.get("evidence_independence_group"),
        "operation": operation,
        "payload": payload,
        "previous_hash": previous_hash,
        "idempotency_key": idempotency_key,
        "request_fingerprint": request_fingerprint,
    }


def _parse_event(raw: object, line_no: int, profile_id: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise UserContinuityLedgerError("MEMORY_LEDGER_CORRUPT", f"ledger line {line_no} is not an object", 409)
    required = {
        "schema",
        "event_seq",
        "event_id",
        "timestamp",
        "profile_id",
        "actor",
        "source_instance",
        "operation",
        "payload",
        "previous_hash",
        "idempotency_key",
        "request_fingerprint",
        "event_hash",
    }
    missing = sorted(required - set(raw))
    if missing:
        raise UserContinuityLedgerError(
            "MEMORY_LEDGER_CORRUPT", f"ledger line {line_no} missing fields: {missing}", 409
        )
    if raw.get("schema") != LEDGER_SCHEMA or raw.get("profile_id") != profile_id:
        raise UserContinuityLedgerError("MEMORY_LEDGER_CORRUPT", f"ledger line {line_no} schema/profile mismatch", 409)
    return dict(raw)


def read_events(profile_id: str) -> list[dict[str, Any]]:
    pid = _profile_id(profile_id)
    path = _paths(pid).ledger
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            if len(line.encode("utf-8")) > MAX_EVENT_BYTES:
                raise UserContinuityLedgerError(
                    "MEMORY_LEDGER_CORRUPT", f"ledger line {line_no} exceeds event byte ceiling", 409
                )
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise UserContinuityLedgerError(
                    "MEMORY_LEDGER_CORRUPT", f"ledger line {line_no} is invalid JSON", 409
                ) from exc
            events.append(_parse_event(raw, line_no, pid))
    return events


def verify_events(profile_id: str, events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    pid = _profile_id(profile_id)
    materialized = read_events(pid) if events is None else list(events)
    failures: list[dict[str, Any]] = []
    expected_previous: str | None = None
    for index, event in enumerate(materialized, 1):
        if int(event.get("event_seq") or -1) != index:
            failures.append({"event_seq": index, "error": "sequence_mismatch", "actual": event.get("event_seq")})
        if event.get("previous_hash") != expected_previous:
            failures.append(
                {
                    "event_seq": index,
                    "error": "previous_hash_mismatch",
                    "expected": expected_previous,
                    "actual": event.get("previous_hash"),
                }
            )
        event_hash = str(event.get("event_hash") or "")
        body = {key: value for key, value in event.items() if key != "event_hash"}
        computed = _sha256_json(body)
        if event_hash != computed:
            failures.append(
                {"event_seq": index, "error": "event_hash_mismatch", "expected": computed, "actual": event_hash}
            )
        expected_previous = event_hash
    return {
        "ok": not failures,
        "profile_id": pid,
        "event_count": len(materialized),
        "head_hash": materialized[-1]["event_hash"] if materialized else None,
        "failures": failures,
    }


def _active_target_id(state: dict[str, Any], target: str) -> str | None:
    memory_id = state["targets"].get(target)
    if not memory_id:
        return None
    fact = state["facts"].get(memory_id)
    if not fact or fact.get("status") in _HIDDEN_DEFAULT_STATUSES:
        return None
    return str(memory_id)


def _verification_groups(event: dict[str, Any], evidence: list[dict[str, Any]]) -> set[str]:
    groups = {
        str(item.get("independence_group"))
        for item in evidence
        if item.get("independence_group")
    }
    direct = event.get("evidence_independence_group")
    if direct:
        groups.add(str(direct))
    return groups


def _apply_event(state: dict[str, Any], event: dict[str, Any]) -> None:
    op = str(event["operation"])
    payload = dict(event["payload"])
    if op == "ADD":
        fact = copy.deepcopy(payload["fact"])
        fact["created_event_id"] = event["event_id"]
        fact["updated_event_id"] = event["event_id"]
        fact["created_at"] = event["timestamp"]
        fact["updated_at"] = event["timestamp"]
        group = event.get("evidence_independence_group")
        if group:
            fact["verification_summary"]["evidence_independence_groups"] = [str(group)]
            fact["verification_summary"]["independent_evidence_count"] = 1
        state["facts"][fact["memory_id"]] = fact
        state["targets"][fact["target"]] = fact["memory_id"]
    elif op == "UPDATE":
        memory_id = str(payload["memory_id"])
        fact = state["facts"][memory_id]
        patch = dict(payload["patch"])
        old_target = str(fact["target"])
        fact.update(copy.deepcopy(patch))
        fact["updated_event_id"] = event["event_id"]
        fact["updated_at"] = event["timestamp"]
        if old_target != fact["target"]:
            state["targets"].pop(old_target, None)
            state["targets"][fact["target"]] = memory_id
    elif op == "SUPERSEDE":
        old_id = str(payload["target_memory_id"])
        old = state["facts"][old_id]
        old["status"] = "SUPERSEDED"
        old["superseded_by_event_id"] = event["event_id"]
        old["superseded_by_memory_id"] = payload["replacement"]["memory_id"]
        old["superseded_by_evidence"] = copy.deepcopy(payload["superseded_by_evidence"])
        old["updated_event_id"] = event["event_id"]
        old["updated_at"] = event["timestamp"]
        replacement = copy.deepcopy(payload["replacement"])
        replacement["created_event_id"] = event["event_id"]
        replacement["updated_event_id"] = event["event_id"]
        replacement["created_at"] = event["timestamp"]
        replacement["updated_at"] = event["timestamp"]
        replacement["supersedes_memory_id"] = old_id
        replacement["superseded_by_evidence"] = copy.deepcopy(payload["superseded_by_evidence"])
        state["facts"][replacement["memory_id"]] = replacement
        state["targets"][old["target"]] = replacement["memory_id"]
    elif op == "VERIFY":
        memory_id = str(payload["memory_id"])
        fact = state["facts"][memory_id]
        evidence = list(payload["evidence"])
        summary = fact.setdefault(
            "verification_summary",
            {"verification_count": 0, "evidence_independence_groups": [], "independent_evidence_count": 0, "last_verification": None},
        )
        summary["verification_count"] = int(summary.get("verification_count") or 0) + 1
        groups = set(summary.get("evidence_independence_groups") or [])
        groups.update(_verification_groups(event, evidence))
        summary["evidence_independence_groups"] = sorted(groups)
        summary["independent_evidence_count"] = len(groups)
        summary["last_verification"] = {
            "event_id": event["event_id"],
            "timestamp": event["timestamp"],
            "source_instance": event["source_instance"],
            "evidence": copy.deepcopy(evidence),
        }
        fact["last_verified_at"] = payload.get("verified_at") or event["timestamp"]
        if payload.get("status"):
            fact["status"] = payload["status"]
        if payload.get("confidence"):
            fact["confidence"] = payload["confidence"]
        fact["updated_event_id"] = event["event_id"]
        fact["updated_at"] = event["timestamp"]
    elif op == "FORGET_REQUEST":
        memory_id = str(payload["memory_id"])
        fact = state["facts"][memory_id]
        fact["status"] = "FORGET_REQUESTED"
        fact["forget_requested_at"] = event["timestamp"]
        fact["forget_reason"] = payload["reason"]
        fact["updated_event_id"] = event["event_id"]
        fact["updated_at"] = event["timestamp"]
        if state["targets"].get(fact["target"]) == memory_id:
            state["targets"].pop(fact["target"], None)
    else:
        raise UserContinuityLedgerError("MEMORY_LEDGER_CORRUPT", f"unknown operation {op}", 409)
    state["event_count"] = int(event["event_seq"])
    state["head_hash"] = event["event_hash"]
    state["updated_at"] = event["timestamp"]
    state["idempotency"][event["idempotency_key"]] = {
        "request_fingerprint": event["request_fingerprint"],
        "event_id": event["event_id"],
        "event_seq": event["event_seq"],
        "event_hash": event["event_hash"],
        "operation": op,
        "payload": copy.deepcopy(payload),
    }


def build_state(profile_id: str, events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    pid = _profile_id(profile_id)
    materialized = read_events(pid) if events is None else list(events)
    verification = verify_events(pid, materialized)
    if not verification["ok"]:
        raise UserContinuityLedgerError(
            "MEMORY_LEDGER_CORRUPT", "user continuity ledger failed hash-chain verification", 409,
            failures=verification["failures"],
        )
    state = _empty_state(pid)
    for event in materialized:
        try:
            _apply_event(state, event)
        except (KeyError, TypeError, ValueError) as exc:
            raise UserContinuityLedgerError(
                "MEMORY_LEDGER_CORRUPT", f"event {event.get('event_id')} cannot be folded: {exc}", 409
            ) from exc
    return state


def _load_verified_state_locked(profile_id: str) -> dict[str, Any]:
    cached = _cached_state(profile_id)
    if cached is not None:
        return cached
    path = _paths(profile_id).ledger
    if not path.exists():
        return _empty_state(profile_id)
    state = build_state(profile_id)
    _cache_state(profile_id, state)
    return state


def _read_last_nonempty_line(path: Path) -> str | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        read_size = min(size, MAX_EVENT_BYTES + 2)
        handle.seek(size - read_size)
        data = handle.read(read_size)
    lines = [line for line in data.splitlines() if line.strip()]
    if not lines:
        return None
    if len(lines[-1]) > MAX_EVENT_BYTES:
        raise UserContinuityLedgerError("MEMORY_LEDGER_CORRUPT", "last ledger event exceeds byte ceiling", 409)
    return lines[-1].decode("utf-8")


def ledger_head(profile_id: str) -> dict[str, Any]:
    pid = _profile_id(profile_id)
    path = _paths(pid).ledger
    line = _read_last_nonempty_line(path)
    if line is None:
        return {"event_seq": 0, "event_hash": None, "event_id": None}
    try:
        raw = json.loads(line)
    except json.JSONDecodeError as exc:
        raise UserContinuityLedgerError("MEMORY_LEDGER_CORRUPT", "last ledger event is invalid JSON", 409) from exc
    event = _parse_event(raw, -1, pid)
    body = {key: value for key, value in event.items() if key != "event_hash"}
    if event["event_hash"] != _sha256_json(body):
        raise UserContinuityLedgerError("MEMORY_LEDGER_CORRUPT", "last ledger event hash is invalid", 409)
    return {"event_seq": int(event["event_seq"]), "event_hash": event["event_hash"], "event_id": event["event_id"]}


def _fact_for_snapshot(fact: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(fact)


def _core_document(state: dict[str, Any]) -> dict[str, Any]:
    facts = [
        _fact_for_snapshot(fact)
        for fact in state["facts"].values()
        if fact.get("always_load") and fact.get("status") not in _HIDDEN_DEFAULT_STATUSES
    ]
    facts.sort(key=lambda row: (int(row.get("hydration_priority") or 100), str(row.get("target") or "")))
    return {
        "schema": OBJECT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "profile_id": state["profile_id"],
        "kind": "core",
        "snapshot_from_seq": state["event_count"],
        "facts": facts,
    }


def _section_documents(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for fact in state["facts"].values():
        grouped.setdefault(str(fact["section"]), []).append(_fact_for_snapshot(fact))
    docs: dict[str, dict[str, Any]] = {}
    for section_name, facts in grouped.items():
        facts.sort(key=lambda row: (str(row.get("target") or ""), str(row.get("memory_id") or "")))
        docs[section_name] = {
            "schema": OBJECT_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "profile_id": state["profile_id"],
            "kind": "section",
            "section": section_name,
            "snapshot_from_seq": state["event_count"],
            "facts": facts,
        }
    return docs


def _target_index_document(state: dict[str, Any]) -> dict[str, Any]:
    targets: dict[str, Any] = {}
    for target, memory_id in state["targets"].items():
        fact = state["facts"].get(memory_id)
        if not fact or fact.get("status") in _HIDDEN_DEFAULT_STATUSES:
            continue
        targets[str(target)] = {"memory_id": str(memory_id), "section": str(fact["section"])}
    return {
        "schema": OBJECT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "profile_id": state["profile_id"],
        "kind": "target_index",
        "snapshot_from_seq": state["event_count"],
        "targets": targets,
    }


def _preflight_core(state: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    core = _core_document(state)
    encoded = _canonical_bytes(core)
    if len(encoded) > CORE_MAX_BYTES:
        raise UserContinuityConflict(
            "MEMORY_CORE_BUDGET_EXCEEDED",
            f"always-loaded core would exceed hard {CORE_MAX_BYTES}-byte budget",
            409,
            core_bytes=len(encoded),
            core_max_bytes=CORE_MAX_BYTES,
        )
    return core, encoded


def _preflight_snapshot_limits(state: dict[str, Any]) -> None:
    _preflight_core(state)
    sections = _section_documents(state)
    if len(sections) > MAX_SECTIONS:
        raise UserContinuityConflict(
            "MEMORY_SECTION_COUNT_EXCEEDED",
            f"materialized snapshot would exceed {MAX_SECTIONS} addressable sections",
            409,
            section_count=len(sections),
            max_sections=MAX_SECTIONS,
        )
    for section_name, document in sections.items():
        size = len(_canonical_bytes(document))
        if size > SECTION_MAX_BYTES:
            raise UserContinuityConflict(
                "MEMORY_SECTION_BUDGET_EXCEEDED",
                f"section {section_name} would exceed {SECTION_MAX_BYTES} encoded bytes",
                409,
                section=section_name,
                section_bytes=size,
                section_max_bytes=SECTION_MAX_BYTES,
            )
    target_index_bytes = len(_canonical_bytes(_target_index_document(state)))
    if target_index_bytes > TARGET_INDEX_MAX_BYTES:
        raise UserContinuityConflict(
            "MEMORY_TARGET_INDEX_BUDGET_EXCEEDED",
            f"target index would exceed {TARGET_INDEX_MAX_BYTES} encoded bytes",
            409,
            target_index_bytes=target_index_bytes,
            target_index_max_bytes=TARGET_INDEX_MAX_BYTES,
        )


def _write_object(paths: MemoryPaths, document: dict[str, Any], encoded: bytes | None = None) -> dict[str, Any]:
    payload = encoded if encoded is not None else _canonical_bytes(document)
    sha = _sha256_bytes(payload)
    path = paths.objects / f"{sha}.json"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        with tmp.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            tmp.replace(path)
        finally:
            tmp.unlink(missing_ok=True)
    return {"sha256": sha, "bytes": len(payload), "object": f"objects/{sha}.json"}


def _materialize_locked(profile_id: str, state: dict[str, Any]) -> dict[str, Any]:
    paths = _paths(profile_id)
    _preflight_snapshot_limits(state)
    core, core_bytes = _preflight_core(state)
    core_ref = _write_object(paths, core, core_bytes)
    target_index = _target_index_document(state)
    target_index_ref = _write_object(paths, target_index)
    target_index_ref["target_count"] = len(target_index["targets"])
    section_refs: dict[str, Any] = {}
    for section_name, document in _section_documents(state).items():
        ref = _write_object(paths, document)
        ref["fact_count"] = len(document["facts"])
        section_refs[section_name] = ref
    generated_at = _utc_now()
    manifest = {
        "schema": SNAPSHOT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "profile_id": profile_id,
        "generated_at": generated_at,
        "snapshot_from_seq": int(state["event_count"]),
        "ledger_head_seq": int(state["event_count"]),
        "ledger_head_hash": state["head_hash"],
        "core_max_bytes": CORE_MAX_BYTES,
        "core": {**core_ref, "fact_count": len(core["facts"])},
        "target_index": target_index_ref,
        "sections": section_refs,
        "fact_count": len(state["facts"]),
        "laws": [
            "CONTINUITY_IS_NAVIGATION_NOT_PROOF",
            "USER_CONTINUITY_NE_PROJECT_AUTHORITY",
            "TWO_ASSISTANTS_AGREEING_NE_INDEPENDENT_CONFIRMATION",
            "MEMORY_MECHANISM_NE_MEMORY_CONTENT",
            "PORTABLE_STACK_NE_USER_SPECIFIC_OVERLAY",
            "FORGET_REQUEST_NE_PHYSICAL_ERASURE",
        ],
    }
    manifest_hash = _sha256_json(manifest)
    immutable = paths.snapshots / f"{state['event_count']:020d}-{(state['head_hash'] or 'genesis')[:16]}.json"
    immutable.parent.mkdir(parents=True, exist_ok=True)
    if not immutable.exists():
        save_json_atomic(immutable, manifest)
    save_json_atomic(paths.current, manifest)
    return {**manifest, "manifest_sha256": manifest_hash, "manifest_path": str(paths.current)}


def _load_current_manifest(profile_id: str) -> dict[str, Any] | None:
    path = _paths(profile_id).current
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UserContinuityLedgerError("MEMORY_SNAPSHOT_CORRUPT", "current snapshot manifest is unreadable", 409) from exc
    if not isinstance(raw, dict) or raw.get("schema") != SNAPSHOT_SCHEMA or raw.get("profile_id") != profile_id:
        raise UserContinuityLedgerError("MEMORY_SNAPSHOT_CORRUPT", "current snapshot manifest schema/profile mismatch", 409)
    return raw


def _snapshot_currentness(profile_id: str, manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    current = _load_current_manifest(profile_id) if manifest is None else manifest
    head = ledger_head(profile_id)
    if current is None:
        return {"current": head["event_seq"] == 0, "manifest": None, "ledger_head": head}
    ok = (
        int(current.get("snapshot_from_seq") or -1) == int(head["event_seq"])
        and int(current.get("ledger_head_seq") or -1) == int(head["event_seq"])
        and current.get("ledger_head_hash") == head["event_hash"]
    )
    return {"current": ok, "manifest": current, "ledger_head": head}


def _load_object(profile_id: str, ref: dict[str, Any]) -> dict[str, Any]:
    paths = _paths(profile_id)
    sha = str(ref.get("sha256") or "")
    if not _SHA256_RE.fullmatch(sha):
        raise UserContinuityLedgerError("MEMORY_SNAPSHOT_CORRUPT", "snapshot object reference has invalid sha256", 409)
    path = paths.objects / f"{sha}.json"
    if not path.is_file():
        raise UserContinuityLedgerError("MEMORY_SNAPSHOT_CORRUPT", f"snapshot object {sha} is missing", 409)
    data = path.read_bytes()
    if len(data) != int(ref.get("bytes") or -1) or _sha256_bytes(data) != sha:
        raise UserContinuityLedgerError("MEMORY_SNAPSHOT_CORRUPT", f"snapshot object {sha} failed hash/size readback", 409)
    try:
        raw = json.loads(data.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise UserContinuityLedgerError("MEMORY_SNAPSHOT_CORRUPT", f"snapshot object {sha} is invalid JSON", 409) from exc
    if not isinstance(raw, dict) or raw.get("schema") != OBJECT_SCHEMA:
        raise UserContinuityLedgerError("MEMORY_SNAPSHOT_CORRUPT", f"snapshot object {sha} has invalid schema", 409)
    return raw


def _request_fingerprint(operation: str, payload: dict[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "idempotency_key"}
    return _sha256_json({"operation": operation, "request": body})


def _idempotency_key(payload: dict[str, Any]) -> str:
    return _safe_token(payload.get("idempotency_key"), "idempotency_key")


def _check_replay(state: dict[str, Any], idempotency_key: str, request_fingerprint: str) -> dict[str, Any] | None:
    existing = state["idempotency"].get(idempotency_key)
    if not existing:
        return None
    if existing["request_fingerprint"] != request_fingerprint:
        raise UserContinuityConflict(
            "MEMORY_IDEMPOTENCY_CONFLICT",
            "idempotency_key is already bound to a different semantic memory mutation",
            409,
            existing_event_id=existing["event_id"],
        )
    return copy.deepcopy(existing)


def _check_expected_head(state: dict[str, Any], expected: object | None) -> None:
    if expected in (None, ""):
        return
    text = str(expected).strip().lower()
    if text == "genesis":
        text = ""
    actual = str(state.get("head_hash") or "")
    if text != actual:
        raise UserContinuityConflict(
            "MEMORY_HEAD_CONFLICT",
            "expected_ledger_head_hash does not match current authoritative memory head",
            409,
            expected_ledger_head_hash=text or None,
            current_ledger_head_hash=actual or None,
            current_event_seq=state["event_count"],
        )


def _append_event_locked(
    profile_id: str,
    state: dict[str, Any],
    *,
    operation: str,
    event_payload: dict[str, Any],
    provenance: dict[str, Any],
    idempotency_key: str,
    request_fingerprint: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    paths = _paths(profile_id)
    event_seq = int(state["event_count"]) + 1
    event_id = f"MEM-{event_seq:012d}-{uuid.uuid4().hex[:12]}"
    body = _event_body(
        event_seq=event_seq,
        event_id=event_id,
        timestamp=_utc_now(),
        profile_id=profile_id,
        operation=operation,
        provenance=provenance,
        payload=copy.deepcopy(event_payload),
        previous_hash=state.get("head_hash"),
        idempotency_key=idempotency_key,
        request_fingerprint=request_fingerprint,
    )
    event = {**body, "event_hash": _sha256_json(body)}
    encoded = _canonical_bytes(event) + b"\n"
    if len(encoded) > MAX_EVENT_BYTES:
        raise UserContinuityError("MEMORY_EVENT_TOO_LARGE", f"encoded event exceeds {MAX_EVENT_BYTES} bytes", 400)

    projected = copy.deepcopy(state)
    _apply_event(projected, event)
    _preflight_snapshot_limits(projected)

    paths.ledger.parent.mkdir(parents=True, exist_ok=True)
    with paths.ledger.open("ab") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())

    manifest = _materialize_locked(profile_id, projected)
    _cache_state(profile_id, projected)
    return event, manifest


def _mutation_receipt(
    profile_id: str,
    event: dict[str, Any] | None,
    manifest: dict[str, Any],
    *,
    replayed: bool,
    affected_memory_ids: list[str],
) -> dict[str, Any]:
    return {
        "ok": True,
        "profile_id": profile_id,
        "replayed": replayed,
        "event": (
            {
                "event_seq": event["event_seq"],
                "event_id": event["event_id"],
                "event_hash": event["event_hash"],
                "operation": event["operation"],
            }
            if event
            else None
        ),
        "affected_memory_ids": affected_memory_ids,
        "ledger_head_seq": manifest["ledger_head_seq"],
        "ledger_head_hash": manifest["ledger_head_hash"],
        "snapshot_from_seq": manifest["snapshot_from_seq"],
        "snapshot_manifest_sha256": manifest.get("manifest_sha256") or _sha256_json(
            {key: value for key, value in manifest.items() if key not in {"manifest_sha256", "manifest_path"}}
        ),
        "snapshot_current": True,
        "core_bytes": manifest["core"]["bytes"],
        "core_max_bytes": manifest["core_max_bytes"],
    }


def _replay_receipt(profile_id: str, state: dict[str, Any], replay: dict[str, Any]) -> dict[str, Any]:
    currentness = _snapshot_currentness(profile_id)
    if not currentness["current"]:
        raise UserContinuityConflict(
            "MEMORY_SNAPSHOT_STALE",
            "idempotent event exists but materialized snapshot is stale; run memory.compact_snapshot",
            409,
            ledger_head=currentness["ledger_head"],
        )
    manifest = dict(currentness["manifest"])
    manifest["manifest_sha256"] = _sha256_json(manifest)
    op = replay["operation"]
    payload = replay["payload"]
    ids: list[str] = []
    if op == "ADD":
        ids = [payload["fact"]["memory_id"]]
    elif op == "SUPERSEDE":
        ids = [payload["target_memory_id"], payload["replacement"]["memory_id"]]
    else:
        ids = [payload["memory_id"]]
    event = {
        "event_seq": replay["event_seq"],
        "event_id": replay["event_id"],
        "event_hash": replay["event_hash"],
        "operation": op,
    }
    return _mutation_receipt(profile_id, event, manifest, replayed=True, affected_memory_ids=ids)


def memory_add(payload: dict[str, Any]) -> dict[str, Any]:
    profile_id = _profile_id(payload.get("profile_id"))
    idem = _idempotency_key(payload)
    fingerprint = _request_fingerprint("ADD", payload)
    provenance = _provenance(payload)
    with _profile_lock(profile_id):
        state = _load_verified_state_locked(profile_id)
        replay = _check_replay(state, idem, fingerprint)
        if replay:
            return _replay_receipt(profile_id, state, replay)
        _check_expected_head(state, payload.get("expected_ledger_head_hash"))
        fact = _fact_payload(payload)
        existing = _active_target_id(state, fact["target"])
        if existing:
            raise UserContinuityConflict(
                "MEMORY_TARGET_EXISTS",
                "target already has a current fact; use memory.supersede for material correction",
                409,
                target=fact["target"],
                existing_memory_id=existing,
            )
        event, manifest = _append_event_locked(
            profile_id,
            state,
            operation="ADD",
            event_payload={"fact": fact},
            provenance=provenance,
            idempotency_key=idem,
            request_fingerprint=fingerprint,
        )
        return _mutation_receipt(profile_id, event, manifest, replayed=False, affected_memory_ids=[fact["memory_id"]])


def memory_update(payload: dict[str, Any]) -> dict[str, Any]:
    profile_id = _profile_id(payload.get("profile_id"))
    idem = _idempotency_key(payload)
    fingerprint = _request_fingerprint("UPDATE", payload)
    provenance = _provenance(payload)
    memory_id = _safe_token(payload.get("memory_id"), "memory_id")
    allowed_patch = {
        "status",
        "reason",
        "provenance",
        "confidence",
        "requires_live_verification",
        "sensitivity",
        "export_class",
        "always_load",
        "hydration_priority",
        "last_verified_at",
        "revalidate_after",
        "revalidate_when",
        "section",
    }
    raw_patch = payload.get("patch")
    if not isinstance(raw_patch, dict) or not raw_patch:
        raise UserContinuityError("BAD_REQUEST", "patch must be a non-empty object", 400)
    unknown = sorted(set(raw_patch) - allowed_patch)
    if unknown:
        raise UserContinuityError(
            "MATERIAL_MEMORY_CHANGE_REQUIRES_SUPERSEDE",
            f"memory.update cannot change material identity/value fields: {unknown}",
            400,
        )
    with _profile_lock(profile_id):
        state = _load_verified_state_locked(profile_id)
        replay = _check_replay(state, idem, fingerprint)
        if replay:
            return _replay_receipt(profile_id, state, replay)
        _check_expected_head(state, payload.get("expected_ledger_head_hash"))
        fact = state["facts"].get(memory_id)
        if not fact:
            raise UserContinuityError("MEMORY_NOT_FOUND", f"memory_id {memory_id} not found", 404)
        patch: dict[str, Any] = {}
        for key, value in raw_patch.items():
            if key == "status":
                parsed_status = _enum(value, key, MEMORY_STATUSES)
                if parsed_status in {"SUPERSEDED", "FORGET_REQUESTED"}:
                    raise UserContinuityError(
                        "SEMANTIC_MEMORY_TRANSITION_REQUIRED",
                        "use memory.supersede or memory.forget_request for this lifecycle transition",
                        400,
                    )
                patch[key] = parsed_status
            elif key == "reason":
                patch[key] = _required_text(value, key, max_chars=8000)
            elif key == "provenance":
                patch[key] = _optional_text(value, key, max_chars=16000)
            elif key == "confidence":
                patch[key] = _enum(value, key, CONFIDENCE, lower=True)
            elif key == "sensitivity":
                patch[key] = _enum(value, key, SENSITIVITY, lower=True)
            elif key == "export_class":
                patch[key] = _enum(value, key, EXPORT_CLASSES)
            elif key == "section":
                patch[key] = _section(value)
            elif key in {"last_verified_at", "revalidate_after"}:
                patch[key] = _iso8601(value, key)
            elif key == "revalidate_when":
                patch[key] = _string_list(value, key)
            elif key == "hydration_priority":
                ivalue = int(value)
                if ivalue < 0 or ivalue > 100000:
                    raise UserContinuityError("BAD_REQUEST", "hydration_priority must be 0-100000", 400)
                patch[key] = ivalue
            else:
                patch[key] = bool(value)
        projected = copy.deepcopy(fact)
        projected.update(patch)
        if projected["class"] == "PROJECT_STATE" and not projected["requires_live_verification"]:
            raise UserContinuityError(
                "PROJECT_STATE_REQUIRES_LIVE_VERIFICATION",
                "PROJECT_STATE facts must retain requires_live_verification=true",
                400,
            )
        event, manifest = _append_event_locked(
            profile_id,
            state,
            operation="UPDATE",
            event_payload={"memory_id": memory_id, "patch": patch},
            provenance=provenance,
            idempotency_key=idem,
            request_fingerprint=fingerprint,
        )
        return _mutation_receipt(profile_id, event, manifest, replayed=False, affected_memory_ids=[memory_id])


def memory_supersede(payload: dict[str, Any]) -> dict[str, Any]:
    profile_id = _profile_id(payload.get("profile_id"))
    idem = _idempotency_key(payload)
    fingerprint = _request_fingerprint("SUPERSEDE", payload)
    provenance = _provenance(payload)
    target_memory_id = _safe_token(payload.get("memory_id"), "memory_id")
    replacement_raw = payload.get("replacement")
    if not isinstance(replacement_raw, dict):
        raise UserContinuityError("BAD_REQUEST", "replacement must be an object", 400)
    evidence = _evidence_list(payload.get("superseded_by_evidence"), "superseded_by_evidence", required=True)
    with _profile_lock(profile_id):
        state = _load_verified_state_locked(profile_id)
        replay = _check_replay(state, idem, fingerprint)
        if replay:
            return _replay_receipt(profile_id, state, replay)
        _check_expected_head(state, payload.get("expected_ledger_head_hash"))
        old = state["facts"].get(target_memory_id)
        if not old:
            raise UserContinuityError("MEMORY_NOT_FOUND", f"memory_id {target_memory_id} not found", 404)
        if old.get("status") in {"SUPERSEDED", "FORGET_REQUESTED"}:
            raise UserContinuityConflict("MEMORY_NOT_CURRENT", "only a current memory fact can be superseded", 409)
        merged = dict(replacement_raw)
        merged.setdefault("target", old["target"])
        merged.setdefault("section", old["section"])
        merged.setdefault("class", old["class"])
        merged.setdefault("status", "ACTIVE")
        merged.setdefault("export_class", old["export_class"])
        merged.setdefault("sensitivity", old["sensitivity"])
        merged.setdefault("requires_live_verification", old["requires_live_verification"])
        merged.setdefault("always_load", old["always_load"])
        merged.setdefault("hydration_priority", old["hydration_priority"])
        replacement = _fact_payload(merged)
        if replacement["target"] != old["target"]:
            raise UserContinuityError(
                "MATERIAL_MEMORY_CHANGE_REQUIRES_STABLE_TARGET",
                "memory.supersede must preserve the stable dotted target; add a separate fact for a new target",
                400,
            )
        event, manifest = _append_event_locked(
            profile_id,
            state,
            operation="SUPERSEDE",
            event_payload={
                "target_memory_id": target_memory_id,
                "replacement": replacement,
                "superseded_by_evidence": evidence,
            },
            provenance=provenance,
            idempotency_key=idem,
            request_fingerprint=fingerprint,
        )
        return _mutation_receipt(
            profile_id,
            event,
            manifest,
            replayed=False,
            affected_memory_ids=[target_memory_id, replacement["memory_id"]],
        )


def memory_verify(payload: dict[str, Any]) -> dict[str, Any]:
    profile_id = _profile_id(payload.get("profile_id"))
    idem = _idempotency_key(payload)
    fingerprint = _request_fingerprint("VERIFY", payload)
    provenance = _provenance(payload)
    memory_id = _safe_token(payload.get("memory_id"), "memory_id")
    evidence = _evidence_list(payload.get("evidence"), "evidence", required=True)
    verified_at = _iso8601(payload.get("verified_at"), "verified_at") or _utc_now()
    status = payload.get("status")
    confidence = payload.get("confidence")
    with _profile_lock(profile_id):
        state = _load_verified_state_locked(profile_id)
        replay = _check_replay(state, idem, fingerprint)
        if replay:
            return _replay_receipt(profile_id, state, replay)
        _check_expected_head(state, payload.get("expected_ledger_head_hash"))
        fact = state["facts"].get(memory_id)
        if not fact:
            raise UserContinuityError("MEMORY_NOT_FOUND", f"memory_id {memory_id} not found", 404)
        if fact.get("status") in {"SUPERSEDED", "FORGET_REQUESTED"}:
            raise UserContinuityConflict("MEMORY_NOT_CURRENT", "superseded/forgotten memory cannot be re-verified as current", 409)
        event_payload: dict[str, Any] = {"memory_id": memory_id, "verified_at": verified_at, "evidence": evidence}
        if status is not None:
            parsed_status = _enum(status, "status", MEMORY_STATUSES)
            if parsed_status in {"SUPERSEDED", "FORGET_REQUESTED"}:
                raise UserContinuityError(
                    "SEMANTIC_MEMORY_TRANSITION_REQUIRED",
                    "use memory.supersede or memory.forget_request for this lifecycle transition",
                    400,
                )
            event_payload["status"] = parsed_status
        if confidence is not None:
            event_payload["confidence"] = _enum(confidence, "confidence", CONFIDENCE, lower=True)
        event, manifest = _append_event_locked(
            profile_id,
            state,
            operation="VERIFY",
            event_payload=event_payload,
            provenance=provenance,
            idempotency_key=idem,
            request_fingerprint=fingerprint,
        )
        return _mutation_receipt(profile_id, event, manifest, replayed=False, affected_memory_ids=[memory_id])


def memory_forget_request(payload: dict[str, Any]) -> dict[str, Any]:
    profile_id = _profile_id(payload.get("profile_id"))
    idem = _idempotency_key(payload)
    fingerprint = _request_fingerprint("FORGET_REQUEST", payload)
    provenance = _provenance(payload)
    memory_id = _safe_token(payload.get("memory_id"), "memory_id")
    reason = _required_text(payload.get("reason"), "reason", max_chars=8000)
    with _profile_lock(profile_id):
        state = _load_verified_state_locked(profile_id)
        replay = _check_replay(state, idem, fingerprint)
        if replay:
            receipt = _replay_receipt(profile_id, state, replay)
            receipt["physical_erasure"] = False
            return receipt
        _check_expected_head(state, payload.get("expected_ledger_head_hash"))
        fact = state["facts"].get(memory_id)
        if not fact:
            raise UserContinuityError("MEMORY_NOT_FOUND", f"memory_id {memory_id} not found", 404)
        if fact.get("status") == "FORGET_REQUESTED":
            raise UserContinuityConflict("MEMORY_ALREADY_FORGET_REQUESTED", "forget request already exists", 409)
        event, manifest = _append_event_locked(
            profile_id,
            state,
            operation="FORGET_REQUEST",
            event_payload={"memory_id": memory_id, "reason": reason},
            provenance=provenance,
            idempotency_key=idem,
            request_fingerprint=fingerprint,
        )
        receipt = _mutation_receipt(profile_id, event, manifest, replayed=False, affected_memory_ids=[memory_id])
        receipt["physical_erasure"] = False
        receipt["semantic_note"] = "FORGET_REQUEST != PHYSICAL_ERASURE; append-only provenance is retained"
        return receipt


def memory_compact_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    profile_id = _profile_id(payload.get("profile_id"))
    with _profile_lock(profile_id):
        events = read_events(profile_id)
        verification = verify_events(profile_id, events)
        if not verification["ok"]:
            raise UserContinuityLedgerError(
                "MEMORY_LEDGER_CORRUPT", "cannot compact an invalid continuity ledger", 409,
                failures=verification["failures"],
            )
        expected = payload.get("expected_ledger_head_hash")
        if expected not in (None, ""):
            text = str(expected).strip().lower()
            actual = str(verification["head_hash"] or "")
            if text == "genesis":
                text = ""
            if text != actual:
                raise UserContinuityConflict(
                    "MEMORY_HEAD_CONFLICT", "snapshot CAS expectation does not match ledger head", 409,
                    expected_ledger_head_hash=text or None, current_ledger_head_hash=actual or None,
                )
        state = build_state(profile_id, events)
        manifest = _materialize_locked(profile_id, state)
        if events:
            _cache_state(profile_id, state)
        return {
            "ok": True,
            "profile_id": profile_id,
            "snapshot_from_seq": manifest["snapshot_from_seq"],
            "ledger_head_seq": manifest["ledger_head_seq"],
            "ledger_head_hash": manifest["ledger_head_hash"],
            "snapshot_manifest_sha256": manifest["manifest_sha256"],
            "core_bytes": manifest["core"]["bytes"],
            "core_max_bytes": manifest["core_max_bytes"],
            "fact_count": manifest["fact_count"],
            "section_count": len(manifest["sections"]),
            "ledger_verified": True,
        }


def _fact_revalidation(fact: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    reasons: list[str] = []
    deadline = fact.get("revalidate_after")
    if deadline:
        try:
            parsed = datetime.fromisoformat(str(deadline).replace("Z", "+00:00"))
            if parsed.tzinfo is not None and parsed <= current:
                reasons.append("revalidate_after_elapsed")
        except ValueError:
            reasons.append("invalid_revalidate_after")
    if fact.get("requires_live_verification"):
        reasons.append("requires_live_verification")
    triggers = list(fact.get("revalidate_when") or [])
    return {
        "due": bool(reasons),
        "reasons": reasons,
        "event_triggers": triggers,
        "stale_capable": bool(reasons or triggers),
    }


def _decorate_fact(fact: dict[str, Any]) -> dict[str, Any]:
    decorated = copy.deepcopy(fact)
    decorated["revalidation"] = _fact_revalidation(decorated)
    return decorated


def _export_filter(payload: dict[str, Any]) -> set[str] | None:
    raw = payload.get("export_classes")
    if raw in (None, []):
        return None
    if not isinstance(raw, list) or len(raw) > len(EXPORT_CLASSES):
        raise UserContinuityError("BAD_REQUEST", "export_classes must be a bounded array", 400)
    return {_enum(item, "export_classes", EXPORT_CLASSES) for item in raw}


def _visible_fact(fact: dict[str, Any], include_superseded: bool) -> bool:
    if include_superseded:
        return True
    return fact.get("status") not in _HIDDEN_DEFAULT_STATUSES


def _bounded_tail(profile_id: str, count: int, *, target: str | None = None) -> list[dict[str, Any]]:
    if count <= 0:
        return []
    count = min(count, MAX_LEDGER_TAIL)
    events = read_events(profile_id)
    if target:
        matching: list[dict[str, Any]] = []
        state = build_state(profile_id, events)
        for event in events:
            payload = event.get("payload") or {}
            fact = payload.get("fact") or payload.get("replacement") or {}
            event_target = fact.get("target")
            memory_id = payload.get("memory_id") or payload.get("target_memory_id")
            if event_target == target:
                matching.append(event)
            elif memory_id:
                known = state["facts"].get(str(memory_id))
                if known and known.get("target") == target:
                    matching.append(event)
        events = matching
    return [
        {
            "event_seq": event["event_seq"],
            "event_id": event["event_id"],
            "timestamp": event["timestamp"],
            "actor": event["actor"],
            "source_instance": event["source_instance"],
            "operation": event["operation"],
            "event_hash": event["event_hash"],
            "evidence_independence_group": event.get("evidence_independence_group"),
        }
        for event in events[-count:]
    ]


def memory_read(payload: dict[str, Any]) -> dict[str, Any]:
    profile_id = _profile_id(payload.get("profile_id"))
    currentness = _snapshot_currentness(profile_id)
    head = currentness["ledger_head"]
    if head["event_seq"] == 0 and currentness["manifest"] is None:
        return {
            "ok": True,
            "profile_id": profile_id,
            "initialized": False,
            "snapshot_current": True,
            "ledger_head_seq": 0,
            "ledger_head_hash": None,
            "core": {"facts": []},
            "sections": {},
            "ledger_tail": [],
            "authority_ceiling": "continuity/navigation; never proof of live project state",
        }
    if not currentness["current"]:
        raise UserContinuityConflict(
            "MEMORY_SNAPSHOT_STALE",
            "materialized snapshot does not match authoritative ledger head; run memory.compact_snapshot",
            409,
            snapshot_from_seq=(currentness["manifest"] or {}).get("snapshot_from_seq"),
            ledger_head=head,
        )
    manifest = dict(currentness["manifest"])
    requested_sections = payload.get("sections") or []
    if not isinstance(requested_sections, list) or len(requested_sections) > MAX_READ_SECTIONS:
        raise UserContinuityError("BAD_REQUEST", f"sections must contain at most {MAX_READ_SECTIONS} names", 400)
    section_names = [_section(name) for name in requested_sections]
    include_superseded = bool(payload.get("include_superseded", False))
    export_filter = _export_filter(payload)
    target_filter = _optional_text(payload.get("target"), "target", max_chars=256)
    if target_filter is not None:
        target_filter = _target(target_filter)
        target_index = _load_object(profile_id, manifest["target_index"])
        target_row = (target_index.get("targets") or {}).get(target_filter)
        if target_row and not section_names:
            section_names = [str(target_row["section"])]
    def select(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        chosen = []
        for fact in facts:
            if not _visible_fact(fact, include_superseded):
                continue
            if export_filter is not None and fact.get("export_class") not in export_filter:
                continue
            if target_filter is not None and fact.get("target") != target_filter:
                continue
            chosen.append(_decorate_fact(fact))
        return chosen
    core = _load_object(profile_id, manifest["core"])
    core["facts"] = select(list(core.get("facts", [])))
    sections: dict[str, Any] = {}
    for section_name in section_names:
        ref = (manifest.get("sections") or {}).get(section_name)
        if ref is None:
            sections[section_name] = {"section": section_name, "facts": [], "present": False}
            continue
        document = _load_object(profile_id, ref)
        document["facts"] = select(list(document.get("facts", [])))
        document["present"] = True
        sections[section_name] = document
    tail_count = int(payload.get("ledger_tail", 0) or 0)
    if tail_count < 0 or tail_count > MAX_LEDGER_TAIL:
        raise UserContinuityError("BAD_REQUEST", f"ledger_tail must be 0-{MAX_LEDGER_TAIL}", 400)
    return {
        "ok": True,
        "profile_id": profile_id,
        "initialized": True,
        "schema_version": SCHEMA_VERSION,
        "snapshot_current": True,
        "snapshot_from_seq": manifest["snapshot_from_seq"],
        "ledger_head_seq": head["event_seq"],
        "ledger_head_hash": head["event_hash"],
        "snapshot_manifest_sha256": _sha256_json(manifest),
        "core": core,
        "sections": sections,
        "available_sections": sorted((manifest.get("sections") or {}).keys()),
        "ledger_tail": _bounded_tail(profile_id, tail_count, target=target_filter),
        "revalidation_hazards": [
            {"memory_id": fact["memory_id"], "target": fact["target"], **fact["revalidation"]}
            for document in [core, *sections.values()]
            for fact in document.get("facts", [])
            if fact.get("revalidation", {}).get("stale_capable")
        ],
        "export_filter": sorted(export_filter) if export_filter is not None else None,
        "authority_ceiling": "continuity/navigation; never proof of live project state",
        "hydration_rule": "core + relevant lazy sections + bounded ledger tail; verify live project authority before mutation",
    }


def memory_search(payload: dict[str, Any]) -> dict[str, Any]:
    profile_id = _profile_id(payload.get("profile_id"))
    query = _required_text(payload.get("query"), "query", max_chars=500).lower()
    limit = int(payload.get("limit", 20) or 20)
    if limit < 1 or limit > MAX_SEARCH_RESULTS:
        raise UserContinuityError("BAD_REQUEST", f"limit must be 1-{MAX_SEARCH_RESULTS}", 400)
    include_superseded = bool(payload.get("include_superseded", False))
    export_filter = _export_filter(payload)
    currentness = _snapshot_currentness(profile_id)
    if not currentness["current"]:
        raise UserContinuityConflict(
            "MEMORY_SNAPSHOT_STALE", "cannot search a stale materialized memory snapshot", 409,
            ledger_head=currentness["ledger_head"],
        )
    manifest = currentness["manifest"]
    if manifest is None:
        return {"ok": True, "profile_id": profile_id, "query": query, "results": [], "count": 0}
    terms = [term for term in re.split(r"\s+", query) if term]
    section_filter = payload.get("sections") or []
    if not isinstance(section_filter, list) or len(section_filter) > MAX_READ_SECTIONS:
        raise UserContinuityError("BAD_REQUEST", f"sections must contain at most {MAX_READ_SECTIONS} names", 400)
    if section_filter:
        selected = {_section(item) for item in section_filter}
    else:
        available = sorted(manifest["sections"].keys())
        if len(available) > MAX_SEARCH_SECTIONS:
            raise UserContinuityError(
                "MEMORY_SEARCH_SCOPE_TOO_BROAD",
                f"memory has {len(available)} sections; specify sections when more than {MAX_SEARCH_SECTIONS} exist",
                400,
                section_count=len(available),
                max_implicit_search_sections=MAX_SEARCH_SECTIONS,
            )
        selected = set(available)
    results: list[dict[str, Any]] = []
    for section_name in sorted(selected):
        ref = manifest["sections"].get(section_name)
        if not ref:
            continue
        document = _load_object(profile_id, ref)
        for fact in document.get("facts", []):
            if not _visible_fact(fact, include_superseded):
                continue
            if export_filter is not None and fact.get("export_class") not in export_filter:
                continue
            haystack = " ".join(
                [
                    str(fact.get("target") or ""),
                    str(fact.get("class") or ""),
                    str(fact.get("reason") or ""),
                    str(fact.get("provenance") or ""),
                    json.dumps(fact.get("value"), ensure_ascii=False, sort_keys=True),
                ]
            ).lower()
            hits = sum(1 for term in terms if term in haystack)
            if hits == 0:
                continue
            results.append(
                {
                    "score": hits / max(1, len(terms)),
                    "memory_id": fact["memory_id"],
                    "target": fact["target"],
                    "section": fact["section"],
                    "class": fact["class"],
                    "status": fact["status"],
                    "confidence": fact["confidence"],
                    "requires_live_verification": fact["requires_live_verification"],
                    "export_class": fact["export_class"],
                    "value": fact["value"],
                    "revalidation": _fact_revalidation(fact),
                }
            )
    results.sort(key=lambda row: (-float(row["score"]), str(row["target"]), str(row["memory_id"])))
    bounded = results[:limit]
    return {
        "ok": True,
        "profile_id": profile_id,
        "query": query,
        "count": len(bounded),
        "results": bounded,
        "snapshot_from_seq": manifest["snapshot_from_seq"],
        "ledger_head_hash": manifest["ledger_head_hash"],
        "bounded": len(results) > len(bounded),
    }
