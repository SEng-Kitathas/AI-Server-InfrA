"""Native semantic tools for user-owned continuity memory."""
from __future__ import annotations

from collections.abc import Callable, MutableMapping
from typing import Any

from .user_continuity_store import (
    ACTORS,
    CONFIDENCE,
    EXPORT_CLASSES,
    MAX_LEDGER_TAIL,
    MAX_READ_SECTIONS,
    MAX_SEARCH_RESULTS,
    MEMORY_CLASSES,
    MEMORY_STATUSES,
    SENSITIVITY,
    UserContinuityError,
    memory_add,
    memory_compact_snapshot,
    memory_forget_request,
    memory_read,
    memory_search,
    memory_supersede,
    memory_update,
    memory_verify,
)

JsonObject = MutableMapping[str, Any]
Registrar = Callable[..., Any]


def _run(error_cls: type[Exception], fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        return fn()
    except UserContinuityError as exc:
        raise error_cls(exc.error_code, exc.message, exc.status, **exc.extra) from exc


def _source_properties() -> dict[str, Any]:
    return {
        "profile_id": {"type": "string", "minLength": 1, "maxLength": 160},
        "actor": {"type": "string", "enum": sorted(ACTORS)},
        "source_instance": {"type": "string", "minLength": 1, "maxLength": 160},
        "source_thread": {"type": ["string", "null"], "maxLength": 500},
        "source_event": {"type": ["string", "null"], "maxLength": 500},
        "evidence_independence_group": {"type": ["string", "null"], "maxLength": 200},
        "idempotency_key": {"type": "string", "minLength": 1, "maxLength": 160},
        "expected_ledger_head_hash": {
            "type": ["string", "null"],
            "description": "Optional CAS expectation; use genesis for an empty ledger.",
        },
    }


def _fact_properties() -> dict[str, Any]:
    return {
        "target": {"type": "string", "minLength": 1, "maxLength": 256},
        "section": {"type": "string", "minLength": 1, "maxLength": 128},
        "class": {"type": "string", "enum": sorted(MEMORY_CLASSES)},
        "status": {"type": "string", "enum": sorted(MEMORY_STATUSES)},
        "value": {},
        "reason": {"type": "string", "minLength": 1, "maxLength": 8000},
        "provenance": {"type": ["string", "null"], "maxLength": 16000},
        "confidence": {"type": "string", "enum": sorted(CONFIDENCE)},
        "requires_live_verification": {"type": "boolean"},
        "sensitivity": {"type": "string", "enum": sorted(SENSITIVITY)},
        "export_class": {"type": "string", "enum": sorted(EXPORT_CLASSES)},
        "always_load": {"type": "boolean"},
        "hydration_priority": {"type": "integer", "minimum": 0, "maximum": 100000},
        "last_verified_at": {"type": ["string", "null"]},
        "revalidate_after": {"type": ["string", "null"]},
        "revalidate_when": {
            "type": "array",
            "maxItems": 32,
            "items": {"type": "string", "minLength": 1, "maxLength": 200},
        },
    }


def _evidence_schema() -> dict[str, Any]:
    return {
        "type": "array",
        "minItems": 1,
        "maxItems": 32,
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "ref"],
            "properties": {
                "type": {"type": "string", "minLength": 1, "maxLength": 160},
                "ref": {"type": "string", "minLength": 1, "maxLength": 2000},
                "sha256": {"type": ["string", "null"], "pattern": "^[0-9a-fA-F]{64}$"},
                "independence_group": {"type": ["string", "null"], "maxLength": 200},
            },
        },
    }


def _schema(required: list[str], properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "required": required,
        "additionalProperties": False,
        "properties": properties,
    }


