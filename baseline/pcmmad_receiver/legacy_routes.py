"""Legacy control-plane routes for project manifests, planning, and append-only commits."""

from __future__ import annotations
from dataclasses import dataclass

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any
from collections.abc import MutableMapping

JsonObject = MutableMapping[str, Any]

from flask import Blueprint, jsonify, request

from .control_plane_models import CommitLedgerRecord, ManifestDocument, ManifestEntryRecord
from .execution_routes import execution_capabilities
from .api_wire_models import CompactCapabilitiesResponse
from .lab_tools import compact_control_surface_descriptor, server_native_router_descriptor
from .project_mutation_authority import ProjectMutationAuthorityError, consequence_guard
from .shared_core import (
    ensure_safe_mutation_target_identity,
    ALLOWED_OPERATIONS,
    APPEND_ALLOWED_CLASSES,
    ARTIFACT_RELATIVE_MAP,
    PROJECTS_ROOT,
    ROOT,
    append_jsonl,
    capabilities,
    commits_ledger_path_for,
    ensure_parent,
    get_project_root,
    idempotency_path_for,
    init_project_layout,
    load_json,
    manifest_path_for,
    require_valid_api_key,
    resolve_target,
    save_json_atomic,
    sha256_bytes,
    sha256_file,
    sha256_text,
    utc_now,
)

from .runtime_axioms import constitutional_seed

legacy_bp = Blueprint("legacy", __name__, url_prefix="")


class LegacyIdempotencyError(RuntimeError):
    def __init__(self, error_code: str, message: str, status: int = 409) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status = status


@dataclass(frozen=True)
class ManifestUpdateSpec:
    project_id: str
    target: Path
    artifact_class: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class LegacyPlanRequest:
    project_id: str
    artifact_class: str
    logical_name: str
    operation: str
    content: str
    provided_sha: str | None
    expected_previous_sha: str | None

    @classmethod
    def from_payload(cls, payload: JsonObject) -> "LegacyPlanRequest":
        return cls(
            project_id=str(payload.get("project_id", "")),
            artifact_class=str(payload.get("artifact_class", "")),
            logical_name=str(payload.get("logical_name", "")),
            operation=str(payload.get("operation", "")),
            content=str(payload.get("content", "")),
            provided_sha=payload.get("sha256") if isinstance(payload.get("sha256"), str) else None,
            expected_previous_sha=(
                payload.get("expected_previous_sha256")
                if isinstance(payload.get("expected_previous_sha256"), str)
                else None
            ),
        )


@dataclass(frozen=True)
class LegacyCommitRequest:
    plan: LegacyPlanRequest
    session_id: str
    commit_id: str
    idempotency_key: str
    mutation_authority: dict[str, Any] | None = None

    @classmethod
    def from_payload(cls, payload: JsonObject) -> "LegacyCommitRequest":
        return cls(
            plan=LegacyPlanRequest.from_payload(payload),
            session_id=str(payload.get("session_id", "")),
            commit_id=str(payload.get("commit_id", "")),
            idempotency_key=str(payload.get("idempotency_key", "")),
            mutation_authority=(dict(payload["mutation_authority"]) if isinstance(payload.get("mutation_authority"), dict) else None),
        )


@dataclass(frozen=True)
class LegacyValidationResult:
    request: LegacyPlanRequest
    target: Path
    current_sha: str | None
    computed_sha: str


def error_response(error_code: str, message: str, status: int, **extra: Any) -> object:
    payload = {"ok": False, "error_code": error_code, "message": message, "time": utc_now()}
    payload.update(extra)
    return jsonify(payload), status


def require_api_key() -> object | None:
    try:
        require_valid_api_key(request.headers)
        return None
    except PermissionError as e:
        return error_response("UNAUTHORIZED", str(e), 401)


def get_request_json() -> JsonObject:
    data = request.get_json(silent=False, force=True)
    if not isinstance(data, dict):
        raise ValueError("JSON request body must be an object")
    return data


def get_manifest(project_id: str) -> ManifestDocument:
    raw = load_json(manifest_path_for(project_id), {"updated_at": None, "files": {}})
    return ManifestDocument.from_dict(raw if isinstance(raw, dict) else {})


def save_manifest(project_id: str, manifest: ManifestDocument) -> None:
    manifest.updated_at = utc_now()
    save_json_atomic(manifest_path_for(project_id), manifest.to_dict())


