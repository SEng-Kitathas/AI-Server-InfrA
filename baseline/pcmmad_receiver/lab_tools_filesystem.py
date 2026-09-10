"""Filesystem lab-tool registration surface for mounted and absolute path operations."""

from __future__ import annotations

import glob
import shutil
import zipfile
from dataclasses import dataclass
from .lab_tool_primitives import (
    ToolPayload,
    ToolResult,
    payload_bool,
    payload_list_of_str,
    payload_str,
)
from .server_hardening import tolerant_rglob
from .project_mutation_authority import ProjectMutationAuthorityError, resolved_paths_consequence_guard
from .shared_core import ensure_safe_mutation_target_identity
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class FsGlobRequest:
    pattern: str
    project_id: str
    recursive: bool
    limit: int


@dataclass(frozen=True)
class FsGrepRequest:
    query: str
    limit: int | None
    max_file_bytes: int | None


@dataclass(frozen=True)
class FsTreeRequest:
    depth: int
    include_hidden: bool
    exclude_dirs: set[str]
    extensions: set[str] | None
    min_size_bytes: int
    limit: int | None


@dataclass(frozen=True)
class GrepResultSpec:
    request: FsGrepRequest
    hits: list[ToolResult]
    partial: bool
    files_scanned: int
    skipped_oversized: int
    walk_errors: list[ToolResult]


@dataclass(frozen=True)
class ZipReadRequest:
    entries: list[str]
    max_entry_bytes: int


@dataclass(frozen=True)
class FilesystemToolDeps:
    error_cls: type[Exception]
    resolve_general_path: Callable[..., Path]
    ensure_within_allowed: Callable[[Path], Path]
    get_project_root: Callable[[str], Path]
    resolve_mount_spec: Callable[..., Path]
    request_optional_positive_int: Callable[..., int | None]
    ensure_parent: Callable[[Path], None]
    stream_grep: Callable[..., tuple[list[ToolResult], bool, bool]]
    text_extensions: set[str]
    default_grep_max_file_bytes: int | None
    read_text_preview: Callable[..., ToolResult] | None
    mount_summary: Callable[..., ToolResult] | None


def _default_ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _filesystem_deps(deps: ToolPayload) -> FilesystemToolDeps:
    return FilesystemToolDeps(
        error_cls=deps["error_cls"],
        resolve_general_path=deps["resolve_general_path"],
        ensure_within_allowed=deps["ensure_within_allowed"],
        get_project_root=deps["get_project_root"],
        resolve_mount_spec=deps["resolve_mount_spec"],
        request_optional_positive_int=deps["request_optional_positive_int"],
        ensure_parent=deps.get("ensure_parent") or _default_ensure_parent,
        stream_grep=deps["stream_grep"],
        text_extensions=deps["text_extensions"],
        default_grep_max_file_bytes=deps["default_grep_max_file_bytes"],
        read_text_preview=deps.get("read_text_preview"),
        mount_summary=deps.get("mount_summary"),
    )


def _glob_request(payload: ToolPayload, dep: FilesystemToolDeps) -> FsGlobRequest:
    pattern = payload_str(payload, "pattern").strip()
    if not pattern:
        raise dep.error_cls("BAD_REQUEST", "pattern is required", 400)
    return FsGlobRequest(
        pattern=pattern,
        project_id=payload_str(payload, "project_id").strip(),
        recursive=payload_bool(payload, "recursive", True),
        limit=max(1, min(int(payload.get("limit", 500)), 5000)),
    )


def _grep_request(payload: ToolPayload, dep: FilesystemToolDeps) -> FsGrepRequest:
    query = payload_str(payload, "query").strip()
    if not query:
        raise dep.error_cls("BAD_REQUEST", "query is required", 400)
    return FsGrepRequest(
        query=query,
        limit=dep.request_optional_positive_int(payload.get("limit", 100), 100, minimum=1),
        max_file_bytes=dep.request_optional_positive_int(
            payload.get("max_file_bytes", dep.default_grep_max_file_bytes),
            dep.default_grep_max_file_bytes,
            minimum=1024,
        ),
    )


