"""Optional workload proof-of-possession for authenticated HTTP requests.

The existing receiver API key remains the outer compatibility boundary.  This
module adds an optional per-workload keyed proof which binds identity to one
exact request and rejects nonce replay.  It is intentionally not presented as
mTLS or asymmetric peer identity.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import shutil
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

PROOF_VERSION = "pcmmad-workload-proof-v1"
MODE_ENV = "PCMMAD_WORKLOAD_IDENTITY_MODE"
KEYS_ENV = "PCMMAD_WORKLOAD_KEYS_JSON"
ALLOWED_MODES = frozenset({"off", "optional", "required"})
DEFAULT_MODE = "optional"
MAX_CLOCK_SKEW_SECONDS = 300
REPLAY_BUCKET_SECONDS = 300
MIN_SECRET_BYTES = 32
MAX_SECRET_BYTES = 128
MAX_TARGET_CHARS = 8192
MAX_ID_CHARS = 128
MAX_NONCE_CHARS = 128
MIN_NONCE_CHARS = 20
IDENTITY_RE = re.compile(r"^[A-Za-z0-9._:@-]{1,128}$")
NONCE_RE = re.compile(r"^[A-Za-z0-9._~-]{20,128}$")
HEX_SIGNATURE_RE = re.compile(r"^[0-9a-fA-F]{64}$")

HEADER_WORKLOAD_ID = "X-PCMMAD-Workload-Id"
HEADER_KEY_ID = "X-PCMMAD-Workload-Key-Id"
HEADER_TIMESTAMP = "X-PCMMAD-Workload-Timestamp"
HEADER_NONCE = "X-PCMMAD-Workload-Nonce"
HEADER_SIGNATURE = "X-PCMMAD-Workload-Signature"
PROOF_HEADERS = (
    HEADER_WORKLOAD_ID,
    HEADER_KEY_ID,
    HEADER_TIMESTAMP,
    HEADER_NONCE,
    HEADER_SIGNATURE,
)


class WorkloadIdentityError(PermissionError):
    """Proof is missing, malformed, stale, unknown, invalid, or replayed."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


def _header(headers: Mapping[str, object], name: str) -> str:
    raw = headers.get(name, "")
    return raw if isinstance(raw, str) else str(raw or "")


def proof_headers_present(headers: Mapping[str, object]) -> bool:
    return any(bool(_header(headers, name).strip()) for name in PROOF_HEADERS)


def workload_identity_mode() -> str:
    mode = str(os.environ.get(MODE_ENV, DEFAULT_MODE) or DEFAULT_MODE).strip().lower()
    if mode not in ALLOWED_MODES:
        raise WorkloadIdentityError(
            "WORKLOAD_IDENTITY_CONFIG_INVALID",
            f"{MODE_ENV} must be one of {sorted(ALLOWED_MODES)}",
        )
    return mode


def _decode_secret(value: object) -> bytes:
    text = str(value or "").strip()
    if not text:
        raise ValueError("secret is empty")
    try:
        encoded = text.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("secret must be base64url ASCII") from exc
    padding = b"=" * ((4 - len(encoded) % 4) % 4)
    try:
        secret = base64.b64decode(encoded + padding, altchars=b"-_", validate=True)
    except Exception as exc:
        raise ValueError("secret must be strict base64url") from exc
    if len(secret) < MIN_SECRET_BYTES or len(secret) > MAX_SECRET_BYTES:
        raise ValueError(
            f"decoded secret must be between {MIN_SECRET_BYTES} and {MAX_SECRET_BYTES} bytes"
        )
    return secret


