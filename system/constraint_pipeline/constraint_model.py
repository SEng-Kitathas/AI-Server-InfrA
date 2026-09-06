"""Normalized gate and claim models for project constraint finalization."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Mapping
from typing import Literal, TypeAlias

JsonValue: TypeAlias = (
    str | int | float | bool | None | list["JsonValue"] | Mapping[str, "JsonValue"]
)
GateStatus: TypeAlias = Literal["pass", "fail", "skip", "stale", "not_applicable"]
ClaimEffect: TypeAlias = Literal[
    "blocks_reply_claim",
    "blocks_promotion",
    "blocks_package",
    "requires_local_patch",
    "advisory_with_waiver",
    "not_applicable",
]
RecommendedAction: TypeAlias = Literal[
    "none",
    "bounded_patch",
    "profile_waiver",
    "full_refactor",
    "rerun_with_fresh_evidence",
]
ClaimStatus: TypeAlias = Literal["allowed", "blocked", "downgraded", "unknown"]


@dataclass(frozen=True)
class GateFinding:
    rule: str
    severity: str
    message: str
    file: str | None = None
    line: int | None = None
    claim_effects: tuple[ClaimEffect, ...] = ()
    recommended_action: RecommendedAction = "bounded_patch"

    def to_dict(self) -> Mapping[str, JsonValue]:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "message": self.message,
            "file": self.file,
            "line": self.line,
            "claim_effects": list(self.claim_effects),
            "recommended_action": self.recommended_action,
        }


@dataclass(frozen=True)
class GateResult:
    gate_id: str
    gate_family: str
    status: GateStatus
    profile: str
    claim_effects: tuple[ClaimEffect, ...] = ()
    recommended_action: RecommendedAction = "none"
    finding_count: int = 0
    strict_failure_count: int = 0
    advisory_count: int = 0
    evidence_path: str | None = None
    surface_scope: tuple[str, ...] = ()
    skip_reason: str | None = None
    freshness: str = "fresh"
    findings: tuple[GateFinding, ...] = ()
    notes: tuple[str, ...] = ()

    def to_dict(self) -> Mapping[str, JsonValue]:
        return {
            "gate_id": self.gate_id,
            "gate_family": self.gate_family,
            "status": self.status,
            "profile": self.profile,
            "claim_effects": list(self.claim_effects),
            "recommended_action": self.recommended_action,
            "finding_count": self.finding_count,
            "strict_failure_count": self.strict_failure_count,
            "advisory_count": self.advisory_count,
            "evidence_path": self.evidence_path,
            "surface_scope": list(self.surface_scope),
            "skip_reason": self.skip_reason,
            "freshness": self.freshness,
            "findings": [finding.to_dict() for finding in self.findings],
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class ClaimPermission:
    claim: str
    status: ClaimStatus
    required_gates: tuple[str, ...]
    blocking_gates: tuple[str, ...] = ()
    downgrade_reason: str | None = None

    def to_dict(self) -> Mapping[str, JsonValue]:
        return {
            "claim": self.claim,
            "status": self.status,
            "required_gates": list(self.required_gates),
            "blocking_gates": list(self.blocking_gates),
            "downgrade_reason": self.downgrade_reason,
        }


@dataclass(frozen=True)
class ConstraintFinalizerReport:
    project_id: str
    profile: str
    created_at_utc: str
    gates: tuple[GateResult, ...]
    claims: tuple[ClaimPermission, ...]
    final_clean: bool
    required_action: RecommendedAction
    summary: Mapping[str, JsonValue] = field(default_factory=dict)

    def to_dict(self) -> Mapping[str, JsonValue]:
        return {
            "project_id": self.project_id,
            "profile": self.profile,
            "created_at_utc": self.created_at_utc,
            "gates": [gate.to_dict() for gate in self.gates],
            "claims": [claim.to_dict() for claim in self.claims],
            "final_clean": self.final_clean,
            "required_action": self.required_action,
            "summary": self.summary,
        }
