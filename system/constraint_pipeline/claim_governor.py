"""Claim permission derivation from normalized gate results."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from constraint_model import ClaimPermission, GateResult

CLAIM_REQUIREMENTS = MappingProxyType(
    {
        "reply_claim_clean": (
            "loc_code_shape",
            "guide_quality_style",
            "semantic_footgun_dataflow",
            "receiver_full_route_trace",
            "receiver_resilience_suite",
        ),
        "runtime_working": (
            "receiver_selftest",
            "schema_authority",
            "semantic_footgun_dataflow",
            "receiver_full_route_trace",
            "receiver_resilience_suite",
        ),
        "promotion_clean": (
            "loc_code_shape",
            "guide_quality_style",
            "semantic_footgun_dataflow",
            "receiver_full_route_trace",
            "receiver_resilience_suite",
            "receiver_selftest",
            "schema_authority",
            "task_finalizer",
        ),
        "package_clean": (
            "loc_code_shape",
            "guide_quality_style",
            "semantic_footgun_dataflow",
            "receiver_full_route_trace",
            "receiver_resilience_suite",
            "receiver_selftest",
            "schema_authority",
            "task_finalizer",
        ),
    }
)


def _gate_map(gates: tuple[GateResult, ...]) -> Mapping[str, GateResult]:
    return {gate.gate_id: gate for gate in gates}


def _blocking_gates(required: tuple[str, ...], by_id: Mapping[str, GateResult]) -> tuple[str, ...]:
    missing = tuple(gate_id for gate_id in required if gate_id not in by_id)
    failing = tuple(
        gate_id
        for gate_id in required
        if gate_id in by_id and by_id[gate_id].status not in {"pass", "not_applicable"}
    )
    return missing + failing


def _advisory_gates(required: tuple[str, ...], by_id: Mapping[str, GateResult]) -> tuple[str, ...]:
    return tuple(
        gate.gate_id
        for gate in (by_id[gate_id] for gate_id in required)
        if gate.advisory_count and "advisory_with_waiver" in gate.claim_effects
    )


def _permission_for_claim(
    claim: str, required: tuple[str, ...], by_id: Mapping[str, GateResult]
) -> ClaimPermission:
    blocking = _blocking_gates(required, by_id)
    if blocking:
        return ClaimPermission(
            claim=claim,
            status="blocked",
            required_gates=required,
            blocking_gates=blocking,
            downgrade_reason="required gate missing or not passing",
        )
    _advisory_gates(required, by_id)
    return ClaimPermission(claim=claim, status="allowed", required_gates=required)


def claim_permissions(gates: tuple[GateResult, ...]) -> tuple[ClaimPermission, ...]:
    by_id = _gate_map(gates)
    return tuple(
        _permission_for_claim(claim, required, by_id)
        for claim, required in CLAIM_REQUIREMENTS.items()
    )


def final_clean_from_claims(claims: tuple[ClaimPermission, ...]) -> bool:
    promotion_claims = {"promotion_clean", "runtime_working"}
    return all(claim.status == "allowed" for claim in claims if claim.claim in promotion_claims)


def required_action(gates: tuple[GateResult, ...]) -> str:
    priority = ["full_refactor", "bounded_patch", "rerun_with_fresh_evidence", "profile_waiver"]
    actions = {gate.recommended_action for gate in gates if gate.recommended_action != "none"}
    for action in priority:
        if action in actions:
            return action
    return "none"
