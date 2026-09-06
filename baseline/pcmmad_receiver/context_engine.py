"""Project context listing, reading, search, rehydration, model, and archive helpers."""

from __future__ import annotations
import os, re, time, zipfile, struct, threading
from dataclasses import dataclass
from collections import Counter, OrderedDict
from types import MappingProxyType
from pathlib import Path
from typing import Any
from collections.abc import MutableMapping
from api_wire_common import IndexCacheStats, WarningItem
from api_wire_context import (
    ArchiveExtractResponse,
    ArchiveInspectResponse,
    ArchiveItem,
    ArchiveListResponse,
    FileItem,
    FileListResponse,
    FileReadResponse,
    FileSearchResponse,
    FileSlice,
    ModelInspectResponse,
    ModelItem,
    ModelListResponse,
    SearchHit,
    SearchWindow,
)
from server_hardening import safe_json_dumps, safe_json_loads
from shared_core import (
    ARCHIVE_EXTENSIONS,
    MODEL_EXTENSIONS,
    TEXT_EXTENSIONS,
    get_mount_roots,
    get_project_root,
)
from context_config import (
    ARCHIVE_INSPECT_DEFAULT_MAX_ENTRIES,
    ARCHIVE_LIST_DEFAULT_LIMIT,
    DEFAULT_ALLOWED_ROOTS,
    DEFAULT_LIST_LIMIT,
    DEFAULT_READ_BYTES,
    DEFAULT_REHYDRATE_BUDGET_BYTES,
    DEFAULT_SEARCH_LIMIT,
    INDEX_CACHE_MAX_BYTES,
    INDEX_CACHE_TTL_SECONDS,
    MAX_LIST_RESULTS,
    MAX_READ_BYTES,
    MAX_READ_LINES,
    MAX_REHYDRATE_BUDGET_BYTES,
    MAX_REHYDRATE_ITEMS,
    MAX_SEARCH_FILE_BYTES,
    MAX_SEARCH_HITS,
    MODEL_LIST_DEFAULT_LIMIT,
)

JsonObject = MutableMapping[str, Any]


@dataclass(frozen=True)
class FileListRequest:
    path: str = ""
    base_root: str | None = None
    recursive: bool = False
    contains: str | None = None
    limit: int | None = None


@dataclass(frozen=True)
class FileReadRequest:
    path: str
    base_root: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    max_bytes: int | None = None


@dataclass(frozen=True)
class FileSearchRequest:
    query: str
    base_root: str | None = None
    path: str = ""
    artifact_classes: list[str] | None = None
    recursive: bool = True
    limit: int | None = None


@dataclass(frozen=True)
class FileSearchResponseSpec:
    query: str
    target: Path
    hits: list[JsonObject]
    warnings: list[JsonObject]
    skipped: list[str]
    partial: bool


@dataclass(frozen=True)
class RehydrateRequest:
    topic: str
    base_root: str | None = None
    path: str = ""
    budget_bytes: int | None = None
    debug: bool = False


@dataclass(frozen=True)
class ModelListRequest:
    project_id: str
    path: str = "."
    recursive: bool = True
    model_type: str = "auto"
    limit: int | None = None


@dataclass(frozen=True)
class ArchiveListRequest:
    project_id: str
    path: str = "."
    recursive: bool = True
    archive_type: str = "auto"
    limit: int | None = None


@dataclass(frozen=True)
class ArchiveExtractRequest:
    project_id: str
    path: str
    destination_path: str
    archive_type: str = "auto"
    selected_entries: list[str] | None = None
    overwrite: bool = False


TOKEN_RE = re.compile(r"[A-Za-z0-9_./:-]{3,}")
STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "that",
        "with",
        "from",
        "this",
        "have",
        "their",
        "into",
        "using",
        "used",
        "are",
        "was",
        "were",
        "has",
        "had",
        "but",
        "not",
        "you",
        "your",
        "can",
        "will",
        "they",
        "its",
        "than",
        "then",
        "such",
        "over",
        "also",
        "these",
        "those",
        "our",
        "out",
        "all",
        "one",
        "two",
        "may",
        "via",
        "use",
        "file",
        "files",
        "data",
        "notes",
        "note",
        "read",
        "search",
        "project",
        "state",
        "context",
        "latest",
        "current",
        "work",
        "line",
    }
)
_INDEX_CACHE: "OrderedDict[str, JsonObject]" = OrderedDict()
_INDEX_CACHE_TOTAL_BYTES = 0
_INDEX_CACHE_LOCK = threading.RLock()

TRANSIENT_CONTEXT_DIR_NAMES = frozenset(
    {
        ".pcmmad_sync_runs",
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".nox",
        "node_modules",
        "venv",
        "_v30_backups",
    }
)

ICF_ANCHOR_CLASSES = (
    "state.current",
    "continuity.icf_standard",
    "continuity.intent",
    "state.next_steps",
    "state.doctrine_snapshot",
    "state.revisit_ledger",
    "state.trace_matrix",
    "continuity.live_shadow",
    "continuity.design_thread_stream",
)


class ContextPlaneError(Exception):
    error_code = "CONTEXT_ERROR"


class UnauthorizedError(ContextPlaneError):
    error_code = "UNAUTHORIZED"


class BadPathError(ContextPlaneError):
    error_code = "BAD_PATH"


class NotFoundError(ContextPlaneError):
    error_code = "NOT_FOUND"


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text) if token.lower() not in STOPWORDS]


def get_allowed_roots() -> list[Path]:
    roots = get_mount_roots()
    return [Path(p).resolve() for p in (roots or DEFAULT_ALLOWED_ROOTS)]


def get_root_summary() -> list[str]:
    return [str(p) for p in get_allowed_roots()]


def project_root_path(project_id: str) -> str:
    return str(get_project_root(project_id))


def _warn_item(raw: JsonObject) -> WarningItem:
    return WarningItem(
        kind=str(raw.get("kind", "warning")),
        message=str(raw.get("message", "")),
        path=raw.get("path"),
    )


