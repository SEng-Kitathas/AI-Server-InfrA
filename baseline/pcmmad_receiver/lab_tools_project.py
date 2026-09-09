"""Project lab-tool registration surface for manifests, commits, files, and context handles."""

from __future__ import annotations
from collections.abc import MutableMapping


import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypeAlias

JsonObject = MutableMapping[str, Any]

from context_engine import (
    ArchiveExtractRequest,
    ArchiveListRequest,
    FileListRequest,
    FileReadRequest,
    FileSearchRequest,
    ModelListRequest,
    RehydrateRequest,
)

ToolPayload: TypeAlias = JsonObject
ToolResult: TypeAlias = JsonObject


def _get_str(payload: ToolPayload, key: str, default: str = "") -> str:
    value = payload.get(key, default)
    return default if value is None else str(value)


def _default_positive_int(value: int | None, default: int, *, minimum: int = 1) -> int:
    raw = default if value in (None, 0, -1) else int(value)
    return max(minimum, raw)


def _get_bool(payload: ToolPayload, key: str, default: bool = False) -> bool:
    value = payload.get(key, default)
    return value if isinstance(value, bool) else bool(value)


def _get_int(payload: ToolPayload, key: str, default: int) -> int:
    try:
        return int(payload.get(key, default))
    except (TypeError, ValueError, OverflowError):
        return default


def _get_list(payload: ToolPayload, key: str) -> list[Any]:
    value = payload.get(key)
    return value if isinstance(value, list) else []


def _project_id(payload: ToolPayload) -> str:
    return _get_str(payload, "project_id").strip()


def _payload_project_path(project_id: str, path: str | None = None) -> ToolPayload:
    payload: ToolPayload = {"project_id": project_id}
    if path is not None:
        payload["path"] = path
    return payload


def _optional_positive_int(payload: ToolPayload, key: str) -> int | None:
    raw = payload.get(key)
    if raw is None or raw == "":
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if value > 0 else None


def _string_list(payload: ToolPayload, key: str) -> list[str]:
    return [str(item) for item in _get_list(payload, key)]


def _object_list(payload: ToolPayload, key: str) -> list[ToolPayload]:
    return [item for item in _get_list(payload, key) if isinstance(item, dict)]


@dataclass(frozen=True)
class ProjectPathRequest:
    project_id: str
    path: str

    @classmethod
    def from_payload(cls, payload: ToolPayload) -> "ProjectPathRequest":
        return cls(project_id=_project_id(payload), path=_get_str(payload, "path"))


@dataclass(frozen=True)
class ProjectFilesListRequest:
    project_id: str
    path: str
    recursive: bool
    contains: str | None
    limit: int | None

    @classmethod
    def from_payload(
        cls, payload: ToolPayload, normalize_project_path: Callable[[ToolPayload], str]
    ) -> "ProjectFilesListRequest":
        return cls(
            project_id=_project_id(payload),
            path=normalize_project_path(payload),
            recursive=_get_bool(payload, "recursive", False),
            contains=_get_str(payload, "contains") or None,
            limit=_optional_positive_int(payload, "limit"),
        )


@dataclass(frozen=True)
class ProjectFilesReadRequest:
    project_id: str
    path: str
    start_line: int | None
    end_line: int | None
    max_bytes: int | None

    @classmethod
    def from_payload(
        cls, payload: ToolPayload, normalize_project_path: Callable[[ToolPayload], str]
    ) -> "ProjectFilesReadRequest":
        return cls(
            project_id=_project_id(payload),
            path=normalize_project_path(payload),
            start_line=_optional_positive_int(payload, "start_line"),
            end_line=_optional_positive_int(payload, "end_line"),
            max_bytes=_optional_positive_int(payload, "max_bytes"),
        )


@dataclass(frozen=True)
class ProjectFilesSearchRequest:
    project_id: str
    query: str
    path: str
    artifact_classes: list[str] | None
    recursive: bool
    limit: int | None

    @classmethod
    def from_payload(
        cls, payload: ToolPayload, normalize_project_path: Callable[[ToolPayload], str]
    ) -> "ProjectFilesSearchRequest":
        return cls(
            project_id=_project_id(payload),
            query=_get_str(payload, "query"),
            path=normalize_project_path(payload),
            artifact_classes=_string_list(payload, "artifact_classes") or None,
            recursive=_get_bool(payload, "recursive", True),
            limit=_optional_positive_int(payload, "limit"),
        )


