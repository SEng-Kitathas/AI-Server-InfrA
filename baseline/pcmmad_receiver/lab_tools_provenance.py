"""Native project provenance read/verification capabilities."""
from __future__ import annotations
from typing import Any, Callable
from provenance_store import (
    consistency_receipt,
    inclusion_receipt,
    project_root_receipt,
    surface_root_receipt,
    verify_events,
)


def register_provenance_tools(register_tool: Callable[..., Any], *, error_cls: type[Exception]) -> None:
    @register_tool(
        "project.provenance.status",
        "Verify project provenance hash chains and return project/surface heads.",
        "low",
        category="project",
        mutating=False,
        side_effect_class="read",
        effect_traits=["bounded_output", "project_scope_enforced", "reads_project_provenance", "derived_rebuildable"],
        input_schema={"type":"object","properties":{"project_id":{"type":"string","minLength":1}},"required":["project_id"],"additionalProperties":False},
    )
    def tool_project_provenance_status(payload):
        try:
            return verify_events(payload["project_id"])
        except Exception as exc:
            raise error_cls("PROVENANCE_VERIFY_FAILED", str(exc), 400) from exc

    @register_tool(
        "project.provenance.root",
        "Return derived project-wide or per-surface provenance Merkle root.",
        "low",
        category="project",
        mutating=False,
        side_effect_class="read",
        effect_traits=["bounded_output", "project_scope_enforced", "reads_project_provenance", "derived_rebuildable"],
        input_schema={"type":"object","properties":{"project_id":{"type":"string","minLength":1},"surface_id":{"type":"string"}},"required":["project_id"],"additionalProperties":False},
    )
    def tool_project_provenance_root(payload):
        try:
            if payload.get("surface_id"):
                return surface_root_receipt(payload["project_id"], payload["surface_id"])
            return project_root_receipt(payload["project_id"])
        except Exception as exc:
            raise error_cls("PROVENANCE_ROOT_FAILED", str(exc), 400) from exc

    @register_tool(
        "project.provenance.inclusion",
        "Return inclusion proof for one project provenance event.",
        "low",
        category="project",
        mutating=False,
        side_effect_class="read",
        effect_traits=["bounded_output", "project_scope_enforced", "reads_project_provenance", "derived_rebuildable"],
        input_schema={"type":"object","properties":{"project_id":{"type":"string","minLength":1},"project_sequence":{"type":"integer","minimum":1}},"required":["project_id","project_sequence"],"additionalProperties":False},
    )
    def tool_project_provenance_inclusion(payload):
        try:
            return inclusion_receipt(payload["project_id"], int(payload["project_sequence"]))
        except Exception as exc:
            raise error_cls("PROVENANCE_INCLUSION_FAILED", str(exc), 400) from exc

    @register_tool(
        "project.provenance.consistency",
        "Return append-consistency proof from an earlier project provenance tree size.",
        "low",
        category="project",
        mutating=False,
        side_effect_class="read",
        effect_traits=["bounded_output", "project_scope_enforced", "reads_project_provenance", "derived_rebuildable"],
        input_schema={"type":"object","properties":{"project_id":{"type":"string","minLength":1},"old_tree_size":{"type":"integer","minimum":0}},"required":["project_id","old_tree_size"],"additionalProperties":False},
    )
    def tool_project_provenance_consistency(payload):
        try:
            return consistency_receipt(payload["project_id"], int(payload["old_tree_size"]))
        except Exception as exc:
            raise error_cls("PROVENANCE_CONSISTENCY_FAILED", str(exc), 400) from exc
