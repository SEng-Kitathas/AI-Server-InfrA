"""Power-user project routes for sync execution, files, archives, journals, and checkpoints."""

from __future__ import annotations

import os
from subprocess import Popen, TimeoutExpired
import sys
import tempfile
import time
import uuid
import zipfile
from contextlib import ExitStack
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import Any
from collections.abc import MutableMapping

from flask import Blueprint, jsonify, request

from api_wire_models import (
    CheckpointCreateRequest,
    CheckpointCreateResponse,
    ErrorEnvelope,
    FileTreeItem,
    FileTreeRequest as FileTreeRequestModel,
    FileTreeResponse,
    JournalAppendRequest,
    JournalAppendResponse,
    JournalEntry,
    JournalReadRequest,
    JournalReadResponse,
    PythonExecRequest,
    ReadManyFileResult,
    ReadManyRequest,
    ReadManyResponse,
    SyncExecRequest,
    SyncExecResponse,
    WaitExecutionRequest,
    WaitExecutionResponse,
    WriteFileRequest,
    WriteFileResponse,
    ZipReadRequest,
    ZipReadResponse,
)

JsonObject = MutableMapping[str, Any]

from context_engine import FileReadRequest, read_file
from control_plane_models import TextWindow
from execution_routes import (
    MAX_OUTPUT_BYTES,
    _finalize,
    _limit_for_wire,
    _read_job,
    _request_optional_positive_int,
    _resolve_cwd,
    _tail_text,
    ExecutionRequestError,
    submit_execution_job,
)
from server_hardening import safe_json_dumps, safe_json_loads
from shared_core import (
    ensure_parent,
    get_project_root,
    init_project_layout,
    journal_path_for,
    require_valid_api_key,
    sha256_file,
    utc_now,
)


@dataclass(frozen=True)
class StreamExecResponseSpec:
    spec: "StreamExecSpec"
    status: str
    return_code: int
    started: float
    stdout_path: Path
    stderr_path: Path
    windows: tuple[str, str, bool, bool, int, int, JsonObject, JsonObject]


@dataclass(frozen=True)
class StreamExecSpec:
    project_id: str
    command: list[str]
    cwd_rel: str | None
    timeout_seconds: int | None
    stdout_max_bytes: int | None
    stderr_max_bytes: int | None
    env: dict[str, str]


@dataclass(frozen=True)
class ProcessStartSpec:
    command: list[str]
    cwd: Path
    stdout: object
    stderr: object
    env: dict[str, str]


@dataclass(frozen=True)
class TreeIterSpec:
    root: Path
    depth: int
    include_hidden: bool
    exclude_dirs: set[str]
    extensions: set[str] | None
    min_size_bytes: int
    limit: int


power_bp = Blueprint("power", __name__, url_prefix="")


def _bounded_zip_entry_text(
    zf: zipfile.ZipFile, name: str, max_entry_bytes: int
) -> SyncExecResponse:
    info = zf.getinfo(name)
    if info.is_dir():
        return {"ok": False, "entry_name": str(name), "error": "entry is a directory"}
    with zf.open(info, "r") as handle:
        data = handle.read(max_entry_bytes + 1)
    truncated = len(data) > max_entry_bytes or info.file_size > max_entry_bytes
    if truncated:
        data = data[:max_entry_bytes]
    return {
        "ok": True,
        "entry_name": str(name),
        "bytes": len(data),
        "original_bytes": info.file_size,
        "truncated": truncated,
        "content": data.decode("utf-8", errors="replace"),
    }


def _error(error_code: str, message: str, status: int, **extra: Any) -> object:
    return (
        jsonify(
            ErrorEnvelope(
                ok=False, error_code=error_code, message=message, time=utc_now(), extra=extra
            ).to_dict()
        ),
        status,
    )


def _auth() -> object | None:
    try:
        require_valid_api_key(request.headers)
        return None
    except PermissionError as e:
        return _error("UNAUTHORIZED", str(e), 401)


def _json() -> JsonObject:
    request_payload = request.get_json(silent=False, force=True)
    if not isinstance(request_payload, dict):
        raise ValueError("JSON request body must be an object")
    return request_payload