@dataclass(frozen=True)
class ProjectContextRehydrateRequest:
    project_id: str
    topic: str
    path: str
    budget_bytes: int | None
    debug: bool

    @classmethod
    def from_payload(
        cls, payload: ToolPayload, normalize_project_path: Callable[[ToolPayload], str]
    ) -> "ProjectContextRehydrateRequest":
        return cls(
            project_id=_project_id(payload),
            topic=_get_str(payload, "topic"),
            path=normalize_project_path(payload),
            budget_bytes=_optional_positive_int(payload, "budget_bytes"),
            debug=_get_bool(payload, "debug", False),
        )


@dataclass(frozen=True)
class ProjectModelsListRequest:
    project_id: str
    path: str
    recursive: bool
    model_type: str
    limit: int | None

    @classmethod
    def from_payload(
        cls, payload: ToolPayload, normalize_project_path: Callable[[ToolPayload], str]
    ) -> "ProjectModelsListRequest":
        return cls(
            project_id=_project_id(payload),
            path=normalize_project_path(payload),
            recursive=_get_bool(payload, "recursive", True),
            model_type=_get_str(payload, "model_type", "auto"),
            limit=_optional_positive_int(payload, "limit"),
        )


@dataclass(frozen=True)
class ProjectModelInspectRequest:
    project_id: str
    path: str
    model_type: str

    @classmethod
    def from_payload(cls, payload: ToolPayload) -> "ProjectModelInspectRequest":
        return cls(
            project_id=_project_id(payload),
            path=_get_str(payload, "path"),
            model_type=_get_str(payload, "model_type", "auto"),
        )


@dataclass(frozen=True)
class ProjectArchivesListRequest:
    project_id: str
    path: str
    recursive: bool
    archive_type: str
    limit: int | None

    @classmethod
    def from_payload(
        cls, payload: ToolPayload, normalize_project_path: Callable[[ToolPayload], str]
    ) -> "ProjectArchivesListRequest":
        return cls(
            project_id=_project_id(payload),
            path=normalize_project_path(payload),
            recursive=_get_bool(payload, "recursive", True),
            archive_type=_get_str(payload, "archive_type", "auto"),
            limit=_optional_positive_int(payload, "limit"),
        )


@dataclass(frozen=True)
class ProjectArchiveInspectRequest:
    project_id: str
    path: str
    archive_type: str
    max_entries: int | None

    @classmethod
    def from_payload(cls, payload: ToolPayload) -> "ProjectArchiveInspectRequest":
        return cls(
            project_id=_project_id(payload),
            path=_get_str(payload, "path"),
            archive_type=_get_str(payload, "archive_type", "auto"),
            max_entries=_optional_positive_int(payload, "max_entries"),
        )


@dataclass(frozen=True)
class ProjectArchiveExtractRequest:
    project_id: str
    path: str
    destination_path: str
    archive_type: str
    selected_entries: list[str]
    overwrite: bool

    @classmethod
    def from_payload(cls, payload: ToolPayload) -> "ProjectArchiveExtractRequest":
        return cls(
            project_id=_project_id(payload),
            path=_get_str(payload, "path"),
            destination_path=_get_str(payload, "destination_path"),
            archive_type=_get_str(payload, "archive_type", "auto"),
            selected_entries=_string_list(payload, "selected_entries"),
            overwrite=_get_bool(payload, "overwrite", False),
        )


@dataclass(frozen=True)
class ReadManyFileEntry:
    content: str = ""
    size_bytes: int = 0
    truncated: bool = False
    error: str | None = None

    @classmethod
    def from_read_result(cls, result: object) -> "ReadManyFileEntry":
        as_dict = result.to_dict() if hasattr(result, "to_dict") else result
        data = as_dict if isinstance(as_dict, dict) else {}
        return cls(
            content=_get_str(data, "content"),
            size_bytes=_get_int(data, "size_bytes", 0),
            truncated=_get_bool(data, "truncated", False),
        )

    @classmethod
    def from_error(cls, exc: Exception) -> "ReadManyFileEntry":
        return cls(error=str(exc))

    def to_dict(self) -> ToolResult:
        data: ToolResult = {
            "truncated": self.truncated,
            "size_bytes": self.size_bytes,
        }
        if self.error is not None:
            data["error"] = self.error
        else:
            data["content"] = self.content
        return data


