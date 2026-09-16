from __future__ import annotations

import hashlib
import itertools
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from ..evidence.authority import FixedQualifier
from ..evidence.ledger import EvidenceLedger, canonical_json, sha256_bytes
from ..runtime.types import Authority, EpistemicStatus, EvidenceRef, QualificationState


def _mode(counter: Counter[str]) -> str | None:
    if not counter:
        return None
    return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


@dataclass(frozen=True)
class ProjectionSample:
    """Opaque interaction sample for bounded projection proposal generation.

    Raw positions, action tokens, and effect tokens are intentionally
    uninterpreted. The operational frame owns the raw coordinate boundary; this
    object does not claim Microseed constructed or semantically understands it.
    """

    sample_id: str
    raw_tokens: tuple[str, ...]
    action_token: str
    effect_token: str
    operational_scope_id: str | None
    frame_id: str
    frame_epoch: int

    def __post_init__(self) -> None:
        if not self.sample_id or not self.raw_tokens or not self.action_token or not self.effect_token:
            raise ValueError("INCOMPLETE_PROJECTION_SAMPLE")
        if not self.frame_id or int(self.frame_epoch) < 0:
            raise ValueError("PROJECTION_SAMPLE_REQUIRES_FRAME_CURRENTNESS")
        object.__setattr__(self, "raw_tokens", tuple(str(x) for x in self.raw_tokens))
        object.__setattr__(self, "frame_epoch", int(self.frame_epoch))

    def serializable(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "raw_tokens": list(self.raw_tokens),
            "action_token": self.action_token,
            "effect_token": self.effect_token,
            "operational_scope_id": self.operational_scope_id,
            "frame_id": self.frame_id,
            "frame_epoch": self.frame_epoch,
        }


@dataclass(frozen=True)
class ProjectionDiscoveryConfig:
    """Supplied bounded constructor grammar for proposal generation only."""

    max_subset: int = 2
    min_train_support: int = 20
    min_key_action_support: int = 3
    min_validation_accuracy: float = 0.82
    min_lift_over_action_baseline: float = 0.18
    min_scope_accuracy: float = 0.74
    complexity_penalty: float = 0.008
    max_candidates: int = 12

    def __post_init__(self) -> None:
        if not 1 <= int(self.max_subset) <= 4:
            raise ValueError("BOUNDED_PROJECTION_SUBSET_GRAMMAR_REQUIRED")
        if int(self.min_train_support) < 1 or int(self.min_key_action_support) < 1:
            raise ValueError("INVALID_PROJECTION_DISCOVERY_SUPPORT")
        if int(self.max_candidates) < 1:
            raise ValueError("INVALID_PROJECTION_MAX_CANDIDATES")

    def assistance_ancestry(self) -> tuple[str, ...]:
        return (
            "SUPPLIED_RAW_OBSERVATION_BOUNDARIES",
            "SUPPLIED_OPAQUE_ACTION_TOKENS",
            "SUPPLIED_OPAQUE_EFFECT_TOKENS",
            f"FIXED_SUBSET_GRAMMAR_MAX_{int(self.max_subset)}",
            "PREDICTIVE_EQUIVALENCE_COMPRESSION",
            "FIXED_DISCOVERY_THRESHOLDS",
        )