def read_text_window(path: Path, max_bytes: int | None, mode: str) -> JsonObject:
    data = path.read_bytes()
    file_size = len(data)
    if max_bytes in (None, 0, -1) or max_bytes >= file_size:
        selected = data
        truncated = False
    elif mode == "tail":
        selected = data[-max_bytes:]
        truncated = True
    else:
        selected = data[:max_bytes]
        truncated = True
    return {
        "content": selected.decode("utf-8", errors="replace"),
        "truncated": truncated,
        "file_size": file_size,
    }


def _read_output_with_limit(path: Path, max_bytes: int | None) -> tuple[str, bool, int]:
    if not path.exists():
        return "", False, 0
    window = read_text_window(
        path, max_bytes=max_bytes, mode="tail" if max_bytes not in (None, 0, -1) else "all"
    )
    return window["content"], bool(window["truncated"]), int(window["file_size"])


def _sync_run_paths(cwd: Path) -> tuple[str, Path, Path]:
    run_root = cwd / ".pcmmad_sync_runs"
    run_root.mkdir(parents=True, exist_ok=True)
    run_id = f"sync-{uuid.uuid4().hex[:12]}"
    return run_id, run_root / f"{run_id}.stdout.log", run_root / f"{run_id}.stderr.log"


def start_background_process(spec: ProcessStartSpec) -> Popen[bytes]:
    return Popen(
        spec.command,
        cwd=str(spec.cwd),
        stdout=spec.stdout,
        stderr=spec.stderr,
        env=spec.env,
    )


def _wait_stream_process(proc: Any, timeout_seconds: int | None) -> tuple[int, str]:
    try:
        return_code = proc.wait(timeout=timeout_seconds)
        return return_code, "COMPLETED" if return_code == 0 else "FAILED"
    except TimeoutExpired:
        proc.kill()
        return -9, "TIMEOUT"


def _stream_text_windows(
    spec: StreamExecSpec, stdout_path: Path, stderr_path: Path
) -> tuple[str, str, bool, bool, int, int]:
    stdout_text, stdout_truncated, stdout_bytes = _read_output_with_limit(
        stdout_path, spec.stdout_max_bytes
    )
    stderr_text, stderr_truncated, stderr_bytes = _read_output_with_limit(
        stderr_path, spec.stderr_max_bytes
    )
    return stdout_text, stderr_text, stdout_truncated, stderr_truncated, stdout_bytes, stderr_bytes


def _text_window_payload(
    mode: str, file_size: int, requested_bytes: int | None, text: str
) -> JsonObject:
    return {
        "mode": mode,
        "file_size": file_size,
        "requested_bytes": requested_bytes,
        "returned_bytes": len(text.encode("utf-8")),
    }


def _stream_windows(
    spec: StreamExecSpec, stdout_path: Path, stderr_path: Path
) -> tuple[str, str, bool, bool, int, int, JsonObject, JsonObject]:
    stdout_text, stderr_text, stdout_truncated, stderr_truncated, stdout_bytes, stderr_bytes = (
        _stream_text_windows(spec, stdout_path, stderr_path)
    )
    stdout_window = _text_window_payload(
        "tail" if spec.stdout_max_bytes is not None else "all",
        stdout_bytes,
        spec.stdout_max_bytes,
        stdout_text,
    )
    stderr_window = _text_window_payload(
        "tail" if spec.stderr_max_bytes is not None else "all",
        stderr_bytes,
        spec.stderr_max_bytes,
        stderr_text,
    )
    return (
        stdout_text,
        stderr_text,
        stdout_truncated,
        stderr_truncated,
        stdout_bytes,
        stderr_bytes,
        stdout_window,
        stderr_window,
    )


