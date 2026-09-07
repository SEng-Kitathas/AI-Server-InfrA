"""PCMMAD-native runtime protocol tools registered behind the lab router."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from lab_tool_primitives import (
    ToolPayload,
    ToolResult,
    payload_bool,
    payload_list_of_str,
    payload_optional_int,
    payload_optional_str,
    payload_str,
    payload_value,
)
from protocol_models import ProtocolValidationError
from protocol_merkle import (
    merkle_consistency_receipt,
    merkle_inclusion_receipt,
    merkle_root_receipt,
)
from protocol_store import (
    ProtocolConflictError,
    ProtocolLedgerError,
    ensure_protocol,
    evaluate_mode_gate,
    protocol_status,
    record_claim,
    record_constraint,
    record_continuity,
    record_promotion,
    record_waiver,
    register_artifact,
    set_objective,
    transition_mode,
    verify_events,
)

ProtocolRegistrar = Callable[
    ..., Callable[[Callable[[ToolPayload], ToolResult]], Callable[[ToolPayload], ToolResult]]
]


@dataclass(frozen=True)
class ProtocolRegistrationContext:
    """Dependencies shared by protocol-tool registration groups."""

    register_tool: ProtocolRegistrar
    error_cls: type[Exception]
    common_schema: Mapping[str, object]


def _project_id(payload: ToolPayload) -> str:
    return payload_str(payload, "project_id").strip()


def _actor(payload: ToolPayload) -> str:
    return payload_str(payload, "actor", "pcmmad.operator").strip() or "pcmmad.operator"


def _evidence(payload: ToolPayload) -> list[object]:
    value = payload_value(payload, "evidence", [])
    return list(value) if isinstance(value, list) else []


def _float_or_none(payload: ToolPayload, key: str) -> float | None:
    value = payload_value(payload, key)
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ProtocolValidationError(f"{key} must be numeric") from exc


def _event_result(event: Any) -> ToolResult:
    return {"event": event.to_dict()}


def _translate_errors(error_cls: type[Exception], fn: Callable[[], ToolResult]) -> ToolResult:
    try:
        return fn()
    except ProtocolValidationError as exc:
        raise error_cls("PROTOCOL_VALIDATION_FAILED", str(exc), 400) from exc
    except ProtocolConflictError as exc:
        raise error_cls("PROTOCOL_CONFLICT", str(exc), 409) from exc
    except ProtocolLedgerError as exc:
        raise error_cls("PROTOCOL_LEDGER_INVALID", str(exc), 409) from exc


def _schema(required: list[str], properties: Mapping[str, object]) -> dict[str, object]:
    return {
        "type": "object",
        "properties": dict(properties),
        "required": required,
        "additionalProperties": True,
    }


def _run(context: ProtocolRegistrationContext, fn: Callable[[], ToolResult]) -> ToolResult:
    return _translate_errors(context.error_cls, fn)


def _register_observation_tools(context: ProtocolRegistrationContext) -> None:
    common = context.common_schema

    @context.register_tool(
        "protocol.initialize",
        "Initialize the append-only PCMMAD runtime protocol for a project.",
        "medium",
        category="protocol",
        tags=["pcmmad", "state", "genesis", "pdver"],
        mutating=True,
        input_schema=_schema(
            ["project_id"],
            {
                **common,
                "rigor_level": {
                    "type": "string",
                    "enum": ["STANDARD", "ELEVATED", "CRITICAL"],
                },
                "initial_mode": {
                    "type": "string",
                    "enum": [
                        "DISCUSSION",
                        "AUDIT",
                        "BUILD_PLAN",
                        "BUILD_COMMIT",
                        "RECOVERY",
                        "CHECKPOINT",
                        "MERGE",
                        "PROMOTION",
                    ],
                },
            },
        ),
    )
    def tool_protocol_initialize(payload: ToolPayload) -> ToolResult:
        return _run(
            context,
            lambda: {
                "state": ensure_protocol(
                    _project_id(payload),
                    actor=_actor(payload),
                    rigor_level=payload_str(payload, "rigor_level", "STANDARD"),
                    initial_mode=payload_str(payload, "initial_mode", "DISCUSSION"),
                ).to_dict()
            },
        )

    @context.register_tool(
        "protocol.status",
        "Read the verified PCMMAD runtime-protocol state and ledger head.",
        "low",
        category="protocol",
        tags=["pcmmad", "state", "continuity", "ledger"],
        side_effect_class="read",
        effect_traits=["reads_state", "verifies_hash_chain", "non_initializing"],
        input_schema=_schema(["project_id"], common),
    )
    def tool_protocol_status(payload: ToolPayload) -> ToolResult:
        return _run(
            context,
            lambda: protocol_status(_project_id(payload), initialize=False, actor=_actor(payload)),
        )

    @context.register_tool(
        "protocol.guard.check",
        "Evaluate whether the current PCMMAD mode permits read, governance, specimen, or promotion work.",
        "low",
        category="protocol",
        tags=["pcmmad", "mode", "guard", "discourse-build-boundary"],
        side_effect_class="read",
        effect_traits=["reads_state", "evaluates_policy", "non_initializing"],
        input_schema=_schema(
            ["project_id", "mutation_domain"],
            {
                **common,
                "mutation_domain": {
                    "type": "string",
                    "enum": ["READ", "GOVERNANCE", "SPECIMEN", "PROMOTION"],
                },
            },
        ),
    )
    def tool_protocol_guard_check(payload: ToolPayload) -> ToolResult:
        return _run(
            context,
            lambda: evaluate_mode_gate(
                _project_id(payload),
                payload_str(payload, "mutation_domain"),
                actor=_actor(payload),
            ),
        )


def _register_mode_and_objective_tools(context: ProtocolRegistrationContext) -> None:
    common = context.common_schema

    @context.register_tool(
        "protocol.mode.transition",
        "Explicitly transition the PCMMAD discourse/build/recovery/promotion mode.",
        "medium",
        category="protocol",
        tags=["pcmmad", "mode", "boundary"],
        mutating=True,
        input_schema=_schema(
            ["project_id", "to_mode", "reason"],
            {
                **common,
                "to_mode": {"type": "string"},
                "expected_mode": {"type": "string"},
                "reason": {"type": "string", "minLength": 1},
            },
        ),
    )
    def tool_protocol_mode_transition(payload: ToolPayload) -> ToolResult:
        return _run(
            context,
            lambda: _event_result(
                transition_mode(
                    _project_id(payload),
                    to_mode=payload_str(payload, "to_mode"),
                    expected_mode=payload_optional_str(payload, "expected_mode"),
                    reason=payload_str(payload, "reason"),
                    actor=_actor(payload),
                )
            ),
        )

    @context.register_tool(
        "protocol.objective.set",
        "Set the active objective as an append-only superseding event.",
        "medium",
        category="protocol",
        tags=["pcmmad", "objective", "state"],
        mutating=True,
        input_schema=_schema(
            ["project_id", "objective_id", "statement"],
            {
                **common,
                "objective_id": {"type": "string"},
                "statement": {"type": "string"},
                "success_criteria": {"type": "array", "items": {"type": "string"}},
                "scope": {"type": "string"},
            },
        ),
    )
    def tool_protocol_objective_set(payload: ToolPayload) -> ToolResult:
        return _run(
            context,
            lambda: _event_result(
                set_objective(
                    _project_id(payload),
                    objective_id=payload_str(payload, "objective_id"),
                    statement=payload_str(payload, "statement"),
                    success_criteria=payload_list_of_str(payload, "success_criteria"),
                    scope=payload_optional_str(payload, "scope"),
                    actor=_actor(payload),
                )
            ),
        )


def _register_constraint_and_continuity_tools(
    context: ProtocolRegistrationContext,
) -> None:
    common = context.common_schema

    @context.register_tool(
        "protocol.constraint.record",
        "Append or supersede a typed PCMMAD constraint without erasing history.",
        "medium",
        category="protocol",
        tags=["pcmmad", "constraint", "state"],
        mutating=True,
        input_schema=_schema(
            ["project_id", "constraint_id", "statement", "strength"],
            {
                **common,
                "constraint_id": {"type": "string"},
                "statement": {"type": "string"},
                "strength": {
                    "type": "string",
                    "enum": ["REQUIRED", "PREFERRED", "ADVISORY"],
                },
                "source": {"type": "string"},
                "active": {"type": "boolean"},
            },
        ),
    )
    def tool_protocol_constraint_record(payload: ToolPayload) -> ToolResult:
        return _run(
            context,
            lambda: _event_result(
                record_constraint(
                    _project_id(payload),
                    constraint_id=payload_str(payload, "constraint_id"),
                    statement=payload_str(payload, "statement"),
                    strength=payload_str(payload, "strength"),
                    source=payload_optional_str(payload, "source"),
                    active=payload_bool(payload, "active", True),
                    actor=_actor(payload),
                )
            ),
        )

    @context.register_tool(
        "protocol.continuity.record",
        "Record live-shadow, design-thread, revisit, doctrine, trace, memory, or maintenance continuity.",
        "medium",
        category="protocol",
        tags=["pcmmad", "continuity", "state"],
        mutating=True,
        input_schema=_schema(
            ["project_id", "continuity_id", "kind", "summary"],
            {
                **common,
                "continuity_id": {"type": "string"},
                "kind": {"type": "string"},
                "summary": {"type": "string"},
                "artifact_ref": {"type": "string"},
                "open_loops": {"type": "array", "items": {"type": "string"}},
            },
        ),
    )
    def tool_protocol_continuity_record(payload: ToolPayload) -> ToolResult:
        return _run(
            context,
            lambda: _event_result(
                record_continuity(
                    _project_id(payload),
                    continuity_id=payload_str(payload, "continuity_id"),
                    kind=payload_str(payload, "kind"),
                    summary=payload_str(payload, "summary"),
                    artifact_ref=payload_optional_str(payload, "artifact_ref"),
                    open_loops=payload_list_of_str(payload, "open_loops"),
                    actor=_actor(payload),
                )
            ),
        )


def _register_claim_and_artifact_tools(context: ProtocolRegistrationContext) -> None:
    common = context.common_schema

    @context.register_tool(
        "protocol.claim.record",
        "Record or revise a typed claim with evidence and confidence.",
        "medium",
        category="protocol",
        tags=["pcmmad", "claim", "evidence", "adjudication"],
        mutating=True,
        input_schema=_schema(
            ["project_id", "claim_id", "kind", "statement"],
            {
                **common,
                "claim_id": {"type": "string"},
                "kind": {"type": "string"},
                "statement": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "evidence": {"type": "array", "items": {"type": "object"}},
            },
        ),
    )
    def tool_protocol_claim_record(payload: ToolPayload) -> ToolResult:
        return _run(
            context,
            lambda: _event_result(
                record_claim(
                    _project_id(payload),
                    claim_id=payload_str(payload, "claim_id"),
                    kind=payload_str(payload, "kind"),
                    statement=payload_str(payload, "statement"),
                    confidence=_float_or_none(payload, "confidence"),
                    evidence=_evidence(payload),
                    actor=_actor(payload),
                )
            ),
        )

    @context.register_tool(
        "protocol.artifact.register",
        "Register a typed artifact identity, provenance, and optional seal in protocol state.",
        "medium",
        category="protocol",
        tags=["pcmmad", "artifact", "provenance", "seal"],
        mutating=True,
        input_schema=_schema(
            ["project_id", "artifact_id", "artifact_class"],
            {
                **common,
                "artifact_id": {"type": "string"},
                "artifact_class": {"type": "string"},
                "path": {"type": "string"},
                "sha256": {"type": "string"},
                "sealed": {"type": "boolean"},
                "provenance": {"type": "array", "items": {"type": "string"}},
            },
        ),
    )
    def tool_protocol_artifact_register(payload: ToolPayload) -> ToolResult:
        return _run(
            context,
            lambda: _event_result(
                register_artifact(
                    _project_id(payload),
                    artifact_id=payload_str(payload, "artifact_id"),
                    artifact_class=payload_str(payload, "artifact_class"),
                    path=payload_optional_str(payload, "path"),
                    sha256=payload_optional_str(payload, "sha256"),
                    sealed=payload_bool(payload, "sealed", False),
                    provenance=payload_list_of_str(payload, "provenance"),
                    actor=_actor(payload),
                )
            ),
        )


def _register_promotion_and_waiver_tools(context: ProtocolRegistrationContext) -> None:
    common = context.common_schema

    @context.register_tool(
        "protocol.promotion.record",
        "Adjudicate a claim or artifact as ratified, provisional, rejected, deferred, demoted, or superseded.",
        "high",
        category="protocol",
        tags=["pcmmad", "promotion", "adjudication", "evidence"],
        approval_required=True,
        mutating=True,
        input_schema=_schema(
            ["project_id", "target_type", "target_id", "decision", "rationale"],
            {
                **common,
                "target_type": {"type": "string", "enum": ["claim", "artifact"]},
                "target_id": {"type": "string"},
                "decision": {"type": "string"},
                "rationale": {"type": "string"},
                "evidence": {"type": "array", "items": {"type": "object"}},
                "waiver_ids": {"type": "array", "items": {"type": "string"}},
            },
        ),
    )
    def tool_protocol_promotion_record(payload: ToolPayload) -> ToolResult:
        return _run(
            context,
            lambda: _event_result(
                record_promotion(
                    _project_id(payload),
                    target_type=payload_str(payload, "target_type"),
                    target_id=payload_str(payload, "target_id"),
                    decision=payload_str(payload, "decision"),
                    rationale=payload_str(payload, "rationale"),
                    evidence=_evidence(payload),
                    waiver_ids=payload_list_of_str(payload, "waiver_ids"),
                    actor=_actor(payload),
                )
            ),
        )

    @context.register_tool(
        "protocol.waiver.record",
        "Record a scoped, owned, expiring doctrine waiver with claim lineage.",
        "high",
        category="protocol",
        tags=["pcmmad", "waiver", "governance", "expiry"],
        approval_required=True,
        mutating=True,
        input_schema=_schema(
            ["project_id", "waiver_id", "scope", "reason", "doctrine_basis", "owner"],
            {
                **common,
                "waiver_id": {"type": "string"},
                "scope": {"type": "string"},
                "reason": {"type": "string"},
                "doctrine_basis": {"type": "string"},
                "owner": {"type": "string"},
                "status": {"type": "string"},
                "expires_at": {"type": "string"},
                "affected_claims": {"type": "array", "items": {"type": "string"}},
            },
        ),
    )
    def tool_protocol_waiver_record(payload: ToolPayload) -> ToolResult:
        return _run(
            context,
            lambda: _event_result(
                record_waiver(
                    _project_id(payload),
                    waiver_id=payload_str(payload, "waiver_id"),
                    scope=payload_str(payload, "scope"),
                    reason=payload_str(payload, "reason"),
                    doctrine_basis=payload_str(payload, "doctrine_basis"),
                    owner=payload_str(payload, "owner"),
                    status=payload_str(payload, "status", "ACTIVE"),
                    expires_at=payload_optional_str(payload, "expires_at"),
                    affected_claims=payload_list_of_str(payload, "affected_claims"),
                    actor=_actor(payload),
                )
            ),
        )


def _register_integrity_tools(context: ProtocolRegistrationContext) -> None:
    @context.register_tool(
        "protocol.ledger.verify",
        "Verify sequence, project identity, previous hashes, and event hashes in the protocol ledger.",
        "low",
        category="protocol",
        tags=["pcmmad", "ledger", "verification", "integrity"],
        side_effect_class="read",
        effect_traits=["reads_state", "verifies_hash_chain", "non_initializing"],
        input_schema=_schema(["project_id"], context.common_schema),
    )
    def tool_protocol_ledger_verify(payload: ToolPayload) -> ToolResult:
        return _run(context, lambda: verify_events(_project_id(payload)))

    @context.register_tool(
        "protocol.merkle.root",
        "Derive a CT-style Merkle root from a verified snapshot of the authoritative protocol ledger.",
        "low",
        category="protocol",
        tags=["pcmmad", "ledger", "merkle", "proof", "integrity"],
        side_effect_class="read",
        effect_traits=["reads_state", "verifies_hash_chain", "derives_merkle_root", "non_initializing"],
        input_schema=_schema(["project_id"], context.common_schema),
    )
    def tool_protocol_merkle_root(payload: ToolPayload) -> ToolResult:
        return _run(context, lambda: merkle_root_receipt(_project_id(payload)))

    @context.register_tool(
        "protocol.merkle.inclusion",
        "Return a compact inclusion receipt proving one protocol event hash is in a verified ledger snapshot.",
        "low",
        category="protocol",
        tags=["pcmmad", "ledger", "merkle", "inclusion", "proof"],
        side_effect_class="read",
        effect_traits=["reads_state", "verifies_hash_chain", "derives_merkle_proof", "non_initializing"],
        input_schema=_schema(
            ["project_id", "sequence"],
            {**context.common_schema, "sequence": {"type": "integer", "minimum": 1}},
        ),
    )
    def tool_protocol_merkle_inclusion(payload: ToolPayload) -> ToolResult:
        sequence = payload_optional_int(payload, "sequence")
        if sequence is None or sequence < 1:
            raise context.error_cls("BAD_REQUEST", "sequence must be an integer >= 1", 400)
        return _run(context, lambda: merkle_inclusion_receipt(_project_id(payload), sequence))

    @context.register_tool(
        "protocol.merkle.consistency",
        "Return a compact proof that an earlier protocol Merkle tree is an append-only prefix of a verified ledger snapshot.",
        "low",
        category="protocol",
        tags=["pcmmad", "ledger", "merkle", "consistency", "append-only", "proof"],
        side_effect_class="read",
        effect_traits=["reads_state", "verifies_hash_chain", "derives_merkle_proof", "non_initializing"],
        input_schema=_schema(
            ["project_id", "old_tree_size"],
            {**context.common_schema, "old_tree_size": {"type": "integer", "minimum": 0}},
        ),
    )
    def tool_protocol_merkle_consistency(payload: ToolPayload) -> ToolResult:
        old_size = payload_optional_int(payload, "old_tree_size")
        if old_size is None or old_size < 0:
            raise context.error_cls("BAD_REQUEST", "old_tree_size must be an integer >= 0", 400)
        return _run(context, lambda: merkle_consistency_receipt(_project_id(payload), old_size))


def register_protocol_tools(
    register_tool: ProtocolRegistrar, *, error_cls: type[Exception]
) -> None:
    """Register the complete PCMMAD protocol surface in cohesive groups."""

    context = ProtocolRegistrationContext(
        register_tool=register_tool,
        error_cls=error_cls,
        common_schema={
            "project_id": {"type": "string", "minLength": 1},
            "actor": {"type": "string"},
        },
    )
    _register_observation_tools(context)
    _register_mode_and_objective_tools(context)
    _register_constraint_and_continuity_tools(context)
    _register_claim_and_artifact_tools(context)
    _register_promotion_and_waiver_tools(context)
    _register_integrity_tools(context)
