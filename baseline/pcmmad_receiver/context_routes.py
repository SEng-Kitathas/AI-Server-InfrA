"""Context HTTP routes for files, search, rehydration, models, and archives."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from .context_engine import (
    ArchiveExtractRequest,
    ArchiveListRequest,
    BadPathError,
    FileListRequest,
    FileReadRequest,
    FileSearchRequest,
    ModelListRequest,
    RehydrateRequest,
    ContextPlaneError,
    NotFoundError,
    extract_archive,
    get_index_cache_stats,
    get_root_summary,
    inspect_archive,
    inspect_model,
    list_archives,
    list_files,
    list_models,
    project_root_path,
    read_file,
    rehydrate_context,
    search_files,
)
from .shared_core import require_valid_api_key
from .api_wire_models import (
    ContextHealthResponse,
    ErrorEnvelope,
    ProjectArchivesExtractRequest,
    ProjectArchivesInspectRequest,
    ProjectArchivesListRequest,
    ProjectContextRehydrateRequest,
    ProjectFilesListRequest,
    ProjectFilesReadRequest,
    ProjectFilesSearchRequest,
    ProjectModelsInspectRequest,
    ProjectModelsListRequest,
)

context_bp = Blueprint("context_plane", __name__, url_prefix="")


def _error(error_code: str, message: str, status: int, **extra: object) -> object:
    return (
        jsonify(
            ErrorEnvelope(ok=False, error_code=error_code, message=message, extra=extra).to_dict()
        ),
        status,
    )


def _auth() -> object | None:
    try:
        require_valid_api_key(request.headers)
        return None
    except PermissionError as exc:
        return _error("UNAUTHORIZED", str(exc), 401)


def _json_body() -> dict:
    data = request.get_json(silent=False, force=True)
    if not isinstance(data, dict):
        raise ValueError("JSON request body must be an object")
    return data


def _handle_context_error(prefix: str, exc: Exception) -> object:
    if isinstance(exc, BadPathError):
        return _error(exc.error_code, str(exc), 400)
    if isinstance(exc, NotFoundError):
        return _error(exc.error_code, str(exc), 404)
    if isinstance(exc, ContextPlaneError):
        return _error(exc.error_code, str(exc), 400)
    return _error(prefix, str(exc), 500)


@context_bp.get("/context/health")
def context_health() -> object:
    auth_error = _auth()
    if auth_error:
        return auth_error
    return jsonify(
        ContextHealthResponse(
            ok=True,
            status="online",
            roots=get_root_summary(),
            index_cache=get_index_cache_stats(),
            capabilities=[
                "files.list",
                "files.read",
                "files.search",
                "context.rehydrate",
                "project.files.list",
                "project.files.read",
                "project.files.search",
                "project.context.rehydrate",
                "project.models.list",
                "project.models.inspect",
                "project.archives.list",
                "project.archives.inspect",
                "project.archives.extract",
            ],
        ).to_dict()
    )


@context_bp.post("/project/files/list")
def project_files_list() -> object:
    auth_error = _auth()
    if auth_error:
        return auth_error
    try:
        req = ProjectFilesListRequest.from_json(_json_body())
        return jsonify(
            list_files(
                FileListRequest(
                    path=req.path,
                    base_root=project_root_path(req.project_id),
                    recursive=req.recursive,
                    contains=req.contains,
                    limit=req.limit,
                )
            ).to_dict()
        )
    except (BadPathError, NotFoundError, ContextPlaneError, ValueError, OSError, TypeError) as exc:
        return _handle_context_error("PROJECT_FILES_LIST_FAILED", exc)


@context_bp.post("/project/files/read")
def project_files_read() -> object:
    auth_error = _auth()
    if auth_error:
        return auth_error
    try:
        req = ProjectFilesReadRequest.from_json(_json_body())
        return jsonify(
            read_file(
                FileReadRequest(
                    path=req.path,
                    base_root=project_root_path(req.project_id),
                    start_line=req.start_line,
                    end_line=req.end_line,
                    max_bytes=req.max_bytes,
                )
            ).to_dict()
        )
    except (
        BadPathError,
        NotFoundError,
        ContextPlaneError,
        ValueError,
        OSError,
        TypeError,
        UnicodeError,
    ) as exc:
        return _handle_context_error("PROJECT_FILES_READ_FAILED", exc)


@context_bp.post("/project/files/search")
def project_files_search() -> object:
    auth_error = _auth()
    if auth_error:
        return auth_error
    try:
        req = ProjectFilesSearchRequest.from_json(_json_body())
        return jsonify(
            search_files(
                FileSearchRequest(
                    query=req.query,
                    base_root=project_root_path(req.project_id),
                    path=req.path,
                    artifact_classes=req.artifact_classes,
                    recursive=req.recursive,
                    limit=req.limit,
                )
            ).to_dict()
        )
    except (
        BadPathError,
        NotFoundError,
        ContextPlaneError,
        ValueError,
        OSError,
        TypeError,
        UnicodeError,
    ) as exc:
        return _handle_context_error("PROJECT_FILES_SEARCH_FAILED", exc)


@context_bp.post("/project/context/rehydrate")
def project_context_rehydrate() -> object:
    auth_error = _auth()
    if auth_error:
        return auth_error
    try:
        req = ProjectContextRehydrateRequest.from_json(_json_body())
        return jsonify(
            rehydrate_context(
                RehydrateRequest(
                    topic=req.topic,
                    base_root=project_root_path(req.project_id),
                    path=req.path,
                    budget_bytes=req.budget_bytes,
                    debug=req.debug,
                )
            )
        )
    except (
        BadPathError,
        NotFoundError,
        ContextPlaneError,
        ValueError,
        OSError,
        TypeError,
        UnicodeError,
    ) as exc:
        return _handle_context_error("PROJECT_CONTEXT_REHYDRATE_FAILED", exc)


@context_bp.post("/project/models/list")
def project_models_list() -> object:
    auth_error = _auth()
    if auth_error:
        return auth_error
    try:
        req = ProjectModelsListRequest.from_json(_json_body())
        return jsonify(
            list_models(
                ModelListRequest(
                    project_id=req.project_id,
                    path=req.path,
                    recursive=req.recursive,
                    model_type=req.model_type,
                    limit=req.limit,
                )
            ).to_dict()
        )
    except (BadPathError, NotFoundError, ContextPlaneError, ValueError, OSError, TypeError) as exc:
        return _handle_context_error("PROJECT_MODELS_LIST_FAILED", exc)


@context_bp.post("/project/models/inspect")
def project_models_inspect() -> object:
    auth_error = _auth()
    if auth_error:
        return auth_error
    try:
        req = ProjectModelsInspectRequest.from_json(_json_body())
        return jsonify(
            inspect_model(
                project_id=req.project_id,
                path=req.path,
                model_type=req.model_type,
            ).to_dict()
        )
    except (BadPathError, NotFoundError, ContextPlaneError, ValueError, OSError, TypeError) as exc:
        return _handle_context_error("PROJECT_MODEL_INSPECT_FAILED", exc)


@context_bp.post("/project/archives/list")
def project_archives_list() -> object:
    auth_error = _auth()
    if auth_error:
        return auth_error
    try:
        req = ProjectArchivesListRequest.from_json(_json_body())
        return jsonify(
            list_archives(
                ArchiveListRequest(
                    project_id=req.project_id,
                    path=req.path,
                    recursive=req.recursive,
                    archive_type=req.archive_type,
                    limit=req.limit,
                )
            ).to_dict()
        )
    except (BadPathError, NotFoundError, ContextPlaneError, ValueError, OSError, TypeError) as exc:
        return _handle_context_error("PROJECT_ARCHIVES_LIST_FAILED", exc)


@context_bp.post("/project/archives/inspect")
def project_archives_inspect() -> object:
    auth_error = _auth()
    if auth_error:
        return auth_error
    try:
        req = ProjectArchivesInspectRequest.from_json(_json_body())
        return jsonify(
            inspect_archive(
                project_id=req.project_id,
                path=req.path,
                archive_type=req.archive_type,
                max_entries=req.max_entries,
            ).to_dict()
        )
    except (BadPathError, NotFoundError, ContextPlaneError, ValueError, OSError, TypeError) as exc:
        return _handle_context_error("PROJECT_ARCHIVE_INSPECT_FAILED", exc)


@context_bp.post("/project/archives/extract")
def project_archives_extract() -> object:
    auth_error = _auth()
    if auth_error:
        return auth_error
    try:
        req = ProjectArchivesExtractRequest.from_json(_json_body())
        return jsonify(
            extract_archive(
                ArchiveExtractRequest(
                    project_id=req.project_id,
                    path=req.path,
                    destination_path=req.destination_path,
                    archive_type=req.archive_type,
                    selected_entries=req.selected_entries,
                    overwrite=req.overwrite,
                )
            ).to_dict()
        )
    except (BadPathError, NotFoundError, ContextPlaneError, ValueError, OSError, TypeError) as exc:
        return _handle_context_error("PROJECT_ARCHIVE_EXTRACT_FAILED", exc)
