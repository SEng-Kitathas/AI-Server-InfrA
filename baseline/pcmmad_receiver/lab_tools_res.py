"""Thin server-native Research Epistemic Shadow policy/projection tools.

These capabilities are read-only and authority-neutral. RES persistence continues
through existing project/protocol/artifact mutation surfaces.
"""
from __future__ import annotations

from collections.abc import Callable, MutableMapping
from typing import Any

from res_runtime import (
    ResPolicyError,
    classify_material_change,
    handoff_readiness,
    project_addenda,
    validate_addendum,
    validate_snapshot,
)

JsonObject = MutableMapping[str, Any]
Registrar = Callable[..., Any]


def _schema(required: list[str], properties: dict[str, Any]) -> dict[str, Any]:
    return {"type": "object", "required": required, "properties": properties, "additionalProperties": True}


def _raise(error_cls: type[Exception], exc: ResPolicyError) -> None:
    raise error_cls(exc.code, exc.message, exc.status, **exc.extra)


def register_res_tools(register_tool: Registrar, *, error_cls: type[Exception]) -> None:
    @register_tool(
        "continuity.res.addendum.validate",
        "Validate one RES addendum against the canonical truth/provenance/visible-transition contract without granting authority.",
        "medium",
        category="continuity",
        tags=["continuity", "res", "epistemic", "validation"],
        side_effect_class="read",
        effect_traits=["deterministic", "authority_neutral", "canonical_truth_states", "visible_transition_required"],
        capability_version="1.0.0",
        schema_version="1",
        input_schema=_schema(
            ["addendum"],
            {
                "addendum": {"type": "object"},
                "prior_projection": {"type": "object"},
                "store_result": {"type": "boolean"},
                "project_id": {"type": "string"},
            },
        ),
    )
    def res_addendum_validate(payload: JsonObject) -> JsonObject:
        addendum = payload.get("addendum")
        prior = payload.get("prior_projection")
        if not isinstance(addendum, dict):
            raise error_cls("BAD_REQUEST", "addendum object is required", 400)
        if prior is not None and not isinstance(prior, dict):
            raise error_cls("BAD_REQUEST", "prior_projection must be an object", 400)
        try:
            return validate_addendum(addendum, prior_projection=prior)
        except ResPolicyError as exc:
            _raise(error_cls, exc)

    @register_tool(
        "continuity.res.addenda.project",
        "Project an ordered RES addendum chain into current machine-readable epistemic state while preserving history and authority neutrality.",
        "medium",
        category="continuity",
        tags=["continuity", "res", "projection", "currentness"],
        side_effect_class="read",
        effect_traits=["deterministic", "authority_neutral", "append_chain_verified", "bounded_results"],
        capability_version="1.0.0",
        schema_version="1",
        input_schema=_schema(
            ["addenda"],
            {
                "addenda": {"type": "array", "items": {"type": "object"}},
                "store_result": {"type": "boolean"},
                "project_id": {"type": "string"},
            },
        ),
    )
    def res_addenda_project(payload: JsonObject) -> JsonObject:
        addenda = payload.get("addenda")
        if not isinstance(addenda, list):
            raise error_cls("BAD_REQUEST", "addenda list is required", 400)
        try:
            return project_addenda(addenda)
        except ResPolicyError as exc:
            _raise(error_cls, exc)

    @register_tool(
        "continuity.res.snapshot.validate",
        "Validate a consolidated RES Markdown snapshot for the canonical 22-section shape, truth grammar, and doctrine firewall.",
        "medium",
        category="continuity",
        tags=["continuity", "res", "snapshot", "validation"],
        side_effect_class="read",
        effect_traits=["deterministic", "authority_neutral", "22_section_schema", "doctrine_firewall"],
        capability_version="1.0.0",
        schema_version="1",
        input_schema=_schema(
            ["content"],
            {
                "content": {"type": "string"},
                "store_result": {"type": "boolean"},
                "project_id": {"type": "string"},
            },
        ),
    )
    def res_snapshot_validate(payload: JsonObject) -> JsonObject:
        content = payload.get("content")
        if not isinstance(content, str):
            raise error_cls("BAD_REQUEST", "content string is required", 400)
        try:
            return validate_snapshot(content)
        except ResPolicyError as exc:
            _raise(error_cls, exc)

    @register_tool(
        "continuity.res.materiality.classify",
        "Classify whether a declared event requires, recommends, or does not require an RES update under the canonical material-change cadence.",
        "low",
        category="continuity",
        tags=["continuity", "res", "materiality", "policy"],
        side_effect_class="read",
        effect_traits=["deterministic", "authority_neutral", "no_background_daemon"],
        capability_version="1.0.0",
        schema_version="1",
        input_schema=_schema(
            ["event_class"],
            {
                "event_class": {"type": "string"},
                "material": {"type": "boolean"},
            },
        ),
    )
    def res_materiality_classify(payload: JsonObject) -> JsonObject:
        return classify_material_change(
            str(payload.get("event_class") or ""),
            material=bool(payload.get("material", True)),
        )

    @register_tool(
        "continuity.res.handoff.readiness",
        "Derive research-handoff epistemic readiness from the canonical RES snapshot, registered artifact identity, append-only protocol ordering, and material project evidence.",
        "medium",
        category="continuity",
        tags=["continuity", "res", "handoff", "currentness", "readiness"],
        side_effect_class="read",
        effect_traits=["deterministic", "authority_neutral", "project_derived", "fail_closed", "consequence_readback"],
        capability_version="1.0.0",
        schema_version="1",
        input_schema=_schema(
            ["project_id"],
            {
                "project_id": {"type": "string", "minLength": 1},
                "research_intensive": {"type": "boolean"},
            },
        ),
    )
    def res_handoff_readiness(payload: JsonObject) -> JsonObject:
        project_id = str(payload.get("project_id") or "").strip()
        if not project_id:
            raise error_cls("BAD_REQUEST", "project_id is required", 400)
        try:
            return handoff_readiness(
                project_id,
                research_intensive=bool(payload.get("research_intensive", True)),
            )
        except ResPolicyError as exc:
            _raise(error_cls, exc)
        except FileNotFoundError as exc:
            raise error_cls("PROJECT_NOT_FOUND", str(exc), 404) from exc