@dataclass(frozen=True)
class ZipEntryReadResult:
    ok: bool
    entry_name: str
    content: str | None = None
    size_bytes: int | None = None
    truncated: bool | None = None
    error: str | None = None

    @classmethod
    def from_bridge_result(cls, entry_name: str, payload: ToolPayload) -> "ZipEntryReadResult":
        return cls(
            ok=_get_bool(payload, "ok", True),
            entry_name=entry_name,
            content=_get_str(payload, "content") if "content" in payload else None,
            size_bytes=_optional_positive_int(payload, "size_bytes"),
            truncated=_get_bool(payload, "truncated", False) if "truncated" in payload else None,
            error=_get_str(payload, "error") or None,
        )

    @classmethod
    def from_error(cls, entry_name: str, exc: Exception) -> "ZipEntryReadResult":
        return cls(ok=False, entry_name=entry_name, error=str(exc))

    def to_dict(self) -> ToolResult:
        data: ToolResult = {"ok": self.ok, "entry_name": self.entry_name}
        if self.content is not None:
            data["content"] = self.content
        if self.size_bytes is not None:
            data["size_bytes"] = self.size_bytes
        if self.truncated is not None:
            data["truncated"] = self.truncated
        if self.error is not None:
            data["error"] = self.error
        return data


@dataclass(frozen=True)
class ProjectRef:
    project_id: str

    @classmethod
    def from_payload(cls, payload: ToolPayload) -> "ProjectRef":
        project_id = _project_id(payload)
        return cls(project_id=project_id)


@dataclass(frozen=True)
class ProjectFilesReadManyRequest:
    project_id: str
    paths: list[str]
    max_bytes_each: int

    @classmethod
    def from_payload(
        cls, error_cls: type[Exception], payload: ToolPayload
    ) -> "ProjectFilesReadManyRequest":
        project_id = _project_id(payload)
        paths = [str(item) for item in _get_list(payload, "paths")]
        if not paths:
            raise error_cls("BAD_REQUEST", "paths must be a non-empty array", 400)
        if len(paths) > 50:
            raise error_cls("BAD_REQUEST", "paths limit is 50", 400)
        max_bytes_each = max(
            1,
            min(_get_int(payload, "max_bytes_each", _get_int(payload, "max_bytes", 50000)), 200000),
        )
        return cls(project_id=project_id, paths=paths, max_bytes_each=max_bytes_each)


@dataclass(frozen=True)
class ProjectWriteRequest:
    project_id: str
    path: str
    content: str
    mode: str
    encoding: str

    @classmethod
    def from_payload(
        cls,
        error_cls: type[Exception],
        ensure_project_layout: Callable[[ToolPayload], str],
        payload: ToolPayload,
    ) -> "ProjectWriteRequest":
        project_id = ensure_project_layout(payload)
        rel_path = _get_str(payload, "path").strip()
        if not rel_path:
            raise error_cls("BAD_REQUEST", "path is required", 400)
        mode = _get_str(payload, "mode", "overwrite")
        if mode not in {"overwrite", "append", "create_only"}:
            raise error_cls("BAD_REQUEST", "mode must be overwrite, append, or create_only", 400)
        return cls(
            project_id=project_id,
            path=rel_path,
            content=_get_str(payload, "content"),
            mode=mode,
            encoding=_get_str(payload, "encoding", "utf-8"),
        )


@dataclass(frozen=True)
class PathResolverSpec:
    error_cls: type[Exception]
    ensure_within_allowed: Callable[[Path], Path]
    resolve_general_path: Callable[..., Path]
    request_optional_positive_int: Callable[..., int | None] | None = None


@dataclass(frozen=True)
class FsTreeRequest:
    root: Path
    depth: int
    include_hidden: bool
    exclude_dirs: set[str]
    extensions: set[str] | None
    min_size_bytes: int
    limit: int

    @classmethod
    def from_payload(cls, payload: ToolPayload, spec: PathResolverSpec) -> "FsTreeRequest":
        root = spec.ensure_within_allowed(spec.resolve_general_path(payload))
        if not root.exists():
            raise spec.error_cls("NOT_FOUND", "root path not found", 404)
        ext_raw = _get_list(payload, "extensions") or None
        return cls(
            root=root,
            depth=max(1, min(_get_int(payload, "depth", 3), 10)),
            include_hidden=_get_bool(payload, "include_hidden", False),
            exclude_dirs=set(
                _get_list(payload, "exclude_dirs")
                or ["__pycache__", ".git", "node_modules", ".venv", ".venv_cuda", "vendor"]
            ),
            extensions={str(x).lower() for x in ext_raw} if ext_raw else None,
            min_size_bytes=max(0, _get_int(payload, "min_size_bytes", 0)),
            limit=(spec.request_optional_positive_int or _default_positive_int)(
                _get_int(payload, "limit", 500), 500, minimum=1
            ),
        )