@dataclass(frozen=True)
class EpistemicProjectionCandidate:
    """Proposal-only opaque predictive partition discovered from interaction."""

    candidate_id: str
    input_positions: tuple[int, ...]
    key_to_bucket: tuple[tuple[tuple[str, ...], str], ...]
    bucket_action_prediction: tuple[tuple[str, str, str], ...]
    train_accuracy: float
    validation_accuracy: float
    action_baseline_accuracy: float
    min_scope_accuracy: float
    lift: float
    score: float
    raw_key_count: int
    bucket_count: int
    source_sample_ids: tuple[str, ...]
    frame_epochs: tuple[tuple[str, int], ...]
    assistance_ancestry: tuple[str, ...]
    nomination_basis: str = "BOUNDED_ACTION_CONDITIONED_PREDICTIVE_EQUIVALENCE"
    proposal_authority: str = "NONE"
    qualification_authority: str = "NONE"
    semantic_projection_authority: str = "NONE"
    truth_authority: str = "NONE"

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.input_positions:
            raise ValueError("EMPTY_EPISTEMIC_PROJECTION_CANDIDATE")
        if len(set(self.input_positions)) != len(self.input_positions) or min(self.input_positions) < 0:
            raise ValueError("INVALID_EPISTEMIC_PROJECTION_INPUT_POSITIONS")
        if self.proposal_authority != "NONE" or self.qualification_authority != "NONE":
            raise ValueError("PROJECTION_CANDIDATE_CANNOT_SELF_QUALIFY")
        if self.semantic_projection_authority != "NONE" or self.truth_authority != "NONE":
            raise ValueError("PROJECTION_CANDIDATE_CANNOT_CARRY_SEMANTIC_OR_TRUTH_AUTHORITY")
        if not self.key_to_bucket or not self.bucket_action_prediction:
            raise ValueError("PROJECTION_CANDIDATE_REQUIRES_PREDICTIVE_PARTITION")

    def signature_payload(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "input_positions": list(self.input_positions),
            "key_to_bucket": [[list(k), v] for k, v in self.key_to_bucket],
            "bucket_action_prediction": [list(x) for x in self.bucket_action_prediction],
            "train_accuracy": self.train_accuracy,
            "validation_accuracy": self.validation_accuracy,
            "action_baseline_accuracy": self.action_baseline_accuracy,
            "min_scope_accuracy": self.min_scope_accuracy,
            "lift": self.lift,
            "score": self.score,
            "raw_key_count": self.raw_key_count,
            "bucket_count": self.bucket_count,
            "source_sample_ids": list(self.source_sample_ids),
            "frame_epochs": [list(x) for x in self.frame_epochs],
            "assistance_ancestry": list(self.assistance_ancestry),
            "nomination_basis": self.nomination_basis,
            "proposal_authority": self.proposal_authority,
            "qualification_authority": self.qualification_authority,
            "semantic_projection_authority": self.semantic_projection_authority,
            "truth_authority": self.truth_authority,
        }

    def digest(self) -> str:
        return sha256_bytes(canonical_json(self.signature_payload()))

    def serializable(self) -> dict[str, Any]:
        d = self.signature_payload()
        d["candidate_sha256"] = self.digest()
        return d

    @classmethod
    def from_serializable(cls, d: dict[str, Any]) -> "EpistemicProjectionCandidate":
        return cls(
            candidate_id=str(d["candidate_id"]),
            input_positions=tuple(int(x) for x in d["input_positions"]),
            key_to_bucket=tuple((tuple(str(y) for y in k), str(v)) for k, v in d["key_to_bucket"]),
            bucket_action_prediction=tuple(tuple(str(y) for y in x) for x in d["bucket_action_prediction"]),
            train_accuracy=float(d["train_accuracy"]),
            validation_accuracy=float(d["validation_accuracy"]),
            action_baseline_accuracy=float(d["action_baseline_accuracy"]),
            min_scope_accuracy=float(d["min_scope_accuracy"]),
            lift=float(d["lift"]),
            score=float(d["score"]),
            raw_key_count=int(d["raw_key_count"]),
            bucket_count=int(d["bucket_count"]),
            source_sample_ids=tuple(str(x) for x in d["source_sample_ids"]),
            frame_epochs=tuple((str(x[0]), int(x[1])) for x in d["frame_epochs"]),
            assistance_ancestry=tuple(str(x) for x in d.get("assistance_ancestry", ())),
            nomination_basis=str(d.get("nomination_basis", "BOUNDED_ACTION_CONDITIONED_PREDICTIVE_EQUIVALENCE")),
            proposal_authority=str(d.get("proposal_authority", "NONE")),
            qualification_authority=str(d.get("qualification_authority", "NONE")),
            semantic_projection_authority=str(d.get("semantic_projection_authority", "NONE")),
            truth_authority=str(d.get("truth_authority", "NONE")),
        )

    def project(self, raw_tokens: Iterable[str]) -> str | None:
        raw = tuple(str(x) for x in raw_tokens)
        try:
            key = tuple(raw[i] for i in self.input_positions)
        except IndexError:
            return None
        return dict(self.key_to_bucket).get(key)


@dataclass(frozen=True)
class ProjectionQualificationTicket:
    candidate_id: str
    candidate_sha256: str
    state: QualificationState
    qualifier_id: str
    reason: str
    qualification_evidence: tuple[EvidenceRef, ...]


