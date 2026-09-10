"""Typed API wire models for context, file, search, model, and archive responses."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from collections.abc import MutableMapping

from .control_plane_models import (
    CapacitySnapshot,
    CompactControlSurfaceDescriptor,
    CorruptJobFileRecord,
    ExecutionJobRecord,
    ServerCapabilityRouterDescriptor,
    TextWindow,
)
from .api_wire_common import (
    ErrorEnvelope,
    WarningItem,
    IndexCacheStats,
    _require_object,
    _as_str,
    _as_bool,
    _as_int,
    _as_str_list,
)

JsonObject = MutableMapping[str, Any]


@dataclass
class FileItem:
    path: str
    name: str
    is_dir: bool
    size_bytes: int
    modified_at: float
    extension: str
    artifact_class: str

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass
class FileSlice:
    start_line: int
    end_line: int
    max_bytes: int

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass
class FileListResponse:
    ok: bool
    partial: bool
    warnings: list[WarningItem]
    skipped_paths: list[str]
    root_summary: list[str]
    target: str
    recursive: bool
    count: int
    items: list[FileItem]

    def to_dict(self) -> JsonObject:
        return {
            "ok": self.ok,
            "partial": self.partial,
            "warnings": [w.to_dict() for w in self.warnings],
            "skipped_paths": self.skipped_paths,
            "root_summary": self.root_summary,
            "target": self.target,
            "recursive": self.recursive,
            "count": self.count,
            "items": [item.to_dict() for item in self.items],
        }


@dataclass
class FileReadResponse:
    ok: bool
    file: FileItem
    slice: FileSlice
    content: str

    def to_dict(self) -> JsonObject:
        return {
            "ok": self.ok,
            "file": self.file.to_dict(),
            "slice": self.slice.to_dict(),
            "content": self.content,
        }


@dataclass
class SearchWindow:
    start_line: int
    end_line: int

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass
class SearchHit:
    path: str
    artifact_class: str
    score: float
    best_window: SearchWindow
    excerpt: str

    def to_dict(self) -> JsonObject:
        return {
            "path": self.path,
            "artifact_class": self.artifact_class,
            "score": self.score,
            "best_window": self.best_window.to_dict(),
            "excerpt": self.excerpt,
        }


@dataclass
class FileSearchResponse:
    ok: bool
    partial: bool
    warnings: list[WarningItem]
    skipped_paths: list[str]
    query: str
    target: str
    count: int
    hits: list[SearchHit]
    index_cache: IndexCacheStats

    def to_dict(self) -> JsonObject:
        return {
            "ok": self.ok,
            "partial": self.partial,
            "warnings": [w.to_dict() for w in self.warnings],
            "skipped_paths": self.skipped_paths,
            "query": self.query,
            "target": self.target,
            "count": self.count,
            "hits": [h.to_dict() for h in self.hits],
            "index_cache": self.index_cache.to_dict(),
        }


@dataclass
class RehydrateSelectedItem:
    path: str
    artifact_class: str
    score: float
    window: SearchWindow
    excerpt: str

    def to_dict(self) -> JsonObject:
        return {
            "path": self.path,
            "artifact_class": self.artifact_class,
            "score": self.score,
            "window": self.window.to_dict(),
            "excerpt": self.excerpt,
        }


@dataclass
class RehydrateResponse:
    ok: bool
    partial: bool
    warnings: list[WarningItem]
    skipped_paths: list[str]
    header: JsonObject
    selected: list[RehydrateSelectedItem]
    open_seams: list[str]
    index_cache: IndexCacheStats
    debug_trace: JsonObject | None = None

    def to_dict(self) -> JsonObject:
        data = {
            "ok": self.ok,
            "partial": self.partial,
            "warnings": [w.to_dict() for w in self.warnings],
            "skipped_paths": self.skipped_paths,
            "header": self.header,
            "selected": [selected_entry.to_dict() for selected_entry in self.selected],
            "open_seams": self.open_seams,
            "index_cache": self.index_cache.to_dict(),
        }
        if self.debug_trace is not None:
            data["debug_trace"] = self.debug_trace
        return data


@dataclass
class ModelItem:
    path: str
    name: str
    model_type: str
    size_bytes: int
    modified_at: float

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass
class ModelListResponse:
    ok: bool
    partial: bool
    warnings: list[WarningItem]
    skipped_paths: list[str]
    count: int
    items: list[ModelItem]

    def to_dict(self) -> JsonObject:
        return {
            "ok": self.ok,
            "partial": self.partial,
            "warnings": [w.to_dict() for w in self.warnings],
            "skipped_paths": self.skipped_paths,
            "count": self.count,
            "items": [item.to_dict() for item in self.items],
        }


@dataclass
class ModelInspectResponse:
    ok: bool
    path: str
    model_type: str
    size_bytes: int
    metadata: JsonObject
    partial: bool
    warnings: list[WarningItem]

    def to_dict(self) -> JsonObject:
        return {
            "ok": self.ok,
            "path": self.path,
            "model_type": self.model_type,
            "size_bytes": self.size_bytes,
            "metadata": self.metadata,
            "partial": self.partial,
            "warnings": [w.to_dict() for w in self.warnings],
        }


@dataclass
class ArchiveItem:
    path: str
    name: str
    archive_type: str
    size_bytes: int
    modified_at: float

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass
class ArchiveListResponse:
    ok: bool
    partial: bool
    warnings: list[WarningItem]
    skipped_paths: list[str]
    count: int
    items: list[ArchiveItem]

    def to_dict(self) -> JsonObject:
        return {
            "ok": self.ok,
            "partial": self.partial,
            "warnings": [w.to_dict() for w in self.warnings],
            "skipped_paths": self.skipped_paths,
            "count": self.count,
            "items": [item.to_dict() for item in self.items],
        }


@dataclass
class ArchiveInspectResponse:
    ok: bool
    path: str
    archive_type: str
    entry_count: int
    entries: list[str]
    partial: bool
    warnings: list[WarningItem]

    def to_dict(self) -> JsonObject:
        return {
            "ok": self.ok,
            "path": self.path,
            "archive_type": self.archive_type,
            "entry_count": self.entry_count,
            "entries": self.entries,
            "partial": self.partial,
            "warnings": [w.to_dict() for w in self.warnings],
        }


@dataclass
class ArchiveExtractResponse:
    ok: bool
    path: str
    destination_path: str
    extracted_count: int
    partial: bool
    warnings: list[WarningItem]

    def to_dict(self) -> JsonObject:
        return {
            "ok": self.ok,
            "path": self.path,
            "destination_path": self.destination_path,
            "extracted_count": self.extracted_count,
            "partial": self.partial,
            "warnings": [w.to_dict() for w in self.warnings],
        }


@dataclass
class ProjectPathRequest:
    project_id: str
    path: str = "."

    @classmethod
    def from_json(cls, data: JsonObject) -> "ProjectPathRequest":
        data = _require_object(data)
        path = _as_str(data.get("path") or ".", ".").strip() or "."
        return cls(project_id=_as_str(data.get("project_id", "")), path=path)


@dataclass
class ProjectFilesListRequest(ProjectPathRequest):
    recursive: bool = False
    contains: str | None = None
    limit: int | None = None

    @classmethod
    def from_json(cls, data: JsonObject) -> "ProjectFilesListRequest":
        base = ProjectPathRequest.from_json(data)
        return cls(
            project_id=base.project_id,
            path=base.path,
            recursive=_as_bool(data.get("recursive", False)),
            contains=data.get("contains"),
            limit=data.get("limit"),
        )


@dataclass
class ProjectFilesReadRequest(ProjectPathRequest):
    start_line: int | None = None
    end_line: int | None = None
    max_bytes: int | None = None

    @classmethod
    def from_json(cls, data: JsonObject) -> "ProjectFilesReadRequest":
        base = ProjectPathRequest.from_json(data)
        return cls(
            project_id=base.project_id,
            path=base.path,
            start_line=data.get("start_line"),
            end_line=data.get("end_line"),
            max_bytes=data.get("max_bytes"),
        )


@dataclass
class ProjectFilesSearchRequest(ProjectPathRequest):
    query: str = ""
    artifact_classes: list[str] | None = None
    recursive: bool = True
    limit: int | None = None

    @classmethod
    def from_json(cls, data: JsonObject) -> "ProjectFilesSearchRequest":
        base = ProjectPathRequest.from_json(data)
        artifact_classes = data.get("artifact_classes")
        if artifact_classes is not None:
            artifact_classes = _as_str_list(artifact_classes)
        return cls(
            project_id=base.project_id,
            path=base.path,
            query=_as_str(data.get("query", "")),
            artifact_classes=artifact_classes,
            recursive=_as_bool(data.get("recursive", True), True),
            limit=data.get("limit"),
        )


@dataclass
class ProjectContextRehydrateRequest(ProjectPathRequest):
    topic: str = ""
    budget_bytes: int | None = None
    debug: bool = False

    @classmethod
    def from_json(cls, data: JsonObject) -> "ProjectContextRehydrateRequest":
        base = ProjectPathRequest.from_json(data)
        return cls(
            project_id=base.project_id,
            path=base.path,
            topic=_as_str(data.get("topic", "")),
            budget_bytes=data.get("budget_bytes"),
            debug=_as_bool(data.get("debug", False)),
        )


@dataclass
class ProjectModelsListRequest(ProjectPathRequest):
    recursive: bool = True
    model_type: str = "auto"
    limit: int | None = None

    @classmethod
    def from_json(cls, data: JsonObject) -> "ProjectModelsListRequest":
        base = ProjectPathRequest.from_json(data)
        return cls(
            project_id=base.project_id,
            path=base.path,
            recursive=_as_bool(data.get("recursive", True), True),
            model_type=_as_str(data.get("model_type", "auto"), "auto"),
            limit=data.get("limit"),
        )


@dataclass
class ProjectModelsInspectRequest:
    project_id: str
    path: str
    model_type: str = "auto"

    @classmethod
    def from_json(cls, data: JsonObject) -> "ProjectModelsInspectRequest":
        data = _require_object(data)
        return cls(
            project_id=_as_str(data.get("project_id", "")),
            path=_as_str(data.get("path", "")).strip(),
            model_type=_as_str(data.get("model_type", "auto"), "auto"),
        )


@dataclass
class ProjectArchivesListRequest(ProjectPathRequest):
    recursive: bool = True
    archive_type: str = "auto"
    limit: int | None = None

    @classmethod
    def from_json(cls, data: JsonObject) -> "ProjectArchivesListRequest":
        base = ProjectPathRequest.from_json(data)
        return cls(
            project_id=base.project_id,
            path=base.path,
            recursive=_as_bool(data.get("recursive", True), True),
            archive_type=_as_str(data.get("archive_type", "auto"), "auto"),
            limit=data.get("limit"),
        )


@dataclass
class ProjectArchivesInspectRequest:
    project_id: str
    path: str
    archive_type: str = "auto"
    max_entries: int | None = None

    @classmethod
    def from_json(cls, data: JsonObject) -> "ProjectArchivesInspectRequest":
        data = _require_object(data)
        return cls(
            project_id=_as_str(data.get("project_id", "")),
            path=_as_str(data.get("path", "")).strip(),
            archive_type=_as_str(data.get("archive_type", "auto"), "auto"),
            max_entries=data.get("max_entries"),
        )


@dataclass
class ProjectArchivesExtractRequest:
    project_id: str
    path: str
    destination_path: str
    archive_type: str = "auto"
    selected_entries: list[str] | None = None
    overwrite: bool = False

    @classmethod
    def from_json(cls, data: JsonObject) -> "ProjectArchivesExtractRequest":
        data = _require_object(data)
        selected = data.get("selected_entries")
        if selected is not None:
            selected = _as_str_list(selected)
        return cls(
            project_id=_as_str(data.get("project_id", "")),
            path=_as_str(data.get("path", "")).strip(),
            destination_path=_as_str(data.get("destination_path", "")).strip(),
            archive_type=_as_str(data.get("archive_type", "auto"), "auto"),
            selected_entries=selected,
            overwrite=_as_bool(data.get("overwrite", False)),
        )


@dataclass
class ContextHealthResponse:
    ok: bool
    status: str
    roots: list[str]
    index_cache: JsonObject
    capabilities: list[str]

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass
class FileTreeRequest:
    path: str
    project_id: str = ""
    depth: int | str = 3
    include_hidden: bool = False
    exclude_dirs: list[str] | None = None
    extensions: list[str] | None = None
    min_size_bytes: int = 0
    limit: int | None = 500

    @classmethod
    def from_json(cls, data: JsonObject) -> "FileTreeRequest":
        data = _require_object(data)
        exclude_dirs = data.get("exclude_dirs")
        if exclude_dirs is not None:
            exclude_dirs = _as_str_list(exclude_dirs)
        extensions = data.get("extensions")
        if extensions is not None:
            extensions = _as_str_list(extensions)
        return cls(
            path=_as_str(data.get("path", "")).strip(),
            project_id=_as_str(data.get("project_id", "")),
            depth=data.get("depth", 3),
            include_hidden=_as_bool(data.get("include_hidden", False)),
            exclude_dirs=exclude_dirs,
            extensions=extensions,
            min_size_bytes=max(0, int(data.get("min_size_bytes", 0))),
            limit=data.get("limit", 500),
        )


@dataclass
class FileTreeItem:
    path: str
    rel_path: str
    name: str
    is_dir: bool
    size_bytes: int
    depth: int
    extension: str

    def to_dict(self) -> JsonObject:
        return asdict(self)


@dataclass
class FileTreeResponse:
    ok: bool
    root: str
    count: int
    partial: bool
    items: list[JsonObject]

    def to_dict(self) -> JsonObject:
        return asdict(self)
