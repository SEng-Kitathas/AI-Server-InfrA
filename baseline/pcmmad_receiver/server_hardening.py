"""Server hardening primitives for JSON, subprocess, path, and bounded execution envelopes."""

from __future__ import annotations
from collections.abc import MutableMapping

import json
import os
import shutil
import stat
import zipfile
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path, PurePosixPath, PureWindowsPath
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Iterator, Sequence, TypedDict


class WalkErrorRecord(TypedDict):
    path: str
    error: str


class WalkResult(TypedDict):
    files: list[Path]
    errors: list[WalkErrorRecord]
    partial: bool


class ScopeCheckResult(TypedDict):
    ok: bool
    root: str
    candidate: str
    error: str | None


class ZipSafetyResult(TypedDict):
    ok: bool
    unsafe_entries: list[str]
    entry_count: int


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value).replace("\\", "/")
    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def safe_json_dumps(value: Any) -> str:
    return json.dumps(to_jsonable(value), ensure_ascii=False, sort_keys=False, allow_nan=False)


def safe_json_loads(text: str) -> Any:
    return json.loads(text)


def scope_check(root: Path, candidate: Path) -> ScopeCheckResult:
    resolved_root = root.resolve()
    resolved_candidate = candidate.resolve()
    ok = resolved_root == resolved_candidate or resolved_root in resolved_candidate.parents
    return ScopeCheckResult(
        ok=ok,
        root=str(resolved_root),
        candidate=str(resolved_candidate),
        error=None if ok else "candidate escapes root",
    )


def require_within_root(root: Path, candidate: Path) -> Path:
    result = scope_check(root, candidate)
    if not result["ok"]:
        raise ValueError(f"candidate escapes root: {result['candidate']}")
    return candidate.resolve()


def safe_project_cwd(project_root: Path, cwd_path: str | None) -> Path:
    raw = cwd_path or "."
    return require_within_root(project_root, project_root / raw)


def _skip_walk_dir(dirpath: str) -> bool:
    lowered = dirpath.lower()
    return any(
        part in lowered
        for part in (
            r"\$recycle.bin",
            r"\system volume information",
            r"\.git",
            r"\node_modules",
            r"\__pycache__",
        )
    )


def _walk_error_record(root: Path, exc: OSError) -> WalkErrorRecord:
    return WalkErrorRecord(path=str(getattr(exc, "filename", root)), error=str(exc))


def tolerant_rglob(root: Path, *, limit: int | None = None) -> WalkResult:
    files: list[Path] = []
    errors: list[WalkErrorRecord] = []
    root = root.resolve()
    for dirpath, dirnames, filenames in os.walk(
        root, topdown=True, onerror=lambda exc: errors.append(_walk_error_record(root, exc))
    ):
        if _skip_walk_dir(dirpath):
            dirnames[:] = []
            continue
        for filename in filenames:
            files.append(Path(dirpath) / filename)
            if limit is not None and len(files) >= limit:
                return WalkResult(files=files, errors=errors, partial=True)
    return WalkResult(files=files, errors=errors, partial=False)


def _normalized_zip_name(name: str) -> str:
    return name.replace("\\", "/")


def _zip_entry_is_special(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    file_type = stat.S_IFMT(mode)
    if file_type == 0:
        return False
    return not (stat.S_ISREG(mode) or stat.S_ISDIR(mode))


_WINDOWS_RESERVED_DEVICE_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
)
_WINDOWS_FORBIDDEN_COMPONENT_CHARS = frozenset('<>:"|?*')


def _windows_zip_component_reason(part: str) -> str | None:
    if not part:
        return "empty Windows path component"
    if part.endswith((".", " ")):
        return "trailing dot/space Windows path alias"
    if any(ch in part for ch in _WINDOWS_FORBIDDEN_COMPONENT_CHARS):
        if ":" in part:
            return "NTFS alternate data stream or colon-qualified path component"
        return "Windows-forbidden path character"
    normalized = part.rstrip(". ")
    stem = normalized.split(".", 1)[0].upper()
    if stem in _WINDOWS_RESERVED_DEVICE_NAMES:
        return "reserved Windows device name"
    return None


