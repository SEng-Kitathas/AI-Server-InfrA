from __future__ import annotations

from typing import Any, Callable, MutableMapping

from .architecture_registry import ArtifactRegistryDeps, inspect_artifact
from .migration_engine import MigrationDeps, inspect_migration, plan_migration, execute_migration, verify_receipt
from .artifact_commit_service import ArtifactCommitError, commit_artifact

JsonObject = MutableMapping[str, Any]
Registrar = Callable[..., Callable[[Callable[[JsonObject], JsonObject]], Callable[[JsonObject], JsonObject]]]

ARTIFACT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["project_id", "artifact"],
    "additionalProperties": False,
    "properties": {
        "project_id": {"type": "string", "minLength": 1},
        "artifact": {
            "type": "object",
            "required": ["artifact_class", "logical_name"],
            "additionalProperties": False,
            "properties": {
                "artifact_class": {"type": "string", "minLength": 1},
                "logical_name": {"type": "string", "minLength": 1},
            },
        },
    },
}

MIGRATION_INSPECT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["project_id", "kind"],
    "additionalProperties": False,
    "properties": {
        "project_id": {"type": "string", "minLength": 1},
        "kind": {"type": "string", "enum": ["artifact", "res", "ucm_private"]},
        "artifact": ARTIFACT_SCHEMA["properties"]["artifact"],
        "research_intensive": {"type": "boolean"},
        "profile_id": {"type": "string", "minLength": 1},
        "archive_mount_spec": {"type": "string", "minLength": 1},
        "detached_receipt_mount_spec": {"type": "string", "minLength": 1},
    },
}

MIGRATION_EXECUTE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["project_id", "plan", "plan_sha256"],
    "additionalProperties": False,
    "properties": {
        "project_id": {"type": "string", "minLength": 1},
        "plan": {"type": "object"},
        "plan_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "receipt_id": {"type": "string", "minLength": 1, "maxLength": 160},
        "session_id": {"type": "string", "minLength": 1, "maxLength": 200},
        "actor": {"type": "string", "minLength": 1, "maxLength": 200},
    },
}


def runtime_status(project_id: str, ucm_profile_id: str | None, get_project_root: Any) -> dict[str, Any]:
    from .project_mutation_authority import observe_lease
    from .protocol_store import build_snapshot
    from . import ucm_v1_runtime as ucm
    from . import lab_tools as lab
    from . import scheduler_effect_profile as effect
    mutation = observe_lease(project_id)
    protocol = build_snapshot(project_id)
    profile = None
    if ucm_profile_id:
        try:
            profile = ucm.head(ucm_profile_id)
        except Exception as exc:
            profile = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    receipts = get_project_root(project_id) / "system" / "migrations" / "receipts"
    receipt_count = len(list(receipts.glob("*.json"))) if receipts.is_dir() else 0
    cards = {row["name"]: row for row in lab.list_tools()}
    try:
        profile_doc = effect.load_profile()
        verification = effect.verify_profile(profile_doc, cards)
        effect_counts = {
            "current": bool(verification.get("current")),
            "capability_count": int(verification.get("capability_count") or len(cards)),
            "effect_truth_verified": int(verification.get("effect_truth_verified_count") or 0),
            "parallel_verified": int(verification.get("parallel_verified_count") or 0),
        }
    except Exception as exc:
        effect_counts = {"current": False, "error": f"{type(exc).__name__}: {exc}", "capability_count": len(cards)}
    return {
        "schema": "pcmmad.architecture-runtime-status.v1",
        "project_id": project_id,
        "mutation": mutation,
        "protocol": {"mode": protocol.current_mode.value, "event_count": protocol.event_count, "head_hash": protocol.head_hash},
        "ucm": profile,
        "migrations": {"receipt_count": receipt_count},
        "capabilities": {"count": len(cards)},
        "effect_profile": effect_counts,
        "compatibility": {
            "legacy_commit_route": "DEPRECATED_COMPATIBILITY",
            "replacement": ["project.files.write", "continuity.artifact.adopt", "migration.plan", "migration.execute"],
            "retirement_gate": "DISABLE_ONLY_AFTER_ATOMIC_WRITE_LINEAGE_PARITY_AND_HOSTILE_COVERAGE",
        },
    }


ARTIFACT_COMMIT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["project_id", "artifact_class", "logical_name", "operation", "content", "session_id", "commit_id", "idempotency_key"],
    "additionalProperties": False,
    "properties": {
        "project_id": {"type":"string","minLength":1},
        "artifact_class": {"type":"string","minLength":1},
        "logical_name": {"type":"string","minLength":1},
        "operation": {"type":"string","enum":["create","update","append"]},
        "content": {"type":"string"},
        "content_sha256": {"type":["string","null"],"pattern":"^[0-9a-f]{64}$"},
        "expected_previous_sha256": {"type":["string","null"],"pattern":"^[0-9a-f]{64}$"},
        "session_id": {"type":"string","minLength":1,"maxLength":200},
        "commit_id": {"type":"string","minLength":1,"maxLength":200},
        "idempotency_key": {"type":"string","minLength":1,"maxLength":300},
        "render_mode": {"type":"string","enum":["utf8_exact","platform_text"]},
    },
}


