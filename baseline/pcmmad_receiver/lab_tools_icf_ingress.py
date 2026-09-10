"""ICF-CS v1.2 current fresh-instance ingress capability."""
from __future__ import annotations

from collections.abc import Callable, MutableMapping
from typing import Any

from icf_cs_v12_ingress import IcfIngressError, SESSION_MODES, rehydrate_icf_v12

JsonObject = MutableMapping[str, Any]
Registrar = Callable[..., Any]


def register_icf_ingress_tool(register_tool: Registrar, *, error_cls: type[Exception]) -> None:
    @register_tool(
        "continuity.ingress.rehydrate",
        "Execute the current ICF-CS v1.2 fresh-instance continuity sequence: exact current standard, explicit RES/UCM applicability, required plane currentness, bounded project context, and authority-neutral readiness.",
        "medium",
        category="continuity",
        tags=["continuity", "icf-cs", "rehydration", "res", "ucm", "currentness"],
        side_effect_class="read_cache",
        effect_traits=[
            "reads_files",
            "writes_ephemeral_cache",
            "bounded_output",
            "icf_cs_v1_2_currentness",
            "explicit_applicability",
            "res_currentness_gate",
            "ucm_currentness_gate",
            "authority_neutral",
            "fresh_instance_ingress",
        ],
        capability_version="1.0.0",
        schema_version="1",
        input_schema={
            "type": "object",
            "required": ["project_id", "topic", "session_mode"],
            "properties": {
                "project_id": {"type": "string", "minLength": 1, "maxLength": 128},
                "topic": {"type": "string", "minLength": 1, "maxLength": 300},
                "session_mode": {"type": "string", "enum": sorted(SESSION_MODES)},
                "ucm_profile_id": {"type": ["string", "null"], "maxLength": 160},
                "res_required_by_project": {"type": "boolean"},
                "path": {"type": "string"},
                "project_budget_bytes": {"type": "integer", "minimum": 1},
                "debug": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        output_schema={"type": "object"},
    )
    def continuity_ingress_rehydrate(payload: JsonObject) -> JsonObject:
        try:
            return rehydrate_icf_v12(
                project_id=str(payload.get("project_id") or ""),
                topic=str(payload.get("topic") or ""),
                session_mode=str(payload.get("session_mode") or ""),
                ucm_profile_id=(str(payload.get("ucm_profile_id")) if payload.get("ucm_profile_id") is not None else None),
                res_required_by_project=bool(payload.get("res_required_by_project", False)),
                path=str(payload.get("path") or "."),
                project_budget_bytes=(int(payload["project_budget_bytes"]) if payload.get("project_budget_bytes") is not None else None),
                debug=bool(payload.get("debug", False)),
            )
        except IcfIngressError as exc:
            raise error_cls(exc.error_code, exc.message, exc.status, **exc.extra) from exc