def _tree_request(payload: ToolPayload, dep: FilesystemToolDeps) -> FsTreeRequest:
    extensions_raw = payload_list_of_str(payload, "extensions")
    return FsTreeRequest(
        depth=max(1, min(int(payload.get("depth", 3)), 10)),
        include_hidden=payload_bool(payload, "include_hidden", False),
        exclude_dirs=set(
            payload_list_of_str(payload, "exclude_dirs")
            or ["__pycache__", ".git", "node_modules", ".venv", ".venv_cuda", "vendor"]
        ),
        extensions={item.lower() for item in extensions_raw} if extensions_raw else None,
        min_size_bytes=max(0, int(payload.get("min_size_bytes", 0))),
        limit=dep.request_optional_positive_int(payload.get("limit", 500), 500, minimum=1),
    )


def _zip_request(payload: ToolPayload) -> ZipReadRequest:
    return ZipReadRequest(
        entries=payload_list_of_str(payload, "entries"),
        max_entry_bytes=max(1024, min(int(payload.get("max_entry_bytes", 65536)), 1048576)),
    )


def _fs_read_payload(payload: ToolPayload, dep: FilesystemToolDeps) -> ToolResult:
    path = dep.ensure_within_allowed(dep.resolve_general_path(payload))
    if not path.exists() or not path.is_file():
        raise dep.error_cls("NOT_FOUND", "file not found", 404)
    max_bytes = dep.request_optional_positive_int(payload.get("max_bytes"), None, minimum=1)
    data = path.read_bytes()
    clipped = data[:max_bytes] if max_bytes else data
    return {
        "path": str(path),
        "size": len(data),
        "truncated": bool(max_bytes and len(data) > max_bytes),
        "content": clipped.decode("utf-8", errors="replace"),
    }


def _fs_write_payload(payload: ToolPayload, dep: FilesystemToolDeps) -> ToolResult:
    path = dep.ensure_within_allowed(dep.resolve_general_path(payload))
    content = payload_str(payload, "content")
    try:
        ensure_safe_mutation_target_identity(path)
        with resolved_paths_consequence_guard([path], session_id=payload_str(payload, "session_id")):
            dep.ensure_parent(path)
            path.write_text(content, encoding="utf-8")
    except ValueError as exc:
        raise dep.error_cls("BAD_PATH_ALIAS", str(exc), 409) from exc
    except ProjectMutationAuthorityError as exc:
        raise dep.error_cls(exc.error_code, exc.message, exc.status, **exc.extra) from exc
    return {"path": str(path), "bytes_written": len(content.encode("utf-8")), "ok": True}


def _fs_move_payload(payload: ToolPayload, dep: FilesystemToolDeps) -> ToolResult:
    src = dep.ensure_within_allowed(dep.resolve_general_path(payload, "src"))
    dst = dep.ensure_within_allowed(dep.resolve_general_path(payload, "dst"))
    if not src.exists():
        raise dep.error_cls("NOT_FOUND", "src not found", 404)
    try:
        with resolved_paths_consequence_guard(
            [src, dst], session_id=payload_str(payload, "session_id")
        ):
            dep.ensure_parent(dst)
            shutil.move(str(src), str(dst))
    except ProjectMutationAuthorityError as exc:
        raise dep.error_cls(exc.error_code, exc.message, exc.status, **exc.extra) from exc
    return {"src": str(src), "dst": str(dst), "moved": True}


