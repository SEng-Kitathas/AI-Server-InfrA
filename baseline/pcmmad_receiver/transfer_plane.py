"""PCMMAD Transfer Plane V1: bounded, resumable, ticket-scoped binary transport."""
from __future__ import annotations
import base64, hashlib, json, os, secrets, tempfile, threading, time
from pathlib import Path
from typing import Any, Callable
from flask import Blueprint, jsonify, request, send_file
from .shared_core import get_mount_roots, get_project_root, resolve_mount_spec, utc_now, require_valid_api_key
from .lab_errors import LabToolError
from .project_mutation_authority import (
    ProjectMutationAuthorityError,
    project_id_for_resolved_path,
    resolved_paths_consequence_guard,
)

transfer_bp = Blueprint("transfer", __name__, url_prefix="/transfer")
_STATE = Path(tempfile.gettempdir()) / "pcmmad_transfer_plane_v1"
_STATE.mkdir(parents=True, exist_ok=True)
_LOCK = threading.RLock()
DEFAULT_TTL = 1800
MAX_TTL = 86400
DEFAULT_CHUNK = 16 * 1024
MAX_CHUNK = 256 * 1024


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def _within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _allowed(path: Path) -> Path:
    p = path.resolve()
    roots = [r.resolve() for r in get_mount_roots()]
    if not any(_within(p, r) for r in roots):
        raise ValueError("resolved path escapes mounted roots")
    return p


def _resolve(raw: str, project_id: str | None = None) -> Path:
    if not raw:
        raise ValueError("path is required")
    project_root = get_project_root(project_id).resolve() if project_id else None
    candidate = _allowed(
        resolve_mount_spec(raw, default_root=project_root, allow_absolute=True)
    )
    if project_root is not None and not _within(candidate, project_root):
        raise ValueError("resolved path escapes project transfer scope")
    return candidate


def _mp(ticket: str) -> Path:
    if len(ticket) != 64 or any(c not in "0123456789abcdef" for c in ticket):
        raise FileNotFoundError("invalid transfer ticket")
    return _STATE / f"{ticket}.json"


def _manifest_digest(obj: dict[str, Any]) -> str:
    body = {k: v for k, v in obj.items() if k != "manifest_sha256"}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _save(obj: dict[str, Any]) -> None:
    obj["manifest_sha256"] = _manifest_digest(obj)
    p = _mp(obj["ticket"]); tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, sort_keys=True, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def _load(ticket: str) -> dict[str, Any]:
    p = _mp(ticket)
    if not p.is_file():
        raise FileNotFoundError("transfer ticket not found")
    obj = json.loads(p.read_text("utf-8"))
    actual_manifest = str(obj.get("manifest_sha256") or "")
    expected_manifest = _manifest_digest(obj)
    if not actual_manifest or actual_manifest != expected_manifest:
        raise ValueError("transfer ticket manifest integrity check failed")
    if time.time() > float(obj["expires_epoch"]):
        raise TimeoutError("transfer ticket expired")
    return obj


def _public(obj: dict[str, Any]) -> dict[str, Any]:
    keys = ("ticket","direction","created_at","expires_at","project_id","name","size","sha256","offset","complete","chunk_bytes","manifest_sha256")
    return {k: obj.get(k) for k in keys if k in obj}


def create_export(path: str, project_id: str | None = None, ttl_seconds: int = DEFAULT_TTL, chunk_bytes: int = DEFAULT_CHUNK) -> dict[str, Any]:
    src = _resolve(path, project_id)
    if not src.is_file():
        raise FileNotFoundError("source file not found")
    ttl = max(60, min(int(ttl_seconds), MAX_TTL)); chunk = max(4096, min(int(chunk_bytes), MAX_CHUNK))
    now = time.time(); ticket = secrets.token_hex(32); st = src.stat()
    source_identity = _path_identity(src)
    obj = {"ticket": ticket, "direction": "export", "created_at": utc_now(),
           "expires_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + ttl)), "expires_epoch": now + ttl,
           "path": str(src), "name": src.name, "size": st.st_size, "mtime_ns": st.st_mtime_ns,
           "sha256": source_identity["sha256"], "source_identity_at_create": source_identity,
           "chunk_bytes": chunk, "offset": 0, "complete": True}
    with _LOCK: _save(obj)
    return _public(obj)