def update_manifest_entry(spec: ManifestUpdateSpec) -> None:
    manifest = get_manifest(spec.project_id)
    rel = str(spec.target.relative_to(get_project_root(spec.project_id)))
    manifest.files[rel] = ManifestEntryRecord(
        artifact_class=spec.artifact_class,
        sha256=spec.sha256,
        bytes=spec.size_bytes,
        updated_at=utc_now(),
    )
    save_manifest(spec.project_id, manifest)


def _legacy_request_fingerprint(request_model: LegacyCommitRequest) -> str:
    plan = request_model.plan
    payload = {
        "project_id": plan.project_id,
        "artifact_class": plan.artifact_class,
        "logical_name": plan.logical_name,
        "operation": plan.operation,
        "content_sha256": sha256_text(plan.content),
        "provided_sha256": plan.provided_sha,
        "expected_previous_sha256": plan.expected_previous_sha,
        "session_id": request_model.session_id,
        "commit_id": request_model.commit_id,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_idempotency(project_id: str) -> dict[str, JsonObject]:
    raw = load_json(idempotency_path_for(project_id), {})
    if not isinstance(raw, dict):
        return {}
    out: dict[str, JsonObject] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            continue
        if "state" in value:
            out[key] = dict(value)
            continue
        # Backward compatibility: historical entries were bare CommitLedgerRecord
        # payloads. They remain replayable but cannot retroactively prove request
        # fingerprint equality.
        try:
            record = CommitLedgerRecord.from_dict(value)
        except (TypeError, ValueError, KeyError):
            continue
        out[key] = {
            "version": 1,
            "state": "committed",
            "request_fingerprint": None,
            "record": record.to_dict(),
        }
    return out


def save_idempotency(project_id: str, data: dict[str, JsonObject]) -> None:
    save_json_atomic(idempotency_path_for(project_id), data)


def _legacy_text_write_bytes(content: str) -> bytes:
    # Legacy writers use text mode with newline=None, so Python translates LF to
    # the platform line separator on write. Idempotency recovery must bind the
    # physical target bytes, not only the logical request string.
    rendered = content.replace("\n", os.linesep) if os.linesep != "\n" else content
    return rendered.encode("utf-8")


def _intended_final_sha(validation: LegacyValidationResult) -> str:
    plan = validation.request
    written = _legacy_text_write_bytes(plan.content)
    if plan.operation != "append":
        return hashlib.sha256(written).hexdigest()
    digest = hashlib.sha256()
    with validation.target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    digest.update(written)
    return digest.hexdigest()


def _prepared_idempotency_entry(
    request_model: LegacyCommitRequest, validation: LegacyValidationResult
) -> JsonObject:
    plan = request_model.plan
    return {
        "version": 2,
        "state": "prepared",
        "request_fingerprint": _legacy_request_fingerprint(request_model),
        "project_id": plan.project_id,
        "session_id": request_model.session_id,
        "commit_id": request_model.commit_id,
        "idempotency_key": request_model.idempotency_key,
        "artifact_class": plan.artifact_class,
        "logical_name": plan.logical_name,
        "operation": plan.operation,
        "before_sha256": validation.current_sha,
        "intended_final_sha256": _intended_final_sha(validation),
        "prepared_at": utc_now(),
        "record": None,
    }


def _committed_idempotency_entry(entry: JsonObject, record: CommitLedgerRecord) -> JsonObject:
    committed = dict(entry)
    committed["state"] = "committed"
    committed["record"] = record.to_dict()
    committed["committed_at"] = utc_now()
    return committed


def _entry_record(entry: JsonObject) -> CommitLedgerRecord | None:
    raw = entry.get("record")
    return CommitLedgerRecord.from_dict(raw) if isinstance(raw, dict) else None


def _assert_idempotency_request_matches(
    request_model: LegacyCommitRequest, entry: JsonObject
) -> None:
    expected = str(entry.get("request_fingerprint") or "")
    if expected and expected != _legacy_request_fingerprint(request_model):
        raise LegacyIdempotencyError("IDEMPOTENCY_KEY_CONFLICT", "idempotency_key already belongs to another commit request")



def validate_operation_semantics(operation: str, artifact_class: str, target: Path) -> None:
    exists = target.exists()
    if operation == "create" and exists:
        raise ValueError("create is not allowed when target already exists")
    if operation == "update" and not exists:
        raise ValueError("update is not allowed when target does not exist")
    if operation == "append":
        if artifact_class not in APPEND_ALLOWED_CLASSES:
            raise ValueError(f"append is not allowed for artifact_class: {artifact_class}")
        if not exists:
            raise ValueError("append is not allowed when target does not exist")


def get_existing_sha(target: Path) -> str | None:
    if target.exists() and target.is_file():
        return sha256_file(target)
    return None


def _find_commit_record(project_id: str, commit_id: str) -> CommitLedgerRecord | None:
    records_path = commits_ledger_path_for(project_id)
    if not records_path.exists():
        return None
    import json as _json

    with records_path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                raw = _json.loads(line)
            except (OSError, ValueError, TypeError):
                continue
            if isinstance(raw, dict) and raw.get("commit_id") == commit_id:
                return CommitLedgerRecord.from_dict(raw)
    return None


@legacy_bp.get("/health")
def health() -> object:
    ae = require_api_key()
    if ae:
        return ae
    exec_caps = {}
    try:
        exec_caps = execution_capabilities()
    except (OSError, RuntimeError, ValueError, TypeError, KeyError):
        exec_caps = {}
    return jsonify(
        {
            "ok": True,
            "status": "online",
            "root": str(ROOT),
            "projects_root": str(PROJECTS_ROOT),
            "time": utc_now(),
            "constitutional_seed": constitutional_seed(),
            "artifact_classes": sorted(ARTIFACT_RELATIVE_MAP.keys()),
            "capabilities": capabilities(),
            "compact_control_surface": compact_control_surface_descriptor(
                operation_budget=30, action_count=30
            ).to_dict(),
            "server_native_router": server_native_router_descriptor().to_dict(),
            **exec_caps,
        }
    )


@legacy_bp.get("/capabilities")
def get_capabilities() -> object:
    ae = require_api_key()
    if ae:
        return ae
    envelope = CompactCapabilitiesResponse(
        ok=True,
        time=utc_now(),
        capabilities=capabilities(),
        limits={
            "default_read_max_bytes": 50000,
            "default_rehydrate_budget_bytes": 40000,
            "default_search_limit": 30,
            "default_list_limit": 200,
            "default_tree_limit": 500,
            "default_batch_steps": 30,
            **execution_capabilities(),
        },
        compact_control_surface=compact_control_surface_descriptor(
            operation_budget=30, action_count=30
        ),
        server_native_router=server_native_router_descriptor(),
    )
    return jsonify(envelope.to_dict())


@legacy_bp.post("/project/init")
def project_init() -> object:
    ae = require_api_key()
    if ae:
        return ae
    try:
        request_payload = get_request_json()
        project_id = request_payload.get("project_id", "")
        root = init_project_layout(project_id)
        return jsonify(
            {"ok": True, "project_id": project_id, "project_root": str(root), "created": True}
        )
    except (OSError, RuntimeError, ValueError, TypeError) as e:
        return error_response("PROJECT_INIT_FAILED", str(e), 400)


@legacy_bp.post("/project/info")
def project_info() -> object:
    ae = require_api_key()
    if ae:
        return ae
    try:
        request_payload = get_request_json()
        project_id = request_payload.get("project_id", "")
        root = get_project_root(project_id)
        return jsonify(
            {
                "ok": True,
                "project_id": project_id,
                "project_root": str(root),
                "exists": root.exists(),
                "manifest_exists": manifest_path_for(project_id).exists(),
                "ledger_exists": commits_ledger_path_for(project_id).exists(),
            }
        )
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as e:
        return error_response("PROJECT_INFO_FAILED", str(e), 400)


@legacy_bp.post("/project/manifest")
def project_manifest() -> object:
    ae = require_api_key()
    if ae:
        return ae
    try:
        request_payload = get_request_json()
        project_id = request_payload.get("project_id", "")
        return jsonify({"ok": True, "project_id": project_id, **get_manifest(project_id).to_dict()})
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as e:
        return error_response("BAD_PROJECT", str(e), 400)


@legacy_bp.post("/project/status")
def project_status_alias() -> object:
    ae = require_api_key()
    if ae:
        return ae
    try:
        request_payload = get_request_json()
        project_id = request_payload.get("project_id", "")
        commit_id = request_payload.get("commit_id", "")
        record = _find_commit_record(project_id, commit_id)
        if record is None:
            return error_response("NOT_FOUND", "commit not found", 404)
        return jsonify({"ok": True, **record.to_dict()})
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as e:
        return error_response("COMMIT_STATUS_FAILED", str(e), 400)


@legacy_bp.get("/manifest")
def manifest() -> object:
    ae = require_api_key()
    if ae:
        return ae
    project_id = request.args.get("project_id", "")
    try:
        return jsonify({"ok": True, "project_id": project_id, **get_manifest(project_id).to_dict()})
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as e:
        return error_response("BAD_PROJECT", str(e), 400)


@legacy_bp.get("/status/<commit_id>")
def get_commit_status(commit_id: str) -> object:
    ae = require_api_key()
    if ae:
        return ae
    project_id = request.args.get("project_id", "")
    try:
        record = _find_commit_record(project_id, commit_id)
        if record is None:
            return error_response("NOT_FOUND", "commit not found", 404)
        return jsonify({"ok": True, **record.to_dict()})
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as e:
        return error_response("COMMIT_STATUS_FAILED", str(e), 400)


def _validate_legacy_plan(request_model: LegacyPlanRequest) -> LegacyValidationResult:
    if request_model.operation not in ALLOWED_OPERATIONS:
        raise ValueError(f"Unsupported operation: {request_model.operation}")
    init_project_layout(request_model.project_id)
    target = resolve_target(
        request_model.project_id, request_model.artifact_class, request_model.logical_name
    )
    validate_operation_semantics(request_model.operation, request_model.artifact_class, target)
    ensure_safe_mutation_target_identity(target)
    current_sha = get_existing_sha(target)
    if request_model.expected_previous_sha and current_sha != request_model.expected_previous_sha:
        raise PermissionError("expected_previous_sha256 did not match existing file")
    computed_sha = sha256_text(request_model.content)
    if request_model.provided_sha and request_model.provided_sha != computed_sha:
        raise ArithmeticError("Provided sha256 does not match content")
    return LegacyValidationResult(request_model, target, current_sha, computed_sha)


def _legacy_plan_payload(result: LegacyValidationResult) -> JsonObject:
    request_model = result.request
    return {
        "ok": True,
        "validated": {
            "project_id": request_model.project_id,
            "artifact_class": request_model.artifact_class,
            "logical_name": request_model.logical_name,
            "operation": request_model.operation,
            "target_path": str(result.target),
            "exists": result.target.exists(),
            "current_sha256": result.current_sha,
            "incoming_sha256": result.computed_sha,
        },
    }


def _write_legacy_content(target: Path, operation: str, content: str) -> None:
    ensure_parent(target)
    if operation == "append":
        with target.open("a", encoding="utf-8") as handle:
            handle.write(content)
        return
    with tempfile.NamedTemporaryFile("w", delete=False, dir=target.parent, encoding="utf-8") as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    tmp_path.replace(target)


def _legacy_commit_record(
    request_model: LegacyCommitRequest, target: Path, final_sha: str, size_bytes: int
) -> CommitLedgerRecord:
    plan_model = request_model.plan
    return CommitLedgerRecord(
        project_id=plan_model.project_id,
        session_id=request_model.session_id,
        commit_id=request_model.commit_id,
        idempotency_key=request_model.idempotency_key,
        artifact_class=plan_model.artifact_class,
        logical_name=plan_model.logical_name,
        operation=plan_model.operation,
        path=str(target.relative_to(get_project_root(plan_model.project_id))),
        sha256=final_sha,
        bytes=size_bytes,
        time=utc_now(),
    )


def _apply_legacy_commit(
    request_model: LegacyCommitRequest, validation: LegacyValidationResult
) -> CommitLedgerRecord:
    plan_model = request_model.plan
    _write_legacy_content(validation.target, plan_model.operation, plan_model.content)
    final_sha = sha256_file(validation.target)
    size_bytes = validation.target.stat().st_size
    update_manifest_entry(
        ManifestUpdateSpec(
            plan_model.project_id,
            validation.target,
            plan_model.artifact_class,
            final_sha,
            size_bytes,
        )
    )
    record = _legacy_commit_record(request_model, validation.target, final_sha, size_bytes)
    append_jsonl(commits_ledger_path_for(plan_model.project_id), record)
    return record


def _finalize_prepared_legacy_commit(
    request_model: LegacyCommitRequest,
    entry: JsonObject,
    *,
    apply_effect: bool,
) -> CommitLedgerRecord:
    plan = request_model.plan
    target = resolve_target(plan.project_id, plan.artifact_class, plan.logical_name)
    if apply_effect:
        # Revalidation occurs against the same prepared before-state; the target has
        # not changed since preparation.
        validation = _validate_legacy_plan(plan)
        record = _apply_legacy_commit(request_model, validation)
    else:
        final_sha = sha256_file(target)
        if final_sha != str(entry.get("intended_final_sha256") or ""):
            raise LegacyIdempotencyError("IDEMPOTENCY_RECOVERY_CONFLICT", "target is not at intended final state")
        size_bytes = target.stat().st_size
        update_manifest_entry(
            ManifestUpdateSpec(plan.project_id, target, plan.artifact_class, final_sha, size_bytes)
        )
        existing_record = _find_commit_record(plan.project_id, request_model.commit_id)
        if existing_record is not None:
            if existing_record.idempotency_key != request_model.idempotency_key:
                raise LegacyIdempotencyError("IDEMPOTENCY_RECOVERY_CONFLICT", "commit_id belongs to another operation")
            record = existing_record
        else:
            record = _legacy_commit_record(request_model, target, final_sha, size_bytes)
            append_jsonl(commits_ledger_path_for(plan.project_id), record)
    idem = get_idempotency(plan.project_id)
    idem[request_model.idempotency_key] = _committed_idempotency_entry(entry, record)
    save_idempotency(plan.project_id, idem)
    return record


def _replay_or_resume_legacy_commit(
    request_model: LegacyCommitRequest, entry: JsonObject
) -> tuple[CommitLedgerRecord, bool]:
    _assert_idempotency_request_matches(request_model, entry)
    record = _entry_record(entry)
    if str(entry.get("state") or "") == "committed" and record is not None:
        return record, True
    if str(entry.get("state") or "") != "prepared":
        raise LegacyIdempotencyError("IDEMPOTENCY_RECOVERY_CONFLICT", "unknown idempotency record state")
    plan = request_model.plan
    target = resolve_target(plan.project_id, plan.artifact_class, plan.logical_name)
    current_sha = get_existing_sha(target)
    before_sha = entry.get("before_sha256")
    intended_sha = str(entry.get("intended_final_sha256") or "")
    if current_sha == intended_sha:
        return _finalize_prepared_legacy_commit(request_model, entry, apply_effect=False), True
    if current_sha == before_sha:
        return _finalize_prepared_legacy_commit(request_model, entry, apply_effect=True), True
    raise LegacyIdempotencyError(
        "IDEMPOTENCY_RECOVERY_CONFLICT",
        "target changed to neither prepared before-state nor intended final state",
    )



@legacy_bp.post("/plan")
def plan() -> object:
    ae = require_api_key()
    if ae:
        return ae
    try:
        request_model = LegacyPlanRequest.from_payload(get_request_json())
        validation = _validate_legacy_plan(request_model)
        return jsonify(_legacy_plan_payload(validation))
    except PermissionError as e:
        return error_response("HASH_MISMATCH", str(e), 409)
    except ArithmeticError as e:
        return error_response("CONTENT_HASH_INVALID", str(e), 400)
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as e:
        return error_response("PLAN_FAILED", str(e), 400)


@legacy_bp.post("/commit")
def commit() -> object:
    ae = require_api_key()
    if ae:
        return ae
    try:
        request_model = LegacyCommitRequest.from_payload(get_request_json())
        if (
            not request_model.plan.project_id
            or not request_model.session_id
            or not request_model.commit_id
            or not request_model.idempotency_key
        ):
            return error_response(
                "BAD_REQUEST", "Missing project_id, session_id, commit_id, or idempotency_key", 400
            )
        init_project_layout(request_model.plan.project_id)
        with consequence_guard(
            request_model.plan.project_id,
            mutation_authority=request_model.mutation_authority,
            session_id=request_model.session_id,
        ):
            # Idempotency and optimistic currentness are checked while writer exclusion
            # is held; the lease supplements, never replaces, hash/version validation.
            idem = get_idempotency(request_model.plan.project_id)
            existing = idem.get(request_model.idempotency_key)
            if existing is not None:
                record, replayed = _replay_or_resume_legacy_commit(request_model, existing)
                return jsonify({"ok": True, "replayed": replayed, **record.to_dict()})
            validation = _validate_legacy_plan(request_model.plan)
            prepared = _prepared_idempotency_entry(request_model, validation)
            idem[request_model.idempotency_key] = prepared
            save_idempotency(request_model.plan.project_id, idem)
            record = _finalize_prepared_legacy_commit(
                request_model, prepared, apply_effect=True
            )
            return jsonify({"ok": True, "replayed": False, **record.to_dict()})
    except PermissionError as e:
        return error_response("HASH_MISMATCH", str(e), 409)
    except ArithmeticError as e:
        return error_response("CONTENT_HASH_INVALID", str(e), 400)
    except ProjectMutationAuthorityError as e:
        return error_response(e.error_code, e.message, e.status, **e.extra)
    except LegacyIdempotencyError as e:
        return error_response(e.error_code, e.message, e.status)
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as e:
        return error_response("COMMIT_FAILED", str(e), 400)
