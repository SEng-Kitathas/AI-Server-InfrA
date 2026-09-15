from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from ..evidence.authority import FixedQualifier
from ..evidence.ledger import EvidenceLedger, canonical_json, sha256_bytes
from ..runtime.types import Authority, EvidenceRef, QualificationState
from .constructor_growth import ConstructorProjectionSample
from .robust_constructor_growth import RobustProjectionConstructorCandidate, candidate_accuracy


def _mode(counter: Counter[str]) -> str | None:
    if not counter:
        return None
    return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def _action_baseline(rows: tuple[ConstructorProjectionSample, ...]) -> float:
    tab: dict[str, Counter[str]] = defaultdict(Counter)
    for r in rows:
        tab[r.action_token][r.effect_token] += 1
    if not rows:
        return 0.0
    return sum(_mode(tab[r.action_token]) == r.effect_token for r in rows) / len(rows)


def _sample_digest(rows: tuple[ConstructorProjectionSample, ...]) -> str:
    return sha256_bytes(canonical_json([
        {
            "sample_id": r.sample_id,
            "action_token": r.action_token,
            "effect_token": r.effect_token,
            "frame_id": r.frame_id,
            "frame_epoch": r.frame_epoch,
            "episode_schema_id": r.episode_schema_id,
            "episode_schema_epoch": r.episode_schema_epoch,
        }
        for r in rows
    ]))


@dataclass(frozen=True)
class ProjectionDriftStructureConfig:
    """Supplied bounds for comparing a stale law with one qualified alternative.

    This can establish that a different opaque predictive structure is supported.
    It cannot identify a semantic drift cause, nuisance process, or regime identity.
    """

    min_alternative_accuracy: float = 0.90
    min_predictive_advantage: float = 0.20

    def __post_init__(self) -> None:
        if not 0.0 <= float(self.min_alternative_accuracy) <= 1.0:
            raise ValueError("INVALID_ALTERNATIVE_STRUCTURE_ACCURACY_BOUND")
        if not 0.0 <= float(self.min_predictive_advantage) <= 1.0:
            raise ValueError("INVALID_ALTERNATIVE_STRUCTURE_ADVANTAGE_BOUND")

    def assistance_ancestry(self) -> tuple[str, ...]:
        return (
            f"SUPPLIED_MIN_ALTERNATIVE_ACCURACY_{float(self.min_alternative_accuracy):.6f}",
            f"SUPPLIED_MIN_PREDICTIVE_ADVANTAGE_{float(self.min_predictive_advantage):.6f}",
            "QUALIFIED_ALTERNATIVE_STRUCTURE_COMPARISON_ONLY",
            "NO_NOISE_CAUSE_SEMANTICS",
            "NO_REGIME_IDENTITY_AUTHORITY",
        )


@dataclass(frozen=True)
class ProjectionDriftStructureWitness:
    projection_id: str
    stale_projection_epoch: int
    historical_candidate_sha256: str
    alternative_candidate_id: str
    alternative_candidate_sha256: str
    status: str
    historical_accuracy: float
    alternative_accuracy: float
    predictive_advantage: float
    structurally_distinct: bool
    sample_digest_sha256: str
    assistance_ancestry: tuple[str, ...]
    truth_authority: str = "NONE"
    drift_cause_authority: str = "NONE"
    noise_semantics_authority: str = "NONE"
    regime_identity_authority: str = "NONE"
    admission_authority: str = "NONE"

    def __post_init__(self) -> None:
        if self.status not in {"ALTERNATIVE_STRUCTURE_SUPPORTED", "NO_ALTERNATIVE_STRUCTURE_WITHIN_BOUNDS"}:
            raise ValueError("INVALID_DRIFT_STRUCTURE_WITNESS_STATUS")
        if any(getattr(self, k) != "NONE" for k in (
            "truth_authority", "drift_cause_authority", "noise_semantics_authority",
            "regime_identity_authority", "admission_authority",
        )):
            raise ValueError("DRIFT_STRUCTURE_WITNESS_CANNOT_CARRY_AUTHORITY")

    def serializable(self) -> dict[str, Any]:
        return asdict(self)


