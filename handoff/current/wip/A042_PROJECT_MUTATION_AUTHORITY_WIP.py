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
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

from shared_core import (
    get_project_root,
    init_project_layout,
    load_json,
    save_json_atomic,
    utc_now,
    validate_project_id,
)

LEASE_STORE_VERSION = "1"
LEASE_DEFAULT_TTL_SECONDS = 120
LEASE_MIN_TTL_SECONDS = 10
LEASE_MAX_TTL_SECONDS = 900
LEASE_GUARD_TIMEOUT_SECONDS = 5.0

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
    return _control_root(project_id) / ".project_mutation_lease.guard"


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


def _lock_file_windows(handle: Any, *, blocking: bool) -> None:
    import msvcrt

    mode = msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK
    handle.seek(0)
    msvcrt.locking(handle.fileno(), mode, 1)


def _unlock_file_windows(handle: Any) -> None:
    import msvcrt

    handle.seek(0)
    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def _lock_file_posix(handle: Any, *, blocking: bool) -> None:
    import fcntl

    flags = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
    fcntl.flock(handle.fileno(), flags)


def _unlock_file_posix(handle: Any) -> None:
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def _project_guard(project_id: str, timeout_seconds: float = LEASE_GUARD_TIMEOUT_SECONDS) -> Iterator[None]:
    init_project_layout(project_id)
    path = _guard_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + max(0.05, float(timeout_seconds))
    with path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        acquired = False
        while not acquired:
            try:
                if os.name == "nt":
                    _lock_file_windows(handle, blocking=False)
                else:
                    _lock_file_posix(handle, blocking=False)
                acquired = True
            except (OSError, BlockingIOError):
                if time.monotonic() >= deadline:
                    raise ProjectMutationAuthorityError(
                        "PROJECT_MUTATION_GUARD_BUSY",
                        "project mutation authority transition is busy",
                        423,
                        extra={"project_id": project_id},
                    )
                time.sleep(0.01)
        try:
            yield
        finally:
            if os.name == "nt":
                _unlock_file_windows(handle)
            else:
                _unlock_file_posix(handle)


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
        "lease_id": record.get("lease_id"),
        "owner_id": record.get("owner_id"),
        "session_id": record.get("session_id"),
        "client_id": record.get("client_id"),
        "issued_at": record.get("issued_at"),
        "renewed_at": record.get("renewed_at"),
        "expires_at": record.get("expires_at"),
        "released_at": record.get("released_at"),
        "provenance": record.get("provenance"),
    }


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
        if not str(row.get("lease_id") or "").strip() or not str(row.get("owner_id") or "").strip():
            raise ProjectMutationAuthorityError(
                "PROJECT_MUTATION_LEASE_INVALID",
                "active project mutation lease is missing authority identity",
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


def inspect_lease(project_id: str) -> dict[str, Any]:
    with _project_guard(project_id):
        record = _expire_if_needed(project_id, _load(project_id))
        return _public(record, project_id)


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
        record = {
            "store_version": LEASE_STORE_VERSION,
            "project_id": project_id,
            "status": LEASE_STATUS_ACTIVE,
            "generation": generation + 1,
            "lease_id": _new_lease_id(),
            "owner_id": owner,
            "session_id": str(session_id or "").strip() or None,
            "client_id": str(client_id or "").strip() or None,
            "issued_at": now.isoformat(),
            "renewed_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=ttl)).isoformat(),
            "released_at": None,
            "provenance": str(provenance or "").strip() or None,
        }
        return _public(_write(project_id, record), project_id)


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
    if str(current.get("lease_id") or "") != str(lease_id or ""):
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
    """Hold cross-process exclusion for one governed mutation after fencing checks."""
    with _project_guard(project_id, timeout_seconds=timeout_seconds):
        current = _validate_active(
            project_id,
            _load(project_id),
            lease_id=lease_id,
            generation=generation,
            owner_id=owner_id,
            session_id=session_id,
        )
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


@contextmanager
def consequence_guard(
    project_id: str,
    *,
    mutation_authority: Mapping[str, Any] | None = None,
    session_id: str = "",
    timeout_seconds: float = LEASE_GUARD_TIMEOUT_SECONDS,
) -> Iterator[dict[str, Any] | None]:
    """Compose explicit fenced authority with backward-compatible session fencing.

    Explicit mutation authority is canonical.  Legacy callers remain compatible only
    while no governed lease blocks them, or when their session matches the lease's
    intentionally bound session.  The cross-process guard is held for the consequence.
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
    with _project_guard(project_id, timeout_seconds=timeout_seconds):
        current = _expire_if_needed(project_id, _load(project_id))
        if not current or str(current.get("status") or "") != LEASE_STATUS_ACTIVE:
            yield None
            return
        raise ProjectMutationAuthorityError(
            "PROJECT_MUTATION_AUTHORITY_REQUIRED",
            "active project mutation lease requires explicit fenced authority",
            423,
            extra={"current_lease": _public(current, project_id)},
        )
