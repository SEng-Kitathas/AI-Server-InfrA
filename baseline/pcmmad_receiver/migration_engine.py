from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .architecture_registry import ArtifactRegistryDeps, inspect_artifact
from .lab_tools_continuity import AdoptionDeps, adopt_existing_artifact, reconcile_res_snapshot
from .shared_core import resolve_mount_spec

JsonObject = dict[str, Any]


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MigrationDeps:
    error_cls: type[Exception]
    get_project_root: Any
    registry: ArtifactRegistryDeps
    adoption: AdoptionDeps
    utc_now: Any
    save_json_atomic: Any


def _receipts_dir(project_id: str, dep: MigrationDeps) -> Path:
    return dep.get_project_root(project_id) / "system" / "migrations" / "receipts"


def inspect_migration(payload: JsonObject, dep: MigrationDeps) -> JsonObject:
    project_id = str(payload.get("project_id") or "").strip()
    kind = str(payload.get("kind") or "").strip().lower()
    if not project_id or kind not in {"artifact", "res", "ucm_private"}:
        raise dep.error_cls("BAD_REQUEST", "project_id and supported kind are required", 400)
    if kind == "artifact":
        artifact = payload.get("artifact") or {}
        state = inspect_artifact(project_id, str(artifact.get("artifact_class") or ""), str(artifact.get("logical_name") or ""), dep.registry)
        return {"schema": "pcmmad.migration-inspect.v1", "kind": kind, "project_id": project_id, "state": state}
    if kind == "ucm_private":
        profile_id = str(payload.get("profile_id") or "").strip()
        archive_spec = str(payload.get("archive_mount_spec") or "").strip()
        receipt_spec = str(payload.get("detached_receipt_mount_spec") or "").strip()
        if not profile_id or not archive_spec or not receipt_spec:
            raise dep.error_cls("BAD_REQUEST", "ucm_private requires profile_id, archive_mount_spec, and detached_receipt_mount_spec", 400)
        try:
            archive = resolve_mount_spec(archive_spec, allow_absolute=False)
            detached = resolve_mount_spec(receipt_spec, allow_absolute=False)
        except ValueError as exc:
            raise dep.error_cls("BAD_REQUEST", f"invalid UCM migration mount spec: {exc}", 400) from exc
        from . import ucm_v1_runtime as ucm
        head = ucm.head(profile_id)
        return {
            "schema": "pcmmad.migration-inspect.v1",
            "kind": kind,
            "project_id": project_id,
            "state": {
                "profile_id": profile_id,
                "archive_mount_spec": archive_spec,
                "archive_path": str(archive),
                "archive_exists": archive.is_file(),
                "archive_bytes": archive.stat().st_size if archive.is_file() else None,
                "archive_sha256": dep.adoption.sha256_file(archive) if archive.is_file() else None,
                "detached_receipt_mount_spec": receipt_spec,
                "detached_receipt_path": str(detached),
                "detached_receipt_exists": detached.is_file(),
                "target": {
                    "ledger_head_seq": head.get("ledger_head_seq"),
                    "ledger_head_hash": head.get("ledger_head_hash"),
                    "snapshot_from_seq": head.get("snapshot_from_seq"),
                    "snapshot_current": head.get("snapshot_current"),
                },
            },
        }
    from .res_runtime import RES_CANONICAL_SNAPSHOT_PATH
    target = dep.get_project_root(project_id) / RES_CANONICAL_SNAPSHOT_PATH
    return {
        "schema": "pcmmad.migration-inspect.v1",
        "kind": kind,
        "project_id": project_id,
        "state": {"path": str(target), "exists": target.is_file(), "sha256": dep.adoption.sha256_file(target) if target.is_file() else None},
    }


