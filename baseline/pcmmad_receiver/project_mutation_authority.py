"""Server-native project mutation ownership with cross-process fencing.

The lease is an authority object, not a substitute for optimistic hashes/currentness.
A persistent generation fence prevents a stale client from waiting for a newer
campaign to finish and then silently becoming authoritative without re-reading.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

from .shared_core import (
    PROJECTS_ROOT,
    cross_process_file_guard,
    get_project_root,
    init_project_layout,
    load_json,
    save_json_atomic,
    utc_now,
    validate_project_id,
)

def _env_bounded_float(name: str, default: float, *, minimum: float, maximum: float) -> float:
    raw = str(os.environ.get(name, default)).strip()
    try:
        value = float(raw)
    except (TypeError, ValueError, OverflowError):
        return float(default)
    return max(float(minimum), min(float(value), float(maximum)))


LEASE_STORE_VERSION = "2"
LEASE_DEFAULT_TTL_SECONDS = 120
LEASE_MIN_TTL_SECONDS = 10
LEASE_MAX_TTL_SECONDS = 900
LEASE_GUARD_TIMEOUT_SECONDS = 5.0
CONSEQUENCE_HEARTBEAT_INTERVAL_SECONDS = _env_bounded_float(
    "PCMMAD_PROJECT_MUTATION_HEARTBEAT_SECONDS", 0.50, minimum=0.10, maximum=5.0
)
CONSEQUENCE_HEARTBEAT_FRESH_SECONDS = _env_bounded_float(
    "PCMMAD_PROJECT_MUTATION_HEARTBEAT_FRESH_SECONDS",
    2.50,
    minimum=max(0.50, CONSEQUENCE_HEARTBEAT_INTERVAL_SECONDS * 2.0),
    maximum=30.0,
)
CONSEQUENCE_HEALTHY_WAIT_MAX_SECONDS = _env_bounded_float(
    "PCMMAD_PROJECT_MUTATION_HEALTHY_WAIT_MAX_SECONDS", 30.0, minimum=5.0, maximum=900.0
)
CONSEQUENCE_ACQUIRE_SLICE_SECONDS = _env_bounded_float(
    "PCMMAD_PROJECT_MUTATION_ACQUIRE_SLICE_SECONDS", 0.20, minimum=0.05, maximum=1.0
)
CONSEQUENCE_WAIT_BACKOFF_INITIAL_SECONDS = 0.01
CONSEQUENCE_WAIT_BACKOFF_MAX_SECONDS = 0.25
CONSEQUENCE_HOLDER_SCHEMA = "pcmmad.project-mutation-consequence-holder.v1"

LEASE_STATUS_ACTIVE = "ACTIVE"
LEASE_STATUS_RELEASED = "RELEASED"
LEASE_STATUS_EXPIRED = "EXPIRED"
LEASE_STATUS_UNOWNED = "UNOWNED"


class ProjectMutationAuthorityError(RuntimeError):
    def __init__(
        self,
        error_code: str,
        message: str,
        status: int = 409,
        *,
        extra: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status = int(status)
        self.extra = dict(extra or {})


def _control_root(project_id: str) -> Path:
    return get_project_root(project_id) / "system" / "control"


def _state_path(project_id: str) -> Path:
    return _control_root(project_id) / "project_mutation_lease.json"


def _guard_path(project_id: str) -> Path:
    """Compatibility alias for the short-lived lease-state lock path."""
    return _control_root(project_id) / ".project_mutation_lease.state.guard"


def _consequence_guard_path(project_id: str) -> Path:
    return _control_root(project_id) / ".project_mutation_consequence.guard"


def _consequence_state_path(project_id: str) -> Path:
    return _control_root(project_id) / "project_mutation_consequence_holder.json"


def _canonical(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _canonical(value[k]) for k in sorted(value, key=lambda item: str(item))}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _integrity_hash(record: Mapping[str, Any]) -> str:
    payload = {str(k): _canonical(v) for k, v in record.items() if k != "integrity_hash"}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _parse_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _bounded_ttl(value: int | None) -> int:
    raw = LEASE_DEFAULT_TTL_SECONDS if value in (None, 0, -1) else int(value)
    return max(LEASE_MIN_TTL_SECONDS, min(raw, LEASE_MAX_TTL_SECONDS))


def _new_lease_id() -> str:
    return f"pml-{secrets.token_hex(12)}"


@contextmanager
def _file_guard(
    project_id: str,
    path: Path,
    *,
    timeout_seconds: float = LEASE_GUARD_TIMEOUT_SECONDS,
) -> Iterator[None]:
    init_project_layout(project_id)
    try:
        with cross_process_file_guard(path, timeout_seconds=timeout_seconds):
            yield
    except TimeoutError as exc:
        raise ProjectMutationAuthorityError(
            "PROJECT_MUTATION_GUARD_BUSY",
            "project mutation authority transition is busy",
            423,
            extra={"project_id": project_id},
        ) from exc


@contextmanager
def _project_guard(
    project_id: str, timeout_seconds: float = LEASE_GUARD_TIMEOUT_SECONDS
) -> Iterator[None]:
    """Short-lived lease-state lock. Kept under the historical helper name."""
    with _file_guard(project_id, _guard_path(project_id), timeout_seconds=timeout_seconds):
        yield


def _consequence_holder_snapshot(project_id: str) -> dict[str, Any]:
    path = _consequence_state_path(project_id)
    try:
        raw = load_json(path, None)
    except (OSError, ValueError, TypeError):
        raw = None
    if not isinstance(raw, dict):
        return {
            "active": False,
            "heartbeat_fresh": False,
            "holder_token": None,
            "holder_pid": None,
            "heartbeat_age_seconds": None,
            "heartbeat_sequence": 0,
        }
    now_epoch = time.time()
    try:
        heartbeat_epoch = float(raw.get("heartbeat_at_epoch"))
    except (TypeError, ValueError, OverflowError):
        heartbeat_epoch = 0.0
    age = max(0.0, now_epoch - heartbeat_epoch) if heartbeat_epoch > 0 else None
    fresh = age is not None and age <= float(CONSEQUENCE_HEARTBEAT_FRESH_SECONDS)
    result = dict(raw)
    result.update(
        {
            "active": bool(raw.get("holder_token")),
            "heartbeat_fresh": bool(fresh),
            "heartbeat_age_seconds": age,
            "heartbeat_sequence": int(raw.get("heartbeat_sequence") or 0),
        }
    )
    return result


def _write_consequence_holder_state(
    project_id: str,
    *,
    holder_token: str,
    acquired_at: str,
    acquired_at_epoch: float,
    heartbeat_sequence: int,
) -> None:
    now_epoch = time.time()
    payload = {
        "schema": CONSEQUENCE_HOLDER_SCHEMA,
        "authority_effect": "NONE",
        "project_id": project_id,
        "holder_token": holder_token,
        "holder_pid": os.getpid(),
        "holder_thread_id": threading.get_ident(),
        "acquired_at": acquired_at,
        "acquired_at_epoch": acquired_at_epoch,
        "heartbeat_at": utc_now(),
        "heartbeat_at_epoch": now_epoch,
        "heartbeat_sequence": int(heartbeat_sequence),
        "law": "CONSEQUENCE_HEARTBEAT != MUTATION_AUTHORITY",
    }
    save_json_atomic(_consequence_state_path(project_id), payload)


def _consequence_heartbeat_loop(
    project_id: str,
    holder_token: str,
    acquired_at: str,
    acquired_at_epoch: float,
    stop: threading.Event,
    state_barrier: threading.Lock,
) -> None:
    sequence = 1
    while not stop.wait(max(0.02, float(CONSEQUENCE_HEARTBEAT_INTERVAL_SECONDS))):
        # Snapshot + heartbeat write are serialized against teardown. Once teardown
        # acquires this barrier after stop.set(), no heartbeat may recreate state.
        with state_barrier:
            if stop.is_set():
                return
            current = _consequence_holder_snapshot(project_id)
            if str(current.get("holder_token") or "") != holder_token:
                return
            sequence += 1
            if stop.is_set():
                return
            try:
                _write_consequence_holder_state(
                    project_id,
                    holder_token=holder_token,
                    acquired_at=acquired_at,
                    acquired_at_epoch=acquired_at_epoch,
                    heartbeat_sequence=sequence,
                )
            except (OSError, ValueError, TypeError):
                # Coordination heartbeat failure cannot create or revoke authority.
                # The OS file lock remains the actual exclusion primitive.
                continue


def _clear_consequence_holder_state(project_id: str, holder_token: str) -> None:
    path = _consequence_state_path(project_id)
    current = _consequence_holder_snapshot(project_id)
    if str(current.get("holder_token") or "") != holder_token:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


@contextmanager
def _project_consequence_guard(
    project_id: str, timeout_seconds: float = LEASE_GUARD_TIMEOUT_SECONDS
) -> Iterator[None]:
    """Exclusive consequence lock with adaptive healthy-holder coordination.

    The OS file lock remains authoritative exclusion. A non-authoritative holder
    heartbeat lets waiters distinguish healthy occupancy from stale contention and
    extend a short base timeout without spinning or manufacturing authority. The
    heartbeat exists only while the lock is held and goes dormant on release.
    """
    project_id = validate_project_id(project_id)
    init_project_layout(project_id)
    path = _consequence_guard_path(project_id)
    started = time.monotonic()
    base_deadline = started + max(0.05, float(timeout_seconds))
    healthy_deadline = base_deadline
    max_healthy_deadline = started + max(
        float(timeout_seconds), float(CONSEQUENCE_HEALTHY_WAIT_MAX_SECONDS)
    )
    delay = float(CONSEQUENCE_WAIT_BACKOFF_INITIAL_SECONDS)
    guard_cm = None
    last_holder = _consequence_holder_snapshot(project_id)
    while True:
        now = time.monotonic()
        remaining = max(0.05, min(float(CONSEQUENCE_ACQUIRE_SLICE_SECONDS), max_healthy_deadline - now))
        candidate = cross_process_file_guard(path, timeout_seconds=remaining)
        try:
            candidate.__enter__()
            guard_cm = candidate
            break
        except TimeoutError as exc:
            now = time.monotonic()
            last_holder = _consequence_holder_snapshot(project_id)
            if bool(last_holder.get("heartbeat_fresh")) and now < max_healthy_deadline:
                healthy_deadline = min(
                    max_healthy_deadline,
                    max(healthy_deadline, now + float(CONSEQUENCE_HEARTBEAT_FRESH_SECONDS)),
                )
            effective_deadline = max(base_deadline, healthy_deadline)
            if now >= effective_deadline:
                raise ProjectMutationAuthorityError(
                    "PROJECT_MUTATION_GUARD_BUSY",
                    "project mutation consequence guard remains busy",
                    423,
                    extra={
                        "project_id": project_id,
                        "waited_seconds": max(0.0, now - started),
                        "healthy_wait_max_seconds": float(CONSEQUENCE_HEALTHY_WAIT_MAX_SECONDS),
                        "holder": last_holder,
                    },
                ) from exc
            time.sleep(min(delay, max(0.0, effective_deadline - now)))
            delay = min(delay * 2.0, float(CONSEQUENCE_WAIT_BACKOFF_MAX_SECONDS))
    assert guard_cm is not None
    holder_token = secrets.token_hex(12)
    acquired_at = utc_now()
    acquired_at_epoch = time.time()
    try:
        _write_consequence_holder_state(
            project_id,
            holder_token=holder_token,
            acquired_at=acquired_at,
            acquired_at_epoch=acquired_at_epoch,
            heartbeat_sequence=1,
        )
    except (OSError, ValueError, TypeError):
        pass
    stop = threading.Event()
    state_barrier = threading.Lock()
    heartbeat = threading.Thread(
        target=_consequence_heartbeat_loop,
        args=(project_id, holder_token, acquired_at, acquired_at_epoch, stop, state_barrier),
        name=f"pcmmad-mutation-heartbeat-{project_id}",
        daemon=True,
    )
    heartbeat.start()
    try:
        yield
    finally:
        stop.set()
        # Wait out any heartbeat write already in flight, then clear while holding
        # the same barrier. A delayed daemon heartbeat can no longer resurrect the
        # holder after consequence release.
        with state_barrier:
            _clear_consequence_holder_state(project_id, holder_token)
        heartbeat.join(timeout=max(0.1, float(CONSEQUENCE_HEARTBEAT_INTERVAL_SECONDS) * 2.5))
        guard_cm.__exit__(None, None, None)


def _lease_id_hash(lease_id: str) -> str:
    token = str(lease_id or "").strip()
    return hashlib.sha256(("pcmmad-project-mutation-v2:" + token).encode("utf-8")).hexdigest()


_CURRENT_MUTATION_BINDING: ContextVar[dict[str, Any] | None] = ContextVar(
    "pcmmad_current_project_mutation_binding", default=None
)
_CURRENT_MUTATION_AUTHORITY: ContextVar[dict[str, Any] | None] = ContextVar(
    "pcmmad_current_project_mutation_authority", default=None
)


def _binding_from_record(project_id: str, record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "generation": int(record.get("generation") or 0),
        "owner_id": str(record.get("owner_id") or ""),
        "session_id": str(record.get("session_id") or ""),
    }


def _compatibility_binding(project_id: str, session_id: str = "") -> dict[str, Any]:
    return {
        "project_id": project_id,
        "mode": "compatibility_no_lease",
        "generation": 0,
        "owner_id": "",
        "session_id": str(session_id or "").strip(),
    }


@contextmanager
def _raw_binding_context(binding: Mapping[str, Any]) -> Iterator[dict[str, Any]]:
    value = dict(binding)
    token = _CURRENT_MUTATION_BINDING.set(value)
    try:
        yield dict(value)
    finally:
        _CURRENT_MUTATION_BINDING.reset(token)


def current_mutation_binding(project_id: str = "") -> dict[str, Any] | None:
    binding = _CURRENT_MUTATION_BINDING.get()
    if not binding:
        return None
    if project_id and str(binding.get("project_id") or "") != str(project_id):
        return None
    return dict(binding)


def project_id_for_resolved_path(path: Path | str) -> str | None:
    resolved = Path(path).resolve()
    try:
        relative = resolved.relative_to(PROJECTS_ROOT.resolve())
    except ValueError:
        return None
    if not relative.parts:
        return None
    try:
        return validate_project_id(relative.parts[0])
    except ValueError:
        return None



def current_project_mutation_authority() -> dict[str, Any] | None:
    authority = _CURRENT_MUTATION_AUTHORITY.get()
    return dict(authority) if authority else None


@contextmanager
def project_mutation_authority_context(
    authority: Mapping[str, Any] | None,
) -> Iterator[None]:
    token = _CURRENT_MUTATION_AUTHORITY.set(dict(authority) if authority else None)
    try:
        yield
    finally:
        _CURRENT_MUTATION_AUTHORITY.reset(token)


@contextmanager
def resolved_paths_consequence_guard(
    paths: list[Path | str] | tuple[Path | str, ...],
    *,
    session_id: str = "",
    timeout_seconds: float = LEASE_GUARD_TIMEOUT_SECONDS,
) -> Iterator[dict[str, Any] | None]:
    project_ids = sorted(
        {pid for pid in (project_id_for_resolved_path(path) for path in paths) if pid}
    )
    if not project_ids:
        yield None
        return
    if len(project_ids) != 1:
        raise ProjectMutationAuthorityError(
            "CROSS_PROJECT_MUTATION_AUTHORITY_REQUIRED",
            "one mutation consequence cannot span multiple project ownership domains",
            409,
            extra={"project_ids": project_ids},
        )
    project_id = project_ids[0]
    with consequence_guard(
        project_id,
        mutation_authority=current_project_mutation_authority(),
        session_id=session_id,
        timeout_seconds=timeout_seconds,
    ) as receipt:
        yield receipt


@contextmanager
def _binding_context(project_id: str, record: Mapping[str, Any]) -> Iterator[dict[str, Any]]:
    binding = _binding_from_record(project_id, record)
    token = _CURRENT_MUTATION_BINDING.set(binding)
    try:
        yield dict(binding)
    finally:
        _CURRENT_MUTATION_BINDING.reset(token)


def _public(record: Mapping[str, Any] | None, project_id: str) -> dict[str, Any]:
    if not record:
        return {
            "project_id": project_id,
            "status": LEASE_STATUS_UNOWNED,
            "generation": 0,
            "lease_id": None,
            "owner_id": None,
            "session_id": None,
            "client_id": None,
            "issued_at": None,
            "renewed_at": None,
            "expires_at": None,
            "released_at": None,
            "provenance": None,
        }
    return {
        "project_id": project_id,
        "status": record.get("status"),
        "generation": int(record.get("generation") or 0),
        "lease_id": None,
        "owner_id": record.get("owner_id"),
        "session_id": record.get("session_id"),
        "client_id": record.get("client_id"),
        "issued_at": record.get("issued_at"),
        "renewed_at": record.get("renewed_at"),
        "expires_at": record.get("expires_at"),
        "released_at": record.get("released_at"),
        "provenance": record.get("provenance"),
    }


def _public_with_acquired_token(
    record: Mapping[str, Any], project_id: str, lease_id: str
) -> dict[str, Any]:
    payload = _public(record, project_id)
    payload["lease_id"] = lease_id
    return payload


def _write(project_id: str, record: dict[str, Any]) -> dict[str, Any]:
    body = dict(record)
    body["integrity_hash"] = _integrity_hash(body)
    save_json_atomic(_state_path(project_id), body)
    return body


def _validate_record_shape(project_id: str, row: Mapping[str, Any]) -> None:
    if str(row.get("store_version") or "") != LEASE_STORE_VERSION:
        raise ProjectMutationAuthorityError(
            "PROJECT_MUTATION_LEASE_INVALID",
            "project mutation lease store version is unsupported",
            500,
            extra={"project_id": project_id},
        )
    if str(row.get("project_id") or "") != project_id:
        raise ProjectMutationAuthorityError(
            "PROJECT_MUTATION_LEASE_INVALID",
            "project mutation lease belongs to another project",
            500,
            extra={"project_id": project_id},
        )
    status = str(row.get("status") or "")
    if status not in {LEASE_STATUS_ACTIVE, LEASE_STATUS_RELEASED, LEASE_STATUS_EXPIRED}:
        raise ProjectMutationAuthorityError(
            "PROJECT_MUTATION_LEASE_INVALID",
            "project mutation lease status is invalid",
            500,
            extra={"project_id": project_id, "status": status},
        )
    try:
        generation = int(row.get("generation"))
    except (TypeError, ValueError):
        generation = -1
    if generation < 1:
        raise ProjectMutationAuthorityError(
            "PROJECT_MUTATION_LEASE_INVALID",
            "project mutation lease generation is invalid",
            500,
            extra={"project_id": project_id},
        )
    if status == LEASE_STATUS_ACTIVE:
        lease_hash = str(row.get("lease_id_hash") or "").strip().lower()
        if (
            len(lease_hash) != 64
            or any(ch not in "0123456789abcdef" for ch in lease_hash)
            or not str(row.get("owner_id") or "").strip()
        ):
            raise ProjectMutationAuthorityError(
                "PROJECT_MUTATION_LEASE_INVALID",
                "active project mutation lease is missing hashed authority identity",
                500,
                extra={"project_id": project_id},
            )
        if _parse_time(row.get("expires_at")) is None:
            raise ProjectMutationAuthorityError(
                "PROJECT_MUTATION_LEASE_INVALID",
                "active project mutation lease expiry is invalid",
                500,
                extra={"project_id": project_id},
            )


def _load(project_id: str) -> dict[str, Any] | None:
    path = _state_path(project_id)
    if not path.is_file():
        return None
    row = load_json(path, None)
    if not isinstance(row, dict):
        raise ProjectMutationAuthorityError(
            "PROJECT_MUTATION_LEASE_INVALID",
            "project mutation lease record is malformed",
            500,
            extra={"project_id": project_id},
        )
    actual = str(row.get("integrity_hash") or "")
    expected = _integrity_hash(row)
    if not actual or actual != expected:
        raise ProjectMutationAuthorityError(
            "PROJECT_MUTATION_LEASE_INTEGRITY_INVALID",
            "project mutation lease integrity check failed",
            500,
            extra={"project_id": project_id},
        )
    if str(row.get("store_version") or "") == "1":
        legacy_token = str(row.get("lease_id") or "").strip()
        if not legacy_token:
            raise ProjectMutationAuthorityError(
                "PROJECT_MUTATION_LEASE_INVALID",
                "legacy project mutation lease is missing authority identity",
                500,
                extra={"project_id": project_id},
            )
        row = dict(row)
        row["store_version"] = LEASE_STORE_VERSION
        row["lease_id_hash"] = _lease_id_hash(legacy_token)
        row.pop("lease_id", None)
        row = _write(project_id, row)
    _validate_record_shape(project_id, row)
    return row


def _expire_if_needed(project_id: str, record: dict[str, Any] | None) -> dict[str, Any] | None:
    if not record or str(record.get("status") or "") != LEASE_STATUS_ACTIVE:
        return record
    expires_at = _parse_time(record.get("expires_at"))
    if expires_at is not None and _now() <= expires_at:
        return record
    record = dict(record)
    record["status"] = LEASE_STATUS_EXPIRED
    record["expired_at"] = utc_now()
    return _write(project_id, record)


def _with_consequence_observation(project_id: str, lease: dict[str, Any]) -> dict[str, Any]:
    result = dict(lease)
    result["consequence_guard"] = _consequence_holder_snapshot(project_id)
    return result


def observe_lease(project_id: str) -> dict[str, Any]:
    """Observe persisted lease and consequence occupancy without reconciling or writing."""
    return _with_consequence_observation(project_id, _public(_load(project_id), project_id))


def inspect_lease(project_id: str) -> dict[str, Any]:
    """Reconcile persisted expiry under the short-lived transition guard."""
    with _project_guard(project_id):
        record = _expire_if_needed(project_id, _load(project_id))
        return _with_consequence_observation(project_id, _public(record, project_id))


def acquire_lease(
    project_id: str,
    *,
    expected_generation: int,
    owner_id: str,
    session_id: str = "",
    client_id: str = "",
    ttl_seconds: int | None = None,
    provenance: str = "",
) -> dict[str, Any]:
    owner = str(owner_id or "").strip()
    if not owner:
        raise ProjectMutationAuthorityError(
            "PROJECT_MUTATION_OWNER_REQUIRED", "owner_id is required", 400
        )
    expected = int(expected_generation)
    if expected < 0:
        raise ProjectMutationAuthorityError(
            "PROJECT_MUTATION_GENERATION_INVALID", "expected_generation must be >= 0", 400
        )
    ttl = _bounded_ttl(ttl_seconds)
    with _project_consequence_guard(project_id):
        with _project_guard(project_id):
            current = _expire_if_needed(project_id, _load(project_id))
            generation = int(current.get("generation") or 0) if current else 0
            if expected != generation:
                raise ProjectMutationAuthorityError(
                    "PROJECT_MUTATION_GENERATION_STALE",
                    "expected project mutation generation is stale",
                    409,
                    extra={"current_lease": _public(current, project_id), "expected_generation": expected},
                )
            if current and str(current.get("status") or "") == LEASE_STATUS_ACTIVE:
                raise ProjectMutationAuthorityError(
                    "PROJECT_MUTATION_LEASE_BUSY",
                    "project already has an active mutation owner",
                    423,
                    extra={"current_lease": _public(current, project_id)},
                )
            now = _now()
            lease_id = _new_lease_id()
            record = {
                "store_version": LEASE_STORE_VERSION,
                "project_id": project_id,
                "status": LEASE_STATUS_ACTIVE,
                "generation": generation + 1,
                "lease_id_hash": _lease_id_hash(lease_id),
                "owner_id": owner,
                "session_id": str(session_id or "").strip() or None,
                "client_id": str(client_id or "").strip() or None,
                "issued_at": now.isoformat(),
                "renewed_at": now.isoformat(),
                "expires_at": (now + timedelta(seconds=ttl)).isoformat(),
                "released_at": None,
                "provenance": str(provenance or "").strip() or None,
            }
            written = _write(project_id, record)
            return _public_with_acquired_token(written, project_id, lease_id)


def _validate_active(
    project_id: str,
    record: dict[str, Any] | None,
    *,
    lease_id: str,
    generation: int,
    owner_id: str,
    session_id: str = "",
) -> dict[str, Any]:
    current = _expire_if_needed(project_id, record)
    if not current or str(current.get("status") or "") != LEASE_STATUS_ACTIVE:
        raise ProjectMutationAuthorityError(
            "PROJECT_MUTATION_LEASE_NOT_ACTIVE",
            "project has no active mutation lease",
            423,
            extra={"current_lease": _public(current, project_id)},
        )
    if int(current.get("generation") or 0) != int(generation):
        raise ProjectMutationAuthorityError(
            "PROJECT_MUTATION_LEASE_FENCED",
            "project mutation lease generation is no longer current",
            409,
            extra={"current_lease": _public(current, project_id)},
        )
    supplied_hash = _lease_id_hash(str(lease_id or ""))
    current_hash = str(current.get("lease_id_hash") or "")
    if not supplied_hash or not secrets.compare_digest(current_hash, supplied_hash):
        raise ProjectMutationAuthorityError(
            "PROJECT_MUTATION_LEASE_FENCED",
            "project mutation lease token is no longer current",
            409,
            extra={"current_lease": _public(current, project_id)},
        )
    owner = str(owner_id or "").strip()
    if not owner:
        raise ProjectMutationAuthorityError(
            "PROJECT_MUTATION_OWNER_REQUIRED",
            "owner_id is required to exercise project mutation authority",
            400,
            extra={"current_lease": _public(current, project_id)},
        )
    if str(current.get("owner_id") or "") != owner:
        raise ProjectMutationAuthorityError(
            "PROJECT_MUTATION_OWNER_MISMATCH",
            "project mutation lease belongs to another owner",
            403,
            extra={"current_lease": _public(current, project_id)},
        )
    expected_session = str(current.get("session_id") or "").strip()
    session = str(session_id or "").strip()
    if expected_session and session != expected_session:
        raise ProjectMutationAuthorityError(
            "PROJECT_MUTATION_SESSION_MISMATCH",
            "project mutation lease belongs to another session",
            403,
            extra={"current_lease": _public(current, project_id)},
        )
    return current


def renew_lease(
    project_id: str,
    *,
    lease_id: str,
    generation: int,
    owner_id: str,
    session_id: str = "",
    ttl_seconds: int | None = None,
) -> dict[str, Any]:
    ttl = _bounded_ttl(ttl_seconds)
    with _project_guard(project_id):
        current = _validate_active(
            project_id,
            _load(project_id),
            lease_id=lease_id,
            generation=generation,
            owner_id=owner_id,
            session_id=session_id,
        )
        now = _now()
        current = dict(current)
        current["renewed_at"] = now.isoformat()
        current["expires_at"] = (now + timedelta(seconds=ttl)).isoformat()
        return _public(_write(project_id, current), project_id)


def release_lease(
    project_id: str,
    *,
    lease_id: str,
    generation: int,
    owner_id: str,
    session_id: str = "",
) -> dict[str, Any]:
    with _project_consequence_guard(project_id):
        with _project_guard(project_id):
            current = _validate_active(
                project_id,
                _load(project_id),
                lease_id=lease_id,
                generation=generation,
                owner_id=owner_id,
                session_id=session_id,
            )
            current = dict(current)
            current["status"] = LEASE_STATUS_RELEASED
            current["released_at"] = utc_now()
            return _public(_write(project_id, current), project_id)


@contextmanager
def mutation_guard(
    project_id: str,
    *,
    lease_id: str,
    generation: int,
    owner_id: str = "",
    session_id: str = "",
    timeout_seconds: float = LEASE_GUARD_TIMEOUT_SECONDS,
) -> Iterator[dict[str, Any]]:
    """Hold cross-process consequence exclusion after short-lived lease validation."""
    with _project_consequence_guard(project_id, timeout_seconds=timeout_seconds):
        with _project_guard(project_id, timeout_seconds=timeout_seconds):
            current = _validate_active(
                project_id,
                _load(project_id),
                lease_id=lease_id,
                generation=generation,
                owner_id=owner_id,
                session_id=session_id,
            )
        with _binding_context(project_id, current):
            yield _public(current, project_id)


def _validate_runtime_binding(
    project_id: str,
    record: dict[str, Any] | None,
    binding: Mapping[str, Any],
    *,
    allow_expired_same_generation: bool = False,
) -> dict[str, Any]:
    current = _expire_if_needed(project_id, record)
    status = str(current.get("status") or "") if current else ""
    allowed_status = status == LEASE_STATUS_ACTIVE or (
        allow_expired_same_generation and status == LEASE_STATUS_EXPIRED
    )
    if not current or not allowed_status:
        raise ProjectMutationAuthorityError(
            "PROJECT_MUTATION_LEASE_NOT_ACTIVE",
            "project has no eligible mutation lease for bound runtime consequence",
            423,
            extra={"current_lease": _public(current, project_id)},
        )
    if int(current.get("generation") or 0) != int(binding.get("generation") or 0):
        raise ProjectMutationAuthorityError(
            "PROJECT_MUTATION_LEASE_FENCED",
            "bound runtime consequence generation is no longer current",
            409,
            extra={"current_lease": _public(current, project_id)},
        )
    if str(current.get("owner_id") or "") != str(binding.get("owner_id") or ""):
        raise ProjectMutationAuthorityError(
            "PROJECT_MUTATION_OWNER_MISMATCH",
            "bound runtime consequence belongs to another owner",
            403,
            extra={"current_lease": _public(current, project_id)},
        )
    expected_session = str(current.get("session_id") or "")
    bound_session = str(binding.get("session_id") or "")
    if expected_session and expected_session != bound_session:
        raise ProjectMutationAuthorityError(
            "PROJECT_MUTATION_SESSION_MISMATCH",
            "bound runtime consequence belongs to another session",
            403,
            extra={"current_lease": _public(current, project_id)},
        )
    return current


@contextmanager
def runtime_bound_mutation_guard(
    project_id: str,
    binding: Mapping[str, Any],
    *,
    timeout_seconds: float = LEASE_GUARD_TIMEOUT_SECONDS,
    allow_expired_same_generation: bool = False,
) -> Iterator[dict[str, Any]]:
    """Trusted Runtime continuation of a previously validated non-secret lease binding.

    This is for scheduler-authored durable worker continuations only. It deliberately
    cannot be exercised through an adapter authority envelope and never accepts a
    bearer token from a capability payload.
    """
    project_id = validate_project_id(project_id)
    if not isinstance(binding, Mapping) or str(binding.get("project_id") or "") != project_id:
        raise ProjectMutationAuthorityError(
            "PROJECT_MUTATION_BINDING_INVALID",
            "runtime mutation binding does not match project",
            400,
            extra={"project_id": project_id},
        )
    if str(binding.get("mode") or "") == "compatibility_no_lease":
        with _project_consequence_guard(project_id, timeout_seconds=timeout_seconds):
            with _project_guard(project_id, timeout_seconds=timeout_seconds):
                current = _expire_if_needed(project_id, _load(project_id))
                if current and str(current.get("status") or "") == LEASE_STATUS_ACTIVE:
                    raise ProjectMutationAuthorityError(
                        "PROJECT_MUTATION_AUTHORITY_REQUIRED",
                        "governed project mutation lease appeared before compatibility worker consequence",
                        423,
                        extra={"current_lease": _public(current, project_id)},
                    )
            with _raw_binding_context(binding):
                yield _public(current, project_id)
        return
    with _project_consequence_guard(project_id, timeout_seconds=timeout_seconds):
        with _project_guard(project_id, timeout_seconds=timeout_seconds):
            current = _validate_runtime_binding(
                project_id,
                _load(project_id),
                binding,
                allow_expired_same_generation=allow_expired_same_generation,
            )
        with _binding_context(project_id, current):
            yield _public(current, project_id)


def _authority_generation(value: object) -> int:
    try:
        generation = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ProjectMutationAuthorityError(
            "PROJECT_MUTATION_AUTHORITY_INVALID",
            "mutation authority generation must be an integer",
            400,
        ) from exc
    if generation < 1:
        raise ProjectMutationAuthorityError(
            "PROJECT_MUTATION_AUTHORITY_INVALID",
            "mutation authority generation must be >= 1",
            400,
        )
    return generation


def validate_consequence_authority(
    project_id: str,
    *,
    mutation_authority: Mapping[str, Any] | None = None,
    session_id: str = "",
    timeout_seconds: float = LEASE_GUARD_TIMEOUT_SECONDS,
) -> dict[str, Any] | None:
    """Validate current project mutation authority without holding the consequence lock.

    Intended only for two-phase recovery/control flows that must stop an existing
    consequence before entering the ordinary consequence guard.
    """
    project_id = validate_project_id(project_id)
    if isinstance(mutation_authority, Mapping):
        lease_id = str(mutation_authority.get("lease_id") or "").strip()
        owner_id = str(mutation_authority.get("owner_id") or "").strip()
        generation = _authority_generation(mutation_authority.get("generation"))
        if not lease_id or not owner_id or generation is None:
            raise ProjectMutationAuthorityError(
                "PROJECT_MUTATION_AUTHORITY_INVALID",
                "project mutation authority requires lease_id, generation, and owner_id",
                400,
                extra={"project_id": project_id},
            )
        authority_session_id = str(mutation_authority.get("session_id") or "").strip()
        with _project_guard(project_id, timeout_seconds=timeout_seconds):
            current = _validate_active(
                project_id,
                _load(project_id),
                lease_id=lease_id,
                generation=generation,
                owner_id=owner_id,
                session_id=authority_session_id,
            )
            return _public(current, project_id)
    with _project_guard(project_id, timeout_seconds=timeout_seconds):
        current = _expire_if_needed(project_id, _load(project_id))
        if current and str(current.get("status") or "") == LEASE_STATUS_ACTIVE:
            raise ProjectMutationAuthorityError(
                "PROJECT_MUTATION_AUTHORITY_REQUIRED",
                "active project mutation lease requires explicit fenced authority",
                423,
                extra={"current_lease": _public(current, project_id)},
            )
        return None


@contextmanager
def submission_mutation_binding(
    project_id: str,
    *,
    mutation_authority: Mapping[str, Any] | None = None,
    session_id: str = "",
    timeout_seconds: float = LEASE_GUARD_TIMEOUT_SECONDS,
) -> Iterator[dict[str, Any]]:
    """Validate mutation authority for durable enqueue without consequence exclusion.

    Queue admission is not itself the arbitrary-code consequence. This context takes
    only the short lease-state guard, derives the same non-secret durable binding the
    worker historically received, and never holds the project-wide consequence lock.
    The worker must revalidate that binding again before the real consequence.
    """
    project_id = validate_project_id(project_id)
    validated = validate_consequence_authority(
        project_id,
        mutation_authority=mutation_authority,
        session_id=session_id,
        timeout_seconds=timeout_seconds,
    )
    if validated is None:
        binding = _compatibility_binding(project_id, session_id=session_id)
    else:
        binding = _binding_from_record(project_id, validated)
    with _raw_binding_context(binding):
        yield dict(binding)


@contextmanager
def consequence_guard(
    project_id: str,
    *,
    mutation_authority: Mapping[str, Any] | None = None,
    session_id: str = "",
    timeout_seconds: float = LEASE_GUARD_TIMEOUT_SECONDS,
) -> Iterator[dict[str, Any] | None]:
    """Compose explicit fenced authority with backward-compatible session fencing.

    Explicit mutation authority is canonical. Legacy callers remain compatible only
    while no governed lease is active. Textual session identity never inherits an
    active lease. The cross-process consequence guard is held for the mutation.
    """
    project_id = validate_project_id(project_id)
    if mutation_authority is not None:
        if not isinstance(mutation_authority, Mapping):
            raise ProjectMutationAuthorityError(
                "PROJECT_MUTATION_AUTHORITY_INVALID",
                "mutation_authority must be an object",
                400,
                extra={"project_id": project_id},
            )
        lease_id = str(mutation_authority.get("lease_id") or "").strip()
        owner_id = str(mutation_authority.get("owner_id") or "").strip()
        if not lease_id or not owner_id:
            raise ProjectMutationAuthorityError(
                "PROJECT_MUTATION_AUTHORITY_INVALID",
                "mutation_authority requires lease_id and owner_id",
                400,
                extra={"project_id": project_id},
            )
        generation = _authority_generation(mutation_authority.get("generation"))
        with mutation_guard(
            project_id,
            lease_id=lease_id,
            generation=generation,
            owner_id=owner_id,
            session_id=str(mutation_authority.get("session_id") or "").strip(),
            timeout_seconds=timeout_seconds,
        ) as receipt:
            yield receipt
        return

    with compatibility_session_guard(
        project_id,
        session_id=str(session_id or "").strip(),
        timeout_seconds=timeout_seconds,
    ) as receipt:
        yield receipt


@contextmanager
def compatibility_session_guard(
    project_id: str,
    *,
    session_id: str,
    timeout_seconds: float = LEASE_GUARD_TIMEOUT_SECONDS,
) -> Iterator[dict[str, Any] | None]:
    """Backward-compatible guard: active leases fence legacy sessions; no lease means legacy behavior.

    This intentionally does not auto-acquire authority. Legacy callers remain usable
    only while no governed lease is active. Once a lease exists, textual session
    equality is insufficient: explicit lease_id/generation/owner authority is required.
    """
    with _project_consequence_guard(project_id, timeout_seconds=timeout_seconds):
        with _project_guard(project_id, timeout_seconds=timeout_seconds):
            current = _expire_if_needed(project_id, _load(project_id))
            if current and str(current.get("status") or "") == LEASE_STATUS_ACTIVE:
                raise ProjectMutationAuthorityError(
                    "PROJECT_MUTATION_AUTHORITY_REQUIRED",
                    "active project mutation lease requires explicit fenced authority",
                    423,
                    extra={"current_lease": _public(current, project_id)},
                )
        binding = _compatibility_binding(project_id, session_id)
        with _raw_binding_context(binding):
            yield None
