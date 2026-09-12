from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .architecture_registry import ArtifactRegistryDeps, inspect_artifact
from .lab_tools_continuity import AdoptionDeps, adopt_existing_artifact, reconcile_res_snapshot
from .server_hardening import safe_json_dumps

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
    if not project_id or kind not in {"artifact", "res"}:
        raise dep.error_cls("BAD_REQUEST", "project_id and supported kind are required", 400)
    if kind == "artifact":
        artifact = payload.get("artifact") or {}
        state = inspect_artifact(project_id, str(artifact.get("artifact_class") or ""), str(artifact.get("logical_name") or ""), dep.registry)
        return {"schema": "pcmmad.migration-inspect.v1", "kind": kind, "project_id": project_id, "state": state}
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
    if not state.get("exists", state.get("filesystem", {}).get("exists", False)):
        raise dep.error_cls("MIGRATION_SOURCE_MISSING", "migration source artifact is missing", 409)
    expected_sha = state.get("sha256") or state.get("filesystem", {}).get("sha256")
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
    before = inspect_migration({"project_id": project_id, "kind": kind, "artifact": plan.get("artifact")}, dep)
    if kind == "artifact":
        artifact = plan.get("artifact") or {}
        result = adopt_existing_artifact({
            "project_id": project_id,
            "artifact": artifact,
            "expected_sha256": sha,
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
    else:
        raise dep.error_cls("BAD_REQUEST", "unsupported migration kind", 400)
    after = inspect_migration({"project_id": project_id, "kind": kind, "artifact": plan.get("artifact")}, dep)
    receipt_id = str(payload.get("receipt_id") or f"mig-{uuid.uuid4().hex[:16]}")
    receipt = {
        "schema": "pcmmad.migration-receipt.v1",
        "receipt_id": receipt_id,
        "project_id": project_id,
        "kind": kind,
        "plan_sha256": expected,
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
    current = inspect_migration({"project_id": project_id, "kind": receipt["kind"], "artifact": receipt.get("started_from", {}).get("state", {}).get("artifact") or receipt.get("verified_state", {}).get("state", {}).get("artifact")}, dep)
    return {
        "ok": recorded == computed,
        "receipt_id": receipt_id,
        "receipt_hash_valid": recorded == computed,
        "recorded_receipt_sha256": recorded,
        "computed_receipt_sha256": computed,
        "current": current,
    }