def _file_item(raw: JsonObject) -> FileItem:
    return FileItem(
        path=str(raw["path"]),
        name=str(raw["name"]),
        is_dir=bool(raw["is_dir"]),
        size_bytes=int(raw["size_bytes"]),
        modified_at=float(raw["modified_at"]),
        extension=str(raw["extension"]),
        artifact_class=str(raw["artifact_class"]),
    )


def _search_hit(raw: JsonObject) -> SearchHit:
    window = raw["best_window"]
    return SearchHit(
        path=str(raw["path"]),
        artifact_class=str(raw["artifact_class"]),
        score=float(raw["score"]),
        best_window=SearchWindow(
            start_line=int(window["start_line"]), end_line=int(window["end_line"])
        ),
        excerpt=str(raw["excerpt"]),
    )


def _read_archive_excerpt(path: Path) -> str:
    return _read_prefix_bounded(path, 4000)[0]


def _artifact_class_from_path(path: Path) -> str:
    parts = [p.lower() for p in path.parts]
    path_text = str(path).lower()
    name = path.name.lower()
    if name == "intent_constraint_frontier_continuity_standard.md":
        return "continuity.icf_standard"
    if name in {"commanders_intent_current.md", "project_intent_current.md"} or "commanders_intent" in name:
        return "continuity.intent"
    if "continuity" in parts and "live_shadow" in parts:
        return "continuity.live_shadow"
    if "continuity" in parts and "design_thread_stream" in parts:
        return "continuity.design_thread_stream"
    if "checkpoints" in parts:
        return "continuity.checkpoint"
    if "notes" in parts and "maintenance" in parts:
        return "notes.maintenance"
    if "state" in parts and "current" in parts:
        return "state.current"
    if "state" in parts and "next_steps" in parts:
        return "state.next_steps"
    if "state" in parts and "doctrine_snapshot" in parts:
        return "state.doctrine_snapshot"
    if "state" in parts and "revisit_ledger" in parts:
        return "state.revisit_ledger"
    if "state" in parts and "trace_matrix" in parts:
        return "state.trace_matrix"
    if path.suffix.lower() in MODEL_EXTENSIONS:
        return "model.binary"
    if path.suffix.lower() in ARCHIVE_EXTENSIONS or path.name.lower().endswith(".tar.gz"):
        return "archive.binary"
    if "code" in parts or path.suffix.lower() == ".py":
        return "code"
    if "cil" in path_text:
        return "cilnx.related"
    return "generic"


ARTIFACT_PRIORS = MappingProxyType(
    {
        "state.current": 4.0,
        "continuity.icf_standard": 3.9,
        "continuity.intent": 3.8,
        "state.next_steps": 3.5,
        "state.doctrine_snapshot": 3.4,
        "state.revisit_ledger": 3.3,
        "state.trace_matrix": 3.2,
        "continuity.live_shadow": 3.1,
        "continuity.design_thread_stream": 3.0,
        "continuity.checkpoint": 2.5,
        "notes.maintenance": 1.6,
        "code": 1.4,
        "generic": 1.0,
    }
)


def _within(candidate: Path, root: Path) -> bool:
    return candidate == root or root in candidate.parents


def resolve_user_path(user_path: str, base_root: str | None = None) -> Path:
    allowed_roots = get_allowed_roots()
    root = Path(base_root).resolve() if base_root else allowed_roots[0]
    if not any(_within(root, allowed) for allowed in allowed_roots):
        raise BadPathError("base_root is not an allowed root")
    user_path = user_path or "."
    candidate = (
        (root / user_path).resolve()
        if not Path(user_path).is_absolute()
        else Path(user_path).resolve()
    )
    # A scoped/project operation is confined to its exact base root even when
    # both the source and escaped destination happen to live on globally allowed
    # mounts/drives.  Path.resolve() also closes symlink/junction escapes here.
    scope_roots = [root] if base_root else allowed_roots
    if not any(_within(candidate, scope) for scope in scope_roots):
        raise BadPathError(
            "resolved path escapes scoped base root" if base_root else "resolved path escapes allowed roots"
        )
    return candidate


def _safe_stat(path: Path) -> JsonObject:
    st = path.stat()
    return {
        "path": str(path),
        "name": path.name,
        "is_dir": path.is_dir(),
        "size_bytes": st.st_size,
        "modified_at": st.st_mtime,
        "extension": path.suffix.lower(),
        "artifact_class": _artifact_class_from_path(path),
    }


def _is_transient_context_dir(name: str) -> bool:
    lowered = name.lower()
    return lowered in TRANSIENT_CONTEXT_DIR_NAMES or lowered.startswith(".venv")


def _is_transient_context_file(name: str) -> bool:
    lowered = name.lower()
    return lowered.startswith(".pcmmad_tmp_") or lowered.endswith(".tmp")


def _walk(
    root: Path, recursive: bool, limit: int, *, skip_transient: bool = False
) -> tuple[list[Path], list[JsonObject], list[str], bool]:
    results = []
    warnings = []
    skipped = []
    partial = False

    def scan(path: Path) -> None:
        nonlocal partial
        try:
            with os.scandir(path) as it:
                for entry in it:
                    if skip_transient:
                        if entry.is_dir(follow_symlinks=False) and _is_transient_context_dir(entry.name):
                            continue
                        if entry.is_file(follow_symlinks=False) and _is_transient_context_file(entry.name):
                            continue
                    p = Path(entry.path)
                    results.append(p)
                    if len(results) >= limit:
                        partial = True
                        return
                    if recursive and entry.is_dir(follow_symlinks=False):
                        scan(p)
        except (FileNotFoundError, PermissionError, OSError) as e:
            warnings.append({"kind": "walk_skip", "message": str(e), "path": str(path)})
            skipped.append(str(path))
            partial = True

    scan(root)
    return results, warnings, skipped, partial


@dataclass(frozen=True)
class ListFilesResponseSpec:
    target: Path
    request: FileListRequest
    out: list[JsonObject]
    warnings: list[JsonObject]
    skipped: list[str]
    partial: bool


@dataclass(frozen=True)
class SearchHitCollectionSpec:
    files: list[Path]
    request: FileSearchRequest
    qtokens: list[str]
    warnings: list[JsonObject]
    skipped: list[str]