def plan_migration(payload: JsonObject, dep: MigrationDeps) -> JsonObject:
    inspected = inspect_migration(payload, dep)
    kind = inspected["kind"]
    state = inspected["state"]
    if kind == "ucm_private":
        if not state.get("archive_exists") or not state.get("detached_receipt_exists"):
            raise dep.error_cls("MIGRATION_SOURCE_MISSING", "UCM donor archive or detached receipt is missing", 409)
        from .ucm_private_migration import verify_private_release
        verified = verify_private_release(Path(state["archive_path"]), Path(state["detached_receipt_path"]))
        if int(state["target"].get("ledger_head_seq") or 0) != 0:
            raise dep.error_cls("MIGRATION_TARGET_NOT_EMPTY", "UCM private migration target profile already contains authoritative events", 409, ledger_head_seq=state["target"].get("ledger_head_seq"), ledger_head_hash=state["target"].get("ledger_head_hash"))
        expected_sha = state["archive_sha256"]
        steps = ["verify_sealed_private_release", "require_empty_target_profile", "reemit_server_native_ledger", "materialize_snapshot", "verify_fresh_instance_ingress", "persist_migration_receipt"]
    else:
        if not state.get("exists", state.get("filesystem", {}).get("exists", False)):
            raise dep.error_cls("MIGRATION_SOURCE_MISSING", "migration source artifact is missing", 409)
        expected_sha = state.get("sha256") or state.get("filesystem", {}).get("sha256")
        verified = None
        steps = ["verify_exact_source_sha"]
        if kind == "artifact":
            steps += ["adopt_lineage_without_rewrite", "verify_registry_current"]
        else:
            steps += ["reconcile_lineage_and_protocol", "verify_res_handoff_ready"]
    plan = {
        "schema": "pcmmad.migration-plan.v1",
        "project_id": inspected["project_id"],
        "kind": kind,
        "expected_sha256": expected_sha,
        "artifact": payload.get("artifact") if kind == "artifact" else None,
        "research_intensive": bool(payload.get("research_intensive", True)),
        "profile_id": state.get("profile_id") if kind == "ucm_private" else None,
        "archive_mount_spec": state.get("archive_mount_spec") if kind == "ucm_private" else None,
        "detached_receipt_mount_spec": state.get("detached_receipt_mount_spec") if kind == "ucm_private" else None,
        "source_verification": verified if kind == "ucm_private" else None,
        "expected_registered_sha256": (state.get("lineage") or {}).get("latest_registered_sha256") if kind == "artifact" else None,
        "expected_target_head_seq": state.get("target", {}).get("ledger_head_seq") if kind == "ucm_private" else None,
        "expected_target_head_hash": state.get("target", {}).get("ledger_head_hash") if kind == "ucm_private" else None,
        "steps": steps,
        "mutation": {"rewrites_source_bytes": False, "requires_project_mutation_fence": True},
    }
    plan["plan_sha256"] = _digest(plan)
    return plan