def _windows_zip_destination_identity(name: str) -> str:
    normalized = _normalized_zip_name(name).rstrip("/")
    parts = [part.rstrip(". ").casefold() for part in PurePosixPath(normalized).parts]
    return "/".join(parts)


def _zip_entry_reason(info: zipfile.ZipInfo) -> str | None:
    name = info.filename
    normalized = _normalized_zip_name(name)
    if not normalized or "\x00" in normalized:
        return "empty or NUL-containing entry name"
    posix = PurePosixPath(normalized)
    windows = PureWindowsPath(name)
    if posix.is_absolute() or windows.is_absolute() or windows.drive:
        return "absolute, drive-qualified, or UNC entry"
    if any(part in {"", ".", ".."} for part in posix.parts):
        return "ambiguous or traversing path component"
    for part in posix.parts:
        windows_reason = _windows_zip_component_reason(part)
        if windows_reason:
            return windows_reason
    if _zip_entry_is_special(info):
        return "symlink or special filesystem entry"
    return None


def inspect_zip_safety(zip_path: Path) -> ZipSafetyResult:
    unsafe_entries: list[str] = []
    normalized_targets: set[str] = set()
    with zipfile.ZipFile(zip_path, "r") as archive:
        infos = archive.infolist()
        for info in infos:
            reason = _zip_entry_reason(info)
            normalized = _windows_zip_destination_identity(info.filename)
            if normalized in normalized_targets:
                reason = reason or "duplicate normalized destination"
            normalized_targets.add(normalized)
            if reason:
                unsafe_entries.append(f"{info.filename}: {reason}")
    return ZipSafetyResult(
        ok=not unsafe_entries,
        unsafe_entries=unsafe_entries,
        entry_count=len(infos),
    )


def _safe_zip_target(destination: Path, info: zipfile.ZipInfo) -> Path:
    reason = _zip_entry_reason(info)
    if reason:
        raise ValueError(f"unsafe zip entry {info.filename!r}: {reason}")
    relative = PurePosixPath(_normalized_zip_name(info.filename))
    target = destination.joinpath(*relative.parts)
    return require_within_root(destination, target)


def _should_extract_entry(info: zipfile.ZipInfo, selected: set[str]) -> bool:
    return not selected or info.filename in selected


def _extract_one_zip_entry(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    target: Path,
) -> None:
    if info.is_dir():
        target.mkdir(parents=True, exist_ok=True)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with archive.open(info, "r") as source, target.open("wb") as destination:
        shutil.copyfileobj(source, destination, length=1024 * 1024)


def _extract_zip_entries(
    archive: zipfile.ZipFile,
    destination: Path,
    selected: set[str],
    overwrite: bool,
) -> tuple[list[str], list[str]]:
    extracted: list[str] = []
    skipped: list[str] = []
    known_names = {info.filename for info in archive.infolist()}
    unknown_selected = sorted(selected - known_names)
    if unknown_selected:
        raise ValueError(f"selected zip entries do not exist: {unknown_selected}")
    for info in archive.infolist():
        if not _should_extract_entry(info, selected):
            skipped.append(info.filename)
            continue
        target = _safe_zip_target(destination, info)
        if target.exists() and not overwrite:
            skipped.append(info.filename)
            continue
        _extract_one_zip_entry(archive, info, target)
        extracted.append(info.filename)
    return extracted, skipped


def _zip_extract_result(spec: ZipExtractResultSpec) -> JsonObject:
    return {
        "zip_path": str(spec.zip_path),
        "destination": str(spec.destination),
        "entry_count": spec.safety["entry_count"],
        "extracted_count": len(spec.extracted),
        "skipped_count": len(spec.skipped),
        "extracted": spec.extracted,
        "skipped": spec.skipped[:200],
    }