class ExternalProjectionQualifier:
    """Harness-side projection qualifier; never part of Microseed cognition."""

    def __init__(self, ledger: EvidenceLedger, *, qualifier_id: str = "HSP-EXTERNAL-PROJECTION-QUALIFIER"):
        if not qualifier_id or qualifier_id.upper().startswith("MICROSEED"):
            raise ValueError("qualifier_id must identify an external qualification boundary")
        self.ledger = ledger
        self.qualifier_id = qualifier_id

    def qualify(
        self,
        candidate: EpistemicProjectionCandidate,
        *,
        qualification_evidence: Iterable[EvidenceRef],
    ) -> ProjectionQualificationTicket:
        refs = tuple(qualification_evidence)
        decision = FixedQualifier(self.ledger).decide(refs, Authority.REFERENCE_ONLY)
        return ProjectionQualificationTicket(
            candidate_id=candidate.candidate_id,
            candidate_sha256=candidate.digest(),
            state=decision.state,
            qualifier_id=self.qualifier_id,
            reason=decision.reason,
            qualification_evidence=refs,
        )


def validate_external_projection_ticket(
    candidate: EpistemicProjectionCandidate,
    ticket: ProjectionQualificationTicket,
    ledger: EvidenceLedger,
) -> tuple[bool, str]:
    if not ticket.qualifier_id or ticket.qualifier_id.upper().startswith("MICROSEED"):
        return False, "QUALIFIER_NOT_EXTERNAL"
    if ticket.candidate_id != candidate.candidate_id:
        return False, "CANDIDATE_ID_MISMATCH"
    if ticket.candidate_sha256 != candidate.digest():
        return False, "CANDIDATE_DIGEST_MISMATCH"
    if not ticket.qualification_evidence:
        return False, "NO_QUALIFICATION_EVIDENCE"
    decision = FixedQualifier(ledger).decide(ticket.qualification_evidence, Authority.REFERENCE_ONLY)
    if ticket.state != decision.state or ticket.reason != decision.reason:
        return False, "QUALIFICATION_DECISION_MISMATCH"
    if ticket.state not in {QualificationState.SHADOW_QUALIFIED, QualificationState.QUALIFIED}:
        return False, f"NOT_ADMISSIBLE:{ticket.state.value}"
    return True, "VALID_EXTERNAL_PROJECTION_QUALIFICATION"


def _action_baseline(train: tuple[ProjectionSample, ...], validation: tuple[ProjectionSample, ...]) -> float:
    table: dict[str, Counter[str]] = defaultdict(Counter)
    for row in train:
        table[row.action_token][row.effect_token] += 1
    good = 0
    for row in validation:
        good += _mode(table[row.action_token]) == row.effect_token
    return good / max(len(validation), 1)


