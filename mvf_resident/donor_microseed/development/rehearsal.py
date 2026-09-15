from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass, asdict
import hashlib
import json
import math
import statistics
from typing import Iterable

from ..runtime.types import Authority, FeasibilityState
from .recruitment import RecruitmentOption


@dataclass(frozen=True)
class RehearsalTransitionObservation:
    """One opaque action-conditioned transition observation for bounded rehearsal.

    State handles, trace/event boundaries, scalar effect coordinate, and finite
    candidate-action vocabulary are assistance/current operational structure.  The
    observation does not claim semantic state, goal, object, or world-model truth.
    Epoch anchors are checked by the entity before the row may participate.
    """

    evidence_id: str
    state_id: str
    capability_id: str
    next_state_id: str
    value_effect: float
    capability_epoch: int
    frame_id: str
    frame_epoch: int
    episode_schema_id: str
    episode_schema_epoch: int
    topology_id: str | None = None
    topology_epoch: int | None = None
    coordination_id: str | None = None
    coordination_epoch: int | None = None

    def serializable(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RehearsalTransitionRelation:
    state_id: str
    capability_id: str
    next_state_id: str
    value_effect: float
    support: int
    consistency: float
    source_evidence_ids: tuple[str, ...]
    capability_epoch: int
    frame_epoch: tuple[str, int]
    episode_schema_epoch: tuple[str, int]
    topology_epoch: tuple[str, int] | None = None
    coordination_epoch: tuple[str, int] | None = None
    authority: str = "EVIDENCE_BOUND_PREDICTIVE_RELATION_ONLY"
    truth_authority: str = "NONE"
    semantic_state_authority: str = "NONE"
    # MS1780: preserve newer evidence-premise ancestry when a rehearsal edge is
    # used as an ephemeral relational alternative.  Empty defaults keep legacy
    # callers and positional construction unchanged.
    evidence_premise_epochs: tuple[tuple[str, int], ...] = ()
    evidence_premise_signatures: tuple[tuple[str, str], ...] = ()
    # Optional because legacy rehearsal observations carried an externally
    # selected scalar coordinate. Endogenous learned/model alternatives must
    # preserve the coordinate they were actually learned against.
    value_epoch: tuple[str, int] | None = None

    def digest(self) -> str:
        payload = asdict(self)
        # Backward compatibility is part of the carrier contract: adding an
        # optional ancestry field must not rewrite the identity of every legacy
        # relation whose ancestry was lawfully empty.
        if not self.evidence_premise_epochs:
            payload.pop("evidence_premise_epochs", None)
        if not self.evidence_premise_signatures:
            payload.pop("evidence_premise_signatures", None)
        if self.value_epoch is None:
            payload.pop("value_epoch", None)
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class CounterfactualRehearsalConfig:
    """Supplied finite search grammar for the MS1328-1352 bridge.

    The finite horizon/node budget and exact state-action grouping are explicit
    assistance.  Their presence is why this substrate is not a general planner.
    """

    max_horizon: int = 2
    max_nodes: int = 64
    min_support: int = 8
    min_consistency: float = 0.78
    effect_round_digits: int = 3

    def validate(self) -> None:
        if self.max_horizon < 1 or self.max_nodes < 1 or self.min_support < 1:
            raise ValueError("REHEARSAL_INVALID_FINITE_BOUNDS")
        if not (0.5 < self.min_consistency <= 1.0):
            raise ValueError("REHEARSAL_INVALID_CONSISTENCY_GATE")

    def assistance_ancestry(self) -> tuple[str, ...]:
        return (
            "SUPPLIED_OPAQUE_STATE_BUCKETS",
            "SUPPLIED_TRANSITION_TRACE_BOUNDARIES",
            "SUPPLIED_SCALAR_VALUE_EFFECT_COORDINATE",
            f"SUPPLIED_REHEARSAL_HORIZON:{self.max_horizon}",
            f"SUPPLIED_REHEARSAL_NODE_BUDGET:{self.max_nodes}",
            "FIXED_EXACT_STATE_ACTION_GROUPING",
            "FIXED_SUPPORT_AND_CONSISTENCY_GATES",
        )


@dataclass(frozen=True)
class CounterfactualRehearsalProposal:
    proposal_id: str
    start_state_id: str
    sequence: tuple[str, ...]
    final_state_id: str
    predicted_value_effect: float
    predicted_final_value: float
    residual_pressure: float
    transition_relation_digests: tuple[str, ...]
    source_evidence_ids: tuple[str, ...]
    capability_epochs: tuple[tuple[str, int], ...]
    frame_epochs: tuple[tuple[str, int], ...]
    episode_schema_epochs: tuple[tuple[str, int], ...]
    value_epoch: tuple[str, int]
    topology_epochs: tuple[tuple[str, int], ...] = ()
    coordination_epochs: tuple[tuple[str, int], ...] = ()
    predicted_state_path: tuple[str, ...] = ()
    predicted_step_value_effects: tuple[float, ...] = ()
    assistance_ancestry: tuple[str, ...] = ()
    nodes_expanded: int = 0
    authority: str = Authority.MODEL_OUTPUT_ONLY.value
    semantic_goal_authority: str = "NONE"
    truth_authority: str = "NONE"
    execution_authority: str = "NONE"
    qualification_authority: str = "NONE"

    def serializable(self) -> dict:
        d = asdict(self)
        for key in (
            "sequence", "transition_relation_digests", "source_evidence_ids", "capability_epochs",
            "frame_epochs", "episode_schema_epochs", "topology_epochs", "coordination_epochs", "predicted_state_path", "predicted_step_value_effects", "assistance_ancestry"
        ):
            d[key] = list(d[key])
        d["value_epoch"] = list(self.value_epoch)
        return d

    @classmethod
    def from_serializable(cls, d: dict) -> "CounterfactualRehearsalProposal":
        return cls(
            proposal_id=str(d["proposal_id"]), start_state_id=str(d["start_state_id"]),
            sequence=tuple(d.get("sequence", ())), final_state_id=str(d["final_state_id"]),
            predicted_value_effect=float(d["predicted_value_effect"]), predicted_final_value=float(d["predicted_final_value"]),
            residual_pressure=float(d["residual_pressure"]), transition_relation_digests=tuple(d.get("transition_relation_digests", ())),
            source_evidence_ids=tuple(d.get("source_evidence_ids", ())),
            capability_epochs=tuple((str(a), int(b)) for a,b in d.get("capability_epochs", ())),
            frame_epochs=tuple((str(a), int(b)) for a,b in d.get("frame_epochs", ())),
            episode_schema_epochs=tuple((str(a), int(b)) for a,b in d.get("episode_schema_epochs", ())),
            value_epoch=(str(d["value_epoch"][0]), int(d["value_epoch"][1])),
            topology_epochs=tuple((str(a), int(b)) for a,b in d.get("topology_epochs", ())),
            coordination_epochs=tuple((str(a), int(b)) for a,b in d.get("coordination_epochs", ())),
            predicted_state_path=tuple(str(x) for x in d.get("predicted_state_path", ())),
            predicted_step_value_effects=tuple(float(x) for x in d.get("predicted_step_value_effects", ())),
            assistance_ancestry=tuple(d.get("assistance_ancestry", ())), nodes_expanded=int(d.get("nodes_expanded", 0)),
            authority=str(d.get("authority", Authority.MODEL_OUTPUT_ONLY.value)),
            semantic_goal_authority=str(d.get("semantic_goal_authority", "NONE")), truth_authority=str(d.get("truth_authority", "NONE")),
            execution_authority=str(d.get("execution_authority", "NONE")), qualification_authority=str(d.get("qualification_authority", "NONE")),
        )

    def digest(self) -> str:
        payload = self.serializable().copy(); payload.pop("proposal_id", None)
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class CounterfactualRehearsalRegistry:
    """Durable proposal history only; no execute/qualify/model-switch surface."""

    def __init__(self) -> None:
        self.proposals: dict[str, CounterfactualRehearsalProposal] = {}

    def add(self, proposal: CounterfactualRehearsalProposal) -> None:
        if proposal.proposal_id in self.proposals:
            raise ValueError("duplicate counterfactual rehearsal proposal")
        if proposal.authority != Authority.MODEL_OUTPUT_ONLY.value:
            raise ValueError("REHEARSAL_AUTHORITY_ESCALATION")
        if any(x != "NONE" for x in (proposal.semantic_goal_authority, proposal.truth_authority, proposal.execution_authority, proposal.qualification_authority)):
            raise ValueError("REHEARSAL_FORBIDDEN_AUTHORITY")
        self.proposals[proposal.proposal_id] = proposal


def derive_rehearsal_transition_relations(
    observations: Iterable[RehearsalTransitionObservation], cfg: CounterfactualRehearsalConfig
) -> dict[tuple[str, str], RehearsalTransitionRelation]:
    cfg.validate()
    groups: dict[tuple[str, str], list[RehearsalTransitionObservation]] = defaultdict(list)
    for r in observations:
        if not math.isfinite(float(r.value_effect)):
            raise ValueError("REHEARSAL_NONFINITE_EFFECT")
        groups[(r.state_id, r.capability_id)].append(r)
    out: dict[tuple[str, str], RehearsalTransitionRelation] = {}
    for key, rows in groups.items():
        if len(rows) < cfg.min_support:
            continue
        ancestry_shapes = {
            (r.capability_epoch, r.frame_id, r.frame_epoch, r.episode_schema_id, r.episode_schema_epoch,
             r.topology_id, r.topology_epoch, r.coordination_id, r.coordination_epoch)
            for r in rows
        }
        if len(ancestry_shapes) != 1:
            continue
        buckets = Counter((r.next_state_id, round(float(r.value_effect), cfg.effect_round_digits)) for r in rows)
        (next_state, rounded_effect), count = buckets.most_common(1)[0]
        consistency = count / len(rows)
        if consistency < cfg.min_consistency:
            continue
        matching = [r for r in rows if r.next_state_id == next_state and round(float(r.value_effect), cfg.effect_round_digits) == rounded_effect]
        a = matching[0]
        out[key] = RehearsalTransitionRelation(
            state_id=key[0], capability_id=key[1], next_state_id=next_state,
            value_effect=float(statistics.median([r.value_effect for r in matching])), support=len(rows), consistency=consistency,
            source_evidence_ids=tuple(sorted(r.evidence_id for r in rows)), capability_epoch=a.capability_epoch,
            frame_epoch=(a.frame_id, a.frame_epoch), episode_schema_epoch=(a.episode_schema_id, a.episode_schema_epoch),
            topology_epoch=None if a.topology_id is None else (a.topology_id, int(a.topology_epoch)),
            coordination_epoch=None if a.coordination_id is None else (a.coordination_id, int(a.coordination_epoch)),
        )
    return out


def _pressure(x: float, low: float, high: float) -> float:
    if x < low: return low - x
    if x > high: return x - high
    return 0.0


def propose_counterfactual_rehearsal(
    relations: dict[tuple[str, str], RehearsalTransitionRelation],
    *, start_state_id: str, start_value: float, viable_low: float, viable_high: float,
    value_epoch: tuple[str, int], options: Iterable[RecruitmentOption], cfg: CounterfactualRehearsalConfig,
) -> CounterfactualRehearsalProposal | None:
    cfg.validate()
    if not all(math.isfinite(x) for x in (start_value, viable_low, viable_high)) or viable_low > viable_high:
        raise ValueError("REHEARSAL_VALUE_INPUT_INVALID")
    opts = tuple(options)
    if len({o.capability_id for o in opts}) != len(opts):
        raise ValueError("REHEARSAL_DUPLICATE_CAPABILITY_OPTION")
    by = {o.capability_id: o for o in opts}
    # REFUSED and UNKNOWN are not action candidates. This is abstention, not override.
    feasible = {cid for cid,o in by.items() if o.feasibility == FeasibilityState.FEASIBLE}
    if not feasible:
        return None
    q = deque([(start_state_id, start_value, tuple(), tuple(), tuple())])
    best = None
    nodes = 0
    while q:
        state, value, sequence, rels, evidence = q.popleft()
        if len(sequence) >= cfg.max_horizon:
            continue
        candidates = sorted((r for (s,c),r in relations.items() if s == state and c in feasible), key=lambda r:r.capability_id)
        for r in candidates:
            nodes += 1
            if nodes > cfg.max_nodes:
                return None
            new_sequence = sequence + (r.capability_id,)
            new_value = value + r.value_effect
            new_rels = rels + (r,)
            new_evidence = tuple(dict.fromkeys(evidence + r.source_evidence_ids))
            residual = _pressure(new_value, viable_low, viable_high)
            score = (residual, len(new_sequence), sum(float(by[c].local_cost) for c in new_sequence), new_sequence)
            if best is None or score < best[0]:
                best = (score, state, r.next_state_id, new_value, new_sequence, new_rels, new_evidence, nodes)
            q.append((r.next_state_id, new_value, new_sequence, new_rels, new_evidence))
    if best is None:
        return None
    _, _, final_state, final_value, sequence, rels, evidence, nodes = best
    capability_epochs = tuple(dict.fromkeys((r.capability_id, r.capability_epoch) for r in rels))
    frame_epochs = tuple(dict.fromkeys(r.frame_epoch for r in rels))
    episode_epochs = tuple(dict.fromkeys(r.episode_schema_epoch for r in rels))
    topology_epochs = tuple(dict.fromkeys(r.topology_epoch for r in rels if r.topology_epoch is not None))
    coordination_epochs = tuple(dict.fromkeys(r.coordination_epoch for r in rels if r.coordination_epoch is not None))
    assistance = tuple(dict.fromkeys(cfg.assistance_ancestry() + tuple(x for o in opts for x in o.model_evidence_ids if x.startswith("ASSISTANCE:"))))
    payload = {
        "start_state_id": start_state_id, "sequence": sequence, "final_state_id": final_state,
        "predicted_value_effect": final_value-start_value, "predicted_final_value": final_value,
        "value_epoch": value_epoch, "relation_digests": tuple(r.digest() for r in rels),
    }
    pid = "REHEARSAL-" + hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:20]
    return CounterfactualRehearsalProposal(
        proposal_id=pid, start_state_id=start_state_id, sequence=sequence, final_state_id=final_state,
        predicted_value_effect=final_value-start_value, predicted_final_value=final_value,
        residual_pressure=_pressure(final_value, viable_low, viable_high),
        transition_relation_digests=tuple(r.digest() for r in rels), source_evidence_ids=evidence,
        capability_epochs=capability_epochs, frame_epochs=frame_epochs, episode_schema_epochs=episode_epochs,
        value_epoch=value_epoch, topology_epochs=topology_epochs, coordination_epochs=coordination_epochs,
        predicted_state_path=(start_state_id,) + tuple(r.next_state_id for r in rels),
        predicted_step_value_effects=tuple(float(r.value_effect) for r in rels),
        assistance_ancestry=assistance, nodes_expanded=nodes,
    )
