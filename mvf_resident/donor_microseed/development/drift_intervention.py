from __future__ import annotations

import hashlib
import math
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from ..evidence.ledger import canonical_json, sha256_bytes
from .robust_constructor_growth import RobustProjectionConstructorCandidate


def _sha(value: str, *, error: str) -> str:
    v = str(value).lower()
    if len(v) != 64 or any(c not in "0123456789abcdef" for c in v):
        raise ValueError(error)
    return v


def _predict(candidate: RobustProjectionConstructorCandidate, raw_history: tuple[tuple[str, ...], ...], action_token: str) -> str | None:
    bucket = candidate.project(raw_history)
    if bucket is None:
        return None
    return {(b, a): e for b, a, e in candidate.bucket_action_prediction}.get((bucket, str(action_token)))


def _entropy(values: tuple[str, ...]) -> float:
    if not values:
        return 0.0
    counts = Counter(values)
    n = len(values)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


@dataclass(frozen=True)
class DriftInterventionConfig:
    """Supplied finite bounds for one-step drift discrimination.

    Repeated exact outcomes make the witness less brittle than a single trial,
    but the repetition count and decision gates are assistance ancestry. This is
    not a learned noise model, Bayesian cause classifier, or general planner.
    """

    repeats: int = 31
    min_agreement: float = 0.65
    min_margin: float = 0.20
    max_probe_pool: int = 256

    def __post_init__(self) -> None:
        if not 3 <= int(self.repeats) <= 255:
            raise ValueError("BOUNDED_REPEATED_INTERVENTION_COUNT_REQUIRED")
        if not 0.5 <= float(self.min_agreement) <= 1.0:
            raise ValueError("INVALID_INTERVENTION_AGREEMENT_BOUND")
        if not 0.0 <= float(self.min_margin) <= 1.0:
            raise ValueError("INVALID_INTERVENTION_MARGIN_BOUND")
        if not 1 <= int(self.max_probe_pool) <= 4096:
            raise ValueError("BOUNDED_INTERVENTION_POOL_REQUIRED")

    def assistance_ancestry(self) -> tuple[str, ...]:
        return (
            f"SUPPLIED_INTERVENTION_REPEATS_{int(self.repeats)}",
            f"SUPPLIED_MIN_PREDICTION_AGREEMENT_{float(self.min_agreement):.6f}",
            f"SUPPLIED_MIN_PREDICTION_MARGIN_{float(self.min_margin):.6f}",
            f"SUPPLIED_MAX_PROBE_POOL_{int(self.max_probe_pool)}",
            "SUPPLIED_OPAQUE_INTERVENTION_TEMPLATES",
            "EXACT_OPAQUE_OUTCOME_AGREEMENT_ONLY",
            "NO_LEARNED_NOISE_RATE_MODEL",
            "NO_SEMANTIC_DRIFT_CAUSE_ONTOLOGY",
            "NO_GENERAL_MULTI_STEP_ACTIVE_LEARNING",
        )