def assess_projection_drift_structure(
    projection_id: str,
    stale_projection_epoch: int,
    historical_candidate: RobustProjectionConstructorCandidate,
    alternative_candidate: RobustProjectionConstructorCandidate,
    samples: Iterable[ConstructorProjectionSample],
    cfg: ProjectionDriftStructureConfig | None = None,
) -> ProjectionDriftStructureWitness:
    cfg = cfg or ProjectionDriftStructureConfig()
    rows = tuple(samples)
    old_acc = candidate_accuracy(historical_candidate, rows)
    alt_acc = candidate_accuracy(alternative_candidate, rows)
    distinct = (
        historical_candidate.atoms != alternative_candidate.atoms
        or historical_candidate.bucket_action_prediction != alternative_candidate.bucket_action_prediction
        or historical_candidate.key_to_bucket != alternative_candidate.key_to_bucket
    )
    advantage = alt_acc - old_acc
    status = (
        "ALTERNATIVE_STRUCTURE_SUPPORTED"
        if distinct and alt_acc >= cfg.min_alternative_accuracy and advantage >= cfg.min_predictive_advantage
        else "NO_ALTERNATIVE_STRUCTURE_WITHIN_BOUNDS"
    )
    return ProjectionDriftStructureWitness(
        projection_id=str(projection_id),
        stale_projection_epoch=int(stale_projection_epoch),
        historical_candidate_sha256=historical_candidate.digest(),
        alternative_candidate_id=alternative_candidate.candidate_id,
        alternative_candidate_sha256=alternative_candidate.digest(),
        status=status,
        historical_accuracy=old_acc,
        alternative_accuracy=alt_acc,
        predictive_advantage=advantage,
        structurally_distinct=distinct,
        sample_digest_sha256=_sample_digest(rows),
        assistance_ancestry=cfg.assistance_ancestry(),
    )


@dataclass(frozen=True)
class ProjectionRecurrenceConfig:
    window_size: int = 256
    min_window_accuracy: float = 0.90
    min_lift_over_action_baseline: float = 0.25
    consecutive_success_windows: int = 2

    def __post_init__(self) -> None:
        if int(self.window_size) < 8:
            raise ValueError("INVALID_RECURRENCE_WINDOW")
        if not 0.0 <= float(self.min_window_accuracy) <= 1.0:
            raise ValueError("INVALID_RECURRENCE_ACCURACY_BOUND")
        if not 0.0 <= float(self.min_lift_over_action_baseline) <= 1.0:
            raise ValueError("INVALID_RECURRENCE_LIFT_BOUND")
        if int(self.consecutive_success_windows) < 1:
            raise ValueError("INVALID_RECURRENCE_SUCCESS_RUN")

    def assistance_ancestry(self) -> tuple[str, ...]:
        return (
            f"SUPPLIED_RECURRENCE_WINDOW_SIZE_{int(self.window_size)}",
            f"SUPPLIED_RECURRENCE_MIN_ACCURACY_{float(self.min_window_accuracy):.6f}",
            f"SUPPLIED_RECURRENCE_MIN_ACTION_BASELINE_LIFT_{float(self.min_lift_over_action_baseline):.6f}",
            f"SUPPLIED_RECURRENCE_CONSECUTIVE_WINDOWS_{int(self.consecutive_success_windows)}",
            "SUPPLIED_OPERATIONAL_SAMPLE_ORDER",
            "RECURRENT_PREDICTIVE_LAW_NOT_REGIME_IDENTITY",
            "RECURRENCE_EVIDENCE_REQUIRES_EXTERNAL_REQUALIFICATION",
        )


@dataclass(frozen=True)
class ProjectionRecurrenceWitness:
    projection_id: str
    stale_projection_epoch: int
    candidate_sha256: str
    status: str
    window_accuracies: tuple[float, ...]
    action_baseline_accuracy: float
    recurrence_window: int | None
    sample_digest_sha256: str
    assistance_ancestry: tuple[str, ...]
    truth_authority: str = "NONE"
    regime_identity_authority: str = "NONE"
    reactivation_authority: str = "NONE"
    scheduling_authority: str = "NONE"

    def __post_init__(self) -> None:
        if self.status not in {"RECURRENCE_EVIDENCE", "NO_RECURRENCE_WITHIN_BOUNDS"}:
            raise ValueError("INVALID_PROJECTION_RECURRENCE_STATUS")
        if any(getattr(self, k) != "NONE" for k in (
            "truth_authority", "regime_identity_authority", "reactivation_authority", "scheduling_authority"
        )):
            raise ValueError("PROJECTION_RECURRENCE_WITNESS_CANNOT_CARRY_AUTHORITY")
        object.__setattr__(self, "window_accuracies", tuple(float(x) for x in self.window_accuracies))
        object.__setattr__(self, "assistance_ancestry", tuple(str(x) for x in self.assistance_ancestry))

    def signature_payload(self) -> dict[str, Any]:
        return asdict(self)

    def digest(self) -> str:
        return sha256_bytes(canonical_json(self.signature_payload()))

    def serializable(self) -> dict[str, Any]:
        d = self.signature_payload()
        d["witness_sha256"] = self.digest()
        return d

    @classmethod
    def from_serializable(cls, d: dict[str, Any]) -> "ProjectionRecurrenceWitness":
        x = dict(d)
        x.pop("witness_sha256", None)
        x["window_accuracies"] = tuple(x.get("window_accuracies", ()))
        x["assistance_ancestry"] = tuple(x.get("assistance_ancestry", ()))
        return cls(**x)


