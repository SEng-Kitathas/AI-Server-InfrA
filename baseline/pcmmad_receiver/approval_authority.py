"""Target/argument-bound, short-lived approval challenge authority.

Approval is a runtime object, not a boolean tool argument.  A challenge is bound
against one current capability contract and one canonical argument payload.  It
is single-use by default and persists across receiver restart.

This module deliberately does not decide *which* capabilities require approval;
that remains lab policy.  It only creates, validates, consumes, and reports
approval authority objects.
"""
from __future__ import annotations

import hashlib
import json
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from shared_core import SYSTEM_ROOT, load_json, save_json_atomic, utc_now

APPROVAL_DEFAULT_TTL_SECONDS = 300
APPROVAL_MAX_TTL_SECONDS = 900
APPROVAL_STORE_VERSION = "1"
APPROVAL_STATUS_ACTIVE = "ACTIVE"
APPROVAL_STATUS_CONSUMED = "CONSUMED"
APPROVAL_STATUS_REVOKED = "REVOKED"
APPROVAL_STATUS_EXPIRED = "EXPIRED"

_LOCK = threading.RLock()
_TARGET_KEYS = (
    "project_id",
    "job_id",
    "path",
    "source_path",
    "target_path",
    "session_id",
    "ticket",
    "handle",
    "service",
    "service_id",
    "node_id",
    "repo",
    "artifact_id",
    "claim_id",
    "target",
    "target_id",
)
_AUTHORITY_ARGUMENT_KEYS = frozenset({"approval", "approval_handle", "authority"})


class ApprovalAuthorityError(RuntimeError):
    def __init__(self, error_code: str, message: str, *, extra: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.extra = dict(extra or {})


def _root() -> Path:
    return SYSTEM_ROOT / "lab" / "approvals"


def _path(handle: str) -> Path:
    clean = str(handle or "").strip()
    if not clean or "/" in clean or "\\" in clean or not clean.startswith("apr-"):
        raise ApprovalAuthorityError("APPROVAL_HANDLE_INVALID", "invalid approval handle")
    return _root() / f"{clean}.json"


def _canonical(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _canonical(value[k]) for k in sorted(value, key=lambda item: str(item))}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def canonical_arguments(arguments: Mapping[str, Any] | None) -> dict[str, Any]:
    source = dict(arguments or {})
    return _canonical({k: v for k, v in source.items() if k not in _AUTHORITY_ARGUMENT_KEYS})


def _digest(value: Any) -> str:
    raw = json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def arguments_digest(arguments: Mapping[str, Any] | None) -> str:
    return _digest(canonical_arguments(arguments))


def target_summary(arguments: Mapping[str, Any] | None) -> dict[str, Any]:
    canonical = canonical_arguments(arguments)
    return {key: canonical[key] for key in _TARGET_KEYS if key in canonical}


def _record_integrity_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    return {str(k): _canonical(v) for k, v in record.items() if k != "integrity_hash"}


def _integrity_hash(record: Mapping[str, Any]) -> str:
    return _digest(_record_integrity_payload(record))


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


def _write(record: dict[str, Any]) -> dict[str, Any]:
    body = dict(record)
    body["integrity_hash"] = _integrity_hash(body)
    save_json_atomic(_path(str(body["handle"])), body)
    return body


def _load(handle: str) -> dict[str, Any]:
    path = _path(handle)
    if not path.is_file():
        raise ApprovalAuthorityError("APPROVAL_NOT_FOUND", "approval challenge not found")
    row = load_json(path, None)
    if not isinstance(row, dict):
        raise ApprovalAuthorityError("APPROVAL_RECORD_INVALID", "approval challenge record is malformed")
    actual = str(row.get("integrity_hash") or "")
    expected = _integrity_hash(row)
    if not actual or actual != expected:
        raise ApprovalAuthorityError("APPROVAL_INTEGRITY_INVALID", "approval challenge integrity check failed")
    return row


def _spec_value(spec: Any, name: str, default: Any = None) -> Any:
    if hasattr(spec, name):
        return getattr(spec, name)
    if isinstance(spec, Mapping):
        return spec.get(name, default)
    return default


def create_challenge(
    spec: Any,
    arguments: Mapping[str, Any] | None,
    *,
    ttl_seconds: int = APPROVAL_DEFAULT_TTL_SECONDS,
    issuer_hint: str = "runtime-policy",
) -> dict[str, Any]:
    ttl = max(30, min(int(ttl_seconds), APPROVAL_MAX_TTL_SECONDS))
    now = _now()
    handle = f"apr-{uuid.uuid4().hex[:16]}"
    record = {
        "store_version": APPROVAL_STORE_VERSION,
        "handle": handle,
        "status": APPROVAL_STATUS_ACTIVE,
        "single_use": True,
        "capability_id": str(_spec_value(spec, "name", "")),
        "capability_version": str(_spec_value(spec, "capability_version", "1")),
        "schema_hash": str(_spec_value(spec, "schema_hash", "")),
        "contract_digest": str(_spec_value(spec, "contract_digest", "")),
        "arguments_digest": arguments_digest(arguments),
        "target": target_summary(arguments),
        "danger_tier": str(_spec_value(spec, "danger_tier", "medium")),
        "effect_traits": sorted(set(_spec_value(spec, "effect_traits", []) or [])),
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=ttl)).isoformat(),
        "issuer_hint": str(issuer_hint or "runtime-policy"),
        "consumed_at": None,
        "consumer": None,
        "revoked_at": None,
        "revocation_reason": None,
    }
    with _LOCK:
        return public_view(_write(record))


