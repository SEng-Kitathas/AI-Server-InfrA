"""Typed PCMMAD runtime-protocol records and canonical state classifications.

This module owns the vocabulary of the PCMMAD methodology.  Persistence and
transport code may serialize these records, but SHALL NOT redefine their
semantics locally.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class ProtocolValidationError(ValueError):
    """A protocol record would violate a load-bearing runtime invariant."""


class RuntimeMode(StrEnum):
    DISCUSSION = "DISCUSSION"
    AUDIT = "AUDIT"
    BUILD_PLAN = "BUILD_PLAN"
    BUILD_COMMIT = "BUILD_COMMIT"
    RECOVERY = "RECOVERY"
    CHECKPOINT = "CHECKPOINT"
    MERGE = "MERGE"
    PROMOTION = "PROMOTION"


class RigorLevel(StrEnum):
    """Proportionate evidence pressure for the current project protocol."""

    STANDARD = "STANDARD"
    ELEVATED = "ELEVATED"
    CRITICAL = "CRITICAL"

    @property
    def minimum_ratification_evidence(self) -> int:
        return {
            RigorLevel.STANDARD: 1,
            RigorLevel.ELEVATED: 2,
            RigorLevel.CRITICAL: 3,
        }[self]

    @property
    def minimum_verified_evidence(self) -> int:
        return {
            RigorLevel.STANDARD: 0,
            RigorLevel.ELEVATED: 1,
            RigorLevel.CRITICAL: 2,
        }[self]


class EvidenceStatus(StrEnum):
    ASSERTED = "ASSERTED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


class MutationDomain(StrEnum):
    READ = "READ"
    GOVERNANCE = "GOVERNANCE"
    SPECIMEN = "SPECIMEN"
    PROMOTION = "PROMOTION"


class ClaimKind(StrEnum):
    KNOWN = "KNOWN"
    ASSUMPTION = "ASSUMPTION"
    HYPOTHESIS = "HYPOTHESIS"
    UNKNOWN = "UNKNOWN"
    TEST = "TEST"


class AdjudicationDecision(StrEnum):
    RATIFIED = "RATIFIED"
    PROVISIONAL = "PROVISIONAL"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"
    DEMOTED = "DEMOTED"
    SUPERSEDED = "SUPERSEDED"


class ConstraintStrength(StrEnum):
    REQUIRED = "REQUIRED"
    PREFERRED = "PREFERRED"
    ADVISORY = "ADVISORY"


class ContinuityKind(StrEnum):
    LIVE_SHADOW = "LIVE_SHADOW"
    DESIGN_THREAD_STREAM = "DESIGN_THREAD_STREAM"
    REVISIT_LEDGER = "REVISIT_LEDGER"
    DOCTRINE_SNAPSHOT = "DOCTRINE_SNAPSHOT"
    TRACE_MATRIX = "TRACE_MATRIX"
    MEMORY_RECORD = "MEMORY_RECORD"
    MAINTENANCE = "MAINTENANCE"


class WaiverStatus(StrEnum):
    ACTIVE = "ACTIVE"
    WITHDRAWN = "WITHDRAWN"
    SUPERSEDED = "SUPERSEDED"


class ProtocolEventKind(StrEnum):
    GENESIS = "GENESIS"
    MODE_TRANSITION = "MODE_TRANSITION"
    OBJECTIVE_SET = "OBJECTIVE_SET"
    CONSTRAINT_RECORDED = "CONSTRAINT_RECORDED"
    CONTINUITY_RECORDED = "CONTINUITY_RECORDED"
    CLAIM_RECORDED = "CLAIM_RECORDED"
    ARTIFACT_REGISTERED = "ARTIFACT_REGISTERED"
    PROMOTION_RECORDED = "PROMOTION_RECORDED"
    WAIVER_RECORDED = "WAIVER_RECORDED"


@dataclass(frozen=True)
class EvidenceRef:
    kind: str
    ref: str
    sha256: str | None = None
    verifier_id: str | None = None
    observed_at: str | None = None
    expires_at: str | None = None
    status: EvidenceStatus = EvidenceStatus.ASSERTED

    @staticmethod
    def _timestamp(value: object, field_name: str) -> str | None:
        if value is None or str(value).strip() == "":
            return None
        text = str(value).strip()
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ProtocolValidationError(f"evidence {field_name} must be ISO-8601") from exc
        if parsed.tzinfo is None:
            raise ProtocolValidationError(f"evidence {field_name} must include a timezone")
        return parsed.astimezone(timezone.utc).isoformat()

    @classmethod
    def from_dict(cls, raw: object) -> "EvidenceRef":
        if not isinstance(raw, dict):
            raise ProtocolValidationError("evidence entries must be objects")
        kind = str(raw.get("kind", "")).strip()
        ref = str(raw.get("ref", "")).strip()
        digest = raw.get("sha256")
        if not kind or not ref:
            raise ProtocolValidationError("evidence kind and ref are required")
        if digest is not None:
            digest = str(digest).strip().lower()
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                raise ProtocolValidationError("evidence sha256 must be a 64-character hex digest")
        verifier_id = str(raw.get("verifier_id", "")).strip() or None
        try:
            status = EvidenceStatus(str(raw.get("status", "ASSERTED")).strip().upper())
        except ValueError as exc:
            allowed = ", ".join(item.value for item in EvidenceStatus)
            raise ProtocolValidationError(f"evidence status must be one of: {allowed}") from exc
        observed_at = cls._timestamp(raw.get("observed_at"), "observed_at")
        expires_at = cls._timestamp(raw.get("expires_at"), "expires_at")
        if observed_at and expires_at:
            observed = datetime.fromisoformat(observed_at)
            expiry = datetime.fromisoformat(expires_at)
            if expiry <= observed:
                raise ProtocolValidationError("evidence expires_at must be after observed_at")
        return cls(
            kind=kind,
            ref=ref,
            sha256=digest,
            verifier_id=verifier_id,
            observed_at=observed_at,
            expires_at=expires_at,
            status=status,
        )

    @property
    def identity(self) -> tuple[str, str, str | None]:
        return (self.kind, self.ref, self.sha256)

    def is_expired(self, *, now: datetime | None = None) -> bool:
        if not self.expires_at:
            return False
        current = now or datetime.now(timezone.utc)
        return datetime.fromisoformat(self.expires_at) <= current

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass(frozen=True)
class ProtocolEvent:
    sequence: int
    event_id: str
    event_kind: ProtocolEventKind
    project_id: str
    recorded_at: str
    actor: str
    payload: dict[str, Any]
    previous_hash: str | None
    event_hash: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["event_kind"] = self.event_kind.value
        return data


@dataclass
class ProtocolSnapshot:
    project_id: str
    rigor_level: RigorLevel = RigorLevel.STANDARD
    current_mode: RuntimeMode = RuntimeMode.DISCUSSION
    objective: dict[str, Any] | None = None
    constraints: dict[str, dict[str, Any]] = field(default_factory=dict)
    continuity: list[dict[str, Any]] = field(default_factory=list)
    claims: dict[str, dict[str, Any]] = field(default_factory=dict)
    artifacts: dict[str, dict[str, Any]] = field(default_factory=dict)
    promotions: dict[str, dict[str, Any]] = field(default_factory=dict)
    waivers: dict[str, dict[str, Any]] = field(default_factory=dict)
    event_count: int = 0
    head_hash: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "rigor_level": self.rigor_level.value,
            "minimum_ratification_evidence": self.rigor_level.minimum_ratification_evidence,
            "minimum_verified_evidence": self.rigor_level.minimum_verified_evidence,
            "current_mode": self.current_mode.value,
            "objective": self.objective,
            "constraints": self.constraints,
            "continuity": self.continuity,
            "claims": self.claims,
            "artifacts": self.artifacts,
            "promotions": self.promotions,
            "waivers": self.waivers,
            "event_count": self.event_count,
            "head_hash": self.head_hash,
            "updated_at": self.updated_at,
        }
