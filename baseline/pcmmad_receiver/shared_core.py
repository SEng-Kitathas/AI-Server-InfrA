"""Shared project-root, mount, artifact, hash, and JSONL boundary primitives."""

from __future__ import annotations

import hashlib
import json as _json
import os
import re
import secrets
import tempfile
import time
from datetime import datetime, timezone
from types import MappingProxyType
from pathlib import Path
from collections.abc import Mapping
from typing import Any

from workload_identity import (
    WorkloadIdentityError,
    canonical_target as workload_canonical_target,
    proof_headers_present as workload_proof_headers_present,
    verify_workload_proof,
    workload_identity_mode,
)

_DEFAULT_ROOT = Path.home() / "Desktop" / "AI_Pushes_Sandbox"
ROOT = Path(os.environ.get("PCMMAD_ROOT", str(_DEFAULT_ROOT))).resolve()
PROJECTS_ROOT = Path(os.environ.get("PCMMAD_PROJECTS_ROOT", str(ROOT / "projects"))).resolve()
SYSTEM_ROOT = Path(os.environ.get("PCMMAD_SYSTEM_ROOT", str(ROOT / "system"))).resolve()
SANDBOX_ROOT = Path(os.environ.get("PCMMAD_SANDBOX_ROOT", str(ROOT / "sandbox"))).resolve()
TEMP_ROOT = Path(
    os.environ.get("PCMMAD_TEMP_ROOT", str(Path(tempfile.gettempdir()) / "pcmmad_lab"))
).resolve()

SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9._ -]+$")
SAFE_PROJECT_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
MOUNT_SPEC_RE = re.compile(r"^(?P<mount>[A-Za-z0-9._-]+)://(?P<subpath>.*)$")

ALLOWED_OPERATIONS = frozenset({"create", "update", "append"})
APPEND_ALLOWED_CLASSES = frozenset({"continuity.design_thread_stream", "notes.maintenance"})

TEXT_EXTENSIONS = frozenset(
    {
        ".md",
        ".txt",
        ".json",
        ".py",
        ".yaml",
        ".yml",
        ".toml",
        ".log",
        ".ini",
        ".cfg",
        ".csv",
        ".tsv",
        ".xml",
        ".html",
        ".css",
        ".js",
        ".sql",
    }
)
MODEL_EXTENSIONS = frozenset({".safetensors", ".gguf", ".onnx", ".bin", ".pt", ".pth"})
ARCHIVE_EXTENSIONS = frozenset({".zip", ".tar", ".tgz", ".gz", ".7z"})

BASE_DIRS = (
    "continuity/live_shadow",
    "continuity/design_thread_stream",
    "continuity/research_epistemic_shadow",
    "continuity/research_epistemic_shadow/addenda",
    "state/current",
    "state/next_steps",
    "state/doctrine_snapshot",
    "state/revisit_ledger",
    "state/trace_matrix",
    "notes/maintenance",
    "code",
    "checkpoints",
    "system/manifest",
    "system/ledger",
    "system/protocol",
    "system/logs",
    "system/logs/execution",
    "system/journal",
    "system/lab",
    "system/lab/sessions",
    "system/lab/reflexion",
    "system/lab/andon",
    "system/lab/procedures",
    "system/lab/results",
    "system/lab/corpora",
    "data",
    "research",
    "lab_plugins",
)

ARTIFACT_RELATIVE_MAP = MappingProxyType(
    {
        "continuity.live_shadow": Path("continuity/live_shadow"),
        "continuity.design_thread_stream": Path("continuity/design_thread_stream"),
        "continuity.research_epistemic_shadow": Path("continuity/research_epistemic_shadow"),
        "continuity.checkpoint": Path("checkpoints"),
        "state.current": Path("state/current"),
        "state.next_steps": Path("state/next_steps"),
        "state.doctrine_snapshot": Path("state/doctrine_snapshot"),
        "state.revisit_ledger": Path("state/revisit_ledger"),
        "state.trace_matrix": Path("state/trace_matrix"),
        "notes.maintenance": Path("notes/maintenance"),
        "code": Path("code"),
    }
)


def parse_json_boundary(raw: str) -> Any:
    return _json.loads(raw)


