"""Canonical User Continuity System v1.0 native capability surface.

The ``ucm.*`` API is the neutral v1 contract.  Legacy ``memory.*`` tools remain
available as a compatibility projection over the same authoritative ledger.
"""
from __future__ import annotations

from collections.abc import Callable, MutableMapping
from typing import Any

from . import user_continuity_store as backend
from . import ucm_v1_runtime as ucm

JsonObject = MutableMapping[str, Any]
Registrar = Callable[..., Any]

AUTHORITY_TRAITS = [
    "user_owned_continuity",
    "not_project_authority",
    "not_runtime_truth",
    "not_doctrine_authority",
]
READ_TRAITS = [*AUTHORITY_TRAITS, "bounded_results", "currentness_sensitive"]
WRITE_TRAITS = [
    *AUTHORITY_TRAITS,
    "durable_mutation",
    "append_only_hash_chained_ledger",
    "mandatory_seq_hash_cas",
    "idempotency_required",
    "post_write_readback",
]

OBJ = {"type": "object"}
STR = {"type": "string"}
BOOL = {"type": "boolean"}
INT = {"type": "integer"}
ARR_STR = {"type": "array", "items": {"type": "string"}}


def _schema(required: list[str], properties: dict[str, Any], *, additional: bool = False) -> dict[str, Any]:
    return {
        "type": "object",
        "required": required,
        "properties": properties,
        "additionalProperties": additional,
    }


def _profile() -> dict[str, Any]:
    return {"profile_id": {"type": "string", "minLength": 1, "maxLength": 160}}


def _write_base() -> dict[str, Any]:
    return {
        **_profile(),
        "actor": {"type": "string", "enum": sorted(backend.ACTORS)},
        "source_instance": {"type": "string", "minLength": 1, "maxLength": 160},
        "provenance": {
            "type": "object",
            "required": ["source_artifact", "source_pointer", "independence_group"],
            "properties": {
                "source_artifact": {"type": "string", "minLength": 1, "maxLength": 2000},
                "source_pointer": {"type": "string", "minLength": 1, "maxLength": 2000},
                "independence_group": {"type": "string", "minLength": 1, "maxLength": 300},
                "source_thread": {"type": ["string", "null"], "maxLength": 500},
                "source_event": {"type": ["string", "null"], "maxLength": 500},
            },
            "additionalProperties": False,
        },
        "idempotency_key": {"type": "string", "minLength": 1, "maxLength": 160},
        "expected_head_seq": {"type": "integer", "minimum": 0},
        "expected_head_hash": {"type": ["string", "null"], "pattern": "^[0-9a-f]{64}$"},
        "write_posture": {
            "type": "string",
            "enum": sorted(ucm.WRITE_POSTURES),
        },
    }


def _write_schema(extra_required: list[str], extra_properties: dict[str, Any]) -> dict[str, Any]:
    return _schema(
        [
            "profile_id",
            "actor",
            "source_instance",
            "provenance",
            "idempotency_key",
            "expected_head_seq",
            "expected_head_hash",
            "write_posture",
            *extra_required,
        ],
        {**_write_base(), **extra_properties},
    )


def _run(error_cls: type[Exception], fn: Callable[[], JsonObject]) -> JsonObject:
    try:
        return fn()
    except ucm.UcmError as exc:
        raise error_cls(exc.error_code, exc.message, exc.status, **exc.extra) from exc
    except backend.UserContinuityError as exc:
        raise error_cls(exc.error_code, exc.message, exc.status, **exc.extra) from exc