@dataclass(frozen=True)
class DriftInterventionProbe:
    probe_id: str
    capability_id: str
    capability_epoch: int
    raw_history: tuple[tuple[str, ...], ...]
    action_token: str
    frame_id: str
    frame_epoch: int
    episode_schema_id: str | None = None
    episode_schema_epoch: int | None = None
    current_access: bool = True
    assistance_ancestry: tuple[str, ...] = ()
    semantic_intervention_authority: str = "NONE"

    def __post_init__(self) -> None:
        if not self.probe_id or not self.capability_id or not self.frame_id or not self.action_token:
            raise ValueError("INCOMPLETE_DRIFT_INTERVENTION_PROBE")
        if int(self.capability_epoch) < 0 or int(self.frame_epoch) < 0:
            raise ValueError("NEGATIVE_DRIFT_INTERVENTION_EPOCH")
        if not self.raw_history:
            raise ValueError("DRIFT_INTERVENTION_RAW_HISTORY_REQUIRED")
        object.__setattr__(self, "raw_history", tuple(tuple(str(v) for v in row) for row in self.raw_history))
        object.__setattr__(self, "capability_epoch", int(self.capability_epoch))
        object.__setattr__(self, "frame_epoch", int(self.frame_epoch))
        object.__setattr__(self, "current_access", bool(self.current_access))
        object.__setattr__(self, "assistance_ancestry", tuple(str(x) for x in self.assistance_ancestry))
        if (self.episode_schema_id is None) != (self.episode_schema_epoch is None):
            raise ValueError("PARTIAL_DRIFT_INTERVENTION_EPISODE_BINDING")
        if self.episode_schema_epoch is not None and int(self.episode_schema_epoch) < 0:
            raise ValueError("NEGATIVE_DRIFT_INTERVENTION_EPISODE_EPOCH")
        if self.semantic_intervention_authority != "NONE":
            raise ValueError("DRIFT_INTERVENTION_PROBE_CANNOT_CARRY_SEMANTIC_AUTHORITY")

    def signature_payload(self) -> dict[str, Any]:
        return {
            "probe_id": self.probe_id,
            "capability_id": self.capability_id,
            "capability_epoch": self.capability_epoch,
            "raw_history": [list(x) for x in self.raw_history],
            "action_token": self.action_token,
            "frame_id": self.frame_id,
            "frame_epoch": self.frame_epoch,
            "episode_schema_id": self.episode_schema_id,
            "episode_schema_epoch": self.episode_schema_epoch,
            "assistance_ancestry": list(self.assistance_ancestry),
            "semantic_intervention_authority": self.semantic_intervention_authority,
        }

    def digest(self) -> str:
        return sha256_bytes(canonical_json(self.signature_payload()))

    def serializable(self) -> dict[str, Any]:
        d = self.signature_payload()
        d["current_access"] = self.current_access
        d["probe_sha256"] = self.digest()
        return d

    @classmethod
    def from_serializable(cls, d: dict[str, Any]) -> "DriftInterventionProbe":
        return cls(
            probe_id=str(d["probe_id"]), capability_id=str(d["capability_id"]),
            capability_epoch=int(d["capability_epoch"]),
            raw_history=tuple(tuple(str(v) for v in row) for row in d["raw_history"]),
            action_token=str(d["action_token"]), frame_id=str(d["frame_id"]),
            frame_epoch=int(d["frame_epoch"]), episode_schema_id=d.get("episode_schema_id"),
            episode_schema_epoch=d.get("episode_schema_epoch"),
            current_access=bool(d.get("current_access", True)),
            assistance_ancestry=tuple(d.get("assistance_ancestry", ())),
            semantic_intervention_authority=str(d.get("semantic_intervention_authority", "NONE")),
        )


@dataclass(frozen=True)
class DriftInterventionSelection:
    status: str
    projection_id: str
    stale_projection_epoch: int
    historical_candidate_sha256: str
    alternative_candidate_sha256: str
    plan_id: str | None
    probe: DriftInterventionProbe | None
    prediction_partition: tuple[tuple[str, tuple[str, ...]], ...]
    disagreement_entropy: float
    repeats: int
    min_agreement: float
    min_margin: float
    max_probe_pool: int
    assistance_ancestry: tuple[str, ...]
    truth_authority: str = "NONE"
    drift_cause_semantic_authority: str = "NONE"
    model_switch_authority: str = "NONE"
    scheduling_authority: str = "NONE"

    def __post_init__(self) -> None:
        if self.status not in {
            "PROBE_SELECTED", "ACTION_LIMITED", "NO_DISCRIMINATING_INTERVENTION_WITHIN_QUALIFIED_SET"
        }:
            raise ValueError("INVALID_DRIFT_INTERVENTION_SELECTION_STATUS")
        if self.status == "PROBE_SELECTED" and (self.probe is None or self.plan_id is None or self.disagreement_entropy <= 0.0):
            raise ValueError("SELECTED_DRIFT_INTERVENTION_REQUIRES_DISAGREEMENT_PLAN")
        if any(getattr(self, k) != "NONE" for k in (
            "truth_authority", "drift_cause_semantic_authority", "model_switch_authority", "scheduling_authority"
        )):
            raise ValueError("DRIFT_INTERVENTION_SELECTION_CANNOT_CARRY_AUTHORITY")

    def serializable(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "probe": None if self.probe is None else self.probe.serializable(),
            "prediction_partition": [[k, list(v)] for k, v in self.prediction_partition],
        }

    @classmethod
    def from_serializable(cls, d: dict[str, Any]) -> "DriftInterventionSelection":
        x = dict(d)
        x["probe"] = None if x.get("probe") is None else DriftInterventionProbe.from_serializable(x["probe"])
        x["prediction_partition"] = tuple((str(k), tuple(str(v) for v in vals)) for k, vals in x.get("prediction_partition", ()))
        x["assistance_ancestry"] = tuple(x.get("assistance_ancestry", ()))
        return cls(**x)