def _file_object_identity(path: Path) -> dict[str, Any]:
    st = path.stat()
    identity = {
        "st_dev": int(getattr(st, "st_dev", 0)),
        "st_ino": int(getattr(st, "st_ino", 0)),
        "st_nlink": int(getattr(st, "st_nlink", 1)),
        # st_ino alone is not a stable generation witness: filesystems may reuse
        # an inode immediately after unlink/recreate. ctime changes when the inode
        # metadata generation changes and therefore closes that substitution hole.
        "st_ctime_ns": int(getattr(st, "st_ctime_ns", int(getattr(st, "st_ctime", 0.0) * 1_000_000_000))),
    }
    birth_ns = getattr(st, "st_birthtime_ns", None)
    if birth_ns is not None:
        identity["st_birthtime_ns"] = int(birth_ns)
    elif getattr(st, "st_birthtime", None) is not None:
        identity["st_birthtime_ns"] = int(float(st.st_birthtime) * 1_000_000_000)
    return identity


def _same_file_object_identity(current: dict[str, Any], expected: dict[str, Any]) -> bool:
    required = ("st_dev", "st_ino", "st_ctime_ns")
    if any(current.get(key) != expected.get(key) for key in required):
        return False
    expected_birth = expected.get("st_birthtime_ns")
    if expected_birth is not None and current.get("st_birthtime_ns") != expected_birth:
        return False
    return True