def safe_extract_zip(
    zip_path: Path,
    destination: Path,
    *,
    overwrite: bool = False,
    selected_entries: Iterable[str] | None = None,
) -> JsonObject:
    safety = inspect_zip_safety(zip_path)
    if not safety["ok"]:
        raise ValueError(f"unsafe zip entries: {safety['unsafe_entries']}")
    destination.mkdir(parents=True, exist_ok=True)
    destination = destination.resolve()
    with zipfile.ZipFile(zip_path, "r") as archive:
        extracted, skipped = _extract_zip_entries(
            archive,
            destination,
            set(selected_entries or ()),
            overwrite,
        )
    return _zip_extract_result(
        ZipExtractResultSpec(zip_path, destination, safety, extracted, skipped)
    )


class TextWindowResult(TypedDict):
    path: str
    mode: str
    file_size: int
    requested_bytes: int | None
    returned_bytes: int
    offset_bytes: int
    truncated: bool
    content: str


class CommandPreflightResult(TypedDict):
    ok: bool
    command: list[str]
    cwd: str
    error: str | None


class SubprocessEnvelope(TypedDict):
    ok: bool
    status: str
    return_code: int | None
    command: list[str]
    cwd: str
    stdout: str
    stderr: str
    stdout_truncated: bool
    stderr_truncated: bool
    duration_ms: int
    error: str | None


@dataclass(frozen=True)
class ZipExtractResultSpec:
    zip_path: Path
    destination: Path
    safety: ZipSafetyResult
    extracted: list[str]
    skipped: list[str]


@dataclass(frozen=True)
class TextWindowPayloadSpec:
    path: Path
    mode: str
    data: bytes
    file_size: int
    requested: int | None
    offset: int
    truncated: bool


@dataclass(frozen=True)
class ReadWindowBytesSpec:
    path: Path
    mode: str
    limit: int
    file_size: int
    offset_bytes: int | None
    length_bytes: int | None


@dataclass(frozen=True)
class BackgroundProcessSpec:
    cwd: str | Path
    stdout: Any
    stderr: Any
    env: dict[str, str] | None = None


@dataclass(frozen=True)
class TextWindowRequest:
    max_bytes: int | None = None
    mode: str = "tail"
    offset_bytes: int | None = None
    length_bytes: int | None = None


@dataclass(frozen=True)
class SubprocessRunSpec:
    cwd: Path
    timeout_seconds: int | None = None
    stdout_max_bytes: int | None = None
    stderr_max_bytes: int | None = None


ManagedProcess = subprocess.Popen[bytes]


def start_background_process(command: Sequence[str], **options: Any) -> ManagedProcess:
    spec = BackgroundProcessSpec(
        cwd=options["cwd"],
        stdout=options["stdout"],
        stderr=options["stderr"],
        env=options.get("env"),
    )
    return subprocess.Popen(
        list(command),
        cwd=str(spec.cwd),
        stdout=spec.stdout,
        stderr=spec.stderr,
        stdin=subprocess.DEVNULL,
        shell=False,
        env=spec.env,
    )


def write_json_report_atomic(path: Path, payload: Any) -> JsonObject:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = safe_json_dumps(payload)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=str(path.parent), delete=False
    ) as handle:
        handle.write(encoded)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)
    return {"path": str(path), "bytes": path.stat().st_size, "ok": True}


def _empty_text_window(path: Path, mode: str, requested: int | None) -> TextWindowResult:
    return TextWindowResult(
        path=str(path),
        mode=mode,
        file_size=0,
        requested_bytes=requested,
        returned_bytes=0,
        offset_bytes=0,
        truncated=False,
        content="",
    )


def _bytes_text_window(spec: TextWindowPayloadSpec) -> TextWindowResult:
    return TextWindowResult(
        path=str(spec.path),
        mode=spec.mode,
        file_size=spec.file_size,
        requested_bytes=spec.requested,
        returned_bytes=len(spec.data),
        offset_bytes=spec.offset,
        truncated=spec.truncated,
        content=spec.data.decode("utf-8", errors="replace"),
    )