def public_view(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "handle": record.get("handle"),
        "status": record.get("status"),
        "single_use": bool(record.get("single_use", True)),
        "capability_id": record.get("capability_id"),
        "capability_version": record.get("capability_version"),
        "schema_hash": record.get("schema_hash"),
        "contract_digest": record.get("contract_digest"),
        "arguments_digest": record.get("arguments_digest"),
        "target": record.get("target") or {},
        "danger_tier": record.get("danger_tier"),
        "effect_traits": list(record.get("effect_traits") or []),
        "issued_at": record.get("issued_at"),
        "expires_at": record.get("expires_at"),
        "consumed_at": record.get("consumed_at"),
        "consumer": record.get("consumer"),
    }


def inspect_challenge(handle: str) -> dict[str, Any]:
    with _LOCK:
        record = _load(handle)
        expires_at = _parse_time(record.get("expires_at"))
        if record.get("status") == APPROVAL_STATUS_ACTIVE and expires_at is not None and _now() > expires_at:
            record["status"] = APPROVAL_STATUS_EXPIRED
            record = _write(record)
        return public_view(record)


def _mismatch(code: str, message: str, record: Mapping[str, Any], **extra: Any) -> None:
    raise ApprovalAuthorityError(code, message, extra={"approval": public_view(record), **extra})


def validate_and_consume(
    handle: str,
    spec: Any,
    arguments: Mapping[str, Any] | None,
    *,
    permit: bool,
    operator_id: str = "",
    provenance: str = "",
) -> dict[str, Any]:
    if permit is not True:
        raise ApprovalAuthorityError("APPROVAL_CONFIRMATION_REQUIRED", "approval handle requires explicit permit=true")
    with _LOCK:
        record = _load(handle)
        status = str(record.get("status") or "")
        expires_at = _parse_time(record.get("expires_at"))
        if status == APPROVAL_STATUS_ACTIVE and (expires_at is None or _now() > expires_at):
            record["status"] = APPROVAL_STATUS_EXPIRED
            record = _write(record)
            _mismatch("APPROVAL_EXPIRED", "approval challenge expired", record)
        if status == APPROVAL_STATUS_CONSUMED:
            _mismatch("APPROVAL_ALREADY_CONSUMED", "approval challenge is single-use and already consumed", record)
        if status == APPROVAL_STATUS_REVOKED:
            _mismatch("APPROVAL_REVOKED", "approval challenge has been revoked", record)
        if str(record.get("capability_id") or "") != str(_spec_value(spec, "name", "")):
            _mismatch("APPROVAL_CAPABILITY_MISMATCH", "approval challenge belongs to a different capability", record)
        current_contract = str(_spec_value(spec, "contract_digest", ""))
        if str(record.get("contract_digest") or "") != current_contract:
            _mismatch(
                "APPROVAL_CONTRACT_STALE",
                "approval challenge was issued against a different capability contract",
                record,
                current_contract_digest=current_contract,
            )
        current_args = arguments_digest(arguments)
        if str(record.get("arguments_digest") or "") != current_args:
            _mismatch(
                "APPROVAL_ARGUMENTS_MISMATCH",
                "approval challenge does not authorize these arguments/target",
                record,
                current_arguments_digest=current_args,
                current_target=target_summary(arguments),
            )
        record["status"] = APPROVAL_STATUS_CONSUMED
        record["consumed_at"] = utc_now()
        record["consumer"] = {
            "operator_id": str(operator_id or "").strip(),
            "provenance": str(provenance or "").strip(),
        }
        return public_view(_write(record))


def revoke_challenge(handle: str, reason: str = "") -> dict[str, Any]:
    with _LOCK:
        record = _load(handle)
        if record.get("status") == APPROVAL_STATUS_CONSUMED:
            _mismatch("APPROVAL_ALREADY_CONSUMED", "consumed approval cannot be revoked retroactively", record)
        record["status"] = APPROVAL_STATUS_REVOKED
        record["revoked_at"] = utc_now()
        record["revocation_reason"] = str(reason or "").strip()
        return public_view(_write(record))