def execute_migration(payload: JsonObject, dep: MigrationDeps) -> JsonObject:
    plan = payload.get("plan")
    if not isinstance(plan, dict):
        raise dep.error_cls("BAD_REQUEST", "plan object is required", 400)
    supplied = str(payload.get("plan_sha256") or "")
    canonical = dict(plan)
    embedded = canonical.pop("plan_sha256", None)
    expected = _digest(canonical)
    if supplied != expected or (embedded not in (None, expected)):
        raise dep.error_cls("MIGRATION_PLAN_DIGEST_MISMATCH", "migration plan digest does not match plan", 409, expected_plan_sha256=expected)
    project_id = str(plan.get("project_id") or "")
    kind = str(plan.get("kind") or "")
    sha = str(plan.get("expected_sha256") or "")
    inspect_payload = {"project_id": project_id, "kind": kind, "artifact": plan.get("artifact")}
    if kind == "ucm_private":
        inspect_payload.update({"profile_id": plan.get("profile_id"), "archive_mount_spec": plan.get("archive_mount_spec"), "detached_receipt_mount_spec": plan.get("detached_receipt_mount_spec")})
    before = inspect_migration(inspect_payload, dep)
    if kind == "ucm_private":
        target = before["state"]["target"]
        if int(target.get("ledger_head_seq") or 0) != int(plan.get("expected_target_head_seq") or 0) or target.get("ledger_head_hash") != plan.get("expected_target_head_hash"):
            raise dep.error_cls("MIGRATION_TARGET_CHANGED", "UCM target head changed after planning", 409, expected_head_seq=plan.get("expected_target_head_seq"), expected_head_hash=plan.get("expected_target_head_hash"), actual_head_seq=target.get("ledger_head_seq"), actual_head_hash=target.get("ledger_head_hash"))
    if kind == "artifact":
        artifact = plan.get("artifact") or {}
        result = adopt_existing_artifact({
            "project_id": project_id,
            "artifact": artifact,
            "expected_sha256": sha,
            "expected_registered_sha256": plan.get("expected_registered_sha256"),
            "session_id": str(payload.get("session_id") or "migration-engine"),
        }, dep.adoption)
    elif kind == "res":
        result = reconcile_res_snapshot({
            "project_id": project_id,
            "expected_sha256": sha,
            "research_intensive": bool(plan.get("research_intensive", True)),
            "actor": str(payload.get("actor") or "migration-engine"),
            "session_id": str(payload.get("session_id") or "migration-engine"),
        }, dep.adoption)
    elif kind == "ucm_private":
        from .ucm_private_migration import import_private_release
        archive = resolve_mount_spec(str(plan.get("archive_mount_spec") or ""), allow_absolute=False)
        detached = resolve_mount_spec(str(plan.get("detached_receipt_mount_spec") or ""), allow_absolute=False)
        if dep.adoption.sha256_file(archive) != sha:
            raise dep.error_cls("MIGRATION_SOURCE_CHANGED", "UCM donor archive changed after planning", 409, expected_sha256=sha, current_sha256=dep.adoption.sha256_file(archive))
        result = import_private_release(archive, profile_id=str(plan.get("profile_id") or ""), detached_receipt_path=detached)
    else:
        raise dep.error_cls("BAD_REQUEST", "unsupported migration kind", 400)
    after = inspect_migration(inspect_payload, dep)
    receipt_id = str(payload.get("receipt_id") or f"mig-{uuid.uuid4().hex[:16]}")
    receipt = {
        "schema": "pcmmad.migration-receipt.v1",
        "receipt_id": receipt_id,
        "project_id": project_id,
        "kind": kind,
        "plan_sha256": expected,
        "plan": plan,
        "source_sha256": sha,
        "started_from": before,
        "result": result,
        "verified_state": after,
        "completed_at": dep.utc_now(),
    }
    receipt["receipt_sha256"] = _digest(receipt)
    path = _receipts_dir(project_id, dep) / f"{receipt_id}.json"
    dep.save_json_atomic(path, receipt)
    return {"ok": True, "receipt_id": receipt_id, "receipt_path": str(path), "receipt_sha256": receipt["receipt_sha256"], "result": result, "verified_state": after}


def verify_receipt(payload: JsonObject, dep: MigrationDeps) -> JsonObject:
    project_id = str(payload.get("project_id") or "").strip()
    receipt_id = str(payload.get("receipt_id") or "").strip()
    path = _receipts_dir(project_id, dep) / f"{receipt_id}.json"
    if not path.is_file():
        raise dep.error_cls("MIGRATION_RECEIPT_NOT_FOUND", "migration receipt not found", 404)
    receipt = json.loads(path.read_text(encoding="utf-8"))
    recorded = receipt.pop("receipt_sha256", None)
    computed = _digest(receipt)
    receipt["receipt_sha256"] = recorded
    plan = receipt.get("plan") if isinstance(receipt.get("plan"), dict) else {}
    inspect_payload = {"project_id": project_id, "kind": receipt["kind"], "artifact": plan.get("artifact") or receipt.get("started_from", {}).get("state", {}).get("artifact") or receipt.get("verified_state", {}).get("state", {}).get("artifact")}
    if receipt["kind"] == "ucm_private":
        inspect_payload.update({"profile_id": plan.get("profile_id"), "archive_mount_spec": plan.get("archive_mount_spec"), "detached_receipt_mount_spec": plan.get("detached_receipt_mount_spec")})
    current = inspect_migration(inspect_payload, dep)
    return {
        "ok": recorded == computed,
        "receipt_id": receipt_id,
        "receipt_hash_valid": recorded == computed,
        "recorded_receipt_sha256": recorded,
        "computed_receipt_sha256": computed,
        "current": current,
    }