def _read_window_bytes(spec: ReadWindowBytesSpec) -> tuple[bytes, int, bool, int]:
    offset = 0
    limit = spec.limit
    with spec.path.open("rb") as handle:
        if spec.mode == "range":
            offset = max(0, int(spec.offset_bytes or 0))
            limit = int(spec.length_bytes or spec.limit)
            handle.seek(offset)
            data = handle.read(limit + 1)
            return data[:limit], offset, len(data) > limit or offset + limit < spec.file_size, limit
        if spec.mode == "tail" and spec.file_size > limit:
            offset = max(0, spec.file_size - limit)
            handle.seek(offset)
        data = handle.read(limit)
    return data, offset, spec.file_size > limit, limit


def _full_text_window(path: Path, mode: str, file_size: int) -> TextWindowResult:
    data = path.read_bytes()
    return _bytes_text_window(TextWindowPayloadSpec(path, mode, data, file_size, None, 0, False))


def _partial_text_window(
    path: Path, mode: str, request: TextWindowRequest, file_size: int
) -> TextWindowResult:
    data, offset, truncated, requested = _read_window_bytes(
        ReadWindowBytesSpec(
            path,
            mode,
            int(request.max_bytes),
            file_size,
            request.offset_bytes,
            request.length_bytes,
        )
    )
    return _bytes_text_window(
        TextWindowPayloadSpec(path, mode, data, file_size, requested, offset, truncated)
    )


def read_text_window(path: Path, **options: Any) -> TextWindowResult:
    request = TextWindowRequest(
        max_bytes=options.get("max_bytes"),
        mode=options.get("mode", "tail"),
        offset_bytes=options.get("offset_bytes"),
        length_bytes=options.get("length_bytes"),
    )
    mode = (request.mode or "tail").strip().lower()
    mode = mode if mode in {"head", "tail", "range", "all"} else "tail"
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(str(path))
    file_size = path.stat().st_size
    if file_size <= 0:
        return _empty_text_window(path, mode, request.max_bytes)
    if mode == "all" or request.max_bytes is None or request.max_bytes <= 0:
        return _full_text_window(path, mode, file_size)
    return _partial_text_window(path, mode, request, file_size)


def command_preflight(
    project_root: Path, command: Sequence[str], cwd_path: str | None
) -> CommandPreflightResult:
    if not command or not all(isinstance(item, str) and item for item in command):
        return CommandPreflightResult(
            ok=False,
            command=[str(item) for item in command],
            cwd=str(project_root),
            error="command must be a non-empty string sequence",
        )
    try:
        cwd = safe_project_cwd(project_root, cwd_path)
    except (OSError, ValueError, TypeError) as exc:
        return CommandPreflightResult(
            ok=False, command=list(command), cwd=str(project_root), error=str(exc)
        )
    return CommandPreflightResult(ok=True, command=list(command), cwd=str(cwd), error=None)


def _subprocess_success_envelope(
    command: Sequence[str],
    spec: SubprocessRunSpec,
    proc: subprocess.CompletedProcess[bytes],
    duration_ms: int,
) -> SubprocessEnvelope:
    stdout_raw = (
        proc.stdout if spec.stdout_max_bytes is None else proc.stdout[: spec.stdout_max_bytes]
    )
    stderr_raw = (
        proc.stderr if spec.stderr_max_bytes is None else proc.stderr[: spec.stderr_max_bytes]
    )
    return SubprocessEnvelope(
        ok=proc.returncode == 0,
        status="COMPLETED" if proc.returncode == 0 else "FAILED",
        return_code=proc.returncode,
        command=list(command),
        cwd=str(spec.cwd),
        stdout=stdout_raw.decode("utf-8", errors="replace"),
        stderr=stderr_raw.decode("utf-8", errors="replace"),
        stdout_truncated=spec.stdout_max_bytes is not None
        and len(proc.stdout) > spec.stdout_max_bytes,
        stderr_truncated=spec.stderr_max_bytes is not None
        and len(proc.stderr) > spec.stderr_max_bytes,
        duration_ms=duration_ms,
        error=None,
    )


def _timeout_text(data: bytes | str | None, limit: int | None) -> str:
    payload = data or b""
    if isinstance(payload, bytes):
        return (payload if limit is None else payload[:limit]).decode("utf-8", errors="replace")
    return str(payload)