def select_drift_discriminating_intervention(
    projection_id: str,
    stale_projection_epoch: int,
    historical_candidate: RobustProjectionConstructorCandidate,
    alternative_candidate: RobustProjectionConstructorCandidate,
    probes: Iterable[DriftInterventionProbe],
    cfg: DriftInterventionConfig | None = None,
) -> DriftInterventionSelection:
    cfg = cfg or DriftInterventionConfig()
    ps = tuple(probes)
    if len({p.probe_id for p in ps}) != len(ps):
        raise ValueError("DUPLICATE_DRIFT_INTERVENTION_PROBE_ID")
    if len(ps) > int(cfg.max_probe_pool):
        raise ValueError("DRIFT_INTERVENTION_POOL_EXCEEDS_SUPPLIED_BOUND")
    hsha, asha = historical_candidate.digest(), alternative_candidate.digest()
    best: tuple[float, str, DriftInterventionProbe, tuple[tuple[str, tuple[str, ...]], ...]] | None = None
    any_discriminating = False
    for p in ps:
        old = _predict(historical_candidate, p.raw_history, p.action_token)
        alt = _predict(alternative_candidate, p.raw_history, p.action_token)
        if old is None or alt is None or old == alt:
            continue
        any_discriminating = True
        if not p.current_access:
            continue
        partition: dict[str, list[str]] = {}
        partition.setdefault(old, []).append(hsha)
        partition.setdefault(alt, []).append(asha)
        part = tuple((k, tuple(sorted(v))) for k, v in sorted(partition.items()))
        ent = _entropy((old, alt))
        key = (ent, p.probe_id, p, part)
        if best is None or ent > best[0] + 1e-12 or (abs(ent - best[0]) <= 1e-12 and p.probe_id < best[1]):
            best = key
    ancestry = cfg.assistance_ancestry()
    if best is None:
        return DriftInterventionSelection(
            status="ACTION_LIMITED" if any_discriminating else "NO_DISCRIMINATING_INTERVENTION_WITHIN_QUALIFIED_SET",
            projection_id=str(projection_id), stale_projection_epoch=int(stale_projection_epoch),
            historical_candidate_sha256=hsha, alternative_candidate_sha256=asha,
            plan_id=None, probe=None, prediction_partition=(), disagreement_entropy=0.0,
            repeats=int(cfg.repeats), min_agreement=float(cfg.min_agreement), min_margin=float(cfg.min_margin), max_probe_pool=int(cfg.max_probe_pool),
            assistance_ancestry=ancestry,
        )
    ent, _, probe, part = best
    plan_payload = {
        "projection_id": str(projection_id), "stale_projection_epoch": int(stale_projection_epoch),
        "historical_candidate_sha256": hsha, "alternative_candidate_sha256": asha,
        "probe_sha256": probe.digest(), "partition": [[k, list(v)] for k, v in part],
        "repeats": int(cfg.repeats), "min_agreement": float(cfg.min_agreement), "min_margin": float(cfg.min_margin),
    }
    plan_id = "drift-probe-plan-" + hashlib.sha256(canonical_json(plan_payload)).hexdigest()[:24]
    return DriftInterventionSelection(
        status="PROBE_SELECTED", projection_id=str(projection_id), stale_projection_epoch=int(stale_projection_epoch),
        historical_candidate_sha256=hsha, alternative_candidate_sha256=asha,
        plan_id=plan_id, probe=probe, prediction_partition=part, disagreement_entropy=ent,
        repeats=int(cfg.repeats), min_agreement=float(cfg.min_agreement), min_margin=float(cfg.min_margin), max_probe_pool=int(cfg.max_probe_pool),
        assistance_ancestry=ancestry + tuple(probe.assistance_ancestry),
    )