def _fit_candidate(
    train: tuple[ProjectionSample, ...],
    validation: tuple[ProjectionSample, ...],
    positions: tuple[int, ...],
    cfg: ProjectionDiscoveryConfig,
) -> EpistemicProjectionCandidate | None:
    if len(train) < cfg.min_train_support:
        return None
    action_effect: dict[tuple[tuple[str, ...], str], Counter[str]] = defaultdict(Counter)
    keys: set[tuple[str, ...]] = set()
    actions = sorted({r.action_token for r in train})
    frames: dict[str, set[int]] = defaultdict(set)
    for row in train:
        if max(positions) >= len(row.raw_tokens):
            return None
        key = tuple(row.raw_tokens[i] for i in positions)
        keys.add(key)
        action_effect[(key, row.action_token)][row.effect_token] += 1
        frames[row.frame_id].add(row.frame_epoch)
    frame_epochs: list[tuple[str, int]] = []
    for frame_id, epochs in sorted(frames.items()):
        if len(epochs) != 1:
            return None
        frame_epochs.append((frame_id, next(iter(epochs))))

    key_signature: dict[tuple[str, ...], tuple[tuple[str, str], ...]] = {}
    for key in sorted(keys):
        sig: list[tuple[str, str]] = []
        for action in actions:
            c = action_effect.get((key, action), Counter())
            effect = _mode(c) if sum(c.values()) >= cfg.min_key_action_support else "UNKNOWN"
            sig.append((action, str(effect)))
        key_signature[key] = tuple(sig)
    signature_bucket = {
        sig: "bucket-" + hashlib.sha256(canonical_json(sig)).hexdigest()[:16]
        for sig in sorted(set(key_signature.values()))
    }
    key_to_bucket = {key: signature_bucket[sig] for key, sig in key_signature.items()}
    prediction = {
        (bucket, action): effect
        for sig, bucket in signature_bucket.items()
        for action, effect in sig
    }

    def accuracy(rows: tuple[ProjectionSample, ...]) -> tuple[float, float]:
        good = 0
        by_scope: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for row in rows:
            if max(positions) >= len(row.raw_tokens):
                continue
            key = tuple(row.raw_tokens[i] for i in positions)
            bucket = key_to_bucket.get(key)
            pred = prediction.get((bucket, row.action_token), "UNKNOWN") if bucket else "UNKNOWN"
            hit = pred == row.effect_token
            good += hit
            scope = row.operational_scope_id or "__GLOBAL__"
            by_scope[scope][0] += hit
            by_scope[scope][1] += 1
        return good / max(len(rows), 1), min((a / max(b, 1) for a, b in by_scope.values()), default=0.0)

    train_accuracy, _ = accuracy(train)
    validation_accuracy, min_scope_accuracy = accuracy(validation)
    baseline = _action_baseline(train, validation)
    lift = validation_accuracy - baseline
    score = lift - cfg.complexity_penalty * (len(positions) - 1) - cfg.complexity_penalty * math.log2(max(len(signature_bucket), 1))
    mapping = tuple(sorted(key_to_bucket.items()))
    bap = tuple(sorted((b, a, e) for (b, a), e in prediction.items()))
    candidate_payload = {
        "input_positions": list(positions),
        "key_to_bucket": [[list(k), v] for k, v in mapping],
        "bucket_action_prediction": [list(x) for x in bap],
        "frame_epochs": [list(x) for x in frame_epochs],
    }
    candidate_id = "proj-cand-" + hashlib.sha256(canonical_json(candidate_payload)).hexdigest()[:20]
    return EpistemicProjectionCandidate(
        candidate_id=candidate_id,
        input_positions=positions,
        key_to_bucket=mapping,
        bucket_action_prediction=bap,
        train_accuracy=train_accuracy,
        validation_accuracy=validation_accuracy,
        action_baseline_accuracy=baseline,
        min_scope_accuracy=min_scope_accuracy,
        lift=lift,
        score=score,
        raw_key_count=len(keys),
        bucket_count=len(signature_bucket),
        source_sample_ids=tuple(sorted(r.sample_id for r in train)),
        frame_epochs=tuple(frame_epochs),
        assistance_ancestry=cfg.assistance_ancestry(),
    )


def discover_epistemic_projection_candidates(
    training_samples: Iterable[ProjectionSample],
    validation_samples: Iterable[ProjectionSample],
    cfg: ProjectionDiscoveryConfig | None = None,
) -> list[EpistemicProjectionCandidate]:
    """Generate bounded proposal candidates; never qualify or admit them.

    The constructor searches only a fixed subset grammar over opaque positional
    raw coordinates. It groups raw keys by identical action-conditioned effect
    predictions, creating opaque predictive-equivalence buckets. This is a
    deliberately small bridge, not general representation learning.
    """

    cfg = cfg or ProjectionDiscoveryConfig()
    train = tuple(training_samples)
    validation = tuple(validation_samples)
    if not train or not validation:
        return []
    dims = {len(x.raw_tokens) for x in train + validation}
    if len(dims) != 1 or next(iter(dims)) < 1:
        return []
    out: list[EpistemicProjectionCandidate] = []
    dim = next(iter(dims))
    for size in range(1, min(int(cfg.max_subset), dim) + 1):
        for positions in itertools.combinations(range(dim), size):
            candidate = _fit_candidate(train, validation, positions, cfg)
            if candidate is None:
                continue
            if (
                candidate.validation_accuracy >= cfg.min_validation_accuracy
                and candidate.lift >= cfg.min_lift_over_action_baseline
                and candidate.min_scope_accuracy >= cfg.min_scope_accuracy
            ):
                out.append(candidate)
    out.sort(key=lambda x: (-x.score, len(x.input_positions), -x.validation_accuracy, x.input_positions))
    return out[: int(cfg.max_candidates)]
