"""Persistent result-handle storage and preview boundary."""

from __future__ import annotations
from collections.abc import MutableMapping

import base64
import uuid
from pathlib import Path
from typing import Any

from .server_hardening import safe_json_dumps, safe_json_loads
from .shared_core import ensure_parent, get_project_root, sha256_bytes, sha256_file, utc_now, validate_project_id

JsonObject = MutableMapping[str, Any]


def _results_root(project_id: str) -> Path:
    validate_project_id(project_id)
    return get_project_root(project_id) / "system" / "lab" / "results"


def result_path(project_id: str, handle: str) -> Path:
    validate_project_id(project_id)
    clean_handle = (handle or "").strip()
    if not clean_handle:
        raise ValueError("handle is required")
    if "/" in clean_handle or "\\" in clean_handle:
        raise ValueError("handle must not include path separators")
    return _results_root(project_id) / f"{clean_handle}.json"


def store_result(
    project_id: str, payload: Any, *, label: str = "result", tool_name: str = ""
) -> JsonObject:
    handle = f"res-{uuid.uuid4().hex[:12]}"
    body = {
        "project_id": project_id,
        "handle": handle,
        "label": label,
        "tool_name": tool_name,
        "created_at": utc_now(),
        "payload": payload,
    }
    raw = safe_json_dumps(body).encode("utf-8")
    path = result_path(project_id, handle)
    ensure_parent(path)
    path.write_bytes(raw)
    return {
        "project_id": project_id,
        "handle": handle,
        "path": str(path),
        "bytes": len(raw),
        "sha256": sha256_bytes(raw),
        "label": label,
        "tool_name": tool_name,
        "created_at": body["created_at"],
    }


def get_result(project_id: str, handle: str) -> JsonObject:
    path = result_path(project_id, handle)
    if not path.exists():
        raise FileNotFoundError("result handle not found")
    return safe_json_loads(path.read_text(encoding="utf-8"))


def summarize_payload(payload: Any, *, preview_chars: int = 1200) -> JsonObject:
    raw = safe_json_dumps(payload)
    return {
        "type": type(payload).__name__,
        "chars": len(raw),
        "preview": raw[:preview_chars],
        "truncated": len(raw) > preview_chars,
    }


RESULT_INLINE_SAFE_BYTES = 12000
RESULT_RANGE_MAX_BYTES = 65536
RESULT_PREVIEW_MAX_CHARS = 4000


def result_metadata(project_id: str, handle: str) -> JsonObject:
    path = result_path(project_id, handle)
    if not path.exists():
        raise FileNotFoundError("result handle not found")
    raw = path.read_bytes()
    row = safe_json_loads(raw.decode("utf-8"))
    payload = row.get("payload") if isinstance(row, dict) else None
    return {
        "project_id": project_id,
        "handle": handle,
        "bytes": len(raw),
        "sha256": sha256_bytes(raw),
        "label": row.get("label") if isinstance(row, dict) else None,
        "tool_name": row.get("tool_name") if isinstance(row, dict) else None,
        "created_at": row.get("created_at") if isinstance(row, dict) else None,
        "payload_summary": summarize_payload(payload),
        "content_type": "application/json",
    }


def read_result_range(
    project_id: str,
    handle: str,
    *,
    offset_bytes: int = 0,
    length_bytes: int = 32768,
) -> JsonObject:
    path = result_path(project_id, handle)
    if not path.exists():
        raise FileNotFoundError("result handle not found")
    offset = max(0, int(offset_bytes))
    length = max(1, min(int(length_bytes), RESULT_RANGE_MAX_BYTES))
    total = path.stat().st_size
    if offset > total:
        offset = total
    with path.open("rb") as handle_file:
        handle_file.seek(offset)
        chunk = handle_file.read(length)
    raw_hash = sha256_file(path)
    return {
        "project_id": project_id,
        "handle": handle,
        "offset_bytes": offset,
        "length_bytes": len(chunk),
        "requested_length_bytes": length,
        "total_bytes": total,
        "next_offset_bytes": offset + len(chunk) if offset + len(chunk) < total else None,
        "eof": offset + len(chunk) >= total,
        "sha256": raw_hash,
        "content_type": "application/json",
        "encoding": "base64",
        "data_b64": base64.b64encode(chunk).decode("ascii"),
    }