def register_memory_tools(register_tool: Registrar, *, error_cls: type[Exception]) -> None:
    source = _source_properties()
    fact = _fact_properties()
    mutation_traits = [
        "durable_mutation",
        "global_user_continuity",
        "append_only_ledger",
        "hash_chained_ledger",
        "idempotency_required",
        "snapshot_materialized",
        "snapshot_cas_supported",
        "not_project_authority",
    ]

    @register_tool(
        "memory.add",
        "Append one new durable user-continuity fact and materialize the bounded addressable snapshot.",
        "medium",
        category="memory",
        tags=["continuity", "memory", "append-only", "user-overlay"],
        mutating=True,
        side_effect_class="mutation",
        effect_traits=mutation_traits,
        input_schema=_schema(
            [
                "actor",
                "source_instance",
                "idempotency_key",
                "target",
                "section",
                "class",
                "value",
                "reason",
                "export_class",
            ],
            {**source, **fact},
        ),
        output_schema={"type": "object"},
    )
    def tool_memory_add(payload: JsonObject) -> JsonObject:
        return _run(error_cls, lambda: memory_add(dict(payload)))

    update_patch = {
        key: value
        for key, value in fact.items()
        if key
        in {
            "status",
            "reason",
            "provenance",
            "confidence",
            "requires_live_verification",
            "sensitivity",
            "export_class",
            "always_load",
            "hydration_priority",
            "last_verified_at",
            "revalidate_after",
            "revalidate_when",
            "section",
        }
    }
    @register_tool(
        "memory.update",
        "Update non-material metadata/currentness for one memory fact; material value/identity changes require memory.supersede.",
        "medium",
        category="memory",
        tags=["continuity", "memory", "metadata", "currentness"],
        mutating=True,
        side_effect_class="mutation",
        effect_traits=[*mutation_traits, "material_change_requires_supersede"],
        input_schema=_schema(
            ["actor", "source_instance", "idempotency_key", "memory_id", "patch"],
            {
                **source,
                "memory_id": {"type": "string", "minLength": 1, "maxLength": 160},
                "patch": {
                    "type": "object",
                    "minProperties": 1,
                    "additionalProperties": False,
                    "properties": update_patch,
                },
            },
        ),
        output_schema={"type": "object"},
    )
    def tool_memory_update(payload: JsonObject) -> JsonObject:
        return _run(error_cls, lambda: memory_update(dict(payload)))

    @register_tool(
        "memory.supersede",
        "Supersede one current memory fact with a replacement on the same stable target and record the evidence that forced the change.",
        "medium",
        category="memory",
        tags=["continuity", "memory", "supersession", "evidence"],
        mutating=True,
        side_effect_class="mutation",
        effect_traits=[*mutation_traits, "causal_supersession", "superseded_by_evidence_required"],
        input_schema=_schema(
            [
                "actor",
                "source_instance",
                "idempotency_key",
                "memory_id",
                "replacement",
                "superseded_by_evidence",
            ],
            {
                **source,
                "memory_id": {"type": "string", "minLength": 1, "maxLength": 160},
                "replacement": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["value", "reason"],
                    "properties": fact,
                },
                "superseded_by_evidence": _evidence_schema(),
            },
        ),
        output_schema={"type": "object"},
    )
    def tool_memory_supersede(payload: JsonObject) -> JsonObject:
        return _run(error_cls, lambda: memory_supersede(dict(payload)))

    @register_tool(
        "memory.verify",
        "Record verification evidence for one current memory fact without promoting continuity into live/project authority.",
        "medium",
        category="memory",
        tags=["continuity", "memory", "verification", "evidence-independence"],
        mutating=True,
        side_effect_class="mutation",
        effect_traits=[*mutation_traits, "verification_evidence", "independence_groups_preserved"],
        input_schema=_schema(
            ["actor", "source_instance", "idempotency_key", "memory_id", "evidence"],
            {
                **source,
                "memory_id": {"type": "string", "minLength": 1, "maxLength": 160},
                "verified_at": {"type": ["string", "null"]},
                "status": {"type": ["string", "null"], "enum": [*sorted(MEMORY_STATUSES), None]},
                "confidence": {"type": ["string", "null"], "enum": [*sorted(CONFIDENCE), None]},
                "evidence": _evidence_schema(),
            },
        ),
        output_schema={"type": "object"},
    )
    def tool_memory_verify(payload: JsonObject) -> JsonObject:
        return _run(error_cls, lambda: memory_verify(dict(payload)))

    @register_tool(
        "memory.forget_request",
        "Append a forget-request tombstone for a memory fact; this does not pretend append-only history was physically erased.",
        "medium",
        category="memory",
        tags=["continuity", "memory", "forget", "tombstone"],
        mutating=True,
        side_effect_class="mutation",
        effect_traits=[*mutation_traits, "tombstone", "no_physical_erasure_claim"],
        input_schema=_schema(
            ["actor", "source_instance", "idempotency_key", "memory_id", "reason"],
            {
                **source,
                "memory_id": {"type": "string", "minLength": 1, "maxLength": 160},
                "reason": {"type": "string", "minLength": 1, "maxLength": 8000},
            },
        ),
        output_schema={"type": "object"},
    )
    def tool_memory_forget_request(payload: JsonObject) -> JsonObject:
        return _run(error_cls, lambda: memory_forget_request(dict(payload)))

    @register_tool(
        "memory.compact_snapshot",
        "Verify/fold the authoritative user-continuity ledger and rebuild the bounded content-addressed snapshot with optional head CAS.",
        "medium",
        category="memory",
        tags=["continuity", "memory", "snapshot", "recovery", "cas"],
        mutating=True,
        side_effect_class="reconcile",
        effect_traits=[
            "derived_state_mutation",
            "verifies_hash_chain",
            "snapshot_materialization_serialized",
            "snapshot_cas_supported",
            "content_addressed_sections",
            "not_memory_authority_mutation",
        ],
        input_schema=_schema(
            [],
            {
                "profile_id": {"type": "string", "minLength": 1, "maxLength": 160},
                "expected_ledger_head_hash": {"type": ["string", "null"]},
            },
        ),
        output_schema={"type": "object"},
    )
    def tool_memory_compact_snapshot(payload: JsonObject) -> JsonObject:
        return _run(error_cls, lambda: memory_compact_snapshot(dict(payload)))

    @register_tool(
        "memory.read",
        "Read the hard-capped always-load core plus selected lazy sections and a bounded ledger tail; fail closed on stale snapshot currentness.",
        "low",
        category="memory",
        tags=["continuity", "memory", "hydration", "currentness"],
        side_effect_class="read",
        effect_traits=[
            "reads_persistent_state",
            "bounded_output",
            "bounded_ledger_head_read",
            "addressable_snapshot",
            "source_currentness_check",
            "non_initializing",
            "not_project_authority",
        ],
        input_schema=_schema(
            [],
            {
                "profile_id": {"type": "string", "minLength": 1, "maxLength": 160},
                "sections": {
                    "type": "array",
                    "maxItems": MAX_READ_SECTIONS,
                    "items": {"type": "string", "minLength": 1, "maxLength": 128},
                },
                "include_superseded": {"type": "boolean"},
                "export_classes": {
                    "type": "array",
                    "maxItems": 4,
                    "items": {"type": "string", "enum": sorted(EXPORT_CLASSES)},
                },
                "ledger_tail": {"type": "integer", "minimum": 0, "maximum": MAX_LEDGER_TAIL},
                "target": {"type": ["string", "null"], "maxLength": 256},
            },
        ),
        output_schema={"type": "object"},
    )
    def tool_memory_read(payload: JsonObject) -> JsonObject:
        return _run(error_cls, lambda: memory_read(dict(payload)))

    @register_tool(
        "memory.search",
        "Search the current addressable memory snapshot with bounded lexical matching; stale snapshots fail closed instead of returning stale-as-current results.",
        "low",
        category="memory",
        tags=["continuity", "memory", "search", "currentness"],
        side_effect_class="read",
        effect_traits=[
            "reads_persistent_state",
            "bounded_results",
            "source_currentness_check",
            "non_initializing",
            "not_project_authority",
        ],
        input_schema=_schema(
            ["query"],
            {
                "profile_id": {"type": "string", "minLength": 1, "maxLength": 160},
                "query": {"type": "string", "minLength": 1, "maxLength": 500},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_SEARCH_RESULTS},
                "sections": {
                    "type": "array",
                    "maxItems": MAX_READ_SECTIONS,
                    "items": {"type": "string", "minLength": 1, "maxLength": 128},
                },
                "include_superseded": {"type": "boolean"},
                "export_classes": {
                    "type": "array",
                    "maxItems": 4,
                    "items": {"type": "string", "enum": sorted(EXPORT_CLASSES)},
                },
            },
        ),
        output_schema={"type": "object"},
    )
    def tool_memory_search(payload: JsonObject) -> JsonObject:
        return _run(error_cls, lambda: memory_search(dict(payload)))