@dataclass(frozen=True)
class ZipReadRequest:
    zip_path: Path
    entries: list[str]
    max_entry_bytes: int

    @classmethod
    def from_payload(cls, payload: JsonObject, spec: PathResolverSpec) -> "ZipReadRequest":
        zip_path = spec.ensure_within_allowed(spec.resolve_general_path(payload, "zip_path"))
        if not zip_path.exists():
            raise spec.error_cls("NOT_FOUND", "zip archive not found", 404)
        return cls(
            zip_path=zip_path,
            entries=[str(item) for item in _get_list(payload, "entries")],
            max_entry_bytes=max(1024, min(_get_int(payload, "max_entry_bytes", 65536), 1048576)),
        )


@dataclass(frozen=True)
class ProjectToolDeps:
    error_cls: type[Exception]
    context_wrap: Callable[..., ToolResult]
    normalize_project_path: Callable[[ToolPayload], str]
    project_root_path: Callable[[str], str]
    list_files: Callable[..., ToolResult]
    read_file: Callable[..., ToolResult]
    search_files: Callable[..., ToolResult]
    rehydrate_context: Callable[..., ToolResult]
    list_models: Callable[..., ToolResult]
    inspect_model: Callable[..., ToolResult]
    list_archives: Callable[..., ToolResult]
    inspect_archive: Callable[..., ToolResult]
    extract_archive: Callable[..., ToolResult]
    ensure_project_layout: Callable[[ToolPayload], str]
    get_project_root: Callable[[str], Path]
    ensure_parent: Callable[[Path], None]
    sha256_file: Callable[[Path], str]
    utc_now: Callable[[], str]
    request_optional_positive_int: Callable[..., int | None]
    ensure_within_allowed: Callable[[Path], Path]
    resolve_general_path: Callable[..., Path]
    bounded_zip_entry_text: Callable[..., ToolResult]
    iter_tree: Callable[..., tuple[list[ToolResult], bool]]


def _project_deps(deps: JsonObject) -> ProjectToolDeps:
    return ProjectToolDeps(
        error_cls=deps["error_cls"],
        context_wrap=deps["context_wrap"],
        normalize_project_path=deps["normalize_project_path"],
        project_root_path=deps["project_root_path"],
        list_files=deps["list_files"],
        read_file=deps["read_file"],
        search_files=deps["search_files"],
        rehydrate_context=deps["rehydrate_context"],
        list_models=deps["list_models"],
        inspect_model=deps["inspect_model"],
        list_archives=deps["list_archives"],
        inspect_archive=deps["inspect_archive"],
        extract_archive=deps["extract_archive"],
        ensure_project_layout=deps["ensure_project_layout"],
        get_project_root=deps["get_project_root"],
        ensure_parent=deps["ensure_parent"],
        sha256_file=deps["sha256_file"],
        utc_now=deps["utc_now"],
        request_optional_positive_int=deps["request_optional_positive_int"],
        ensure_within_allowed=deps["ensure_within_allowed"],
        resolve_general_path=deps["resolve_general_path"],
        bounded_zip_entry_text=deps["bounded_zip_entry_text"],
        iter_tree=deps["iter_tree"],
    )


def _project_files_list_payload(payload: ToolPayload, dep: ProjectToolDeps) -> ToolResult:
    request = ProjectFilesListRequest.from_payload(payload, dep.normalize_project_path)
    result = dep.context_wrap(
        lambda: dep.list_files(
            FileListRequest(
                path=request.path,
                base_root=dep.project_root_path(request.project_id),
                recursive=request.recursive,
                contains=request.contains,
                limit=request.limit,
            )
        )
    )
    return result.to_dict() if hasattr(result, "to_dict") else result