def _stream_exec_response(response_spec: StreamExecResponseSpec) -> JsonObject:
    (
        stdout_text,
        stderr_text,
        stdout_truncated,
        stderr_truncated,
        stdout_bytes,
        stderr_bytes,
        stdout_window,
        stderr_window,
    ) = response_spec.windows
    return {
        "ok": response_spec.status == "COMPLETED",
        "status": response_spec.status,
        "command": response_spec.spec.command,
        "cwd": str(_resolve_cwd(response_spec.spec.project_id, response_spec.spec.cwd_rel)),
        "return_code": response_spec.return_code,
        "duration_ms": int((time.time() - response_spec.started) * 1000),
        "stdout": stdout_text,
        "stderr": stderr_text,
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
        "stdout_path": str(response_spec.stdout_path),
        "stderr_path": str(response_spec.stderr_path),
        "stdout_bytes": stdout_bytes,
        "stderr_bytes": stderr_bytes,
        "stdout_window": stdout_window,
        "stderr_window": stderr_window,
    }


def _stream_exec_to_files(spec: StreamExecSpec) -> JsonObject:
    cwd = _resolve_cwd(spec.project_id, spec.cwd_rel)
    _, stdout_path, stderr_path = _sync_run_paths(cwd)
    started = time.time()
    with ExitStack() as stack:
        stdout_handle = stack.enter_context(stdout_path.open("wb"))
        stderr_handle = stack.enter_context(stderr_path.open("wb"))
        proc = start_background_process(
            ProcessStartSpec(spec.command, cwd, stdout_handle, stderr_handle, spec.env)
        )
        return_code, status = _wait_stream_process(proc, spec.timeout_seconds)
    return _stream_exec_response(
        StreamExecResponseSpec(
            spec,
            status,
            return_code,
            started,
            stdout_path,
            stderr_path,
            _stream_windows(spec, stdout_path, stderr_path),
        )
    )


def _bounded_exec_limits(
    req: SyncExecRequest | PythonExecRequest,
) -> tuple[int | None, int | None, int | None]:
    return (
        _request_optional_positive_int(req.timeout_seconds, None, minimum=1),
        _request_optional_positive_int(
            req.stdout_max_bytes, None, minimum=1024, maximum=MAX_OUTPUT_BYTES
        ),
        _request_optional_positive_int(
            req.stderr_max_bytes, None, minimum=1024, maximum=MAX_OUTPUT_BYTES
        ),
    )


def _run_sync_payload(req: SyncExecRequest) -> JsonObject:
    timeout_seconds, stdout_max_bytes, stderr_max_bytes = _bounded_exec_limits(req)
    return _stream_exec_to_files(
        StreamExecSpec(
            req.project_id,
            req.command + req.args,
            req.cwd,
            timeout_seconds,
            stdout_max_bytes,
            stderr_max_bytes,
            {**os.environ.copy(), **req.env},
        )
    )


def _python_exec_payload(req: PythonExecRequest, tmp_path: Path) -> JsonObject:
    timeout_seconds, stdout_max_bytes, stderr_max_bytes = _bounded_exec_limits(req)
    return _stream_exec_to_files(
        StreamExecSpec(
            req.project_id,
            [sys.executable, str(tmp_path)],
            req.cwd,
            timeout_seconds,
            stdout_max_bytes,
            stderr_max_bytes,
            {**os.environ.copy(), **req.env, "PYTHONIOENCODING": "utf-8"},
        )
    )


def _read_many_file(root: Path, path: str, max_bytes_each: int | None) -> JsonObject:
    try:
        result = read_file(
            FileReadRequest(path=path, base_root=str(root), max_bytes=(max_bytes_each or 10**12))
        )
        result_data = result.to_dict() if hasattr(result, "to_dict") else result
        return ReadManyFileResult(
            content=result_data.get("content", ""),
            size_bytes=result_data.get("size_bytes", 0),
            truncated=result_data.get("truncated", False),
        ).to_dict()
    except (ValueError, OSError, UnicodeError, TypeError) as exc:
        return ReadManyFileResult(error=str(exc), truncated=False, size_bytes=0).to_dict()


def _read_many_payload(req: ReadManyRequest) -> JsonObject:
    max_bytes_each = _request_optional_positive_int(req.max_bytes_each, None, minimum=1)
    root = get_project_root(req.project_id)
    files = {path: _read_many_file(root, path, max_bytes_each) for path in req.paths}
    error_count = sum(1 for item in files.values() if item.get("error"))
    return ReadManyResponse(
        ok=True,
        files=files,
        read_count=len(req.paths) - error_count,
        error_count=error_count,
    ).to_dict()