def _bounded_list_limit(limit_value: int | None) -> int:
    return (
        MAX_LIST_RESULTS
        if limit_value in (None, 0, -1)
        else max(1, min(limit_value, MAX_LIST_RESULTS))
    )


def _list_file_items(
    items: list[Path], needle: str | None, warnings: list[JsonObject], skipped: list[str]
) -> tuple[list[JsonObject], bool]:
    out: list[JsonObject] = []
    partial = False
    for path in items:
        try:
            info = _safe_stat(path)
        except (OSError, ValueError, TypeError) as exc:
            warnings.append({"kind": "stat_skip", "message": str(exc), "path": str(path)})
            skipped.append(str(path))
            partial = True
            continue
        if needle and needle not in _norm(info["name"]) and needle not in _norm(info["path"]):
            continue
        out.append(info)
    out.sort(key=lambda item: (item["is_dir"] is False, item["path"]))
    return out, partial


def _list_files_response(spec: ListFilesResponseSpec) -> FileListResponse:
    return FileListResponse(
        ok=True,
        partial=spec.partial,
        warnings=[_warn_item(warning) for warning in spec.warnings],
        skipped_paths=spec.skipped,
        root_summary=get_root_summary(),
        target=str(spec.target),
        recursive=spec.request.recursive,
        count=len(spec.out),
        items=[_file_item(item) for item in spec.out],
    )


def list_files(request: FileListRequest) -> FileListResponse:
    target = resolve_user_path(request.path or ".", base_root=request.base_root)
    if not target.exists():
        raise NotFoundError("target path does not exist")
    if not target.is_dir():
        raise BadPathError("list target must be a directory")
    items, warnings, skipped, partial = _walk(
        target, request.recursive, _bounded_list_limit(request.limit)
    )
    out, item_partial = _list_file_items(
        items, _norm(request.contains) if request.contains else None, warnings, skipped
    )
    return _list_files_response(
        ListFilesResponseSpec(target, request, out, warnings, skipped, partial or item_partial)
    )


def _decode_text_bounded(data: bytes, max_bytes: int) -> str:
    text = data.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


def _read_prefix_bounded(path: Path, max_bytes: int) -> tuple[str, int, int]:
    with path.open("rb") as handle:
        data = handle.read(max_bytes + 1)
    content = _decode_text_bounded(data[:max_bytes], max_bytes)
    if not content:
        return "", 1, 0
    end_line = max(1, len(content.splitlines()))
    return content, 1, end_line


def _read_line_window_bounded(
    path: Path, start_line: int, requested_end_line: int | None, max_bytes: int
) -> tuple[str, int, int]:
    start = max(1, int(start_line))
    hard_end = start + MAX_READ_LINES - 1
    end_limit = min(int(requested_end_line), hard_end) if requested_end_line is not None else hard_end
    end_limit = max(start, end_limit)
    selected = bytearray()
    current_line = 1
    last_selected = start
    with path.open("rb") as handle:
        while current_line <= end_limit and len(selected) < max_bytes:
            fragment = handle.readline(8192)
            if not fragment:
                break
            if current_line >= start:
                remaining = max_bytes - len(selected)
                if remaining > 0:
                    selected.extend(fragment[:remaining])
                    last_selected = current_line
            if fragment.endswith(b"\n"):
                if current_line >= end_limit:
                    break
                current_line += 1
    content = _decode_text_bounded(bytes(selected), max_bytes)
    # Match historical line-window behavior: line terminators are normalized and
    # omitted at the outer edge of the returned window.
    content = "\n".join(content.splitlines())
    return content, start, last_selected if content else start


def read_file(request: FileReadRequest) -> FileReadResponse:
    target = resolve_user_path(request.path, base_root=request.base_root)
    if not target.exists() or not target.is_file():
        raise NotFoundError("file not found")
    if target.suffix.lower() not in TEXT_EXTENSIONS:
        raise BadPathError("file is not readable as text; use model/archive inspect")
    max_bytes = (
        MAX_READ_BYTES
        if request.max_bytes in (None, 0, -1)
        else min(max(1, int(request.max_bytes)), MAX_READ_BYTES)
    )
    if request.start_line is None and request.end_line is None:
        content, rs, re = _read_prefix_bounded(target, max_bytes)
    else:
        content, rs, re = _read_line_window_bounded(
            target,
            request.start_line or 1,
            request.end_line,
            max_bytes,
        )
    return FileReadResponse(
        ok=True,
        file=_file_item(_safe_stat(target)),
        slice=FileSlice(start_line=rs, end_line=re, max_bytes=max_bytes),
        content=content,
    )


def _cache_key(path: Path) -> str:
    return str(path.resolve())


def _cache_source_identity(path: Path) -> tuple[int, int]:
    st = path.stat()
    return int(st.st_size), int(st.st_mtime_ns)


def _estimate_size(obj: Any) -> int:
    return len(safe_json_dumps(obj).encode("utf-8"))


def _cache_prune() -> None:
    global _INDEX_CACHE_TOTAL_BYTES
    with _INDEX_CACHE_LOCK:
        now = time.time()
        expired = [
            cache_key
            for cache_key, cache_value in list(_INDEX_CACHE.items())
            if now - cache_value["created_at"] > INDEX_CACHE_TTL_SECONDS
        ]
        for cache_key in expired:
            rem = _INDEX_CACHE.pop(cache_key, None)
            if rem:
                _INDEX_CACHE_TOTAL_BYTES -= rem["size_bytes"]
        while _INDEX_CACHE_TOTAL_BYTES > INDEX_CACHE_MAX_BYTES and _INDEX_CACHE:
            _, rem = _INDEX_CACHE.popitem(last=False)
            _INDEX_CACHE_TOTAL_BYTES -= rem["size_bytes"]


def _cache_get(path: Path) -> JsonObject | None:
    global _INDEX_CACHE_TOTAL_BYTES
    key = _cache_key(path)
    try:
        source_size, source_mtime_ns = _cache_source_identity(path)
    except OSError:
        return None
    with _INDEX_CACHE_LOCK:
        rec = _INDEX_CACHE.get(key)
        if not rec:
            return None
        stale = (
            time.time() - rec["created_at"] > INDEX_CACHE_TTL_SECONDS
            or rec.get("source_size") != source_size
            or rec.get("source_mtime_ns") != source_mtime_ns
        )
        if stale:
            rem = _INDEX_CACHE.pop(key, None)
            if rem:
                _INDEX_CACHE_TOTAL_BYTES -= rem["size_bytes"]
            return None
        _INDEX_CACHE.move_to_end(key)
        return rec["payload"]