def _project_files_read_payload(payload: ToolPayload, dep: ProjectToolDeps) -> ToolResult:
    request = ProjectFilesReadRequest.from_payload(payload, dep.normalize_project_path)
    return dep.context_wrap(
        lambda: dep.read_file(
            FileReadRequest(
                path=request.path,
                base_root=dep.project_root_path(request.project_id),
                start_line=request.start_line,
                end_line=request.end_line,
                max_bytes=request.max_bytes,
            )
        )
    )


def _project_files_search_payload(payload: ToolPayload, dep: ProjectToolDeps) -> ToolResult:
    request = ProjectFilesSearchRequest.from_payload(payload, dep.normalize_project_path)
    return dep.context_wrap(
        lambda: dep.search_files(
            FileSearchRequest(
                query=request.query,
                base_root=dep.project_root_path(request.project_id),
                path=request.path,
                artifact_classes=request.artifact_classes,
                recursive=request.recursive,
                limit=request.limit,
            )
        )
    )


def _project_context_rehydrate_payload(payload: ToolPayload, dep: ProjectToolDeps) -> ToolResult:
    request = ProjectContextRehydrateRequest.from_payload(payload, dep.normalize_project_path)
    return dep.context_wrap(
        lambda: dep.rehydrate_context(
            RehydrateRequest(
                topic=request.topic,
                base_root=dep.project_root_path(request.project_id),
                path=request.path,
                budget_bytes=request.budget_bytes,
                debug=request.debug,
            )
        )
    )


def _register_project_file_tools(register_tool: Callable[..., Any], dep: ProjectToolDeps) -> None:
    @register_tool(
        "project.files.list", "List files under a project path.", "low", category="project", side_effect_class="read", effect_traits=["reads_files", "project_scope_enforced", "bounded_results"]
    )
    def tool_project_files_list(payload: ToolPayload) -> ToolResult:
        return _project_files_list_payload(payload, dep)

    @register_tool(
        "project.files.read", "Read one project file or a line range.", "low", category="project", side_effect_class="read", effect_traits=["reads_files", "project_scope_enforced", "bounded_output"]
    )
    def tool_project_files_read(payload: ToolPayload) -> ToolResult:
        return _project_files_read_payload(payload, dep)

    @register_tool(
        "project.files.search", "Search within project files.", "low", category="project", side_effect_class="read_cache", effect_traits=["reads_files", "project_scope_enforced", "writes_ephemeral_cache", "bounded_results", "source_currentness_check"]
    )
    def tool_project_files_search(payload: ToolPayload) -> ToolResult:
        return _project_files_search_payload(payload, dep)

    @register_tool(
        "project.context.rehydrate",
        "Rehydrate bounded project context on a topic.",
        "low",
        category="project",
        side_effect_class="read_cache",
        effect_traits=["reads_files", "project_scope_enforced", "writes_ephemeral_cache", "bounded_output", "source_currentness_check", "icf_authority_aware"],
    )
    def tool_project_context_rehydrate(payload: ToolPayload) -> ToolResult:
        return _project_context_rehydrate_payload(payload, dep)


def _project_models_list_payload(payload: ToolPayload, dep: ProjectToolDeps) -> ToolResult:
    request = ProjectModelsListRequest.from_payload(payload, dep.normalize_project_path)
    return dep.context_wrap(
        lambda: dep.list_models(
            ModelListRequest(
                project_id=request.project_id,
                path=request.path,
                recursive=request.recursive,
                model_type=request.model_type,
                limit=request.limit,
            )
        )
    )


def _project_model_inspect_payload(payload: ToolPayload, dep: ProjectToolDeps) -> ToolResult:
    request = ProjectModelInspectRequest.from_payload(payload)
    return dep.context_wrap(
        lambda: dep.inspect_model(
            project_id=request.project_id, path=request.path, model_type=request.model_type
        )
    )


def _register_project_model_tools(register_tool: Callable[..., Any], dep: ProjectToolDeps) -> None:
    @register_tool(
        "project.models.list", "List model artifacts in a project.", "low", category="project", side_effect_class="read", effect_traits=["reads_files", "project_scope_enforced", "bounded_results"]
    )
    def tool_project_models_list(payload: ToolPayload) -> ToolResult:
        return _project_models_list_payload(payload, dep)

    @register_tool(
        "project.models.inspect",
        "Inspect a model artifact in a project.",
        "low",
        category="project",
        side_effect_class="read",
        effect_traits=["reads_files", "project_scope_enforced"],
    )
    def tool_project_models_inspect(payload: ToolPayload) -> ToolResult:
        return _project_model_inspect_payload(payload, dep)