def _write_file_target(req: WriteFileRequest) -> tuple[Path, bool]:
    root = init_project_layout(req.project_id)
    target = (root / req.path).resolve()
    if root.resolve() not in [target, *target.parents]:
        raise ValueError("path escapes project root")
    if req.mode not in {"overwrite", "append", "create_only"}:
        raise ValueError("mode must be overwrite, append, or create_only")
    if req.mode == "create_only" and target.exists():
        raise FileExistsError("file exists and mode=create_only")
    existed_before = target.exists()
    ensure_parent(target)
    return target, existed_before


def _write_file_payload(req: WriteFileRequest) -> JsonObject:
    target, existed_before = _write_file_target(req)
    if req.mode == "append":
        with target.open("a", encoding=req.encoding) as handle:
            handle.write(req.content)
    else:
        target.write_text(req.content, encoding=req.encoding)
    size_bytes = target.stat().st_size
    return {
        "ok": True,
        "project_id": req.project_id,
        "path": req.path,
        "absolute_path": str(target),
        "bytes_written": size_bytes,
        "created": not existed_before,
        "sha256": sha256_file(target),
        "bytes": size_bytes,
        "time": utc_now(),
    }


@power_bp.post("/run")
def run_sync() -> object:
    ae = _auth()
    if ae:
        return ae
    try:
        return jsonify(_run_sync_payload(SyncExecRequest.from_json(_json())))
    except ValueError as e:
        return _error("BAD_REQUEST", str(e), 400)
    except ExecutionRequestError as e:
        return _error(e.error_code, e.message, e.status, **e.extra)
    except (OSError, RuntimeError, TypeError) as e:
        return _error("RUN_SYNC_FAILED", str(e), 500)


@power_bp.post("/run/python")
def run_python() -> object:
    ae = _auth()
    if ae:
        return ae
    try:
        req = PythonExecRequest.from_json(_json())
        if not req.code:
            return _error("BAD_REQUEST", "code is required", 400)
        _resolve_cwd(req.project_id, req.cwd)
        with tempfile.NamedTemporaryFile("w", suffix=".py", encoding="utf-8", delete=False) as tmp:
            tmp.write(req.code)
            tmp_path = Path(tmp.name)
        try:
            return jsonify(_python_exec_payload(req, tmp_path))
        finally:
            tmp_path.unlink(missing_ok=True)
    except ValueError as e:
        return _error("BAD_REQUEST", str(e), 400)
    except (OSError, RuntimeError, TypeError) as e:
        return _error("RUN_PYTHON_FAILED", str(e), 500)


@power_bp.post("/project/files/read_many")
def read_many_project_files() -> object:
    ae = _auth()
    if ae:
        return ae
    try:
        return jsonify(_read_many_payload(ReadManyRequest.from_json(_json())))
    except ValueError as e:
        return _error("BAD_REQUEST", str(e), 400)
    except (OSError, RuntimeError, TypeError, UnicodeError) as e:
        return _error("READ_MANY_FAILED", str(e), 500)


@power_bp.post("/project/files/write")
def write_project_file() -> object:
    ae = _auth()
    if ae:
        return ae
    try:
        req = WriteFileRequest.from_json(_json())
        if not req.project_id or not req.path:
            return _error("BAD_REQUEST", "project_id and path are required", 400)
        return jsonify(_write_file_payload(req))
    except FileExistsError as e:
        return _error("ALREADY_EXISTS", str(e), 409)
    except ValueError as e:
        return _error("BAD_REQUEST", str(e), 400)
    except (OSError, RuntimeError, TypeError, UnicodeError) as e:
        return _error("WRITE_FILE_FAILED", str(e), 500)