def assess_projection_recurrence(
    projection_id: str,
    stale_projection_epoch: int,
    candidate: RobustProjectionConstructorCandidate,
    samples: Iterable[ConstructorProjectionSample],
    cfg: ProjectionRecurrenceConfig | None = None,
) -> ProjectionRecurrenceWitness:
    cfg = cfg or ProjectionRecurrenceConfig()
    rows = tuple(samples)
    baseline = _action_baseline(rows)
    accs: list[float] = []
    run = 0
    recurrence_window = None
    for wi, start in enumerate(range(0, len(rows), int(cfg.window_size))):
        block = rows[start:start + int(cfg.window_size)]
        if len(block) < int(cfg.window_size):
            break
        acc = candidate_accuracy(candidate, block)
        accs.append(acc)
        if acc >= cfg.min_window_accuracy and acc - baseline >= cfg.min_lift_over_action_baseline:
            run += 1
            if run >= int(cfg.consecutive_success_windows) and recurrence_window is None:
                recurrence_window = wi
        else:
            run = 0
    return ProjectionRecurrenceWitness(
        projection_id=str(projection_id),
        stale_projection_epoch=int(stale_projection_epoch),
        candidate_sha256=candidate.digest(),
        status="RECURRENCE_EVIDENCE" if recurrence_window is not None else "NO_RECURRENCE_WITHIN_BOUNDS",
        window_accuracies=tuple(accs),
        action_baseline_accuracy=baseline,
        recurrence_window=recurrence_window,
        sample_digest_sha256=_sample_digest(rows),
        assistance_ancestry=cfg.assistance_ancestry(),
    )


@dataclass(frozen=True)
class ProjectionRecurrenceQualificationTicket:
    projection_id: str
    stale_projection_epoch: int
    candidate_sha256: str
    recurrence_witness_sha256: str
    state: QualificationState
    qualifier_id: str
    reason: str
    qualification_evidence: tuple[EvidenceRef, ...]


class ExternalProjectionRecurrenceQualifier:
    """External requalification boundary for operational projection recurrence."""

    def __init__(self, ledger: EvidenceLedger, *, qualifier_id: str = "HSP-EXTERNAL-PROJECTION-RECURRENCE-QUALIFIER"):
        if not qualifier_id or qualifier_id.upper().startswith("MICROSEED"):
            raise ValueError("qualifier_id must identify an external qualification boundary")
        self.ledger = ledger
        self.qualifier_id = qualifier_id

    def qualify(
        self,
        witness: ProjectionRecurrenceWitness,
        *,
        qualification_evidence: Iterable[EvidenceRef],
    ) -> ProjectionRecurrenceQualificationTicket:
        refs = tuple(qualification_evidence)
        decision = FixedQualifier(self.ledger).decide(refs, Authority.REFERENCE_ONLY)
        return ProjectionRecurrenceQualificationTicket(
            projection_id=witness.projection_id,
            stale_projection_epoch=witness.stale_projection_epoch,
            candidate_sha256=witness.candidate_sha256,
            recurrence_witness_sha256=witness.digest(),
            state=decision.state,
            qualifier_id=self.qualifier_id,
            reason=decision.reason,
            qualification_evidence=refs,
        )


def validate_external_projection_recurrence_ticket(
    witness: ProjectionRecurrenceWitness,
    ticket: ProjectionRecurrenceQualificationTicket,
    ledger: EvidenceLedger,
) -> tuple[bool, str]:
    if witness.status != "RECURRENCE_EVIDENCE":
        return False, "RECURRENCE_NOT_ESTABLISHED"
    if not ticket.qualifier_id or ticket.qualifier_id.upper().startswith("MICROSEED"):
        return False, "QUALIFIER_NOT_EXTERNAL"
    if ticket.projection_id != witness.projection_id:
        return False, "PROJECTION_ID_MISMATCH"
    if int(ticket.stale_projection_epoch) != int(witness.stale_projection_epoch):
        return False, "PROJECTION_EPOCH_MISMATCH"
    if ticket.candidate_sha256 != witness.candidate_sha256:
        return False, "RECURRENCE_CANDIDATE_MISMATCH"
    if ticket.recurrence_witness_sha256 != witness.digest():
        return False, "RECURRENCE_WITNESS_DIGEST_MISMATCH"
    if not ticket.qualification_evidence:
        return False, "NO_REQUALIFICATION_EVIDENCE"
    decision = FixedQualifier(ledger).decide(ticket.qualification_evidence, Authority.REFERENCE_ONLY)
    if ticket.state != decision.state or ticket.reason != decision.reason:
        return False, "REQUALIFICATION_DECISION_MISMATCH"
    if ticket.state not in {QualificationState.SHADOW_QUALIFIED, QualificationState.QUALIFIED}:
        return False, f"NOT_ADMISSIBLE:{ticket.state.value}"
    return True, "VALID_EXTERNAL_PROJECTION_RECURRENCE_REQUALIFICATION"