def _project_archives_list_payload(payload: ToolPayload, dep: ProjectToolDeps) -> ToolResult:
    request = ProjectArchivesListRequest.from_payload(payload, dep.normalize_project_path)
    return dep.context_wrap(
        lambda: dep.list_archives(
            ArchiveListRequest(
                project_id=request.project_id,
                path=request.path,
                recursive=request.recursive,
                archive_type=request.archive_type,
                limit=request.limit,
            )
        )
    )


def _project_archive_inspect_payload(payload: ToolPayload, dep: ProjectToolDeps) -> ToolResult:
    request = ProjectArchiveInspectRequest.from_payload(payload)
    return dep.context_wrap(
        lambda: dep.inspect_archive(
            project_id=request.project_id,
            path=request.path,
            archive_type=request.archive_type,
            max_entries=request.max_entries,
        )
    )


def _project_archive_extract_payload(payload: ToolPayload, dep: ProjectToolDeps) -> ToolResult:
    request = ProjectArchiveExtractRequest.from_payload(payload)
    archive_request = ArchiveExtractRequest(
        project_id=request.project_id,
        path=request.path,
        destination_path=request.destination_path,
        archive_type=request.archive_type,
        selected_entries=request.selected_entries,
        overwrite=request.overwrite,
    )
    return dep.context_wrap(lambda: dep.extract_archive(archive_request))


def _register_project_archive_tools(
    register_tool: Callable[..., Any], dep: ProjectToolDeps
) -> None:
    @register_tool(
        "project.archives.list", "List archive artifacts in a project.", "low", category="project", side_effect_class="read", effect_traits=["reads_files", "project_scope_enforced", "bounded_results"]
    )
    def tool_project_archives_list(payload: ToolPayload) -> ToolResult:
        return _project_archives_list_payload(payload, dep)

    @register_tool(
        "project.archives.inspect", "Inspect an archive in a project.", "low", category="project",
        side_effect_class="read", effect_traits=["reads_files", "reads_archive", "project_scope_enforced", "bounded_output"]
    )
    def tool_project_archives_inspect(payload: ToolPayload) -> ToolResult:
        return _project_archive_inspect_payload(payload, dep)

    @register_tool(
        "project.archives.extract",
        "Extract an archive within a project.",
        "high",
        category="project",
        approval_required=True,
        mutating=True,
        effect_traits=["durable_mutation", "project_mutation_fenced"],
    )
    def tool_project_archives_extract(payload: ToolPayload) -> ToolResult:
        return _project_archive_extract_payload(payload, dep)


def _project_read_one_many(
    path: str, root: Path, request: ProjectFilesReadManyRequest, dep: ProjectToolDeps
) -> tuple[str, ToolResult, bool]:
    try:
        result = dep.read_file(
            FileReadRequest(path=path, base_root=str(root), max_bytes=request.max_bytes_each)
        )
        return path, ReadManyFileEntry.from_read_result(result).to_dict(), False
    except (OSError, RuntimeError, ValueError, TypeError, UnicodeError) as exc:
        return path, ReadManyFileEntry.from_error(exc).to_dict(), True


def _project_read_many_payload(payload: ToolPayload, dep: ProjectToolDeps) -> ToolResult:
    request = ProjectFilesReadManyRequest.from_payload(dep.error_cls, payload)
    root = dep.get_project_root(request.project_id)
    files: ToolResult = {}
    error_count = 0
    for path in request.paths:
        key, value, failed = _project_read_one_many(path, root, request, dep)
        files[key] = value
        error_count += 1 if failed else 0
    return {
        "project_id": request.project_id,
        "files": files,
        "read_count": len(request.paths) - error_count,
        "error_count": error_count,
    }