def _register_basic_file_tools(register_tool: Callable[..., Any], dep: FilesystemToolDeps) -> None:
    @register_tool(
        "fs.read", "Read a file from a mounted or absolute path.", "medium", category="filesystem",
        side_effect_class="read", effect_traits=["reads_files", "allowed_root_scope"]
    )
    def tool_fs_read(payload: ToolPayload) -> ToolResult:
        return _fs_read_payload(payload, dep)

    @register_tool(
        "fs.write",
        "Write a file to a mounted or absolute path.",
        "high",
        category="filesystem",
        approval_required=True,
        mutating=True,
        side_effect_class="mutation",
        effect_traits=["durable_mutation", "path_project_mutation_fenced", "allowed_root_scope"],
    )
    def tool_fs_write(payload: ToolPayload) -> ToolResult:
        return _fs_write_payload(payload, dep)

    @register_tool(
        "fs.move",
        "Move a file within allowed roots.",
        "high",
        category="filesystem",
        approval_required=True,
        mutating=True,
        side_effect_class="mutation",
        effect_traits=["durable_mutation", "path_project_mutation_fenced", "allowed_root_scope"],
    )
    def tool_fs_move(payload: ToolPayload) -> ToolResult:
        return _fs_move_payload(payload, dep)


def _fs_glob_payload(payload: ToolPayload, dep: FilesystemToolDeps) -> ToolResult:
    request = _glob_request(payload, dep)
    default_root = dep.get_project_root(request.project_id) if request.project_id else None
    try:
        resolved_pattern = str(
            dep.resolve_mount_spec(request.pattern, default_root=default_root, allow_absolute=True)
        )
    except (OSError, ValueError, TypeError) as exc:
        raise dep.error_cls("BAD_PATH", str(exc), 400)
    matches: list[str] = []
    for hit in glob.glob(resolved_pattern, recursive=request.recursive):
        path = Path(hit).resolve()
        try:
            dep.ensure_within_allowed(path)
        except (OSError, ValueError, TypeError):
            continue
        matches.append(str(path))
        if len(matches) >= request.limit:
            break
    return {
        "pattern": request.pattern,
        "count": len(matches),
        "partial": len(matches) >= request.limit,
        "matches": matches,
    }


def _register_filesystem_search_tools(
    register_tool: Callable[..., Any], dep: FilesystemToolDeps
) -> None:
    @register_tool(
        "fs.glob", "Glob files under a mounted or absolute path.", "medium", category="filesystem",
        side_effect_class="read", effect_traits=["reads_files", "traverses_filesystem", "allowed_root_scope", "bounded_results"]
    )
    def tool_fs_glob(payload: ToolPayload) -> ToolResult:
        return _fs_glob_payload(payload, dep)

    @register_tool(
        "fs.grep",
        "Search text across mounted or absolute filesystem paths.",
        "medium",
        category="filesystem",
        side_effect_class="read",
        effect_traits=["reads_files", "traverses_filesystem", "allowed_root_scope", "bounded_results"],
    )
    def tool_fs_grep(payload: ToolPayload) -> ToolResult:
        request = _grep_request(payload, dep)
        path = dep.ensure_within_allowed(dep.resolve_general_path(payload))
        return _grep_path(path, request, dep)


def _grep_walker(path: Path) -> tuple[list[Path], list[ToolResult], bool]:
    if path.is_file():
        return [path], [], False
    walk_result = tolerant_rglob(path)
    return walk_result["files"], walk_result["errors"], bool(walk_result["partial"])


def _grep_file(
    entry: Path, request: FsGrepRequest, dep: FilesystemToolDeps, remaining: int
) -> tuple[list[ToolResult], bool, bool]:
    return dep.stream_grep(entry, request.query, remaining, request.max_file_bytes or (10**12))


def _grep_result_payload(spec: GrepResultSpec) -> ToolResult:
    return {
        "query": spec.request.query,
        "count": len(spec.hits),
        "partial": spec.partial,
        "hits": spec.hits,
        "files_scanned": spec.files_scanned,
        "skipped_oversized": spec.skipped_oversized,
        "walk_error_count": len(spec.walk_errors),
        "walk_errors_sample": spec.walk_errors[:20],
        "max_file_bytes": spec.request.max_file_bytes,
    }