@dataclass(frozen=True)
class DriftInterventionWitness:
    witness_id: str
    plan_id: str
    projection_id: str
    stale_projection_epoch: int
    probe_id: str
    probe_sha256: str
    evidence_id: str
    evidence_sha256: str
    outcome_counts: tuple[tuple[str, int], ...]
    candidate_scores: tuple[tuple[str, float], ...]
    status: str
    supported_candidate_sha256: str | None
    assistance_ancestry: tuple[str, ...]
    truth_authority: str = "NONE"
    drift_cause_semantic_authority: str = "NONE"
    model_switch_authority: str = "NONE"
    qualification_authority: str = "NONE"

    def __post_init__(self) -> None:
        if self.status not in {"NARROWED_TO_SINGLE_OPAQUE_PREDICTIVE_CANDIDATE", "UNRESOLVED_WITHIN_BOUNDS", "MODEL_SPACE_CHALLENGE"}:
            raise ValueError("INVALID_DRIFT_INTERVENTION_WITNESS_STATUS")
        if self.status.startswith("NARROWED") and self.supported_candidate_sha256 is None:
            raise ValueError("NARROWED_DRIFT_INTERVENTION_REQUIRES_SUPPORTED_CANDIDATE")
        if any(getattr(self, k) != "NONE" for k in (
            "truth_authority", "drift_cause_semantic_authority", "model_switch_authority", "qualification_authority"
        )):
            raise ValueError("DRIFT_INTERVENTION_WITNESS_CANNOT_CARRY_AUTHORITY")

    def serializable(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "outcome_counts": [list(x) for x in self.outcome_counts],
            "candidate_scores": [list(x) for x in self.candidate_scores],
        }

    @classmethod
    def from_serializable(cls, d: dict[str, Any]) -> "DriftInterventionWitness":
        x = dict(d)
        x["outcome_counts"] = tuple((str(a), int(b)) for a, b in x.get("outcome_counts", ()))
        x["candidate_scores"] = tuple((str(a), float(b)) for a, b in x.get("candidate_scores", ()))
        x["assistance_ancestry"] = tuple(x.get("assistance_ancestry", ()))
        return cls(**x)


def assess_drift_intervention_outcomes(
    selection: DriftInterventionSelection,
    outcomes: Iterable[str],
    evidence_id: str,
    evidence_sha256: str,
    cfg: DriftInterventionConfig | None = None,
) -> DriftInterventionWitness:
    cfg = cfg or DriftInterventionConfig(repeats=selection.repeats, min_agreement=selection.min_agreement, min_margin=selection.min_margin, max_probe_pool=selection.max_probe_pool)
    if (int(cfg.repeats), float(cfg.min_agreement), float(cfg.min_margin)) != (int(selection.repeats), float(selection.min_agreement), float(selection.min_margin)):
        raise ValueError("DRIFT_INTERVENTION_CONFIG_MUST_MATCH_SELECTED_PLAN")
    if selection.status != "PROBE_SELECTED" or selection.probe is None or selection.plan_id is None:
        raise ValueError("DRIFT_INTERVENTION_OUTCOMES_REQUIRE_SELECTED_PLAN")
    outs = tuple(str(x) for x in outcomes)
    if len(outs) != int(cfg.repeats):
        raise ValueError("DRIFT_INTERVENTION_OUTCOME_COUNT_MISMATCH")
    evsha = _sha(evidence_sha256, error="DRIFT_INTERVENTION_EVIDENCE_SHA256_REQUIRED")
    predicted: dict[str, str] = {}
    for outcome, candidates in selection.prediction_partition:
        for csha in candidates:
            predicted[csha] = outcome
    scores = tuple(sorted((csha, sum(x == pred for x in outs) / len(outs)) for csha, pred in predicted.items()))
    ranked = sorted(scores, key=lambda kv: (-kv[1], kv[0]))
    top_sha, top_score = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    known = set(predicted.values())
    if all(x not in known for x in outs):
        status = "MODEL_SPACE_CHALLENGE"; supported = None
    elif top_score >= cfg.min_agreement and top_score - second >= cfg.min_margin:
        status = "NARROWED_TO_SINGLE_OPAQUE_PREDICTIVE_CANDIDATE"; supported = top_sha
    else:
        status = "UNRESOLVED_WITHIN_BOUNDS"; supported = None
    counts = tuple(sorted((k, int(v)) for k, v in Counter(outs).items()))
    wid_payload = {
        "plan_id": selection.plan_id, "evidence_id": str(evidence_id), "evidence_sha256": evsha,
        "counts": [list(x) for x in counts], "scores": [list(x) for x in scores], "status": status,
    }
    witness_id = "drift-probe-witness-" + hashlib.sha256(canonical_json(wid_payload)).hexdigest()[:24]
    return DriftInterventionWitness(
        witness_id=witness_id, plan_id=selection.plan_id, projection_id=selection.projection_id,
        stale_projection_epoch=selection.stale_projection_epoch, probe_id=selection.probe.probe_id,
        probe_sha256=selection.probe.digest(), evidence_id=str(evidence_id), evidence_sha256=evsha,
        outcome_counts=counts, candidate_scores=scores, status=status, supported_candidate_sha256=supported,
        assistance_ancestry=tuple(selection.assistance_ancestry) + cfg.assistance_ancestry(),
    )