def _project_write_payload(payload: ToolPayload, dep: ProjectToolDeps) -> ToolResult:
    request = ProjectWriteRequest.from_payload(dep.error_cls, dep.ensure_project_layout, payload)
    root = dep.get_project_root(request.project_id)
    target = (root / request.path).resolve()
    if root.resolve() not in [target, *target.parents]:
        raise dep.error_cls("BAD_PATH", "path escapes project root", 400)
    if request.mode == "create_only" and target.exists():
        raise dep.error_cls("ALREADY_EXISTS", "file exists and mode=create_only", 409)
    dep.ensure_parent(target)
    if request.mode == "append":
        with target.open("a", encoding=request.encoding) as handle:
            handle.write(request.content)
    else:
        target.write_text(request.content, encoding=request.encoding)
    return {
        "project_id": request.project_id,
        "path": str(target.relative_to(root)),
        "absolute_path": str(target),
        "bytes_written": target.stat().st_size,
        "sha256": dep.sha256_file(target),
        "time": dep.utc_now(),
    }


def _register_project_mutation_tools(
    register_tool: Callable[..., Any], dep: ProjectToolDeps
) -> None:
    @register_tool(
        "project.files.read_many",
        "Read many project files in a single dispatch.",
        "medium",
        category="project",
        side_effect_class="read",
        effect_traits=["reads_files", "project_scope_enforced", "bounded_output"],
    )
    def tool_project_files_read_many(payload: ToolPayload) -> ToolResult:
        return _project_read_many_payload(payload, dep)

    @register_tool(
        "project.files.write",
        "Write or append a project file directly.",
        "high",
        category="project",
        approval_required=True,
        mutating=True,
        effect_traits=["durable_mutation", "project_mutation_fenced"],
    )
    def tool_project_files_write(payload: ToolPayload) -> ToolResult:
        return _project_write_payload(payload, dep)


def _project_path_resolver(dep: ProjectToolDeps) -> PathResolverSpec:
    return PathResolverSpec(
        dep.error_cls,
        dep.ensure_within_allowed,
        dep.resolve_general_path,
        dep.request_optional_positive_int,
    )


def _project_fs_tree_payload(payload: ToolPayload, dep: ProjectToolDeps) -> ToolResult:
    request = FsTreeRequest.from_payload(payload, _project_path_resolver(dep))
    items, partial = dep.iter_tree(
        request.root,
        request.depth,
        request.include_hidden,
        request.exclude_dirs,
        request.extensions,
        request.min_size_bytes,
        request.limit,
    )
    return {"root": str(request.root), "count": len(items), "partial": partial, "items": items}


def _project_zip_read_payload(payload: ToolPayload, dep: ProjectToolDeps) -> ToolResult:
    request = ZipReadRequest.from_payload(payload, _project_path_resolver(dep))
    with zipfile.ZipFile(request.zip_path, "r") as zf:
        listing = [
            {
                "name": info.filename,
                "file_size": info.file_size,
                "compress_size": info.compress_size,
                "is_dir": info.is_dir(),
            }
            for info in zf.infolist()
        ]
        contents: ToolResult = {}
        for name in request.entries:
            try:
                contents[str(name)] = ZipEntryReadResult.from_bridge_result(
                    str(name), dep.bounded_zip_entry_text(zf, str(name), request.max_entry_bytes)
                ).to_dict()
            except (KeyError, OSError, RuntimeError, ValueError, TypeError) as exc:
                contents[str(name)] = ZipEntryReadResult.from_error(str(name), exc).to_dict()
    return {"zip_path": str(request.zip_path), "listing": listing, "contents": contents}


def _register_project_filesystem_tools(
    register_tool: Callable[..., Any], dep: ProjectToolDeps
) -> None:
    @register_tool(
        "fs.tree",
        "Traverse a filesystem tree from a mounted or absolute path.",
        "high",
        category="filesystem",
        approval_required=True,
    )
    def tool_fs_tree(payload: ToolPayload) -> ToolResult:
        return _project_fs_tree_payload(payload, dep)

    @register_tool(
        "zip.read",
        "List or read entries from a mounted or absolute zip archive.",
        "medium",
        category="filesystem",
    )
    def tool_zip_read(payload: ToolPayload) -> ToolResult:
        return _project_zip_read_payload(payload, dep)


def register_project_tools(
    register_tool: (
        Callable[
            ...,
            Callable[[Callable[[ToolPayload], ToolResult]], Callable[[ToolPayload], ToolResult]],
        ]
        | Callable[..., Any]
    ),
    **deps: Any,
) -> None:
    dep = _project_deps(deps)
    _register_project_file_tools(register_tool, dep)
    _register_project_model_tools(register_tool, dep)
    _register_project_archive_tools(register_tool, dep)
    _register_project_mutation_tools(register_tool, dep)
    _register_project_filesystem_tools(register_tool, dep)