def _configured_keys(raw_json: str | None = None) -> dict[str, dict[str, bytes]]:
    raw = str(raw_json if raw_json is not None else os.environ.get(KEYS_ENV, "") or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise WorkloadIdentityError(
            "WORKLOAD_IDENTITY_CONFIG_INVALID", f"{KEYS_ENV} is not valid JSON"
        ) from exc
    if not isinstance(parsed, dict):
        raise WorkloadIdentityError(
            "WORKLOAD_IDENTITY_CONFIG_INVALID", f"{KEYS_ENV} must be an object"
        )
    result: dict[str, dict[str, bytes]] = {}
    try:
        for workload_id, kid_map in parsed.items():
            wid = str(workload_id or "").strip()
            if not IDENTITY_RE.fullmatch(wid):
                raise ValueError(f"invalid workload id: {wid!r}")
            if not isinstance(kid_map, dict) or not kid_map:
                raise ValueError(f"workload {wid!r} must map to one or more key ids")
            keys: dict[str, bytes] = {}
            for key_id, encoded_secret in kid_map.items():
                kid = str(key_id or "").strip()
                if not IDENTITY_RE.fullmatch(kid):
                    raise ValueError(f"invalid key id for workload {wid!r}: {kid!r}")
                keys[kid] = _decode_secret(encoded_secret)
            result[wid] = keys
    except ValueError as exc:
        raise WorkloadIdentityError("WORKLOAD_IDENTITY_CONFIG_INVALID", str(exc)) from exc
    return result


def canonical_target(path: str, query_string: bytes | str = b"") -> str:
    base = str(path or "").strip()
    if not base.startswith("/"):
        raise ValueError("request path must start with /")
    if isinstance(query_string, bytes):
        query = query_string.decode("latin-1")
    else:
        query = str(query_string or "")
    target = f"{base}?{query}" if query else base
    if len(target) > MAX_TARGET_CHARS or "\n" in target or "\r" in target:
        raise ValueError("request target is invalid or too long")
    return target


def canonical_proof_message(
    *,
    workload_id: str,
    key_id: str,
    timestamp: int,
    nonce: str,
    method: str,
    target: str,
    body_sha256: str,
) -> bytes:
    fields = (
        PROOF_VERSION,
        workload_id,
        key_id,
        str(int(timestamp)),
        nonce,
        str(method or "").upper(),
        target,
        body_sha256.lower(),
    )
    if any("\n" in field or "\r" in field for field in fields):
        raise ValueError("canonical proof fields may not contain newlines")
    return ("\n".join(fields) + "\n").encode("utf-8")


def sign_proof_for_test_or_client(
    secret: bytes,
    *,
    workload_id: str,
    key_id: str,
    timestamp: int,
    nonce: str,
    method: str,
    target: str,
    body: bytes,
) -> str:
    """Deterministic signing helper; no secret is persisted or returned."""
    body_sha256 = hashlib.sha256(body).hexdigest()
    message = canonical_proof_message(
        workload_id=workload_id,
        key_id=key_id,
        timestamp=timestamp,
        nonce=nonce,
        method=method,
        target=target,
        body_sha256=body_sha256,
    )
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def _validate_identity_token(value: str, field: str) -> str:
    text = value.strip()
    if not IDENTITY_RE.fullmatch(text):
        raise WorkloadIdentityError("WORKLOAD_IDENTITY_BAD_PROOF", f"invalid {field}")
    return text


def _parse_timestamp(value: str) -> int:
    try:
        parsed = int(value.strip())
    except (TypeError, ValueError, OverflowError) as exc:
        raise WorkloadIdentityError(
            "WORKLOAD_IDENTITY_BAD_PROOF", "invalid workload timestamp"
        ) from exc
    if parsed <= 0:
        raise WorkloadIdentityError("WORKLOAD_IDENTITY_BAD_PROOF", "invalid workload timestamp")
    return parsed


def _nonce(value: str) -> str:
    text = value.strip()
    if not NONCE_RE.fullmatch(text):
        raise WorkloadIdentityError(
            "WORKLOAD_IDENTITY_BAD_PROOF",
            f"nonce must be {MIN_NONCE_CHARS}-{MAX_NONCE_CHARS} URL-safe characters",
        )
    return text


def _signature(value: str) -> str:
    text = value.strip().lower()
    if not HEX_SIGNATURE_RE.fullmatch(text):
        raise WorkloadIdentityError(
            "WORKLOAD_IDENTITY_BAD_PROOF", "workload signature must be 64 hex characters"
        )
    return text


def _replay_token(workload_id: str, key_id: str, nonce: str) -> str:
    return hashlib.sha256(f"{workload_id}\0{key_id}\0{nonce}".encode("utf-8")).hexdigest()


def _reserve_nonce(
    replay_root: Path,
    *,
    workload_id: str,
    key_id: str,
    timestamp: int,
    nonce: str,
    accepted_at: int,
    method: str,
    target_sha256: str,
    request_body_sha256: str,
    proof_message_sha256: str,
) -> str:
    replay_root = Path(replay_root).resolve()
    bucket = int(timestamp) // REPLAY_BUCKET_SECONDS
    bucket_dir = replay_root / str(bucket)
    bucket_dir.mkdir(parents=True, exist_ok=True)
    token = _replay_token(workload_id, key_id, nonce)
    path = bucket_dir / f"{token}.json"
    payload = json.dumps(
        {
            "schema": "pcmmad.workload-proof-replay.v1",
            "workload_id": workload_id,
            "key_id": key_id,
            "timestamp": int(timestamp),
            "nonce_sha256": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
            "accepted_at": int(accepted_at),
            "method": str(method or "").upper(),
            "target_sha256": target_sha256,
            "request_body_sha256": request_body_sha256,
            "proof_message_sha256": proof_message_sha256,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8") + b"\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise WorkloadIdentityError(
            "WORKLOAD_IDENTITY_REPLAY", "workload proof nonce has already been used"
        ) from exc
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            path.unlink(missing_ok=True)
        finally:
            raise

    # Fixed-bucket cleanup avoids an unbounded historical directory scan on the
    # request hot path.  A bucket three intervals behind current time cannot
    # contain a proof within the configured +/- 300 second freshness window.
    current_bucket = int(accepted_at) // REPLAY_BUCKET_SECONDS
    stale_dir = replay_root / str(current_bucket - 3)
    if stale_dir != bucket_dir:
        shutil.rmtree(stale_dir, ignore_errors=True)
    return token


def verify_workload_proof(
    headers: Mapping[str, object],
    *,
    method: str,
    target: str,
    body: bytes,
    replay_root: Path,
    now_epoch: int | None = None,
    mode: str | None = None,
    keys_json: str | None = None,
) -> dict[str, Any] | None:
    effective_mode = str(mode or workload_identity_mode()).strip().lower()
    if effective_mode not in ALLOWED_MODES:
        raise WorkloadIdentityError(
            "WORKLOAD_IDENTITY_CONFIG_INVALID", f"invalid workload identity mode: {effective_mode}"
        )
    present = proof_headers_present(headers)
    if effective_mode == "off":
        if present:
            raise WorkloadIdentityError(
                "WORKLOAD_IDENTITY_DISABLED",
                "workload proof was supplied while workload identity verification is off",
            )
        return None
    if not present:
        if effective_mode == "required":
            raise WorkloadIdentityError(
                "WORKLOAD_IDENTITY_REQUIRED", "workload proof is required for this receiver"
            )
        return None

    values = {name: _header(headers, name).strip() for name in PROOF_HEADERS}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise WorkloadIdentityError(
            "WORKLOAD_IDENTITY_BAD_PROOF", "workload proof headers must be supplied as a complete set"
        )

    workload_id = _validate_identity_token(values[HEADER_WORKLOAD_ID], "workload id")
    key_id = _validate_identity_token(values[HEADER_KEY_ID], "key id")
    timestamp = _parse_timestamp(values[HEADER_TIMESTAMP])
    nonce = _nonce(values[HEADER_NONCE])
    supplied_signature = _signature(values[HEADER_SIGNATURE])
    now = int(time.time()) if now_epoch is None else int(now_epoch)
    skew = abs(now - timestamp)
    if skew > MAX_CLOCK_SKEW_SECONDS:
        raise WorkloadIdentityError(
            "WORKLOAD_IDENTITY_STALE",
            f"workload proof timestamp is outside the {MAX_CLOCK_SKEW_SECONDS}s freshness window",
        )

    keys = _configured_keys(keys_json)
    secret = keys.get(workload_id, {}).get(key_id)
    if secret is None:
        # Do not reveal whether the workload id or key id was unknown.
        raise WorkloadIdentityError(
            "WORKLOAD_IDENTITY_INVALID", "invalid workload identity proof"
        )

    if len(target) > MAX_TARGET_CHARS or "\n" in target or "\r" in target:
        raise WorkloadIdentityError("WORKLOAD_IDENTITY_BAD_PROOF", "invalid request target")
    body_sha256 = hashlib.sha256(body).hexdigest()
    try:
        message = canonical_proof_message(
            workload_id=workload_id,
            key_id=key_id,
            timestamp=timestamp,
            nonce=nonce,
            method=method,
            target=target,
            body_sha256=body_sha256,
        )
    except ValueError as exc:
        raise WorkloadIdentityError("WORKLOAD_IDENTITY_BAD_PROOF", str(exc)) from exc
    proof_message_sha256 = hashlib.sha256(message).hexdigest()
    expected_signature = hmac.new(secret, message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(supplied_signature, expected_signature):
        raise WorkloadIdentityError(
            "WORKLOAD_IDENTITY_INVALID", "invalid workload identity proof"
        )

    replay_token = _reserve_nonce(
        replay_root,
        workload_id=workload_id,
        key_id=key_id,
        timestamp=timestamp,
        nonce=nonce,
        accepted_at=now,
        method=method,
        target_sha256=hashlib.sha256(target.encode("utf-8")).hexdigest(),
        request_body_sha256=body_sha256,
        proof_message_sha256=proof_message_sha256,
    )
    return {
        "verified": True,
        "proof_version": PROOF_VERSION,
        "workload_id": workload_id,
        "key_id": key_id,
        "timestamp": timestamp,
        "clock_skew_seconds": now - timestamp,
        "nonce_sha256": hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
        "request_body_sha256": body_sha256,
        "proof_message_sha256": proof_message_sha256,
        "replay_token_sha256": replay_token,
    }