def _resolve_zip_path(req: ZipReadRequest) -> Path:
    if not req.zip_path:
        raise ValueError("zip_path is required")
    if req.project_id and not Path(req.zip_path).is_absolute():
        base = get_project_root(req.project_id)
        zip_path = (base / req.zip_path).resolve()
        if base.resolve() not in [zip_path, *zip_path.parents]:
            raise ValueError("zip_path escapes project root")
        return zip_path
    return Path(req.zip_path).resolve()


def _zip_listing(zf: zipfile.ZipFile) -> list[JsonObject]:
    return [
        {
            "name": info.filename,
            "file_size": info.file_size,
            "compress_size": info.compress_size,
            "is_dir": info.is_dir(),
        }
        for info in zf.infolist()
    ]


def _zip_contents(
    zf: zipfile.ZipFile, entries: list[str], max_entry_bytes: int | None
) -> JsonObject:
    contents: JsonObject = {}
    for name in entries:
        try:
            contents[str(name)] = _bounded_zip_entry_text(
                zf, str(name), max_entry_bytes or (2**31 - 1)
            )
        except (KeyError, ValueError, OSError, RuntimeError, zipfile.BadZipFile) as exc:
            contents[str(name)] = {"ok": False, "entry_name": str(name), "error": str(exc)}
    return contents


def _zip_read_payload(req: ZipReadRequest) -> JsonObject:
    zip_path = _resolve_zip_path(req)
    if not zip_path.exists():
        raise FileNotFoundError("zip file not found")
    max_entry_bytes = _request_optional_positive_int(req.max_entry_bytes, None, minimum=1024)
    with zipfile.ZipFile(zip_path, "r") as zf:
        return ZipReadResponse(
            ok=True,
            zip_path=str(zip_path),
            listing=_zip_listing(zf),
            contents=_zip_contents(zf, req.entries, max_entry_bytes),
        ).to_dict()


@power_bp.post("/zip/read")
def read_zip_entries() -> object:
    ae = _auth()
    if ae:
        return ae
    try:
        return jsonify(_zip_read_payload(ZipReadRequest.from_json(_json())))
    except FileNotFoundError as e:
        return _error("NOT_FOUND", str(e), 404)
    except ValueError as e:
        return _error("BAD_REQUEST", str(e), 400)
    except (OSError, RuntimeError, TypeError, zipfile.BadZipFile) as e:
        return _error("ZIP_READ_FAILED", str(e), 500)


def _wait_execution_response(
    req: WaitExecutionRequest, job: JsonObject, max_bytes: int | None, timed_out: bool
) -> WaitExecutionResponse:
    stdout_text = ""
    stderr_text = ""
    stdout_truncated = False
    if not timed_out:
        stdout_text, stdout_truncated = _tail_text(Path(job.get("stdout_path", "")), max_bytes)
        stderr_text, _ = _tail_text(Path(job.get("stderr_path", "")), max_bytes)
    return WaitExecutionResponse(
        ok=True,
        job_id=req.job_id,
        status=job.get("status"),
        timed_out=timed_out,
        stdout=stdout_text,
        stderr=stderr_text,
        return_code=job.get("return_code"),
        duration_ms=job.get("duration_ms"),
        stdout_truncated=stdout_truncated,
        max_bytes=_limit_for_wire(max_bytes),
    )


@power_bp.post("/project/execution/wait")
def wait_for_project_execution() -> object:
    ae = _auth()
    if ae:
        return ae
    try:
        req = WaitExecutionRequest.from_json(_json())
        if not req.project_id or not req.job_id:
            return _error("BAD_REQUEST", "project_id and job_id are required", 400)
        timeout_seconds = _request_optional_positive_int(req.timeout_seconds, None, minimum=1)
        max_bytes = _request_optional_positive_int(
            req.max_bytes, None, minimum=1024, maximum=MAX_OUTPUT_BYTES
        )
        deadline = None if timeout_seconds is None else (time.time() + timeout_seconds)
        while deadline is None or time.time() < deadline:
            job = _finalize(req.project_id, req.job_id, _read_job(req.project_id, req.job_id))
            if job.get("status") not in {"RUNNING", "SUBMITTED", "QUEUED", "STARTING"}:
                return jsonify(
                    _wait_execution_response(req, job, max_bytes, timed_out=False).to_dict()
                )
            time.sleep(0.5)
        job = _finalize(req.project_id, req.job_id, _read_job(req.project_id, req.job_id))
        return jsonify(_wait_execution_response(req, job, max_bytes, timed_out=True).to_dict())
    except FileNotFoundError:
        return _error("NOT_FOUND", "job not found", 404)
    except ValueError as e:
        return _error("BAD_REQUEST", str(e), 400)
    except (OSError, RuntimeError, TypeError) as e:
        return _error("EXECUTION_WAIT_FAILED", str(e), 500)