def _grep_path(path: Path, request: FsGrepRequest, dep: FilesystemToolDeps) -> ToolResult:
    hits: list[ToolResult] = []
    files_scanned = 0
    skipped_oversized = 0
    walker, walk_errors, partial = _grep_walker(path)
    for entry in walker:
        if (
            not isinstance(entry, Path)
            or not entry.is_file()
            or entry.suffix.lower() not in dep.text_extensions
        ):
            continue
        files_scanned += 1
        remaining = (request.limit - len(hits)) if request.limit is not None else 10**9
        file_hits, file_partial, file_skipped = _grep_file(entry, request, dep, remaining)
        hits.extend(file_hits)
        skipped_oversized += 1 if file_skipped else 0
        if file_partial or (request.limit is not None and len(hits) >= request.limit):
            partial = True
            break
    return _grep_result_payload(
        GrepResultSpec(request, hits, partial, files_scanned, skipped_oversized, walk_errors)
    )


def _fs_tree_payload(payload: ToolPayload, dep: FilesystemToolDeps) -> ToolResult:
    from .power_routes import TreeIterSpec, _iter_tree

    root = dep.ensure_within_allowed(dep.resolve_general_path(payload))
    if not root.exists():
        raise dep.error_cls("NOT_FOUND", "root path not found", 404)
    request = _tree_request(payload, dep)
    items, partial = _iter_tree(
        TreeIterSpec(
            root=root,
            depth=request.depth,
            include_hidden=request.include_hidden,
            exclude_dirs=request.exclude_dirs,
            extensions=request.extensions,
            min_size_bytes=request.min_size_bytes,
            limit=request.limit,
        )
    )
    return {
        "root": str(root),
        "count": len(items),
        "partial": partial,
        "items": [item.to_dict() for item in items],
    }


def _zip_listing(zf: zipfile.ZipFile) -> list[ToolResult]:
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
    zf: zipfile.ZipFile, request: ZipReadRequest, dep: FilesystemToolDeps
) -> ToolResult:
    from .lab_tools import _bounded_zip_entry_text

    contents: ToolResult = {}
    for name in request.entries:
        try:
            contents[name] = _bounded_zip_entry_text(zf, name, request.max_entry_bytes)
        except (KeyError, OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
            contents[name] = {"ok": False, "entry_name": name, "error": str(exc)}
    return contents


def _zip_read_payload(payload: ToolPayload, dep: FilesystemToolDeps) -> ToolResult:
    zip_path = dep.ensure_within_allowed(dep.resolve_general_path(payload, "zip_path"))
    if not zip_path.exists():
        raise dep.error_cls("NOT_FOUND", "zip archive not found", 404)
    request = _zip_request(payload)
    with zipfile.ZipFile(zip_path, "r") as zf:
        return {
            "zip_path": str(zip_path),
            "listing": _zip_listing(zf),
            "contents": _zip_contents(zf, request, dep),
        }


def _register_filesystem_tree_zip_tools(
    register_tool: Callable[..., Any], dep: FilesystemToolDeps
) -> None:
    @register_tool(
        "fs.tree",
        "Traverse a filesystem tree from a mounted or absolute path.",
        "high",
        category="filesystem",
        approval_required=True,
        side_effect_class="read",
        effect_traits=["reads_files", "traverses_filesystem", "allowed_root_scope", "bounded_results"],
    )
    def tool_fs_tree(payload: ToolPayload) -> ToolResult:
        return _fs_tree_payload(payload, dep)

    @register_tool(
        "zip.read",
        "List or read entries from a mounted or absolute zip archive.",
        "medium",
        category="filesystem",
        side_effect_class="read",
        effect_traits=["reads_files", "reads_archive", "allowed_root_scope", "bounded_output"],
    )
    def tool_zip_read(payload: ToolPayload) -> ToolResult:
        return _zip_read_payload(payload, dep)


def register_filesystem_tools(
    register_tool: (
        Callable[
            ...,
            Callable[[Callable[[ToolPayload], ToolResult]], Callable[[ToolPayload], ToolResult]],
        ]
        | Callable[..., Any]
    ),
    **deps: Any,
) -> None:
    dep = _filesystem_deps(deps)
    _register_basic_file_tools(register_tool, dep)
    _register_filesystem_search_tools(register_tool, dep)
    _register_filesystem_tree_zip_tools(register_tool, dep)