def _subprocess_timeout_envelope(
    command: Sequence[str],
    spec: SubprocessRunSpec,
    exc: subprocess.TimeoutExpired,
    duration_ms: int,
) -> SubprocessEnvelope:
    stdout_data = exc.stdout or b""
    stderr_data = exc.stderr or b""
    return SubprocessEnvelope(
        ok=False,
        status="TIMEOUT",
        return_code=None,
        command=list(command),
        cwd=str(spec.cwd),
        stdout=_timeout_text(stdout_data, spec.stdout_max_bytes),
        stderr=_timeout_text(stderr_data, spec.stderr_max_bytes),
        stdout_truncated=spec.stdout_max_bytes is not None
        and isinstance(stdout_data, bytes)
        and len(stdout_data) > spec.stdout_max_bytes,
        stderr_truncated=spec.stderr_max_bytes is not None
        and isinstance(stderr_data, bytes)
        and len(stderr_data) > spec.stderr_max_bytes,
        duration_ms=duration_ms,
        error=f"timeout after {spec.timeout_seconds}s",
    )


def _bounded_capture_file(path: Path, limit: int | None) -> tuple[str, bool]:
    size = path.stat().st_size if path.exists() else 0
    if limit is None:
        data = path.read_bytes() if path.exists() else b""
        return data.decode("utf-8", errors="replace"), False
    cap = max(0, int(limit))
    with path.open("rb") as handle:
        data = handle.read(cap)
    return data.decode("utf-8", errors="replace"), size > cap


def run_subprocess_envelope(command: Sequence[str], **options: Any) -> SubprocessEnvelope:
    """Run one synchronous subprocess with physically bounded returned output.

    stdout/stderr are spooled to local temporary files while the child runs so a
    noisy command cannot force Python to materialize its entire output merely to
    return a bounded envelope.  Only the requested prefix is read back.
    """
    spec = SubprocessRunSpec(
        cwd=options["cwd"],
        timeout_seconds=options.get("timeout_seconds"),
        stdout_max_bytes=options.get("stdout_max_bytes"),
        stderr_max_bytes=options.get("stderr_max_bytes"),
    )
    import time as _time

    started = _time.time()
    temp_dir = Path(tempfile.mkdtemp(prefix="pcmmad-subprocess-"))
    stdout_path = temp_dir / "stdout.bin"
    stderr_path = temp_dir / "stderr.bin"
    proc: subprocess.Popen[bytes] | None = None
    timed_out = False
    try:
        with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
            proc = subprocess.Popen(
                list(command),
                cwd=str(spec.cwd),
                stdout=stdout_handle,
                stderr=stderr_handle,
                stdin=subprocess.DEVNULL,
                shell=False,
                env=options.get("env"),
            )
            try:
                return_code = proc.wait(timeout=spec.timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                proc.kill()
                return_code = proc.wait()

        duration_ms = int((_time.time() - started) * 1000)
        stdout_text, stdout_truncated = _bounded_capture_file(
            stdout_path, spec.stdout_max_bytes
        )
        stderr_text, stderr_truncated = _bounded_capture_file(
            stderr_path, spec.stderr_max_bytes
        )
        if timed_out:
            return SubprocessEnvelope(
                ok=False,
                status="TIMEOUT",
                return_code=None,
                command=list(command),
                cwd=str(spec.cwd),
                stdout=stdout_text,
                stderr=stderr_text,
                stdout_truncated=stdout_truncated,
                stderr_truncated=stderr_truncated,
                duration_ms=duration_ms,
                error=f"timeout after {spec.timeout_seconds}s",
            )
        return SubprocessEnvelope(
            ok=return_code == 0,
            status="COMPLETED" if return_code == 0 else "FAILED",
            return_code=return_code,
            command=list(command),
            cwd=str(spec.cwd),
            stdout=stdout_text,
            stderr=stderr_text,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            duration_ms=duration_ms,
            error=None,
        )
    finally:
        if proc is not None and proc.poll() is None:
            try:
                proc.kill()
                proc.wait(timeout=5)
            except Exception:
                pass
        shutil.rmtree(temp_dir, ignore_errors=True)