def _path_identity(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    if not path.is_file():
        return {"exists": True, "kind": "non_file"}
    st = path.stat()
    return {
        "exists": True,
        "kind": "file",
        "size": int(st.st_size),
        "mtime_ns": int(st.st_mtime_ns),
        "sha256": _sha(path),
        "file_object": _file_object_identity(path),
    }


def _require_stage_identity(path: Path, expected: dict[str, Any]) -> None:
    if not path.exists() or not path.is_file():
        raise ValueError("import stage identity changed after ticket creation")
    current = _file_object_identity(path)
    if not _same_file_object_identity(current, expected):
        raise ValueError("import stage identity changed after ticket creation")
    if int(current.get("st_nlink", 1)) != 1:
        raise ValueError("import stage identity is multiply linked")


def _require_export_source_identity(path: Path, ticket: dict[str, Any]) -> None:
    current = _path_identity(path)
    if current.get("kind") != "file":
        raise ValueError("source changed after export ticket creation")
    original = ticket.get("source_identity_at_create") or {}
    current_object = current.get("file_object") or {}
    original_object = original.get("file_object") or {}
    if not _same_file_object_identity(current_object, original_object):
        raise ValueError("source changed: source identity changed after export ticket creation")
    if current.get("size") != original.get("size") or current.get("mtime_ns") != original.get("mtime_ns"):
        raise ValueError("source changed after export ticket creation")
    if current.get("sha256") != original.get("sha256"):
        raise ValueError("source changed after export ticket creation")


def create_import(path: str, expected_size: int, expected_sha256: str, project_id: str | None = None,
                  ttl_seconds: int = DEFAULT_TTL, chunk_bytes: int = DEFAULT_CHUNK, overwrite: bool = False) -> dict[str, Any]:
    dst = _resolve(path, project_id)
    resolved_project_id = project_id_for_resolved_path(dst)
    if project_id and resolved_project_id and str(project_id) != resolved_project_id:
        raise ValueError("destination project identity does not match project_id")
    destination_identity = _path_identity(dst)
    if destination_identity.get("kind") == "non_file":
        raise FileExistsError("destination exists and is not a regular file")
    if dst.exists() and not overwrite:
        raise FileExistsError("destination exists; set overwrite=true")
    digest = expected_sha256.strip().lower(); size = int(expected_size)
    if size < 0: raise ValueError("expected_size must be >= 0")
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("expected_sha256 must be 64 hex characters")
    ttl = max(60, min(int(ttl_seconds), MAX_TTL)); chunk = max(4096, min(int(chunk_bytes), MAX_CHUNK))
    now = time.time(); ticket = secrets.token_hex(32)
    try:
        with resolved_paths_consequence_guard([dst], session_id="transfer"):
            stage_dir = dst.parent / ".pcmmad_transfer_staging"
            stage_dir.mkdir(parents=True, exist_ok=True)
            stage = stage_dir / f"{ticket}.part"
            stage.write_bytes(b"")
            stage_identity = _file_object_identity(stage)
            if int(stage_identity.get("st_nlink", 1)) != 1:
                raise ValueError("import stage identity is multiply linked at creation")
            obj = {"ticket": ticket, "direction": "import", "created_at": utc_now(),
                   "expires_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + ttl)), "expires_epoch": now + ttl,
                   "project_id": resolved_project_id, "path": str(dst), "stage": str(stage), "name": dst.name, "size": size, "sha256": digest,
                   "chunk_bytes": chunk, "offset": 0, "complete": False, "overwrite": bool(overwrite),
                   "destination_identity_at_create": destination_identity,
                   "stage_identity_at_create": stage_identity,
                   "stage_identity_current": stage_identity}
            with _LOCK: _save(obj)
    except ProjectMutationAuthorityError:
        raise
    return _public(obj)


def read_chunk(ticket: str, offset: int = 0, length: int | None = None) -> dict[str, Any]:
    obj = _load(ticket)
    if obj["direction"] != "export": raise ValueError("not an export ticket")
    src = Path(obj["path"]); _require_export_source_identity(src, obj)
    off = max(0, int(offset)); n = min(max(1, int(length or obj["chunk_bytes"])), int(obj["chunk_bytes"]))
    if off > int(obj["size"]): raise ValueError("offset beyond EOF")
    with src.open("rb") as f: f.seek(off); data = f.read(n)
    return {"ticket": ticket, "offset": off, "next_offset": off + len(data),
            "eof": off + len(data) >= int(obj["size"]), "bytes": len(data),
            "chunk_sha256": hashlib.sha256(data).hexdigest(), "data_b64": base64.b64encode(data).decode("ascii")}


def append_chunk(ticket: str, offset: int, data_b64: str, chunk_sha256: str | None = None) -> dict[str, Any]:
    with _LOCK:
        preflight = _load(ticket)
        if preflight["direction"] != "import": raise ValueError("not an import ticket")
        stage_path = Path(preflight["stage"])
    with resolved_paths_consequence_guard([stage_path], session_id="transfer"):
        with _LOCK:
            obj = _load(ticket)
            if obj["direction"] != "import": raise ValueError("not an import ticket")
            if obj["complete"]: raise ValueError("transfer already complete")
            off = int(offset)
            if off != int(obj["offset"]): raise ValueError(f"offset mismatch: expected {obj['offset']}, got {off}")
            try: data = base64.b64decode(data_b64, validate=True)
            except Exception as e: raise ValueError("invalid base64 chunk") from e
            if not data: raise ValueError("empty chunk")
            if len(data) > int(obj["chunk_bytes"]): raise ValueError("chunk exceeds negotiated size")
            if off + len(data) > int(obj["size"]): raise ValueError("chunk exceeds expected file size")
            actual = hashlib.sha256(data).hexdigest()
            expected_chunk = str(chunk_sha256 or "").strip().lower()
            if not expected_chunk:
                raise ValueError("chunk_sha256 is required")
            if actual != expected_chunk:
                raise ValueError("chunk sha256 mismatch")
            stage = Path(obj["stage"])
            _require_stage_identity(
                stage,
                obj.get("stage_identity_current") or obj.get("stage_identity_at_create") or {},
            )
            with stage.open("r+b") as f:
                f.seek(off); f.write(data); f.flush(); os.fsync(f.fileno())
            # Authorized writes legitimately advance POSIX ctime. Persist the new
            # object-generation witness only after the fsynced write succeeds.
            obj["stage_identity_current"] = _file_object_identity(stage)
            obj["offset"] = off + len(data); _save(obj)
            return {**_public(obj), "chunk_bytes_written": len(data), "chunk_sha256": actual}


def finalize_import(ticket: str) -> dict[str, Any]:
    with _LOCK:
        preflight = _load(ticket)
        if preflight["direction"] != "import": raise ValueError("not an import ticket")
        stage_path = Path(preflight["stage"]); dst_path = Path(preflight["path"])
    with resolved_paths_consequence_guard([stage_path, dst_path], session_id="transfer"):
        with _LOCK:
            obj = _load(ticket)
            if obj["direction"] != "import": raise ValueError("not an import ticket")
            if int(obj["offset"]) != int(obj["size"]): raise ValueError(f"incomplete: {obj['offset']} of {obj['size']} bytes")
            stage = Path(obj["stage"]); _require_stage_identity(
                stage,
                obj.get("stage_identity_current") or obj.get("stage_identity_at_create") or {},
            ); actual = _sha(stage)
            if actual != obj["sha256"]: raise ValueError(f"full sha256 mismatch: {actual}")
            dst = Path(obj["path"]); dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists() and not obj["overwrite"]: raise FileExistsError("destination exists")
            current_destination = _path_identity(dst)
            if current_destination != obj.get("destination_identity_at_create", {"exists": False}):
                raise ValueError("destination changed after import ticket creation")
            os.replace(stage, dst); obj["complete"] = True; obj["finalized_at"] = utc_now(); _save(obj)
            return {**_public(obj), "path": str(dst), "verified": True}


def cleanup_expired() -> dict[str, int]:
    now = time.time(); manifests = parts = blocked_project_stages = 0
    with _LOCK:
        candidates: list[tuple[Path, dict[str, Any]]] = []
        for manifest_path in _STATE.glob("*.json"):
            try:
                obj = json.loads(manifest_path.read_text("utf-8"))
            except Exception:
                continue
            if now <= float(obj.get("expires_epoch", 0)):
                continue
            candidates.append((manifest_path, obj))

    for manifest_path, obj in candidates:
        stage = Path(obj["stage"]) if obj.get("stage") else None
        try:
            if stage and stage.exists():
                with resolved_paths_consequence_guard([stage], session_id="transfer-cleanup"):
                    stage.unlink(missing_ok=True)
                    parts += 1
            with _LOCK:
                manifest_path.unlink(missing_ok=True)
            manifests += 1
        except ProjectMutationAuthorityError:
            # Do not erase either the project staging bytes or their recovery manifest
            # while another client owns that project's mutation generation.
            blocked_project_stages += 1
            continue
    return {
        "removed_manifests": manifests,
        "removed_parts": parts,
        "blocked_project_stages": blocked_project_stages,
    }


def _require_transfer_auth():
    try:
        require_valid_api_key(request.headers)
        return None
    except Exception as exc:
        return jsonify({"ok": False, "error_code": "UNAUTHORIZED", "message": str(exc)}), 401


def _lab_error_response(exc: Exception):
    error_code = getattr(exc, "error_code", type(exc).__name__.upper())
    message = getattr(exc, "message", str(exc))
    status = int(getattr(exc, "status", 400))
    extra = getattr(exc, "extra", {})
    return jsonify({"ok": False, "error_code": error_code, "message": message, **(extra if isinstance(extra, dict) else {})}), status


def _dispatch_transfer_mutation(tool_name: str, payload: dict[str, Any], authority: dict[str, Any] | None):
    try:
        from .lab_tools import dispatch_tool
        envelope = dispatch_tool(tool_name, payload, authority=authority or {})
        result = envelope.get("result") if isinstance(envelope, dict) else None
        body = {"ok": True, **(result if isinstance(result, dict) else {})}
        body["policy"] = {
            "approved": envelope.get("approved"),
            "approval_mode": envelope.get("approval_mode"),
            "approval_handle": envelope.get("approval_handle"),
        }
        return jsonify(body)
    except Exception as exc:
        if hasattr(exc, "error_code"):
            return _lab_error_response(exc)
        return _err(exc)


def _err(e: Exception):
    status = 404 if isinstance(e, FileNotFoundError) else 410 if isinstance(e, TimeoutError) else 409 if isinstance(e, FileExistsError) else 400
    return jsonify({"ok": False, "error_code": type(e).__name__.upper(), "message": str(e)}), status

@transfer_bp.post("/export/create")
def r_export_create():
    ae = _require_transfer_auth()
    if ae: return ae
    try:
        p = request.get_json(force=True) or {}
        return jsonify({"ok":True, **create_export(str(p.get("path","")), str(p.get("project_id","")) or None, int(p.get("ttl_seconds",DEFAULT_TTL)), int(p.get("chunk_bytes",DEFAULT_CHUNK)))})
    except Exception as e: return _err(e)

@transfer_bp.post("/import/create")
def r_import_create():
    ae = _require_transfer_auth()
    if ae: return ae
    try:
        p = request.get_json(force=True) or {}
        authority = p.pop("authority", {}) if isinstance(p, dict) else {}
        return _dispatch_transfer_mutation("transfer.import.create", p, authority)
    except Exception as e:
        return _err(e)

@transfer_bp.get("/<ticket>/meta")
def r_meta(ticket: str):
    ae = _require_transfer_auth()
    if ae: return ae
    try: return jsonify({"ok":True, **_public(_load(ticket))})
    except Exception as e: return _err(e)

@transfer_bp.get("/<ticket>/chunk")
def r_chunk(ticket: str):
    ae = _require_transfer_auth()
    if ae: return ae
    try: return jsonify({"ok":True, **read_chunk(ticket, int(request.args.get("offset",0)), int(request.args.get("length",0)) or None)})
    except Exception as e: return _err(e)

@transfer_bp.get("/<ticket>/file")
def r_file(ticket: str):
    ae = _require_transfer_auth()
    if ae: return ae
    try:
        obj=_load(ticket)
        if obj["direction"] != "export": raise ValueError("not an export ticket")
        src=Path(obj["path"]); st=src.stat()
        if st.st_size != int(obj["size"]) or st.st_mtime_ns != int(obj["mtime_ns"]): raise ValueError("source changed after export ticket creation")
        resp=send_file(src, as_attachment=True, download_name=obj["name"], conditional=True, max_age=0)
        resp.headers["Cache-Control"]="no-store"; resp.headers["X-PCMMAD-SHA256"]=obj["sha256"]; resp.headers["Accept-Ranges"]="bytes"
        return resp
    except Exception as e: return _err(e)

@transfer_bp.post("/<ticket>/upload-chunk")
def r_upload(ticket: str):
    ae = _require_transfer_auth()
    if ae: return ae
    try:
        p = request.get_json(force=True) or {}
        authority = p.pop("authority", {}) if isinstance(p, dict) else {}
        payload = {"ticket": ticket, **p}
        return _dispatch_transfer_mutation("transfer.chunk.write", payload, authority)
    except Exception as e:
        return _err(e)

@transfer_bp.post("/<ticket>/finalize")
def r_finalize(ticket: str):
    ae = _require_transfer_auth()
    if ae: return ae
    try:
        p = request.get_json(silent=True) or {}
        authority = p.get("authority", {}) if isinstance(p, dict) else {}
        return _dispatch_transfer_mutation("transfer.import.finalize", {"ticket": ticket}, authority)
    except Exception as e:
        return _err(e)

@transfer_bp.post("/cleanup")
def r_cleanup():
    ae = _require_transfer_auth()
    if ae: return ae
    return jsonify({"ok":True, **cleanup_expired()})


def register(register_tool: Callable[..., Any]) -> None:
    def wrap(fn, *a, **kw):
        try:
            return fn(*a, **kw)
        except FileNotFoundError as exc:
            raise LabToolError("NOT_FOUND", str(exc), 404, transfer_exception=type(exc).__name__) from exc
        except Exception as exc:
            status = 410 if isinstance(exc, TimeoutError) else 409 if isinstance(exc, FileExistsError) else 400
            raise LabToolError("TRANSFER_ERROR", str(exc), status, transfer_exception=type(exc).__name__) from exc

    @register_tool("transfer.export.create", "Create one short-lived, resumable, hash-verified export ticket.", "medium", category="transfer", tags=["binary","resumable","sha256"], side_effect_class="ephemeral_mutation", effect_traits=["creates_ephemeral_state","reads_files","hashes_content"])
    def _export(p): return wrap(create_export, str(p.get("path","")), str(p.get("project_id","")) or None, int(p.get("ttl_seconds",DEFAULT_TTL)), int(p.get("chunk_bytes",DEFAULT_CHUNK)))

    @register_tool("transfer.meta", "Inspect transfer metadata without materializing file bytes.", "low", category="transfer", tags=["binary","resumable","sha256"], side_effect_class="read", effect_traits=["reads_ephemeral_state","bounded_output","ticket_scoped"])
    def _meta(p): return wrap(lambda t: _public(_load(t)), str(p.get("ticket","")))

    @register_tool("transfer.chunk.read", "Read one bounded export chunk with per-chunk SHA-256 and Base64 transport.", "medium", category="transfer", tags=["binary","resumable","sha256"], side_effect_class="read", effect_traits=["reads_files","bounded_output","chunk_hash","ticket_scoped","source_currentness_check"])
    def _chunk(p): return wrap(read_chunk, str(p.get("ticket","")), int(p.get("offset",0)), int(p.get("length",0)) or None)

    @register_tool("transfer.import.create", "Create one staged import ticket; destination is not mutated until full SHA-256 verification.", "high", category="transfer", tags=["binary","resumable","sha256"], approval_required=True, mutating=True, side_effect_class="mutation", effect_traits=["durable_mutation","creates_staging_file","creates_ephemeral_state","binds_destination_identity","project_scope_enforced","path_project_mutation_fenced"])
    def _import(p): return wrap(create_import, str(p.get("path","")), int(p.get("expected_size",-1)), str(p.get("expected_sha256","")), str(p.get("project_id","")) or None, int(p.get("ttl_seconds",DEFAULT_TTL)), int(p.get("chunk_bytes",DEFAULT_CHUNK)), bool(p.get("overwrite",False)))

    @register_tool("transfer.chunk.write", "Append one verified chunk to a staged import at the exact expected offset.", "high", category="transfer", tags=["binary","resumable","sha256"], approval_required=True, mutating=True, side_effect_class="mutation", effect_traits=["durable_mutation","writes_staging_file","exact_offset_required","requires_chunk_hash","fsync","ticket_scoped","path_project_mutation_fenced"])
    def _write(p): return wrap(append_chunk, str(p.get("ticket","")), int(p.get("offset",-1)), str(p.get("data_b64","")), str(p.get("chunk_sha256","")) or None)

    @register_tool("transfer.import.finalize", "Atomically promote a staged import only after exact size and full SHA-256 verification.", "high", category="transfer", tags=["binary","resumable","sha256"], approval_required=True, mutating=True, side_effect_class="mutation", effect_traits=["durable_mutation","full_hash_verification","atomic_replace","binds_destination_identity","ticket_scoped","postcondition_verified","path_project_mutation_fenced"])
    def _final(p): return wrap(finalize_import, str(p.get("ticket","")))
