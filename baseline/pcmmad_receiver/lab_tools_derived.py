from __future__ import annotations
from typing import Any, Callable, MutableMapping
from .derived_state import audit_ucm, rebuild_ucm

JsonObject = MutableMapping[str, Any]
Registrar = Callable[..., Any]


def register_derived_state_tools(register_tool: Registrar, *, error_cls: type[Exception]) -> None:
    @register_tool(
        "derived_state.audit",
        "Classify authoritative versus derived state currentness. Initial implementation covers UCM ledgers/snapshots.",
        "low",
        category="architecture",
        side_effect_class="read",
        effect_traits=["reads_runtime_state", "reads_user_continuity", "bounded_results"],
        input_schema={"type":"object","required":["project_id","kind","profile_id"],"additionalProperties":False,"properties":{"project_id":{"type":"string","minLength":1},"kind":{"type":"string","enum":["ucm"]},"profile_id":{"type":"string","minLength":1}}},
        output_schema={"type":"object"},
    )
    def tool_audit(payload: JsonObject) -> JsonObject:
        return audit_ucm(str(payload["profile_id"]))

    @register_tool(
        "derived_state.rebuild",
        "Rebuild UCM derived snapshot state from an exact authoritative ledger head, or clear orphan derived cache only when the authoritative head is zero.",
        "high",
        category="architecture",
        mutating=True,
        approval_required=True,
        side_effect_class="mutation",
        effect_traits=["durable_mutation", "writes_derived_cache", "reads_user_continuity", "project_mutation_fenced", "head_cas_required"],
        input_schema={"type":"object","required":["project_id","kind","profile_id","expected_head_seq"],"additionalProperties":False,"properties":{"project_id":{"type":"string","minLength":1},"kind":{"type":"string","enum":["ucm"]},"profile_id":{"type":"string","minLength":1},"expected_head_seq":{"type":"integer","minimum":0},"expected_head_hash":{"type":["string","null"]}}},
        output_schema={"type":"object"},
    )
    def tool_rebuild(payload: JsonObject) -> JsonObject:
        try:
            return rebuild_ucm(str(payload["profile_id"]), int(payload["expected_head_seq"]), payload.get("expected_head_hash"))
        except Exception as exc:
            if hasattr(exc, "error_code"):
                raise error_cls(exc.error_code, getattr(exc, "message", str(exc)), getattr(exc, "status", 409), **getattr(exc, "extra", {})) from exc
            raise