def render_json_boundary(data: Any) -> str:
    return _json.dumps(data, ensure_ascii=False, indent=2)


def render_jsonl_boundary(data: Any) -> str:
    return _json.dumps(data, ensure_ascii=False)


def _mount_override_item(name: object, path: object) -> tuple[str, Path] | None:
    if not isinstance(name, str) or not isinstance(path, str) or not path.strip():
        return None
    return name, Path(path).expanduser().resolve()


def _apply_mount_override_item(mounts: dict[str, Path], name: object, path: object) -> None:
    item = _mount_override_item(name, path)
    if item is None:
        return
    mounts[item[0]] = item[1]


def _parse_mount_overrides() -> dict[str, Path]:
    mounts = {
        "root": ROOT,
        "projects": PROJECTS_ROOT,
        "system": SYSTEM_ROOT,
        "sandbox": SANDBOX_ROOT,
        "temp": TEMP_ROOT,
        "cwd": Path.cwd().resolve(),
    }
    raw = os.environ.get("PCMMAD_MOUNTS_JSON", "").strip()
    if raw:
        try:
            parsed = parse_json_boundary(raw)
            if isinstance(parsed, dict):
                for name, path in parsed.items():
                    _apply_mount_override_item(mounts, name, path)
        except (TypeError, ValueError, OSError, _json.JSONDecodeError):
            return mounts
    return mounts


_BOOTSTRAP_SKIPPED_PATHS: list[str] = []

MOUNT_TABLE = _parse_mount_overrides()
for _path in {ROOT, PROJECTS_ROOT, SYSTEM_ROOT, SANDBOX_ROOT, TEMP_ROOT, *MOUNT_TABLE.values()}:
    try:
        _path.mkdir(parents=True, exist_ok=True)
    except OSError:
        _BOOTSTRAP_SKIPPED_PATHS.append(str(_path))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def ensure_safe_mutation_target_identity(path: Path) -> None:
    """Reject existing multiply-linked regular files before mutation.

    Path containment proves namespace location, not inode ownership. A project-
    local hardlink can share an inode with data outside the declared boundary.
    Mutating such a pathname would escape the intended consequence scope.
    """
    if not path.exists():
        return
    try:
        stat_result = path.stat()
    except OSError as exc:
        raise ValueError(f"could not inspect mutation target identity: {exc}") from exc
    if path.is_file() and int(getattr(stat_result, "st_nlink", 1)) > 1:
        raise ValueError(
            f"multiply-linked mutation target is not uniquely owned by this pathname (link_count={stat_result.st_nlink})"
        )


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return parse_json_boundary(path.read_text(encoding="utf-8"))


_ATOMIC_REPLACE_RETRY_SECONDS = 0.75
_ATOMIC_REPLACE_RETRY_INITIAL_DELAY_SECONDS = 0.002
_ATOMIC_REPLACE_RETRY_MAX_DELAY_SECONDS = 0.05
_ATOMIC_REPLACE_TRANSIENT_WINERRORS = frozenset({5, 32, 33})


def _atomic_replace_transient(exc: OSError) -> bool:
    winerror = getattr(exc, "winerror", None)
    if winerror in _ATOMIC_REPLACE_TRANSIENT_WINERRORS:
        return True
    # PermissionError maps common sharing/access violations to EACCES on Python/Windows.
    return isinstance(exc, PermissionError) and os.name == "nt"


def save_json_atomic(path: Path, data: Any) -> None:
    ensure_parent(path)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8") as tmp:
            tmp.write(render_json_boundary(data))
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = Path(tmp.name)
        deadline = time.monotonic() + _ATOMIC_REPLACE_RETRY_SECONDS
        delay = _ATOMIC_REPLACE_RETRY_INITIAL_DELAY_SECONDS
        while True:
            try:
                tmp_path.replace(path)
                return
            except OSError as exc:
                if not _atomic_replace_transient(exc) or time.monotonic() >= deadline:
                    raise
                time.sleep(delay)
                delay = min(delay * 2.0, _ATOMIC_REPLACE_RETRY_MAX_DELAY_SECONDS)
    finally:
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def _json_ready(value: Any) -> Any:
    if hasattr(value, "to_dict") and callable(getattr(value, "to_dict")):
        return value.to_dict()
    return value


