"""Compact project-aware receiver access logging.

This module adds one bounded, transport-neutral access line per request. It is
observability only: project tags and job shorthands never grant authority and are
never used to route or validate a request.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
import time
from collections.abc import Mapping
from typing import Any

from flask import Flask, Response, g, request

ACCESS_LOGGER_NAME = "pcmmad.access"
ACCESS_BODY_INSPECT_MAX_BYTES = 128 * 1024
ACCESS_RESPONSE_INSPECT_MAX_BYTES = 64 * 1024
PROJECT_TAG_MAX_CHARS = 12
JOB_TAG_MAX_CHARS = 10

_PROJECT_TOKEN_RE = re.compile(r"[^A-Za-z0-9]+")
_KNOWN_PROJECT_PREFIXES: tuple[tuple[str, str], ...] = (
    ("PCMMAD", "PCMMAD"),
    ("RAHL", "RAHL"),
    ("FORGE", "FORGE"),
    ("CFE", "CFE"),
    ("MICROSEED", "MICROSEED"),
    ("OBE", "OBE"),
)


def _access_logger() -> logging.Logger:
    logger = logging.getLogger(ACCESS_LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def _load_aliases() -> dict[str, str]:
    raw = str(os.environ.get("PCMMAD_PROJECT_LOG_ALIASES_JSON", "")).strip()
    if not raw:
        return {}
    try:
        decoded = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}
    if not isinstance(decoded, dict):
        return {}
    aliases: dict[str, str] = {}
    for key, value in decoded.items():
        project_id = str(key).strip()
        alias = _sanitize_tag(str(value))
        if project_id and alias:
            aliases[project_id] = alias
    return aliases


def _sanitize_tag(value: str) -> str:
    cleaned = _PROJECT_TOKEN_RE.sub("-", str(value).strip()).strip("-").upper()
    return cleaned[:PROJECT_TAG_MAX_CHARS]


def project_log_tag(project_id: str | None, aliases: Mapping[str, str] | None = None) -> str:
    if project_id is None or not str(project_id).strip():
        return "GLOBAL"
    text = str(project_id).strip()
    alias_map = aliases or {}
    explicit = alias_map.get(text)
    if explicit:
        return _sanitize_tag(explicit) or "GLOBAL"
    upper = text.upper()
    for prefix, tag in _KNOWN_PROJECT_PREFIXES:
        if upper.startswith(prefix):
            return tag
    tokens = [token for token in _PROJECT_TOKEN_RE.split(text) if token]
    if not tokens:
        return "GLOBAL"
    first = _sanitize_tag(tokens[0])
    if len(first) <= PROJECT_TAG_MAX_CHARS and len(text) <= PROJECT_TAG_MAX_CHARS:
        return first
    # Long/ambiguous ids keep a human prefix plus stable collision suffix.
    digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:3].upper()
    prefix = (first or "PROJECT")[: max(1, PROJECT_TAG_MAX_CHARS - 4)]
    return f"{prefix}~{digest}"


def _collect_project_ids(value: Any, *, depth: int = 0, found: set[str] | None = None) -> set[str]:
    result = found if found is not None else set()
    if depth > 5 or len(result) > 8:
        return result
    if isinstance(value, dict):
        project_id = value.get("project_id")
        if isinstance(project_id, str) and project_id.strip():
            result.add(project_id.strip())
        for key in ("payload", "arguments", "plan", "steps", "nodes", "items"):
            if key in value:
                _collect_project_ids(value[key], depth=depth + 1, found=result)
    elif isinstance(value, list):
        for item in value[:32]:
            _collect_project_ids(item, depth=depth + 1, found=result)
    return result


def _collect_job_ids(value: Any, *, depth: int = 0, found: set[str] | None = None) -> set[str]:
    result = found if found is not None else set()
    if depth > 4 or len(result) > 4:
        return result
    if isinstance(value, dict):
        job_id = value.get("job_id")
        if isinstance(job_id, str) and job_id.strip():
            result.add(job_id.strip())
        for key in ("payload", "arguments", "result", "job"):
            if key in value:
                _collect_job_ids(value[key], depth=depth + 1, found=result)
    elif isinstance(value, list):
        for item in value[:16]:
            _collect_job_ids(item, depth=depth + 1, found=result)
    return result


def _bounded_json_request_body() -> Any | None:
    length = request.content_length
    if length is None or length <= 0 or length > ACCESS_BODY_INSPECT_MAX_BYTES:
        return None
    if not request.is_json:
        return None
    try:
        raw = request.get_data(cache=True, as_text=False)
    except Exception:
        return None
    if len(raw) > ACCESS_BODY_INSPECT_MAX_BYTES:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        return None


def _bounded_json_response_body(response: Response) -> Any | None:
    if response.is_streamed:
        return None
    length = response.calculate_content_length()
    if length is None or length <= 0 or length > ACCESS_RESPONSE_INSPECT_MAX_BYTES:
        return None
    if not response.is_json:
        return None
    try:
        return response.get_json(silent=True)
    except Exception:
        return None


def _short_job_tag(job_ids: set[str]) -> str | None:
    if not job_ids:
        return None
    if len(job_ids) > 1:
        return "MULTI"
    job_id = next(iter(job_ids))
    compact = job_id.removeprefix("job-")
    return _sanitize_tag(compact)[:JOB_TAG_MAX_CHARS] or None


def _request_project_tag() -> tuple[str, set[str]]:
    project_ids: set[str] = set()
    for source in (request.view_args or {}, request.args):
        candidate = source.get("project_id") if hasattr(source, "get") else None
        if isinstance(candidate, str) and candidate.strip():
            project_ids.add(candidate.strip())
    header_project = request.headers.get("X-PCMMAD-Project")
    if header_project and header_project.strip():
        project_ids.add(header_project.strip())
    body = _bounded_json_request_body()
    if body is not None:
        _collect_project_ids(body, found=project_ids)
    if len(project_ids) > 1:
        return "MULTI", project_ids
    project_id = next(iter(project_ids)) if project_ids else None
    aliases = g.get("_pcmmad_access_aliases", {})
    return project_log_tag(project_id, aliases), project_ids


def install_access_logging(app: Flask) -> None:
    """Install one compact project-aware access line per Flask request."""

    enabled = str(os.environ.get("PCMMAD_ACCESS_LOG", "1")).strip().lower()
    if enabled in {"0", "false", "no", "off"}:
        return
    aliases = _load_aliases()
    logger = _access_logger()

    @app.before_request
    def _pcmmad_access_start() -> None:
        g._pcmmad_access_started = time.perf_counter()
        g._pcmmad_access_aliases = aliases
        tag, project_ids = _request_project_tag()
        g._pcmmad_access_project_tag = tag
        g._pcmmad_access_project_ids = tuple(sorted(project_ids))

    @app.after_request
    def _pcmmad_access_finish(response: Response) -> Response:
        started = float(getattr(g, "_pcmmad_access_started", time.perf_counter()))
        elapsed_ms = max(0.0, (time.perf_counter() - started) * 1000.0)
        tag = str(getattr(g, "_pcmmad_access_project_tag", "GLOBAL") or "GLOBAL")
        request_body = _bounded_json_request_body()
        job_ids: set[str] = set()
        if request_body is not None:
            _collect_job_ids(request_body, found=job_ids)
        response_body = _bounded_json_response_body(response)
        if response_body is not None:
            _collect_job_ids(response_body, found=job_ids)
        job_tag = _short_job_tag(job_ids)
        job_segment = f" [job:{job_tag}]" if job_tag else ""
        logger.info(
            "[%s]%s %s %s %s %.1fms",
            tag,
            job_segment,
            request.method,
            request.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    # The canonical access line above supersedes Flask/Werkzeug's duplicate request
    # line in development mode. Errors remain visible.
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
