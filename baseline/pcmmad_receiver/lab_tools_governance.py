"""Native governance/contact and finite-exhaustion capability surface."""
from __future__ import annotations

from collections.abc import Callable, MutableMapping
from typing import Any

from .governance_runtime import (
    GovernanceError,
    admit_contact_set,
    derive_contact_set,
    enumerate_lawful_frame,
    evaluate_effect_table,
    compress_minimal_witnesses,
)
from .shared_core import get_project_root

JsonObject = MutableMapping[str, Any]
Registrar = Callable[..., Any]

def _schema(required: list[str], properties: dict[str, Any]) -> dict[str, Any]:
    return {"type":"object","properties":properties,"required":required,"additionalProperties":True}

OBJ={"type":"object"}; ARR_OBJ={"type":"array","items":{"type":"object"}}; ARR_STR={"type":"array","items":{"type":"string"}}


def _raise(error_cls: type[Exception], exc: GovernanceError) -> None:
    raise error_cls(exc.code, exc.message, exc.status, **exc.extra)


def register_governance_tools(register_tool: Registrar, *, error_cls: type[Exception]) -> None:
    @register_tool(
        "governance.contacts.resolve",
        "Derive the bounded required governance-contact set for a declared task from an explicit currentness catalog.",
        "medium",
        category="governance",
        tags=["governance", "contact", "currentness", "read-gate"],
        side_effect_class="read",
        effect_traits=["deterministic", "authority_neutral", "bounded_results", "currentness_sensitive"],
        capability_version="1.0.0", schema_version="1",
        input_schema=_schema(["catalog","task"],{"catalog":OBJ,"task":OBJ}),
    )
    def contacts_resolve(payload: JsonObject) -> JsonObject:
        catalog=payload.get("catalog"); task=payload.get("task")
        if not isinstance(catalog,dict) or not isinstance(task,dict):
            raise error_cls("BAD_REQUEST","catalog and task objects are required",400)
        try: return derive_contact_set(catalog,task)
        except GovernanceError as exc: _raise(error_cls,exc)

    @register_tool(
        "governance.contacts.admit",
        "Verify exact task-bound governance contact receipts and local commit-recheck currentness. This is a precondition proof, never mutation authority.",
        "medium",
        category="governance",
        tags=["governance", "contact", "admission", "currentness"],
        side_effect_class="read",
        effect_traits=["deterministic", "authority_neutral", "commit_recheck", "fail_closed"],
        capability_version="1.0.0", schema_version="1",
        input_schema=_schema(["project_id","contact_set","receipts","catalog","task"],{"project_id":{"type":"string","minLength":1},"contact_set":OBJ,"receipts":ARR_OBJ,"catalog":OBJ,"task":OBJ}),
    )
    def contacts_admit(payload: JsonObject) -> JsonObject:
        contact_set=payload.get("contact_set"); receipts=payload.get("receipts"); catalog=payload.get("catalog"); task=payload.get("task")
        if not isinstance(contact_set,dict) or not isinstance(receipts,list) or not isinstance(catalog,dict) or not isinstance(task,dict):
            raise error_cls("BAD_REQUEST","contact_set, catalog, task objects and receipts list are required",400)
        project_id=str(payload.get("project_id") or "").strip()
        if not project_id: raise error_cls("BAD_REQUEST","project_id is required for governance contact admission",400)
        root=get_project_root(project_id)
        try: return admit_contact_set(contact_set,receipts,catalog=catalog,task=task,project_root=root)
        except GovernanceError as exc: _raise(error_cls,exc)

    @register_tool(
        "governance.exhaustion.enumerate",
        "Enumerate an admitted finite lawful pressure/environment frame without assuming every grammar is a Boolean powerset.",
        "medium",
        category="governance",
        tags=["governance", "exact-search", "grammar", "exhaustion"],
        side_effect_class="read",
        effect_traits=["deterministic", "authority_neutral", "bounded_results", "zero_partial_on_insufficient_budget"],
        capability_version="1.0.0", schema_version="1",
        input_schema=_schema(["grammar","environments"],{"project_id":{"type":"string"},"grammar":OBJ,"environments":ARR_OBJ,"compatibility":OBJ,"budget":{"type":"integer","minimum":0},"store_result":{"type":"boolean"}}),
    )
    def exhaustion_enumerate(payload: JsonObject) -> JsonObject:
        grammar=payload.get("grammar"); environments=payload.get("environments")
        if not isinstance(grammar,dict) or not isinstance(environments,list):
            raise error_cls("BAD_REQUEST","grammar object and environments list are required",400)
        compatibility=payload.get("compatibility")
        if compatibility is not None and not isinstance(compatibility,dict): raise error_cls("BAD_REQUEST","compatibility must be an object",400)
        budget=payload.get("budget")
        try: return enumerate_lawful_frame(grammar,environments,compatibility=compatibility,budget=budget)
        except GovernanceError as exc: _raise(error_cls,exc)

    @register_tool(
        "governance.exhaustion.evaluate_table",
        "Validate a complete pre-evaluated effect table against a bound responsibility frame/baseline and preserve full Pareto semantics.",
        "medium",
        category="governance",
        tags=["governance", "exact-search", "evaluator", "pareto", "evidence"],
        side_effect_class="read",
        effect_traits=["deterministic", "authority_neutral", "full_frame_required", "typed_failure"],
        capability_version="1.0.0", schema_version="1",
        input_schema=_schema(["responsibility_frame","binding","case_effects","expected_case_digests"],{"project_id":{"type":"string"},"responsibility_frame":ARR_STR,"binding":OBJ,"baseline":OBJ,"case_effects":ARR_OBJ,"expected_case_digests":ARR_STR,"store_result":{"type":"boolean"}}),
    )
    def exhaustion_evaluate(payload: JsonObject) -> JsonObject:
        frame=payload.get("responsibility_frame"); binding=payload.get("binding"); effects=payload.get("case_effects"); case_digests=payload.get("expected_case_digests")
        if not isinstance(frame,list) or not isinstance(binding,dict) or not isinstance(effects,list) or not isinstance(case_digests,list):
            raise error_cls("BAD_REQUEST","responsibility_frame, binding, case_effects, and expected_case_digests are required",400)
        baseline=payload.get("baseline")
        if baseline is not None and not isinstance(baseline,dict): raise error_cls("BAD_REQUEST","baseline must be an object",400)
        try: return evaluate_effect_table(frame=frame,baseline=baseline,baseline_binding=binding,case_effects=effects,expected_case_digests=case_digests)
        except GovernanceError as exc: _raise(error_cls,exc)
    @register_tool(
        "governance.exhaustion.compress_witnesses",
        "Compress a declared witness set to the lawful semantic-state minimal antichain; superset inheritance requires explicit monotonicity evidence.",
        "medium",
        category="governance",
        tags=["governance", "exact-search", "witness", "antichain"],
        side_effect_class="read",
        effect_traits=["deterministic", "authority_neutral", "monotonicity_gated"],
        capability_version="1.0.0", schema_version="1",
        input_schema=_schema(["cases","witness_case_digests"],{"project_id":{"type":"string"},"cases":ARR_OBJ,"witness_case_digests":ARR_STR,"inherit_supersets":{"type":"boolean"},"monotonicity_evidence":OBJ,"store_result":{"type":"boolean"}}),
    )
    def exhaustion_witnesses(payload: JsonObject) -> JsonObject:
        cases=payload.get("cases"); witnesses=payload.get("witness_case_digests")
        if not isinstance(cases,list) or not isinstance(witnesses,list):
            raise error_cls("BAD_REQUEST","cases and witness_case_digests lists are required",400)
        evidence=payload.get("monotonicity_evidence")
        if evidence is not None and not isinstance(evidence,dict): raise error_cls("BAD_REQUEST","monotonicity_evidence must be an object",400)
        try: return compress_minimal_witnesses(cases=cases,witness_case_digests=witnesses,inherit_supersets=bool(payload.get("inherit_supersets",False)),monotonicity_evidence=evidence)
        except GovernanceError as exc: _raise(error_cls,exc)
