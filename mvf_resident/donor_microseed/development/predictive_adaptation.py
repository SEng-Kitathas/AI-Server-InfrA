from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import json
from typing import Any, Iterable

from .action_learning import (
    ActionOutcomeExperience,
    ActionOutcomePredictiveCandidate,
    QualifiedActionOutcomePredictiveRelation,
    nominate_action_outcome_candidates,
)


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass(frozen=True)
class PredictiveCurrentnessConfig:
    window_size: int = 8
    min_accuracy: float = 0.75
    consecutive_failure_windows: int = 2

    def __post_init__(self) -> None:
        if self.window_size < 2:
            raise ValueError("PREDICTIVE_CURRENTNESS_WINDOW_TOO_SMALL")
        if not (0.0 <= float(self.min_accuracy) <= 1.0):
            raise ValueError("PREDICTIVE_CURRENTNESS_INVALID_ACCURACY")
        if self.consecutive_failure_windows < 1:
            raise ValueError("PREDICTIVE_CURRENTNESS_INVALID_CONSECUTIVE_FAILURES")


@dataclass(frozen=True)
class ActionOutcomePredictiveCurrentnessWitness:
    witness_id: str
    relation_id: str
    relation_candidate_sha256: str
    status: str
    window_accuracies: tuple[float, ...]
    assessed_evidence_ids: tuple[str, ...]
    drift_evidence_ids: tuple[str, ...]
    drift_window: int | None
    config: PredictiveCurrentnessConfig
    currentness_authority: str = "BOUNDED_EMPIRICAL_CURRENTNESS_WITNESS_ONLY"
    truth_authority: str = "NONE"
    drift_cause_authority: str = "NONE"
    semantic_regime_authority: str = "NONE"
    model_switch_authority: str = "NONE"

    def serializable(self) -> dict[str, Any]:
        d = asdict(self)
        d["window_accuracies"] = list(self.window_accuracies)
        d["assessed_evidence_ids"] = list(self.assessed_evidence_ids)
        d["drift_evidence_ids"] = list(self.drift_evidence_ids)
        return d

    @classmethod
    def from_serializable(cls, d: dict[str, Any]) -> "ActionOutcomePredictiveCurrentnessWitness":
        x = dict(d)
        x["window_accuracies"] = tuple(float(v) for v in x.get("window_accuracies", ()))
        x["assessed_evidence_ids"] = tuple(str(v) for v in x.get("assessed_evidence_ids", ()))
        x["drift_evidence_ids"] = tuple(str(v) for v in x.get("drift_evidence_ids", ()))
        x["config"] = PredictiveCurrentnessConfig(**x["config"])
        return cls(**x)


@dataclass(frozen=True)
class ActionOutcomeReplacementLink:
    candidate_id: str
    replacement_of_relation_id: str
    drift_witness_id: str
    drift_evidence_ids: tuple[str, ...]
    authority: str = "MODEL_OUTPUT_ONLY"
    qualification_authority: str = "NONE"
    model_switch_authority: str = "NONE"
    semantic_regime_authority: str = "NONE"

    def serializable(self) -> dict[str, Any]:
        d = asdict(self)
        d["drift_evidence_ids"] = list(self.drift_evidence_ids)
        return d

    @classmethod
    def from_serializable(cls, d: dict[str, Any]) -> "ActionOutcomeReplacementLink":
        x = dict(d)
        x["drift_evidence_ids"] = tuple(str(v) for v in x.get("drift_evidence_ids", ()))
        return cls(**x)


def _same_relation_ancestry(row: ActionOutcomeExperience, relation: QualifiedActionOutcomePredictiveRelation) -> bool:
    return bool(
        row.start_state_id == relation.start_state_id
        and row.capability_id == relation.capability_id
        and row.capability_epoch == relation.capability_epoch
        and row.frame_epochs == relation.frame_epochs
        and row.episode_schema_epochs == relation.episode_schema_epochs
        and row.value_epoch == relation.value_epoch
        and row.topology_epochs == relation.topology_epochs
        and row.coordination_epochs == relation.coordination_epochs
    )