def _cache_put(path: Path, payload: JsonObject) -> None:
    global _INDEX_CACHE_TOTAL_BYTES
    size = _estimate_size(payload)
    if size > INDEX_CACHE_MAX_BYTES:
        return
    try:
        source_size, source_mtime_ns = _cache_source_identity(path)
    except OSError:
        return
    key = _cache_key(path)
    with _INDEX_CACHE_LOCK:
        old = _INDEX_CACHE.pop(key, None)
        if old:
            _INDEX_CACHE_TOTAL_BYTES -= old["size_bytes"]
        _INDEX_CACHE[key] = {
            "created_at": time.time(),
            "size_bytes": size,
            "source_size": source_size,
            "source_mtime_ns": source_mtime_ns,
            "payload": payload,
        }
        _INDEX_CACHE_TOTAL_BYTES += size
        _INDEX_CACHE.move_to_end(key)
        _cache_prune()


def get_index_cache_stats() -> JsonObject:
    _cache_prune()
    with _INDEX_CACHE_LOCK:
        return {
            "entries": len(_INDEX_CACHE),
            "bytes": max(_INDEX_CACHE_TOTAL_BYTES, 0),
            "max_bytes": INDEX_CACHE_MAX_BYTES,
            "ttl_seconds": INDEX_CACHE_TTL_SECONDS,
            "source_currentness": "canonical_path+size+mtime_ns",
        }


def _index_file(path: Path) -> JsonObject | None:
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return None
    cached = _cache_get(path)
    if cached is not None:
        return cached
    raw = _read_prefix_bounded(path, MAX_SEARCH_FILE_BYTES)[0]
    payload = {
        "tokens": Counter(_tokens(raw)),
        "content": raw,
        "lines": raw.splitlines(),
        "artifact_class": _artifact_class_from_path(path),
        "modified_at": path.stat().st_mtime,
    }
    _cache_put(path, payload)
    return payload


def _search_response(spec: FileSearchResponseSpec) -> FileSearchResponse:
    return FileSearchResponse(
        ok=True,
        partial=spec.partial,
        warnings=[_warn_item(warning) for warning in spec.warnings],
        skipped_paths=spec.skipped,
        query=spec.query,
        target=str(spec.target),
        count=len(spec.hits),
        hits=[_search_hit(hit) for hit in spec.hits],
        index_cache=IndexCacheStats(**get_index_cache_stats()),
    )


def _bounded_search_limit(limit_value: int | None) -> int:
    return (
        MAX_SEARCH_HITS
        if limit_value in (None, 0, -1)
        else max(1, min(limit_value, MAX_SEARCH_HITS))
    )


def _search_candidate_files(
    target: Path, recursive: bool, limit: int
) -> tuple[list[Path], list[JsonObject], list[str], bool]:
    if target.is_file():
        return [target], [], [], False
    all_items, warnings, skipped, partial = _walk(target, recursive, limit * 8, skip_transient=True)
    return [path for path in all_items if path.is_file()], warnings, skipped, partial


def _best_line_window(lines: list[str], qtokens: list[str]) -> tuple[int, int, str]:
    best_line, best_score = 1, -1
    for idx, line in enumerate(lines, start=1):
        line_score = sum(1 for token in qtokens if token in _tokens(line))
        if line_score > best_score:
            best_score, best_line = line_score, idx
    window_start = max(1, best_line - 3)
    window_end = min(len(lines), best_line + 3)
    return window_start, window_end, "\n".join(lines[window_start - 1 : window_end])[:4000]


def _search_hit_candidate(
    path: Path, request: FileSearchRequest, qtokens: list[str]
) -> JsonObject | None:
    art = _artifact_class_from_path(path)
    if request.artifact_classes and art not in request.artifact_classes:
        return None
    indexed = _index_file(path)
    if not indexed:
        return None
    counts = indexed["tokens"]
    match_count = sum(counts.get(token, 0) for token in qtokens)
    if match_count <= 0:
        return None
    lexical = sum(min(counts.get(token, 0), 10) * 0.35 for token in qtokens)
    age = max(time.time() - indexed["modified_at"], 1.0)
    recency = 0.8 if age < 86400 else (0.4 if age < 86400 * 7 else 0.0)
    window_start, window_end, excerpt = _best_line_window(indexed["lines"], qtokens)
    return {
        "path": str(path),
        "artifact_class": art,
        "score": round(lexical + ARTIFACT_PRIORS.get(art, 1.0) + recency, 4),
        "best_window": {"start_line": window_start, "end_line": window_end},
        "excerpt": excerpt,
    }


def _collect_search_hits(spec: SearchHitCollectionSpec) -> tuple[list[JsonObject], bool]:
    hits: list[JsonObject] = []
    partial = False
    for path in spec.files:
        try:
            candidate = _search_hit_candidate(path, spec.request, spec.qtokens)
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            spec.warnings.append({"kind": "index_skip", "message": str(exc), "path": str(path)})
            spec.skipped.append(str(path))
            partial = True
            continue
        if candidate:
            hits.append(candidate)
    return hits, partial


def search_files(request: FileSearchRequest) -> FileSearchResponse:
    query = request.query
    if not query.strip():
        raise ContextPlaneError("query is required")
    target = resolve_user_path(request.path or ".", base_root=request.base_root)
    if not target.exists():
        raise NotFoundError("search target does not exist")
    qtokens = _tokens(query)
    if not qtokens:
        raise ContextPlaneError("query did not produce meaningful tokens")
    limit = _bounded_search_limit(request.limit)
    files, warnings, skipped, partial = _search_candidate_files(target, request.recursive, limit)
    hits, hit_partial = _collect_search_hits(
        SearchHitCollectionSpec(files, request, qtokens, warnings, skipped)
    )
    hits.sort(key=lambda hit: hit["score"], reverse=True)
    return _search_response(
        FileSearchResponseSpec(
            query, target, hits[:limit], warnings, skipped, partial or hit_partial
        )
    )