def _tree_item_for_path(path: Path, root: Path, base_depth: int) -> FileTreeItem:
    rel = path.relative_to(root).as_posix() if path != root else "."
    name = path.name if path != root else root.name
    size_bytes = path.stat().st_size if path.exists() and path.is_file() else 0
    return FileTreeItem(
        path=str(path),
        rel_path=rel,
        name=name,
        is_dir=path.is_dir(),
        size_bytes=size_bytes,
        depth=len(path.parts) - base_depth,
        extension=path.suffix.lower() if path.is_file() else "",
    )


def _should_skip_tree_path(path: Path, root: Path, spec: TreeIterSpec, item: FileTreeItem) -> bool:
    if item.depth > spec.depth:
        return True
    if not spec.include_hidden and item.name.startswith(".") and path != root:
        return True
    if path.is_dir() and item.name in spec.exclude_dirs and path != root:
        return True
    if spec.extensions and path.is_file() and item.extension not in spec.extensions:
        return True
    return bool(path.is_file() and item.size_bytes < spec.min_size_bytes)


def _iter_tree(spec: TreeIterSpec) -> tuple[list[JsonObject], bool]:
    items: list[FileTreeItem] = []
    partial = False
    root = spec.root.resolve()
    base_depth = len(root.parts)
    for path in chain((root,), root.rglob("*")):
        if len(items) >= spec.limit:
            partial = True
            break
        item = _tree_item_for_path(path, root, base_depth)
        if _should_skip_tree_path(path, root, spec, item):
            continue
        items.append(item)
    return items, partial


def _tree_root(req: FileTreeRequestModel) -> Path:
    if not req.path:
        raise ValueError("path is required")
    if req.project_id and not Path(req.path).is_absolute():
        base = get_project_root(req.project_id)
        root = (base / req.path).resolve()
        if base.resolve() not in [root, *root.parents]:
            raise ValueError("path escapes project root")
        return root
    return Path(req.path).resolve()


def _tree_spec_from_request(req: FileTreeRequestModel) -> TreeIterSpec:
    root = _tree_root(req)
    if not root.exists():
        raise FileNotFoundError("root path not found")
    exclude_dirs = set(
        req.exclude_dirs or ["__pycache__", ".git", "node_modules", ".venv", ".venv_cuda", "vendor"]
    )
    return TreeIterSpec(
        root=root,
        depth=int(req.depth) if str(req.depth).strip() not in {"0", "-1"} else 10**9,
        include_hidden=req.include_hidden,
        exclude_dirs=exclude_dirs,
        extensions=(
            {str(item).lower() for item in (req.extensions or [])} if req.extensions else None
        ),
        min_size_bytes=req.min_size_bytes,
        limit=_request_optional_positive_int(req.limit, None, minimum=1) or 10**9,
    )


def _file_tree_payload(req: FileTreeRequestModel) -> JsonObject:
    spec = _tree_spec_from_request(req)
    items, partial = _iter_tree(spec)
    return FileTreeResponse(
        ok=True,
        root=str(spec.root),
        count=len(items),
        partial=partial,
        items=[item.to_dict() for item in items],
    ).to_dict()


@power_bp.post("/files/tree")
def get_file_tree() -> object:
    ae = _auth()
    if ae:
        return ae
    try:
        return jsonify(_file_tree_payload(FileTreeRequestModel.from_json(_json())))
    except FileNotFoundError as e:
        return _error("NOT_FOUND", str(e), 404)
    except ValueError as e:
        return _error("BAD_REQUEST", str(e), 400)
    except (OSError, RuntimeError, TypeError) as e:
        return _error("FILE_TREE_FAILED", str(e), 500)