def register_ucm_tools(register_tool: Registrar, *, error_cls: type[Exception]) -> None:
    def register_read(name: str, description: str, required: list[str], properties: dict[str, Any], handler: Callable[[JsonObject], JsonObject], *, traits: list[str] | None = None) -> None:
        @register_tool(
            name,
            description,
            "low",
            category="memory",
            tags=["continuity", "ucm", "user-owned", "currentness"],
            side_effect_class="read",
            effect_traits=[*READ_TRAITS, *(traits or [])],
            capability_version="1.0.0",
            schema_version="1",
            input_schema=_schema(required, properties),
            output_schema={"type": "object"},
        )
        def _handler(payload: JsonObject) -> JsonObject:
            return _run(error_cls, lambda: handler(payload))

    def register_write(name: str, description: str, required: list[str], properties: dict[str, Any], handler: Callable[[JsonObject], JsonObject], *, side_effect_class: str = "mutation", traits: list[str] | None = None) -> None:
        @register_tool(
            name,
            description,
            "medium",
            category="memory",
            tags=["continuity", "ucm", "user-owned", "cas"],
            mutating=True,
            side_effect_class=side_effect_class,
            effect_traits=[*WRITE_TRAITS, *(traits or [])],
            capability_version="1.0.0",
            schema_version="1",
            input_schema=_write_schema(required, properties),
            output_schema={"type": "object"},
        )
        def _handler(payload: JsonObject) -> JsonObject:
            return _run(error_cls, lambda: handler(payload))

    register_read(
        "ucm.describe",
        "Describe the neutral UCS/UCM v1 contract, ingress rules, authority traits, and existing-ledger backend.",
        [],
        {},
        lambda _p: ucm.describe(),
        traits=["system_descriptor", "authority_firewall"],
    )
    register_read(
        "ucm.head",
        "Read authoritative user-ledger head and snapshot currentness without materializing the ledger.",
        ["profile_id"],
        _profile(),
        lambda p: ucm.head(str(p["profile_id"])),
        traits=["bounded_ledger_head_read"],
    )
    register_read(
        "ucm.read_core",
        "Compile and validate the bounded fresh-instance UCM core with all ten required surfaces and required headroom.",
        ["profile_id"],
        _profile(),
        lambda p: ucm.read_core(str(p["profile_id"])),
        traits=["fresh_instance_ingress", "core_budget_12000", "min_headroom_2000"],
    )
    register_read(
        "ucm.read_sections",
        "Read task-relevant UCM hydration groups lazily without treating retrieval as authority.",
        ["profile_id", "groups"],
        {**_profile(), "groups": {"type": "array", "minItems": 1, "maxItems": ucm.MAX_READ_GROUPS, "items": STR}, "include_historical": BOOL},
        lambda p: ucm.read_sections(str(p["profile_id"]), list(p["groups"]), include_historical=bool(p.get("include_historical", False))),
        traits=["lazy_hydration", "hydrated_not_consumed"],
    )
    register_read(
        "ucm.search",
        "Run bounded lexical UCM retrieval; search relevance is explicitly not evidentiary support.",
        ["profile_id", "query"],
        {**_profile(), "query": {"type": "string", "minLength": 1, "maxLength": 500}, "limit": {"type": "integer", "minimum": 1, "maximum": ucm.MAX_SEARCH_RESULTS}, "include_historical": BOOL},
        lambda p: ucm.search(str(p["profile_id"]), str(p["query"]), limit=int(p.get("limit", 20)), include_historical=bool(p.get("include_historical", False))),
        traits=["search_hit_not_claim_support"],
    )
    register_read(
        "ucm.events_tail",
        "Read a bounded semantic event tail from the authoritative UCM ledger.",
        ["profile_id"],
        {**_profile(), "count": {"type": "integer", "minimum": 0, "maximum": ucm.MAX_EVENT_TAIL}},
        lambda p: ucm.events_tail(str(p["profile_id"]), int(p.get("count", 20))),
        traits=["append_only_history", "bounded_ledger_tail"],
    )
    register_read(
        "ucm.get_fact",
        "Resolve one exact canonical UCM fact by stable fact key.",
        ["profile_id", "fact_key"],
        {**_profile(), "fact_key": STR},
        lambda p: {"ok": True, "fact": ucm.get_fact(str(p["profile_id"]), str(p["fact_key"])), "authority_effect": "NONE"},
    )
    register_read(
        "ucm.resolve_identity",
        "Resolve identity by explicit use, scope, status, and precedence; one person is not one name string.",
        ["profile_id", "use_for"],
        {**_profile(), "use_for": STR, "scope": {"type": ["string", "null"]}},
        lambda p: {"ok": True, "identity": ucm.resolve_identity(str(p["profile_id"]), use_for=str(p["use_for"]), scope=p.get("scope")), "authority_effect": "NONE"},
        traits=["identity_use_resolution"],
    )
    register_read(
        "ucm.resolve_referent",
        "Resolve a user/project referent by term, scope, status, and precedence without granting project authority.",
        ["profile_id", "term"],
        {**_profile(), "term": STR, "scope": {"type": ["string", "null"]}},
        lambda p: {"ok": True, "referent": ucm.resolve_referent(str(p["profile_id"]), term=str(p["term"]), scope=p.get("scope")), "authority_effect": "NONE"},
        traits=["referent_resolution_not_project_authority"],
    )
    register_read(
        "ucm.verification_debt",
        "Compute UCM currentness/revalidation debt from explicit verification components, never descriptive tags.",
        ["profile_id"],
        {**_profile(), "condition_tokens": ARR_STR},
        lambda p: {"ok": True, "items": ucm.verification_debt(str(p["profile_id"]), condition_tokens=set(p.get("condition_tokens") or [])), "authority_effect": "NONE"},
        traits=["verification_debt", "descriptive_class_not_behavioral_policy"],
    )
    register_read(
        "ucm.read_decisions",
        "Read user-continuity decision history with rationale/supersession preserved and no project-authority effect.",
        ["profile_id"],
        {**_profile(), "include_historical": BOOL},
        lambda p: {"ok": True, "decisions": ucm.read_decisions(str(p["profile_id"]), include_historical=bool(p.get("include_historical", False))), "authority_effect": "NONE"},
        traits=["decision_history"],
    )
    register_read(
        "ucm.read_control_state",
        "Read manual UCM lock/reset state; user control affects continuity behavior but never external authorization.",
        ["profile_id"],
        _profile(),
        lambda p: {"ok": True, "control_state": ucm.read_control_state(str(p["profile_id"])), "authority_effect": "NONE"},
        traits=["manual_control"],
    )
    register_read(
        "ucm.memory_candidates",
        "Read PROPOSE_ONLY memory candidates without promoting AI pattern detection into active user facts.",
        ["profile_id"],
        {**_profile(), "include_closed": BOOL},
        lambda p: {"ok": True, "candidates": ucm.memory_candidates(str(p["profile_id"]), include_closed=bool(p.get("include_closed", False))), "authority_effect": "NONE"},
        traits=["candidate_not_active_fact"],
    )
    register_read(
        "ucm.compile_context_packet",
        "Compile a bounded task-conditioned UCM packet; retrieval packet remains navigation, not authority.",
        ["profile_id"],
        {**_profile(), "groups": ARR_STR, "query": {"type": ["string", "null"]}, "max_bytes": {"type": "integer", "minimum": 1, "maximum": ucm.MAX_CONTEXT_PACKET_BYTES}},
        lambda p: ucm.compile_context_packet(str(p["profile_id"]), groups=p.get("groups"), query=p.get("query"), max_bytes=int(p.get("max_bytes", 12000))),
        traits=["bounded_adaptive_retrieval", "retrieval_packet_not_authority"],
    )
    register_read(
        "ucm.source_manifest",
        "Read content-addressed source/coverage assertions without interpreting source absence as negation.",
        ["profile_id"],
        _profile(),
        lambda p: {"ok": True, "sources": ucm.source_manifest(str(p["profile_id"])), "authority_effect": "NONE", "law": "ABSENCE_IN_SOURCE != NEGATION"},
        traits=["content_addressed_source_evidence", "source_absence_not_negation"],
    )

    record_type = {"type": "string", "enum": sorted(ucm.RECORD_TYPES)}
    register_write(
        "ucm.add",
        "Append one canonical UCS v1 typed record using mandatory sequence+hash CAS and post-write readback.",
        ["record_type", "record"],
        {"record_type": record_type, "record": OBJ},
        ucm.add,
        traits=["orthogonal_fact_policy", "descriptive_class_not_behavioral_policy"],
    )
    register_write(
        "ucm.update",
        "Update non-material UCM metadata; material value/identity/currentness/verification changes require dedicated semantic operations.",
        ["record_type", "record_key", "patch"],
        {"record_type": STR, "record_key": STR, "patch": OBJ},
        ucm.update,
        traits=["material_change_requires_semantic_transition"],
    )
    register_write(
        "ucm.supersede",
        "Supersede one stable-key UCM record while preserving causal correction evidence.",
        ["record_type", "record_key", "replacement", "evidence_refs"],
        {"record_type": STR, "record_key": STR, "replacement": OBJ, "evidence_refs": {"type": "array", "minItems": 1, "items": STR}},
        ucm.supersede,
        traits=["stable_key", "correction_evidence_required"],
    )
    register_write(
        "ucm.verify",
        "Bind one canonical fact to an explicit live verifier reference and advance currentness through a dedicated semantic transition.",
        ["fact_key", "verification_ref"],
        {"fact_key": STR, "verification_ref": STR, "verified_at": {"type": ["string", "null"]}},
        ucm.verify,
        traits=["verifier_available_not_verified", "live_verification_binding"],
    )
    register_write(
        "ucm.conflict",
        "Preserve a fact conflict and contradictory evidence instead of smoothing it into one current value.",
        ["fact_key", "evidence_refs"],
        {"fact_key": STR, "evidence_refs": {"type": "array", "minItems": 1, "items": STR}},
        ucm.conflict,
        traits=["contradiction_preserved"],
    )
    register_write(
        "ucm.retire",
        "Retire a canonical UCM fact without erasing provenance or historical lineage.",
        ["fact_key"],
        {"fact_key": STR},
        ucm.retire,
        traits=["retirement_not_erasure"],
    )
    register_write(
        "ucm.rediscover",
        "Rediscover a retired/historical UCM fact as new continuity evidence while retaining old lineage.",
        ["fact_key", "evidence_refs"],
        {"fact_key": STR, "evidence_refs": {"type": "array", "minItems": 1, "items": STR}},
        ucm.rediscover,
        traits=["rediscovery_lineage"],
    )
    register_write(
        "ucm.forget_request",
        "Record a direct-user-authorized forget request without pretending append-only history never existed.",
        ["fact_key"],
        {"fact_key": STR},
        ucm.forget_request,
        traits=["forget_request_not_retirement", "direct_user_authorization_required"],
    )
    register_write(
        "ucm.materialize",
        "Verify/fold the authoritative UCM ledger and rebuild content-addressed snapshots under mandatory head CAS; ingress readiness is reported separately.",
        [],
        {},
        ucm.materialize,
        side_effect_class="reconcile",
        traits=["derived_state_is_fold", "materialization_not_authority"],
    )
    register_write(
        "ucm.lock",
        "Apply a direct-user-authorized UCM behavioral lock without granting project/tool authority.",
        ["lock"],
        {"lock": {"type": "string", "enum": sorted(ucm.CONTROL_LOCKS)}},
        ucm.lock,
        traits=["manual_lock_overrides_adaptive_behavior", "direct_user_authorization_required"],
    )
    register_write(
        "ucm.unlock",
        "Remove a direct-user-authorized UCM behavioral lock without granting project/tool authority.",
        ["lock"],
        {"lock": {"type": "string", "enum": sorted(ucm.CONTROL_LOCKS)}},
        ucm.unlock,
        traits=["manual_lock_overrides_adaptive_behavior", "direct_user_authorization_required"],
    )
    register_write(
        "ucm.session_reset",
        "Reset ephemeral/session-adaptive UCM state while explicitly preserving durable memory history.",
        ["scope"],
        {"scope": {"type": "string", "enum": sorted(ucm.RESET_SCOPES)}, "reset_at": {"type": ["string", "null"]}},
        ucm.session_reset,
        traits=["session_reset_not_durable_delete", "direct_user_authorization_required"],
    )
    register_write(
        "ucm.decision_add",
        "Append a user-continuity decision record with rationale/evidence while remaining non-authoritative for project state.",
        ["decision"],
        {"decision": OBJ},
        ucm.decision_add,
        traits=["decision_record_not_project_authority"],
    )
    register_write(
        "ucm.decision_supersede",
        "Supersede one stable decision ID with explicit evidence while retaining decision history.",
        ["decision_id", "replacement", "evidence_refs"],
        {"decision_id": STR, "replacement": OBJ, "evidence_refs": {"type": "array", "minItems": 1, "items": STR}},
        ucm.decision_supersede,
        traits=["decision_history", "stable_key", "correction_evidence_required"],
    )
    register_write(
        "ucm.memory_candidate_confirm",
        "Accept or reject a PROPOSE_ONLY AI memory candidate under direct user authority without silently creating a user-stated fact.",
        ["candidate_id", "user_confirmed"],
        {"candidate_id": STR, "user_confirmed": BOOL},
        ucm.memory_candidate_confirm,
        traits=["candidate_not_active_fact", "direct_user_authorization_required"],
    )

    register_read(
        "ucm.export_filtered",
        "Mechanically filter UCM records by destination/export class while preserving privacy and authority boundaries.",
        ["profile_id", "destination_class"],
        {**_profile(), "destination_class": {"type": "string", "enum": ["NEUTRAL_SYSTEM", "USER_BACKUP", "PROJECT_EXPORT", "DEPLOYMENT_BACKUP"]}},
        lambda p: ucm.export_filtered(str(p["profile_id"]), str(p["destination_class"])),
        traits=["export_class_filter", "privacy_boundary"],
    )