def append_jsonl(path: Path, record: Any) -> None:
    ensure_parent(path)
    payload = _json_ready(record)
    with path.open("a", encoding="utf-8") as f:
        f.write(render_jsonl_boundary(payload) + "\n")
        f.flush()
        os.fsync(f.fileno())


_WINDOWS_RESERVED_COMPONENT_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
)


def validate_filesystem_component_id(value: str, *, field: str) -> str:
    text = str(value or "").strip()
    if not text or text in {".", ".."}:
        raise ValueError(f"{field} is empty or aliases a parent/current directory")
    if text.endswith((".", " ")):
        raise ValueError(f"{field} has a trailing dot/space filesystem alias")
    if any(ch in text for ch in '<>:"/\\|?*'):
        raise ValueError(f"{field} contains a Windows-reserved path character")
    stem = text.rstrip(". ").split(".", 1)[0].upper()
    if stem in _WINDOWS_RESERVED_COMPONENT_NAMES:
        raise ValueError(f"{field} is a reserved Windows device name")
    return text


def validate_project_id(project_id: str) -> str:
    if not project_id:
        raise ValueError("project_id is required")
    if not SAFE_PROJECT_RE.fullmatch(project_id):
        raise ValueError("project_id contains invalid characters")
    validate_filesystem_component_id(project_id, field="project_id")
    return project_id


def get_mount_table() -> dict[str, Path]:
    return dict(MOUNT_TABLE)


def get_mount_roots() -> list[Path]:
    return list(dict.fromkeys(path.resolve() for path in MOUNT_TABLE.values()))


def mount_summary() -> list[dict[str, str]]:
    return [{"name": name, "path": str(path)} for name, path in sorted(MOUNT_TABLE.items())]


def resolve_mount_spec(
    path_spec: str | None, *, default_root: Path | None = None, allow_absolute: bool = True
) -> Path:
    raw = (path_spec or ".").strip()
    match = MOUNT_SPEC_RE.match(raw)
    if match:
        mount = match.group("mount")
        subpath = match.group("subpath")
        base = MOUNT_TABLE.get(mount)
        if base is None:
            raise ValueError(f"unknown mount: {mount}")
        return (base / subpath).resolve()
    candidate = Path(raw).expanduser()
    if candidate.is_absolute():
        if not allow_absolute:
            raise ValueError("absolute paths are not allowed here")
        return candidate.resolve()
    if default_root is None:
        default_root = ROOT
    return (default_root / candidate).resolve()


def get_project_root(project_id: str) -> Path:
    pid = validate_project_id(project_id)
    projects_root = PROJECTS_ROOT.resolve()
    if projects_root.exists():
        try:
            for child in projects_root.iterdir():
                if child.name.casefold() == pid.casefold() and child.name != pid:
                    raise ValueError(
                        f"project_id case conflicts with existing filesystem identity: requested={pid!r} existing={child.name!r}"
                    )
        except OSError as exc:
            raise ValueError(f"could not inspect project namespace identity: {exc}") from exc
    root = (projects_root / pid).resolve()
    if projects_root not in [root, *root.parents]:
        raise ValueError("project root escaped projects root")
    return root


def init_project_layout(project_id: str) -> Path:
    root = get_project_root(project_id)
    root.mkdir(parents=True, exist_ok=True)
    for rel in BASE_DIRS:
        (root / rel).mkdir(parents=True, exist_ok=True)
    return root


def manifest_path_for(project_id: str) -> Path:
    return get_project_root(project_id) / "system" / "manifest" / "manifest.json"


def commits_ledger_path_for(project_id: str) -> Path:
    return get_project_root(project_id) / "system" / "ledger" / "commits.jsonl"


def idempotency_path_for(project_id: str) -> Path:
    return get_project_root(project_id) / "system" / "ledger" / "idempotency.json"


def journal_path_for(project_id: str) -> Path:
    return get_project_root(project_id) / "system" / "journal" / "journal.jsonl"