@power_bp.post("/project/journal/append")
def append_project_journal() -> object:
    ae = _auth()
    if ae:
        return ae
    try:
        req = JournalAppendRequest.from_json(_json())
        entry = JournalEntry(
            time=utc_now(),
            entry_type=req.entry_type,
            title=req.title,
            content=req.content,
            tags=req.tags,
            session_id=req.session_id,
        )
        path = journal_path_for(req.project_id)
        ensure_parent(path)
        with path.open("a", encoding="utf-8") as f:
            f.write(safe_json_dumps(entry.to_dict()) + "\n")
        return jsonify(
            JournalAppendResponse(
                ok=True, project_id=req.project_id, entry=entry.to_dict(), path=str(path)
            ).to_dict()
        )
    except ValueError as e:
        return _error("BAD_REQUEST", str(e), 400)
    except (OSError, RuntimeError, TypeError, UnicodeError) as e:
        return _error("JOURNAL_APPEND_FAILED", str(e), 500)


def _journal_entry_from_line(line: str) -> JsonObject | None:
    try:
        raw = safe_json_loads(line)
        entry = JournalEntry(
            time=str(raw.get("time", "")),
            entry_type=str(raw.get("entry_type", "")),
            title=str(raw.get("title", "")),
            content=str(raw.get("content", "")),
            tags=list(raw.get("tags", [])) if isinstance(raw.get("tags", []), list) else [],
            session_id=raw.get("session_id"),
        )
        return entry.to_dict()
    except (ValueError, TypeError, KeyError):
        return None


def _read_journal_entries(path: Path, limit: int) -> list[JsonObject]:
    entries: list[JsonObject] = []
    recent_lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
    for line in recent_lines:
        entry = _journal_entry_from_line(line)
        if entry is not None:
            entries.append(entry)
    return entries


def _journal_read_payload(req: JournalReadRequest) -> JsonObject:
    limit = max(1, min(req.limit, 500))
    path = journal_path_for(req.project_id)
    entries = _read_journal_entries(path, limit) if path.exists() else []
    return JournalReadResponse(
        ok=True, project_id=req.project_id, count=len(entries), entries=entries
    ).to_dict()


@power_bp.post("/project/journal/read")
def read_project_journal() -> object:
    ae = _auth()
    if ae:
        return ae
    try:
        return jsonify(_journal_read_payload(JournalReadRequest.from_json(_json())))
    except ValueError as e:
        return _error("BAD_REQUEST", str(e), 400)
    except (OSError, RuntimeError, TypeError, UnicodeError) as e:
        return _error("JOURNAL_READ_FAILED", str(e), 500)


def _write_checkpoint_archive(root: Path, out_path: Path) -> None:
    exclude_prefixes = {"checkpoints/", "system/logs/execution/"}
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if any(rel.startswith(prefix) for prefix in exclude_prefixes):
                continue
            zf.write(path, arcname=rel)


def _checkpoint_payload(req: CheckpointCreateRequest) -> JsonObject:
    root = get_project_root(req.project_id)
    checkpoint_name = req.checkpoint_name or f"checkpoint_{uuid.uuid4().hex[:8]}"
    out_dir = root / "checkpoints"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{checkpoint_name}.zip"
    _write_checkpoint_archive(root, out_path)
    return CheckpointCreateResponse(
        ok=True,
        project_id=req.project_id,
        checkpoint_name=checkpoint_name,
        path=str(out_path),
        bytes=out_path.stat().st_size,
        time=utc_now(),
    ).to_dict()


@power_bp.post("/project/checkpoints/create")
def create_project_checkpoint() -> object:
    ae = _auth()
    if ae:
        return ae
    try:
        return jsonify(_checkpoint_payload(CheckpointCreateRequest.from_json(_json())))
    except ValueError as e:
        return _error("BAD_REQUEST", str(e), 400)
    except (OSError, RuntimeError, TypeError, zipfile.BadZipFile) as e:
        return _error("CHECKPOINT_CREATE_FAILED", str(e), 500)