def assess_action_outcome_predictive_currentness(
    relation: QualifiedActionOutcomePredictiveRelation,
    experiences: Iterable[ActionOutcomeExperience],
    config: PredictiveCurrentnessConfig = PredictiveCurrentnessConfig(),
) -> ActionOutcomePredictiveCurrentnessWitness:
    rows = tuple(r for r in experiences if _same_relation_ancestry(r, relation))
    full = (len(rows) // config.window_size) * config.window_size
    rows = rows[:full]
    accuracies: list[float] = []
    bad = 0
    drift_window: int | None = None
    drift_rows: tuple[ActionOutcomeExperience, ...] = ()
    for i in range(0, len(rows), config.window_size):
        chunk = rows[i : i + config.window_size]
        matches = sum(
            r.actual_next_state_id == relation.next_state_id
            and round(float(r.actual_value_effect), 3) == round(float(relation.value_effect), 3)
            for r in chunk
        )
        accuracy = matches / len(chunk)
        accuracies.append(accuracy)
        if accuracy < config.min_accuracy:
            bad += 1
            if bad >= config.consecutive_failure_windows and drift_window is None:
                drift_window = len(accuracies) - 1
                start = (drift_window - config.consecutive_failure_windows + 1) * config.window_size
                stop = (drift_window + 1) * config.window_size
                drift_rows = rows[start:stop]
        else:
            bad = 0
    if drift_window is not None:
        status = "DRIFT_WITNESS"
    elif accuracies:
        status = "CURRENT_WITHIN_BOUNDS"
    else:
        status = "INSUFFICIENT_POST_ADMISSION_EVIDENCE"
    payload = {
        "relation_id": relation.relation_id,
        "candidate_sha256": relation.candidate_sha256,
        "status": status,
        "window_accuracies": accuracies,
        "assessed_evidence_ids": [r.evidence_id for r in rows],
        "drift_evidence_ids": [r.evidence_id for r in drift_rows],
        "drift_window": drift_window,
        "config": asdict(config),
    }
    return ActionOutcomePredictiveCurrentnessWitness(
        witness_id="ACTION-LAW-CURRENTNESS-" + _digest(payload)[:20],
        relation_id=relation.relation_id,
        relation_candidate_sha256=relation.candidate_sha256,
        status=status,
        window_accuracies=tuple(accuracies),
        assessed_evidence_ids=tuple(r.evidence_id for r in rows),
        drift_evidence_ids=tuple(r.evidence_id for r in drift_rows),
        drift_window=drift_window,
        config=config,
    )


def nominate_drift_replacement_candidates(
    relation: QualifiedActionOutcomePredictiveRelation,
    witness: ActionOutcomePredictiveCurrentnessWitness,
    experiences: Iterable[ActionOutcomeExperience],
    *,
    min_support: int = 8,
    min_consistency: float = 0.78,
) -> tuple[tuple[ActionOutcomePredictiveCandidate, ActionOutcomeReplacementLink], ...]:
    if witness.relation_id != relation.relation_id or witness.relation_candidate_sha256 != relation.candidate_sha256:
        raise ValueError("DRIFT_WITNESS_RELATION_BINDING_MISMATCH")
    if witness.status != "DRIFT_WITNESS":
        return ()
    allowed = set(witness.drift_evidence_ids)
    rows = tuple(r for r in experiences if r.evidence_id in allowed and _same_relation_ancestry(r, relation))
    base = nominate_action_outcome_candidates(rows, min_support=min_support, min_consistency=min_consistency)
    out = []
    for candidate in base:
        payload = {
            "replacement_of_relation_id": relation.relation_id,
            "drift_witness_id": witness.witness_id,
            "candidate_sha256": candidate.digest(),
        }
        replacement_id = "ACTION-REPL-CAND-" + _digest(payload)[:20]
        replacement = replace(candidate, candidate_id=replacement_id)
        link = ActionOutcomeReplacementLink(
            candidate_id=replacement_id,
            replacement_of_relation_id=relation.relation_id,
            drift_witness_id=witness.witness_id,
            drift_evidence_ids=witness.drift_evidence_ids,
        )
        out.append((replacement, link))
    return tuple(out)