def validate_logical_name(name: str) -> str:
    if not name:
        raise ValueError("logical_name is required")
    if "/" in name or "\\" in name:
        raise ValueError("logical_name must not include path separators")
    if not SAFE_NAME_RE.fullmatch(name):
        raise ValueError("logical_name contains invalid characters")
    return name


def resolve_target(project_id: str, artifact_class: str, logical_name: str) -> Path:
    root = get_project_root(project_id)
    if artifact_class not in ARTIFACT_RELATIVE_MAP:
        raise ValueError(f"Unknown artifact_class: {artifact_class}")
    target = (
        root / ARTIFACT_RELATIVE_MAP[artifact_class] / validate_logical_name(logical_name)
    ).resolve()
    if root.resolve() not in [target, *target.parents]:
        raise ValueError("resolved path escaped project root")
    return target


def require_valid_api_key(headers: Mapping[str, object]) -> None:
    """Require bearer auth and, when configured/supplied, workload proof.

    The API key remains the compatibility boundary.  Workload proof is additive:
    optional mode preserves hosted callers that only possess the receiver key,
    while required mode is an explicit operator choice.
    """

    expected = os.environ.get("GITHOME_API_KEY", "").strip()
    raw_provided = headers.get("X-GitHome-Key", "")
    provided = raw_provided if isinstance(raw_provided, str) else str(raw_provided)
    if not expected or not provided or not secrets.compare_digest(provided, expected):
        raise PermissionError("Invalid or missing API key")

    try:
        mode = workload_identity_mode()
        proof_present = workload_proof_headers_present(headers)
    except WorkloadIdentityError as exc:
        raise PermissionError(f"{exc.error_code}: {exc.message}") from exc

    # Preserve non-HTTP/internal compatibility unless the caller explicitly asks
    # for workload verification or the operator configured proof as mandatory.
    try:
        from flask import g, has_request_context, request
    except ImportError:  # pragma: no cover - Flask is a receiver dependency
        if proof_present or mode == "required":
            raise PermissionError("Workload identity verification requires HTTP request context")
        return

    if not has_request_context():
        if proof_present or mode == "required":
            raise PermissionError("Workload identity verification requires HTTP request context")
        return

    if not proof_present and mode == "optional":
        setattr(g, "pcmmad_workload_identity", None)
        return

    try:
        target = workload_canonical_target(request.path, request.query_string)
        body = request.get_data(cache=True, as_text=False) if proof_present else b""
        identity = verify_workload_proof(
            headers,
            method=request.method,
            target=target,
            body=body,
            replay_root=TEMP_ROOT / "workload_identity",
            mode=mode,
        )
    except (WorkloadIdentityError, ValueError) as exc:
        if isinstance(exc, WorkloadIdentityError):
            raise PermissionError(f"{exc.error_code}: {exc.message}") from exc
        raise PermissionError(f"WORKLOAD_IDENTITY_BAD_PROOF: {exc}") from exc
    setattr(g, "pcmmad_workload_identity", identity)


CAPABILITY_FLAGS = MappingProxyType(
    {
        "project_routes": True,
        "legacy_routes": True,
        "research": True,
        "context": True,
        "model_inventory": True,
        "archive_inventory": True,
        "archive_extract": True,
        "journal": True,
        "checkpoints": True,
        "partial_traversal_reporting": True,
        "rehydrate_debug": True,
        "execution": True,
        "execution_register": True,
        "execution_replay": True,
        "sync_exec": True,
        "python_exec": True,
        "file_tree": True,
        "zip_read": True,
        "lab_router": True,
        "lab_batch": True,
        "lab_sessions": True,
        "approval_gates": True,
        "workload_identity_proof": True,
        "user_continuity_memory": True,
        "plugin_autoload": True,
        "git_ops": True,
        "web_fetch": True,
        "verify_gates": True,
        "mount_table": True,
        "filesystem_tools": True,
        "browser_bridge_proxy": True,
        "result_handles": True,
        "mcp_manifest": True,
        "protocol_state": True,
        "protocol_hash_chain": True,
        "protocol_promotion": True,
        "protocol_waivers": True,
    }
)


def capabilities() -> dict[str, bool]:
    return dict(CAPABILITY_FLAGS)