@dataclass
class RecentFallbackSpec:
    target: Path
    state: "RehydrateSelectionState"
    budget: int
    warnings: list[WarningItem]
    skipped_paths: list[str]


@dataclass(frozen=True)
class RehydrateResponseSpec:
    request: RehydrateRequest
    topic: str
    target: Path
    search: FileSearchResponse
    state: "RehydrateSelectionState"
    budget: int
    partial: bool


@dataclass
class RehydrateSelectionState:
    selected: list[JsonObject]
    used: int
    picked: set[str]


def _rehydrate_budget(request: RehydrateRequest) -> int:
    if request.budget_bytes in (None, 0, -1):
        return MAX_REHYDRATE_BUDGET_BYTES
    return max(1, min(request.budget_bytes, MAX_REHYDRATE_BUDGET_BYTES))


def _rehydrate_priority() -> list[str]:
    return [
        *ICF_ANCHOR_CLASSES,
        "continuity.checkpoint",
        "notes.maintenance",
        "code",
        "generic",
        "cilnx.related",
    ]


def _clip_excerpt_to_budget(text: str, remaining_bytes: int) -> str:
    if remaining_bytes <= 0:
        return ""
    return _decode_text_bounded(text.encode("utf-8"), remaining_bytes)


def _window_for_excerpt(window: SearchWindow, excerpt: str) -> dict[str, int]:
    start = int(window.start_line)
    line_count = max(1, len(excerpt.splitlines())) if excerpt else 0
    end = min(int(window.end_line), start + max(0, line_count - 1)) if line_count else start
    return {"start_line": start, "end_line": end}


def _select_hit(state: RehydrateSelectionState, hit: FileSearchHit, budget: int) -> None:
    if any(str(row.get("path")) == str(hit.path) for row in state.selected):
        return
    remaining = max(0, int(budget) - int(state.used))
    excerpt = _clip_excerpt_to_budget(hit.excerpt, remaining)
    if not excerpt:
        return
    size = len(excerpt.encode("utf-8"))
    state.selected.append(
        {
            "path": hit.path,
            "artifact_class": hit.artifact_class,
            "score": hit.score,
            "window": _window_for_excerpt(hit.best_window, excerpt),
            "excerpt": excerpt,
        }
    )
    state.used += size
    state.picked.add(hit.artifact_class)


def _select_search_hits(hits: list[FileSearchHit], budget: int) -> RehydrateSelectionState:
    state = RehydrateSelectionState([], 0, set())
    for art in _rehydrate_priority():
        art_hits = [hit for hit in hits if hit.artifact_class == art]
        art_hits.sort(key=lambda hit: hit.score, reverse=True)
        for hit in art_hits:
            if len(state.selected) >= MAX_REHYDRATE_ITEMS:
                break
            _select_hit(state, hit, budget)
        if len(state.selected) >= MAX_REHYDRATE_ITEMS:
            break
    return state


def _recent_candidates(
    target: Path, warnings: list[WarningItem], skipped_paths: list[str]
) -> tuple[list[Path], bool]:
    files, walk_warnings, skipped, partial = _walk(target, True, 50, skip_transient=True)
    warnings.extend(_warn_item(warning) for warning in walk_warnings)
    skipped_paths.extend(skipped)
    recent: list[tuple[float, Path]] = []
    for path in files:
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            recent.append((path.stat().st_mtime, path))
        except (OSError, ValueError, TypeError):
            continue
    recent.sort(reverse=True)
    return [path for _, path in recent], partial


def _fallback_allowed_artifact(artifact_class: str) -> bool:
    return artifact_class in {
        *ICF_ANCHOR_CLASSES,
        "continuity.checkpoint",
        "notes.maintenance",
        "code",
    }


def _append_recent_candidate(
    state: RehydrateSelectionState, path: Path, artifact_class: str, budget: int
) -> None:
    remaining = max(0, int(budget) - int(state.used))
    excerpt = _clip_excerpt_to_budget(_read_archive_excerpt(path), remaining)
    if not excerpt:
        return
    size = len(excerpt.encode("utf-8"))
    state.selected.append(
        {
            "path": str(path),
            "artifact_class": artifact_class,
            "score": 0.1,
            "window": {"start_line": 1, "end_line": min(200, max(1, len(excerpt.splitlines())))},
            "excerpt": excerpt,
        }
    )
    state.used += size
    state.picked.add(artifact_class)


def _apply_recent_fallback(spec: RecentFallbackSpec) -> bool:
    if spec.state.selected or not spec.target.is_dir():
        return False
    recent, partial = _recent_candidates(spec.target, spec.warnings, spec.skipped_paths)
    for path in recent:
        artifact_class = _artifact_class_from_path(path)
        if not _fallback_allowed_artifact(artifact_class):
            continue
        _append_recent_candidate(spec.state, path, artifact_class, spec.budget)
        if len(spec.state.selected) >= MAX_REHYDRATE_ITEMS:
            break
    return partial


def _icf_anchor_directories(target: Path) -> list[Path]:
    if not target.is_dir():
        return []
    candidates: list[Path] = []
    name = target.name.lower()
    if name == "state":
        candidates.extend(
            target / child
            for child in ("current", "next_steps", "doctrine_snapshot", "revisit_ledger", "trace_matrix")
        )
    elif name == "continuity":
        candidates.extend(target / child for child in ("live_shadow", "design_thread_stream"))
    elif name == "checkpoints":
        candidates.append(target)
    else:
        candidates.extend(
            [
                target / "state" / "current",
                target / "state" / "doctrine_snapshot",
                target / "checkpoints",
                target / "state" / "next_steps",
                target / "state" / "revisit_ledger",
                target / "state" / "trace_matrix",
                target / "continuity" / "live_shadow",
                target / "continuity" / "design_thread_stream",
            ]
        )
    return [path for path in candidates if path.exists() and path.is_dir()]