def register_architecture_tools(register_tool: Registrar, **raw: Any) -> None:
    registry = ArtifactRegistryDeps(
        resolve_target=raw["resolve_target"],
        commits_ledger_path_for=raw["commits_ledger_path_for"],
        sha256_file=raw["sha256_file"],
    )
    adoption = raw["adoption_deps"]
    migration = MigrationDeps(
        error_cls=raw["error_cls"],
        get_project_root=raw["get_project_root"],
        registry=registry,
        adoption=adoption,
        utc_now=raw["utc_now"],
        save_json_atomic=raw["save_json_atomic"],
    )

    @register_tool(
        "architecture.runtime.status",
        "Project-centric projection of mutation authority, protocol state, UCM head, migration receipts, capability/effect profile status, and compatibility posture.",
        "low",
        category="architecture",
        side_effect_class="read",
        effect_traits=["reads_runtime_state", "reads_project_state", "reads_protocol_ledger", "reads_user_continuity", "bounded_results"],
        input_schema={"type":"object","required":["project_id"],"additionalProperties":False,"properties":{"project_id":{"type":"string","minLength":1},"ucm_profile_id":{"type":["string","null"]}}},
        output_schema={"type":"object"},
    )
    def tool_runtime_status(payload: JsonObject) -> JsonObject:
        return runtime_status(str(payload["project_id"]), str(payload.get("ucm_profile_id")) if payload.get("ucm_profile_id") else None, raw["get_project_root"])

    @register_tool(
        "artifact.commit",
        "Atomically write one project artifact with exact before-SHA CAS, manifest + lineage update, and durable idempotency recovery. Current replacement for legacy /commit semantics.",
        "high",
        category="continuity",
        mutating=True,
        approval_required=True,
        side_effect_class="mutation",
        effect_traits=["durable_mutation","writes_files","writes_manifest","writes_project_ledger","idempotent_with_key","source_currentness_check","project_scope_enforced","project_mutation_fenced"],
        input_schema=ARTIFACT_COMMIT_SCHEMA,
        output_schema={"type":"object"},
    )
    def tool_artifact_commit(payload: JsonObject) -> JsonObject:
        try:
            return commit_artifact(dict(payload))
        except ArtifactCommitError as exc:
            raise raw["error_cls"](exc.error_code, exc.message, exc.status, **exc.extra) from exc

    @register_tool(
        "architecture.registry.inspect",
        "Inspect one artifact across filesystem, lineage, and protocol registration planes with an explicit repair owner for mismatches.",
        "low",
        category="architecture",
        side_effect_class="read",
        effect_traits=["reads_files", "reads_project_ledger", "reads_protocol_ledger", "project_scope_enforced", "bounded_results"],
        input_schema=ARTIFACT_SCHEMA,
        output_schema={"type": "object"},
    )
    def tool_registry(payload: JsonObject) -> JsonObject:
        artifact = payload["artifact"]
        return inspect_artifact(str(payload["project_id"]), str(artifact["artifact_class"]), str(artifact["logical_name"]), registry)

    @register_tool(
        "migration.inspect",
        "Inspect migration source/currentness without mutation.",
        "low",
        category="migration",
        side_effect_class="read",
        effect_traits=["reads_files", "reads_project_ledger", "reads_protocol_ledger", "project_scope_enforced", "bounded_results"],
        input_schema=MIGRATION_INSPECT_SCHEMA,
        output_schema={"type": "object"},
    )
    def tool_migration_inspect(payload: JsonObject) -> JsonObject:
        return inspect_migration(dict(payload), migration)

    @register_tool(
        "migration.plan",
        "Create a deterministic no-byte-rewrite migration plan and plan digest.",
        "low",
        category="migration",
        side_effect_class="read",
        effect_traits=["reads_files", "reads_project_ledger", "source_currentness_check", "project_scope_enforced", "bounded_results"],
        input_schema=MIGRATION_INSPECT_SCHEMA,
        output_schema={"type": "object"},
    )
    def tool_migration_plan(payload: JsonObject) -> JsonObject:
        return plan_migration(dict(payload), migration)

    @register_tool(
        "migration.execute",
        "Execute an exact digest-bound migration plan and persist a project-local migration receipt.",
        "high",
        category="migration",
        mutating=True,
        approval_required=True,
        side_effect_class="mutation",
        effect_traits=["durable_mutation", "writes_project_ledger", "writes_manifest", "writes_protocol_ledger", "project_scope_enforced", "project_mutation_fenced", "source_currentness_check", "writes_migration_receipt"],
        input_schema=MIGRATION_EXECUTE_SCHEMA,
        output_schema={"type": "object"},
    )
    def tool_migration_execute(payload: JsonObject) -> JsonObject:
        if str(payload["project_id"]) != str((payload.get("plan") or {}).get("project_id") or ""):
            raise raw["error_cls"]("MIGRATION_PROJECT_MISMATCH", "outer project_id must match plan project_id", 409)
        return execute_migration(dict(payload), migration)

    @register_tool(
        "migration.verify",
        "Verify one persisted migration receipt hash and current migration state.",
        "low",
        category="migration",
        side_effect_class="read",
        effect_traits=["reads_files", "reads_project_ledger", "reads_protocol_ledger", "project_scope_enforced", "bounded_results"],
        input_schema={
            "type": "object",
            "required": ["project_id", "receipt_id"],
            "additionalProperties": False,
            "properties": {"project_id": {"type": "string", "minLength": 1}, "receipt_id": {"type": "string", "minLength": 1}},
        },
        output_schema={"type": "object"},
    )
    def tool_migration_verify(payload: JsonObject) -> JsonObject:
        return verify_receipt(dict(payload), migration)