def _icf_anchor_candidates(target: Path) -> list[tuple[str, Path]]:
    by_class: dict[str, list[Path]] = {artifact_class: [] for artifact_class in ICF_ANCHOR_CLASSES}
    for directory in _icf_anchor_directories(target):
        try:
            for path in directory.rglob("*"):
                if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
                    continue
                artifact_class = _artifact_class_from_path(path)
                if artifact_class in by_class:
                    by_class[artifact_class].append(path)
        except (OSError, PermissionError):
            continue
    selected: list[tuple[str, Path]] = []
    for artifact_class in ICF_ANCHOR_CLASSES:
        paths = by_class.get(artifact_class) or []
        if not paths:
            continue
        paths.sort(
            key=lambda path: path.stat().st_mtime_ns if path.exists() else 0,
            reverse=True,
        )
        selected.append((artifact_class, paths[0]))
    return selected


def _seed_icf_anchors(state: RehydrateSelectionState, target: Path, budget: int) -> None:
    anchors = _icf_anchor_candidates(target)
    if not anchors or budget <= 0:
        return
    # Reserve at most half the caller budget for cold-start authority anchors so
    # topic-specific evidence still has room.  Divide fairly so all available
    # ICF roles can survive small rehydration budgets.
    anchor_budget = max(1, budget // 2)
    per_anchor = max(128, anchor_budget // len(anchors))
    for artifact_class, path in anchors:
        if len(state.selected) >= MAX_REHYDRATE_ITEMS or state.used >= anchor_budget:
            break
        remaining_anchor = anchor_budget - state.used
        excerpt_limit = min(per_anchor, remaining_anchor)
        excerpt = _clip_excerpt_to_budget(_read_archive_excerpt(path), excerpt_limit)
        if not excerpt:
            continue
        size = len(excerpt.encode("utf-8"))
        state.selected.append(
            {
                "path": str(path),
                "artifact_class": artifact_class,
                "authority_role": (
                    "frontier"
                    if artifact_class in {"state.current", "state.next_steps"}
                    else "intent"
                    if artifact_class == "continuity.intent"
                    else "standard"
                    if artifact_class == "continuity.icf_standard"
                    else "constraints"
                    if artifact_class in {"state.doctrine_snapshot", "state.revisit_ledger", "state.trace_matrix"}
                    else "history"
                ),
                "score": ARTIFACT_PRIORS.get(artifact_class, 1.0),
                "window": {"start_line": 1, "end_line": max(1, len(excerpt.splitlines()))},
                "excerpt": excerpt,
                "seeded": True,
            }
        )
        state.used += size
        state.picked.add(artifact_class)


def _rehydrate_open_seams(state: RehydrateSelectionState) -> list[str]:
    open_seams: list[str] = []
    if "continuity.live_shadow" not in state.picked:
        open_seams.append("No live shadow selected; continuity state may be weaker.")
    if "continuity.design_thread_stream" not in state.picked:
        open_seams.append("No design-thread chronology selected; recovery path may be incomplete.")
    if not state.selected:
        open_seams.append("No relevant local artifacts found for requested topic.")
    return open_seams


def _rehydrate_response(spec: RehydrateResponseSpec) -> JsonObject:
    resp: JsonObject = {
        "ok": True,
        "partial": spec.partial,
        "warnings": [warning.to_dict() for warning in spec.search.warnings],
        "skipped_paths": list(spec.search.skipped_paths),
        "header": {
            "topic": spec.topic,
            "target": str(spec.target),
            "selected_items": len(spec.state.selected),
            "budget_bytes": spec.budget,
            "used_bytes": spec.state.used,
        },
        "selected": spec.state.selected,
        "open_seams": _rehydrate_open_seams(spec.state),
        "icf_cs": {
            "version": "1.0",
            "selected_classes": [
                artifact_class
                for artifact_class in ICF_ANCHOR_CLASSES
                if artifact_class in spec.state.picked
            ],
            "cold_start_law": "DIRECTION != CONSTRAINTS != FRONTIER != HISTORY",
        },
        "index_cache": get_index_cache_stats(),
    }
    if spec.request.debug:
        resp["debug_trace"] = {"search_hit_count": len(spec.search.hits)}
    return resp


def rehydrate_context(request: RehydrateRequest) -> JsonObject:
    topic = request.topic
    if not topic.strip():
        raise ContextPlaneError("topic is required")
    budget = _rehydrate_budget(request)
    target = resolve_user_path(request.path or ".", base_root=request.base_root)
    if not target.exists():
        raise NotFoundError("rehydration target does not exist")
    search = search_files(
        FileSearchRequest(
            query=topic, base_root=request.base_root, path=request.path, recursive=True, limit=30
        )
    )
    state = RehydrateSelectionState([], 0, set())
    _seed_icf_anchors(state, target, budget)
    seeded_paths = {str(row.get("path")) for row in state.selected}
    remaining_hits = [hit for hit in search.hits if str(hit.path) not in seeded_paths]
    topic_state = _select_search_hits(remaining_hits, max(0, budget - state.used))
    for row in topic_state.selected:
        if len(state.selected) >= MAX_REHYDRATE_ITEMS:
            break
        excerpt = _clip_excerpt_to_budget(str(row.get("excerpt") or ""), budget - state.used)
        if not excerpt:
            continue
        copied = dict(row)
        copied["excerpt"] = excerpt
        copied["seeded"] = False
        state.selected.append(copied)
        state.used += len(excerpt.encode("utf-8"))
        state.picked.add(str(row.get("artifact_class") or "generic"))
    partial = search.partial or _apply_recent_fallback(
        RecentFallbackSpec(target, state, budget, search.warnings, search.skipped_paths)
    )
    return _rehydrate_response(
        RehydrateResponseSpec(request, topic, target, search, state, budget, partial)
    )


def _infer_model_type(path: Path) -> str:
    suffix_text = path.suffix.lower()
    return {
        " .safetensors": "safetensors",
        ".safetensors": "safetensors",
        ".gguf": "gguf",
        ".onnx": "onnx",
        ".bin": "bin",
        ".pt": "pt",
        ".pth": "pth",
    }.get(suffix_text, "auto")


def _model_list_scan_limit(request: ModelListRequest) -> int:
    base = request.limit if request.limit not in (None, 0, -1) else MODEL_LIST_DEFAULT_LIMIT
    return base * 8


def _model_item_from_file_item(item: Any, request: ModelListRequest) -> JsonObject | None:
    path = Path(item.path)
    model_type = _infer_model_type(path)
    if path.suffix.lower() not in MODEL_EXTENSIONS:
        return None
    if request.model_type != "auto" and model_type != request.model_type:
        return None
    return {
        "path": item.path,
        "name": item.name,
        "model_type": model_type,
        "size_bytes": item.size_bytes,
        "modified_at": item.modified_at,
    }


def _collect_model_items(listing: FileListResponse, request: ModelListRequest) -> list[JsonObject]:
    items: list[JsonObject] = []
    for item in listing.items:
        if item.is_dir:
            continue
        model_item = _model_item_from_file_item(item, request)
        if model_item:
            items.append(model_item)
        if request.limit not in (None, 0, -1) and len(items) >= request.limit:
            break
    return items


def _model_listing_response(
    listing: FileListResponse, items: list[JsonObject]
) -> ModelListResponse:
    return ModelListResponse(
        ok=True,
        partial=listing.partial,
        warnings=listing.warnings,
        skipped_paths=listing.skipped_paths,
        count=len(items),
        items=[
            ModelItem(
                path=str(item["path"]),
                name=str(item["name"]),
                model_type=str(item["model_type"]),
                size_bytes=int(item["size_bytes"]),
                modified_at=float(item["modified_at"]),
            )
            for item in items
        ],
    )


def list_models(request: ModelListRequest) -> ModelListResponse:
    listing = list_files(
        FileListRequest(
            path=request.path,
            base_root=project_root_path(request.project_id),
            recursive=request.recursive,
            limit=_model_list_scan_limit(request),
        )
    )
    return _model_listing_response(listing, _collect_model_items(listing, request))


def _read_safetensors_preview(target: Path, warnings: list[JsonObject]) -> JsonObject:
    meta: JsonObject = {}
    with target.open("rb") as f:
        head = f.read(8)
        if len(head) != 8:
            return meta
        header_len = struct.unpack("<Q", head)[0]
        meta["header_bytes"] = int(header_len)
        if not 0 < header_len < 10_000_000:
            return meta
        hdr = f.read(min(header_len, 200000))
    try:
        parsed = safe_json_loads(hdr.decode("utf-8", errors="replace"))
        meta["tensor_count"] = len(parsed.keys())
        meta["tensor_names_preview"] = list(parsed.keys())[:20]
    except (UnicodeError, ValueError, TypeError) as e:
        warnings.append({"kind": "partial_parse", "message": str(e), "path": str(target)})
    return meta


def inspect_model(project_id: str, path: str, model_type: str = "auto") -> ModelInspectResponse:
    target = resolve_user_path(path, base_root=project_root_path(project_id))
    if not target.exists() or not target.is_file():
        raise NotFoundError("model file not found")
    mt = _infer_model_type(target) if model_type == "auto" else model_type
    size = target.stat().st_size
    meta = {"name": target.name, "suffix": target.suffix.lower()}
    warnings = []
    try:
        if mt == "safetensors":
            meta.update(_read_safetensors_preview(target, warnings))
        elif mt == "gguf":
            with target.open("rb") as f:
                meta["magic"] = f.read(4).decode("latin1", errors="replace")
                meta["version"] = int.from_bytes(f.read(4), "little", signed=False)
        else:
            with target.open("rb") as f:
                meta["magic_preview"] = f.read(16).hex()
    except (OSError, RuntimeError, ValueError, TypeError, UnicodeError) as e:
        warnings.append({"kind": "inspect_partial", "message": str(e), "path": str(target)})
    return ModelInspectResponse(
        ok=True,
        path=str(target),
        model_type=mt,
        size_bytes=size,
        metadata=meta,
        partial=bool(warnings),
        warnings=[_warn_item(w) for w in warnings],
    )


def _infer_archive_type(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".tar.gz") or name.endswith(".tgz"):
        return "tar.gz"
    if name.endswith(".zip"):
        return "zip"
    if name.endswith(".tar"):
        return "tar"
    if name.endswith(".7z"):
        return "7z"
    if name.endswith(".gz"):
        return "gz"
    return "auto"


def _archive_list_scan_limit(request: ArchiveListRequest) -> int:
    base = request.limit if request.limit not in (None, 0, -1) else ARCHIVE_LIST_DEFAULT_LIMIT
    return base * 8


def _archive_item_from_file_item(item: Any, request: ArchiveListRequest) -> JsonObject | None:
    path = Path(item.path)
    archive_type = _infer_archive_type(path)
    if path.suffix.lower() not in ARCHIVE_EXTENSIONS and not path.name.lower().endswith(".tar.gz"):
        return None
    if request.archive_type != "auto" and archive_type != request.archive_type:
        return None
    return {
        "path": item.path,
        "name": item.name,
        "archive_type": archive_type,
        "size_bytes": item.size_bytes,
        "modified_at": item.modified_at,
    }


def _collect_archive_items(
    listing: FileListResponse, request: ArchiveListRequest
) -> list[JsonObject]:
    items: list[JsonObject] = []
    for item in listing.items:
        if item.is_dir:
            continue
        archive_item = _archive_item_from_file_item(item, request)
        if archive_item:
            items.append(archive_item)
        if request.limit not in (None, 0, -1) and len(items) >= request.limit:
            break
    return items


def _archive_listing_response(
    listing: FileListResponse, items: list[JsonObject]
) -> ArchiveListResponse:
    return ArchiveListResponse(
        ok=True,
        partial=listing.partial,
        warnings=listing.warnings,
        skipped_paths=listing.skipped_paths,
        count=len(items),
        items=[
            ArchiveItem(
                path=str(item["path"]),
                name=str(item["name"]),
                archive_type=str(item["archive_type"]),
                size_bytes=int(item["size_bytes"]),
                modified_at=float(item["modified_at"]),
            )
            for item in items
        ],
    )


def list_archives(request: ArchiveListRequest) -> ArchiveListResponse:
    listing = list_files(
        FileListRequest(
            path=request.path,
            base_root=project_root_path(request.project_id),
            recursive=request.recursive,
            limit=_archive_list_scan_limit(request),
        )
    )
    return _archive_listing_response(listing, _collect_archive_items(listing, request))


@dataclass(frozen=True)
class ArchiveInspectResponseSpec:
    target: Path
    archive_type: str
    entries: list[str]
    total: int
    warnings: list[JsonObject]


@dataclass(frozen=True)
class ZipExtractSpec:
    target: Path
    dest: Path
    selected_entries: list[str]
    overwrite: bool
    warnings: list[JsonObject]


@dataclass(frozen=True)
class ArchiveExtractResponseSpec:
    target: Path
    dest: Path
    extracted: int
    partial: bool
    warnings: list[JsonObject]


def _bounded_archive_inspect_max(max_entries: int | None) -> int:
    if max_entries in (None, 0, -1):
        return ARCHIVE_INSPECT_DEFAULT_MAX_ENTRIES
    return max(1, min(max_entries, ARCHIVE_INSPECT_DEFAULT_MAX_ENTRIES))


def _inspect_zip_entries(target: Path, max_entries: int) -> tuple[list[str], int]:
    with zipfile.ZipFile(target) as zip_file:
        names = zip_file.namelist()
        return names[:max_entries], len(names)


def _archive_inspect_warning(archive_type: str, target: Path) -> JsonObject:
    return {
        "kind": "unsupported_archive_type",
        "message": f"Inspection for {archive_type} is limited in this build",
        "path": str(target),
    }


def _archive_inspect_response(spec: ArchiveInspectResponseSpec) -> ArchiveInspectResponse:
    return ArchiveInspectResponse(
        ok=True,
        path=str(spec.target),
        archive_type=spec.archive_type,
        entry_count=spec.total,
        entries=spec.entries,
        partial=bool(spec.warnings),
        warnings=[_warn_item(warning) for warning in spec.warnings],
    )


def inspect_archive(
    project_id: str, path: str, archive_type: str = "auto", max_entries: int | None = None
) -> ArchiveInspectResponse:
    target = resolve_user_path(path, base_root=project_root_path(project_id))
    if not target.exists() or not target.is_file():
        raise NotFoundError("archive file not found")
    resolved_type = _infer_archive_type(target) if archive_type == "auto" else archive_type
    warnings: list[JsonObject] = []
    entries: list[str] = []
    total = 0
    try:
        if resolved_type == "zip":
            entries, total = _inspect_zip_entries(target, _bounded_archive_inspect_max(max_entries))
        else:
            warnings.append(_archive_inspect_warning(resolved_type, target))
    except (OSError, RuntimeError, ValueError, TypeError, UnicodeError) as exc:
        warnings.append({"kind": "inspect_partial", "message": str(exc), "path": str(target)})
    return _archive_inspect_response(
        ArchiveInspectResponseSpec(target, resolved_type, entries, total, warnings)
    )


def _record_extract_result(ok: bool, warning: JsonObject | None, warnings: list[JsonObject]) -> int:
    if ok:
        return 1
    if warning:
        warnings.append(warning)
    return 0


def _extract_one_zip_entry(
    zf: zipfile.ZipFile, name: str, dest: Path, overwrite: bool
) -> tuple[bool, JsonObject | None]:
    out = (dest / name).resolve()
    if dest.resolve() not in [out, *out.parents]:
        return False, {"kind": "extract_skip", "message": "entry escaped destination", "path": name}
    if out.exists() and not overwrite:
        return False, {"kind": "extract_skip", "message": "destination exists", "path": str(out)}
    zf.extract(name, path=dest)
    return True, None


def _archive_extract_target(request: ArchiveExtractRequest) -> tuple[Path, Path, str]:
    target = resolve_user_path(request.path, base_root=project_root_path(request.project_id))
    dest = resolve_user_path(
        request.destination_path, base_root=project_root_path(request.project_id)
    )
    if not target.exists() or not target.is_file():
        raise NotFoundError("archive file not found")
    dest.mkdir(parents=True, exist_ok=True)
    archive_type = (
        _infer_archive_type(target) if request.archive_type == "auto" else request.archive_type
    )
    return target, dest, archive_type


def _extract_zip_archive(spec: ZipExtractSpec) -> tuple[int, bool]:
    extracted = 0
    partial = False
    with zipfile.ZipFile(spec.target) as zip_file:
        names = spec.selected_entries or zip_file.namelist()
        for name in names:
            try:
                delta = _record_extract_result(
                    *_extract_one_zip_entry(zip_file, name, spec.dest, spec.overwrite),
                    spec.warnings,
                )
                extracted += delta
                partial = partial or delta == 0
            except (OSError, RuntimeError, ValueError, TypeError, zipfile.BadZipFile) as exc:
                spec.warnings.append({"kind": "extract_skip", "message": str(exc), "path": name})
                partial = True
    return extracted, partial


def _unsupported_extract_warning(archive_type: str, target: Path) -> JsonObject:
    return {
        "kind": "unsupported_archive_type",
        "message": f"Extraction for {archive_type} is limited in this build",
        "path": str(target),
    }


def _archive_extract_response(spec: ArchiveExtractResponseSpec) -> ArchiveExtractResponse:
    return ArchiveExtractResponse(
        ok=True,
        path=str(spec.target),
        destination_path=str(spec.dest),
        extracted_count=spec.extracted,
        partial=spec.partial,
        warnings=[_warn_item(warning) for warning in spec.warnings],
    )


def extract_archive(request: ArchiveExtractRequest) -> ArchiveExtractResponse:
    target, dest, archive_type = _archive_extract_target(request)
    warnings: list[JsonObject] = []
    if archive_type == "zip":
        extracted, partial = _extract_zip_archive(
            ZipExtractSpec(target, dest, request.selected_entries, request.overwrite, warnings)
        )
    else:
        warnings.append(_unsupported_extract_warning(archive_type, target))
        extracted, partial = 0, True
    return _archive_extract_response(
        ArchiveExtractResponseSpec(target, dest, extracted, partial, warnings)
    )
