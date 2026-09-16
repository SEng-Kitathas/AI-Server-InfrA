from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any, Iterable, Mapping

from ..evidence.authority import FixedQualifier
from ..evidence.ledger import EvidenceLedger
from ..runtime.types import Authority, EvidenceRef, QualificationState
from .rehearsal import RehearsalTransitionRelation


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass(frozen=True)
class ActionOutcomeExperience:
    """One executed-action/actual-outcome learning row.

    Intended/predicted effects are deliberately absent from the consequence label.
    They may exist elsewhere as provenance on the originating intent/proposal.
    """
    evidence_id: str
    execution_id: str
    start_state_id: str
    capability_id: str
    actual_next_state_id: str
    actual_value_effect: float
    capability_epoch: int
    frame_epochs: tuple[tuple[str, int], ...]
    episode_schema_epochs: tuple[tuple[str, int], ...]
    value_epoch: tuple[str, int]
    topology_epochs: tuple[tuple[str, int], ...] = ()
    coordination_epochs: tuple[tuple[str, int], ...] = ()
    evidence_premise_epochs: tuple[tuple[str, int], ...] = ()
    evidence_premise_signatures: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.execution_id:
            raise ValueError("ACTION_OUTCOME_EXPERIENCE_REQUIRES_EXECUTION_ID")
        if not math.isfinite(float(self.actual_value_effect)):
            raise ValueError("ACTION_OUTCOME_EXPERIENCE_NONFINITE_EFFECT")
        object.__setattr__(self, "frame_epochs", tuple((str(a), int(b)) for a, b in self.frame_epochs))
        object.__setattr__(self, "episode_schema_epochs", tuple((str(a), int(b)) for a, b in self.episode_schema_epochs))
        object.__setattr__(self, "topology_epochs", tuple((str(a), int(b)) for a, b in self.topology_epochs))
        object.__setattr__(self, "coordination_epochs", tuple((str(a), int(b)) for a, b in self.coordination_epochs))
        object.__setattr__(self, "evidence_premise_epochs", tuple((str(a), int(b)) for a, b in self.evidence_premise_epochs))
        object.__setattr__(self, "evidence_premise_signatures", tuple((str(a), str(b).lower()) for a, b in self.evidence_premise_signatures))
        if any(len(sig) != 64 or any(ch not in "0123456789abcdef" for ch in sig) for _, sig in self.evidence_premise_signatures):
            raise ValueError("INVALID_EVIDENCE_PREMISE_SIGNATURE")
        object.__setattr__(self, "value_epoch", (str(self.value_epoch[0]), int(self.value_epoch[1])))

    def serializable(self) -> dict[str, Any]:
        d = asdict(self)
        for key in ("frame_epochs", "episode_schema_epochs", "topology_epochs", "coordination_epochs", "evidence_premise_epochs", "evidence_premise_signatures"):
            d[key] = [list(x) for x in d[key]]
        d["value_epoch"] = list(d["value_epoch"])
        return d


@dataclass(frozen=True)
class ActionOutcomeAlternativeHypothesis:
    """Proposal-only recurrent outcome mode inside one exact action ancestry group.

    This preserves ambiguity that the ordinary predictive-law learner correctly
    compresses away for exploitation.  It is an epistemic hypothesis carrier
    only: recurrence is anti-surprise evidence, not truth, independence, causal
    identity, qualification, or model-set authority.
    """

    hypothesis_id: str
    start_state_id: str
    capability_id: str
    next_state_id: str
    value_effect: float
    mode_support: int
    group_support: int
    source_evidence_ids: tuple[str, ...]
    source_execution_ids: tuple[str, ...]
    capability_epoch: int
    frame_epochs: tuple[tuple[str, int], ...]
    episode_schema_epochs: tuple[tuple[str, int], ...]
    value_epoch: tuple[str, int]
    topology_epochs: tuple[tuple[str, int], ...] = ()
    coordination_epochs: tuple[tuple[str, int], ...] = ()
    evidence_premise_epochs: tuple[tuple[str, int], ...] = ()
    evidence_premise_signatures: tuple[tuple[str, str], ...] = ()
    proposal_authority: str = "NONE"
    qualification_authority: str = "NONE"
    truth_authority: str = "NONE"
    causal_explanation_authority: str = "NONE"
    evidence_independence_authority: str = "NONE"

    def __post_init__(self) -> None:
        if not self.hypothesis_id or int(self.mode_support) < 2 or int(self.group_support) < int(self.mode_support):
            raise ValueError("INVALID_ACTION_OUTCOME_ALTERNATIVE_HYPOTHESIS")
        if any(x != "NONE" for x in (
            self.proposal_authority, self.qualification_authority, self.truth_authority,
            self.causal_explanation_authority, self.evidence_independence_authority,
        )):
            raise ValueError("ACTION_OUTCOME_ALTERNATIVE_AUTHORITY_ESCALATION")

    def serializable(self) -> dict[str, Any]:
        d=asdict(self)
        for key in ("frame_epochs","episode_schema_epochs","topology_epochs","coordination_epochs","evidence_premise_epochs","evidence_premise_signatures"):
            d[key]=[list(x) for x in d[key]]
        d["value_epoch"]=list(self.value_epoch)
        d["source_evidence_ids"]=list(self.source_evidence_ids)
        d["source_execution_ids"]=list(self.source_execution_ids)
        return d


def discover_action_outcome_alternative_hypotheses(
    experiences: Iterable[ActionOutcomeExperience],
) -> tuple[ActionOutcomeAlternativeHypothesis, ...]:
    """Preserve recurrent competing outcome modes without explaining them.

    The recurrence floor is intentionally fixed at two distinct execution ids per
    outcome mode and cannot be tuned through this API.  This is only structural
    anti-replay recurrence; no physical/evidential independence is inferred.
    """
    groups: dict[tuple[Any, ...], list[ActionOutcomeExperience]] = defaultdict(list)
    for r in experiences:
        key=(
            r.start_state_id,r.capability_id,int(r.capability_epoch),r.frame_epochs,
            r.episode_schema_epochs,r.value_epoch,r.topology_epochs,r.coordination_epochs,
            r.evidence_premise_epochs,r.evidence_premise_signatures,
        )
        groups[key].append(r)
    out=[]
    for key,rows in sorted(groups.items(), key=lambda kv: repr(kv[0])):
        by_mode: dict[tuple[str,float], dict[str, ActionOutcomeExperience]] = defaultdict(dict)
        all_execs=set()
        for r in rows:
            mode=(r.actual_next_state_id,round(float(r.actual_value_effect),3))
            by_mode[mode].setdefault(r.execution_id,r)
            all_execs.add(r.execution_id)
        recurrent=[(mode,exec_rows) for mode,exec_rows in by_mode.items() if len(exec_rows)>=2]
        if len(recurrent)<2:
            continue
        group_support=len(all_execs)
        for (next_state,effect),exec_rows in sorted(recurrent):
            matched=tuple(exec_rows[eid] for eid in sorted(exec_rows))
            payload={
                "start_state_id":key[0],"capability_id":key[1],"next_state_id":next_state,
                "value_effect":effect,"capability_epoch":key[2],"frame_epochs":key[3],
                "episode_schema_epochs":key[4],"value_epoch":key[5],"topology_epochs":key[6],
                "coordination_epochs":key[7],"evidence_premise_epochs":key[8],
                "evidence_premise_signatures":key[9],
            }
            out.append(ActionOutcomeAlternativeHypothesis(
                hypothesis_id="ACTION-ALT-"+_digest(payload)[:20],
                start_state_id=key[0],capability_id=key[1],next_state_id=next_state,value_effect=float(effect),
                mode_support=len(matched),group_support=group_support,
                source_evidence_ids=tuple(sorted({r.evidence_id for r in matched})),
                source_execution_ids=tuple(sorted(exec_rows)),capability_epoch=key[2],
                frame_epochs=key[3],episode_schema_epochs=key[4],value_epoch=key[5],
                topology_epochs=key[6],coordination_epochs=key[7],
                evidence_premise_epochs=key[8],evidence_premise_signatures=key[9],
            ))
    return tuple(out)


@dataclass(frozen=True)
class ActionOutcomeSuccessorCouplingCandidate:
    """Proposal-only recurrent successor coupling between two outcome modes.

    Exact action-successor ancestry can show that one already-observed outcome mode
    repeatedly precedes another. This is bounded co-occurrence structure only: it
    does not establish evidence independence, hidden cause, regime identity, truth,
    or general model-set coherence.
    """
    coupling_id: str
    first_hypothesis_id: str
    second_hypothesis_id: str
    support: int
    source_execution_pairs: tuple[tuple[str, str], ...]
    proposal_authority: str = "NONE"
    truth_authority: str = "NONE"
    causal_explanation_authority: str = "NONE"
    evidence_independence_authority: str = "NONE"
    model_set_authority: str = "NONE"

    def __post_init__(self) -> None:
        if not self.coupling_id or not self.first_hypothesis_id or not self.second_hypothesis_id or int(self.support) < 2:
            raise ValueError("INVALID_ACTION_OUTCOME_SUCCESSOR_COUPLING")
        pairs = tuple((str(a), str(b)) for a, b in self.source_execution_pairs)
        if len(pairs) != int(self.support) or len(set(pairs)) != len(pairs):
            raise ValueError("ACTION_OUTCOME_SUCCESSOR_COUPLING_REPLAY_OR_SUPPORT_MISMATCH")
        object.__setattr__(self, "source_execution_pairs", pairs)
        if any(x != "NONE" for x in (
            self.proposal_authority, self.truth_authority, self.causal_explanation_authority,
            self.evidence_independence_authority, self.model_set_authority,
        )):
            raise ValueError("ACTION_OUTCOME_SUCCESSOR_COUPLING_AUTHORITY_ESCALATION")

    def serializable(self) -> dict[str, Any]:
        d = asdict(self)
        d["source_execution_pairs"] = [list(x) for x in self.source_execution_pairs]
        return d


def discover_action_outcome_successor_couplings(
    hypotheses: Iterable[ActionOutcomeAlternativeHypothesis],
    successor_pairs: Iterable[tuple[str, str]],
) -> tuple[ActionOutcomeSuccessorCouplingCandidate, ...]:
    """Discover recurrent pairwise mode coupling from exact execution-successor links.

    The support floor is fixed at two distinct execution pairs and cannot be tuned.
    Distinct execution ids are anti-replay structure only, never independence proof.
    Only alternatives on the same value coordinate are coupled here.
    """
    hs = tuple(hypotheses)
    by_execution: dict[str, list[ActionOutcomeAlternativeHypothesis]] = defaultdict(list)
    for h in hs:
        for xid in h.source_execution_ids:
            by_execution[xid].append(h)
    counts: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    lookup = {h.hypothesis_id: h for h in hs}
    for first_x, second_x in {(str(a), str(b)) for a, b in successor_pairs}:
        for first in by_execution.get(first_x, ()):
            for second in by_execution.get(second_x, ()):
                if (first.start_state_id, first.capability_id) == (second.start_state_id, second.capability_id):
                    continue
                if first.value_epoch != second.value_epoch:
                    continue
                counts[(first.hypothesis_id, second.hypothesis_id)].add((first_x, second_x))
    out = []
    for (first_id, second_id), pairs in sorted(counts.items()):
        if len(pairs) < 2:
            continue
        payload = {"first_hypothesis_id": first_id, "second_hypothesis_id": second_id}
        out.append(ActionOutcomeSuccessorCouplingCandidate(
            coupling_id="ACTION-COUPLING-" + _digest(payload)[:20],
            first_hypothesis_id=first_id, second_hypothesis_id=second_id,
            support=len(pairs), source_execution_pairs=tuple(sorted(pairs)),
        ))
    return tuple(out)


@dataclass(frozen=True)
class ActionOutcomeThreeLocusChainCandidate:
    """Proposal-only recurrent complete chain across three exact conflict modes."""
    chain_id: str
    hypothesis_ids: tuple[str, str, str]
    support: int
    source_execution_chains: tuple[tuple[str, str, str], ...]
    proposal_authority: str = "NONE"
    truth_authority: str = "NONE"
    causal_explanation_authority: str = "NONE"
    evidence_independence_authority: str = "NONE"
    model_set_authority: str = "NONE"

    def __post_init__(self) -> None:
        if len(self.hypothesis_ids) != 3 or len(set(self.hypothesis_ids)) != 3 or int(self.support) < 2:
            raise ValueError("INVALID_ACTION_OUTCOME_THREE_LOCUS_CHAIN")
        chains = tuple((str(a), str(b), str(c)) for a, b, c in self.source_execution_chains)
        if len(chains) != int(self.support) or len(set(chains)) != len(chains):
            raise ValueError("ACTION_OUTCOME_THREE_LOCUS_CHAIN_REPLAY_OR_SUPPORT_MISMATCH")
        object.__setattr__(self, "source_execution_chains", chains)
        if any(x != "NONE" for x in (
            self.proposal_authority, self.truth_authority, self.causal_explanation_authority,
            self.evidence_independence_authority, self.model_set_authority,
        )):
            raise ValueError("ACTION_OUTCOME_THREE_LOCUS_CHAIN_AUTHORITY_ESCALATION")

    def serializable(self) -> dict[str, Any]:
        d = asdict(self)
        d["hypothesis_ids"] = list(self.hypothesis_ids)
        d["source_execution_chains"] = [list(x) for x in self.source_execution_chains]
        return d


def discover_action_outcome_three_locus_chains(
    hypotheses: Iterable[ActionOutcomeAlternativeHypothesis],
    couplings: Iterable[ActionOutcomeSuccessorCouplingCandidate],
) -> tuple[ActionOutcomeThreeLocusChainCandidate, ...]:
    hs = {h.hypothesis_id: h for h in hypotheses}
    cs = tuple(couplings)
    support: dict[tuple[str, str, str], set[tuple[str, str, str]]] = defaultdict(set)
    for left in cs:
        for right in cs:
            if left.second_hypothesis_id != right.first_hypothesis_id:
                continue
            ids = (left.first_hypothesis_id, left.second_hypothesis_id, right.second_hypothesis_id)
            if len(set(ids)) != 3 or any(i not in hs for i in ids):
                continue
            loci = {
                (
                    hs[i].start_state_id, hs[i].capability_id, hs[i].capability_epoch,
                    hs[i].frame_epochs, hs[i].episode_schema_epochs, hs[i].value_epoch,
                    hs[i].topology_epochs, hs[i].coordination_epochs,
                    hs[i].evidence_premise_epochs, hs[i].evidence_premise_signatures,
                )
                for i in ids
            }
            if len(loci) != 3 or len({hs[i].value_epoch for i in ids}) != 1:
                continue
            right_by_first: dict[str, list[str]] = defaultdict(list)
            for b, c in right.source_execution_pairs:
                right_by_first[b].append(c)
            for a, b in left.source_execution_pairs:
                for c in right_by_first.get(b, ()):
                    support[ids].add((a, b, c))
    out = []
    for ids, chains in sorted(support.items()):
        if len(chains) < 2:
            continue
        out.append(ActionOutcomeThreeLocusChainCandidate(
            chain_id="ACTION-CHAIN3-" + _digest({"hypothesis_ids": ids})[:20],
            hypothesis_ids=ids, support=len(chains), source_execution_chains=tuple(sorted(chains)),
        ))
    return tuple(out)


@dataclass(frozen=True)
class ActionOutcomePredictiveCandidate:
    candidate_id: str
    start_state_id: str
    capability_id: str
    next_state_id: str
    value_effect: float
    support: int
    consistency: float
    source_evidence_ids: tuple[str, ...]
    capability_epoch: int
    frame_epochs: tuple[tuple[str, int], ...]
    episode_schema_epochs: tuple[tuple[str, int], ...]
    value_epoch: tuple[str, int]
    topology_epochs: tuple[tuple[str, int], ...] = ()
    coordination_epochs: tuple[tuple[str, int], ...] = ()
    evidence_premise_epochs: tuple[tuple[str, int], ...] = ()
    evidence_premise_signatures: tuple[tuple[str, str], ...] = ()
    authority: str = Authority.MODEL_OUTPUT_ONLY.value
    truth_authority: str = "NONE"
    causal_theorem_authority: str = "NONE"
    qualification_authority: str = "NONE"
    semantic_goal_authority: str = "NONE"

    def signature_payload(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("candidate_id", None)
        d["source_evidence_ids"] = []  # evidence identifies ancestry, not candidate semantics
        return d

    def digest(self) -> str:
        return _digest(self.signature_payload())

    def serializable(self) -> dict[str, Any]:
        d = asdict(self)
        for key in ("frame_epochs", "episode_schema_epochs", "topology_epochs", "coordination_epochs", "evidence_premise_epochs", "evidence_premise_signatures"):
            d[key] = [list(x) for x in d[key]]
        d["value_epoch"] = list(d["value_epoch"])
        d["candidate_sha256"] = self.digest()
        return d

    @classmethod
    def from_serializable(cls, d: dict[str, Any]) -> "ActionOutcomePredictiveCandidate":
        x = dict(d)
        x.pop("candidate_sha256", None)
        for key in ("frame_epochs", "episode_schema_epochs", "topology_epochs", "coordination_epochs", "evidence_premise_epochs"):
            x[key] = tuple((str(a), int(b)) for a, b in x.get(key, ()))
        x["evidence_premise_signatures"] = tuple((str(a), str(b)) for a, b in x.get("evidence_premise_signatures", ()))
        x["value_epoch"] = (str(x["value_epoch"][0]), int(x["value_epoch"][1]))
        x["source_evidence_ids"] = tuple(str(v) for v in x.get("source_evidence_ids", ()))
        return cls(**x)


@dataclass(frozen=True)
class ActionOutcomeRelationQualificationTicket:
    candidate_id: str
    candidate_sha256: str
    state: QualificationState
    qualifier_id: str
    reason: str
    qualification_evidence: tuple[EvidenceRef, ...]
    holdout_support: int
    holdout_accuracy: float


@dataclass(frozen=True)
class QualifiedActionOutcomePredictiveRelation:
    relation_id: str
    candidate_id: str
    candidate_sha256: str
    start_state_id: str
    capability_id: str
    next_state_id: str
    value_effect: float
    support: int
    consistency: float
    source_evidence_ids: tuple[str, ...]
    qualification_evidence_ids: tuple[str, ...]
    holdout_support: int
    holdout_accuracy: float
    capability_epoch: int
    frame_epochs: tuple[tuple[str, int], ...]
    episode_schema_epochs: tuple[tuple[str, int], ...]
    value_epoch: tuple[str, int]
    topology_epochs: tuple[tuple[str, int], ...] = ()
    coordination_epochs: tuple[tuple[str, int], ...] = ()
    evidence_premise_epochs: tuple[tuple[str, int], ...] = ()
    evidence_premise_signatures: tuple[tuple[str, str], ...] = ()
    authority: str = "EVIDENCE_BOUND_PREDICTIVE_RELATION_ONLY"
    truth_authority: str = "NONE"
    causal_theorem_authority: str = "NONE"
    execution_authority: str = "NONE"
    semantic_goal_authority: str = "NONE"

    def serializable(self) -> dict[str, Any]:
        d = asdict(self)
        for key in ("frame_epochs", "episode_schema_epochs", "topology_epochs", "coordination_epochs", "evidence_premise_epochs", "evidence_premise_signatures"):
            d[key] = [list(x) for x in d[key]]
        d["value_epoch"] = list(d["value_epoch"])
        return d

    @classmethod
    def from_serializable(cls, d: dict[str, Any]) -> "QualifiedActionOutcomePredictiveRelation":
        x = dict(d)
        for key in ("frame_epochs", "episode_schema_epochs", "topology_epochs", "coordination_epochs", "evidence_premise_epochs"):
            x[key] = tuple((str(a), int(b)) for a, b in x.get(key, ()))
        x["evidence_premise_signatures"] = tuple((str(a), str(b)) for a, b in x.get("evidence_premise_signatures", ()))
        x["value_epoch"] = (str(x["value_epoch"][0]), int(x["value_epoch"][1]))
        x["source_evidence_ids"] = tuple(str(v) for v in x.get("source_evidence_ids", ()))
        x["qualification_evidence_ids"] = tuple(str(v) for v in x.get("qualification_evidence_ids", ()))
        return cls(**x)

    def as_rehearsal_relation(self) -> RehearsalTransitionRelation | None:
        # Current Microseed rehearsal relation has one frame + one episode anchor per edge.
        # More complex ancestry remains unpromoted rather than silently collapsed.
        if len(self.frame_epochs) != 1 or len(self.episode_schema_epochs) != 1 or self.evidence_premise_epochs or self.evidence_premise_signatures:
            return None
        if len(self.topology_epochs) > 1 or len(self.coordination_epochs) > 1:
            return None
        return RehearsalTransitionRelation(
            state_id=self.start_state_id,
            capability_id=self.capability_id,
            next_state_id=self.next_state_id,
            value_effect=float(self.value_effect),
            support=int(self.support),
            consistency=float(self.consistency),
            source_evidence_ids=tuple(self.source_evidence_ids) + tuple(self.qualification_evidence_ids),
            capability_epoch=int(self.capability_epoch),
            frame_epoch=self.frame_epochs[0],
            episode_schema_epoch=self.episode_schema_epochs[0],
            topology_epoch=self.topology_epochs[0] if self.topology_epochs else None,
            coordination_epoch=self.coordination_epochs[0] if self.coordination_epochs else None,
            value_epoch=self.value_epoch,
        )

    def as_epistemic_alternative_relation(self) -> RehearsalTransitionRelation | None:
        """Lossless ephemeral edge for bounded epistemic alternative surfaces.

        Unlike the durable ordinary rehearsal bridge, this carrier preserves the
        MS1603+ evidence-premise ancestry and value coordinate.  It grants no new
        authority and is not persisted or admitted as a new predictive law.
        """
        if len(self.frame_epochs) != 1 or len(self.episode_schema_epochs) != 1:
            return None
        if len(self.topology_epochs) > 1 or len(self.coordination_epochs) > 1:
            return None
        return RehearsalTransitionRelation(
            state_id=self.start_state_id,capability_id=self.capability_id,next_state_id=self.next_state_id,
            value_effect=float(self.value_effect),support=int(self.support),consistency=float(self.consistency),
            source_evidence_ids=tuple(self.source_evidence_ids)+tuple(self.qualification_evidence_ids),
            capability_epoch=int(self.capability_epoch),frame_epoch=self.frame_epochs[0],
            episode_schema_epoch=self.episode_schema_epochs[0],
            topology_epoch=self.topology_epochs[0] if self.topology_epochs else None,
            coordination_epoch=self.coordination_epochs[0] if self.coordination_epochs else None,
            authority=self.authority,truth_authority=self.truth_authority,semantic_state_authority="NONE",
            evidence_premise_epochs=self.evidence_premise_epochs,
            evidence_premise_signatures=self.evidence_premise_signatures,value_epoch=self.value_epoch,
        )


class ActionOutcomeLearningRegistry:
    def __init__(self) -> None:
        self.candidates: dict[str, ActionOutcomePredictiveCandidate] = {}
        self.relations: dict[str, QualifiedActionOutcomePredictiveRelation] = {}
        self.currentness_witnesses: dict[str, Any] = {}
        self.replacement_links: dict[str, Any] = {}
        self.relation_replacement_lineage: dict[str, dict[str, str]] = {}
        # MS1453-1477 extends the existing v1.7+ projection lineage rather than
        # creating a second predictive-state registry. These are only bindings
        # from an already-qualified EpistemicProjectionRecord to learned action
        # outcome relations.
        self.projection_routing_candidates: dict[str, Any] = {}
        self.projection_conditioned_bindings: dict[str, Any] = {}

    def add_candidate(self, c: ActionOutcomePredictiveCandidate) -> None:
        if c.authority != Authority.MODEL_OUTPUT_ONLY.value or any(
            x != "NONE" for x in (c.truth_authority, c.causal_theorem_authority, c.qualification_authority, c.semantic_goal_authority)
        ):
            raise ValueError("ACTION_OUTCOME_CANDIDATE_AUTHORITY_ESCALATION")
        self.candidates.setdefault(c.candidate_id, c)

    def add_relation(self, r: QualifiedActionOutcomePredictiveRelation) -> None:
        if any(x != "NONE" for x in (r.truth_authority, r.causal_theorem_authority, r.execution_authority, r.semantic_goal_authority)):
            raise ValueError("ACTION_OUTCOME_RELATION_AUTHORITY_ESCALATION")
        self.relations[r.relation_id] = r

    def add_projection_routing_candidate(self, candidate: Any) -> None:
        if getattr(candidate, "authority", None) != Authority.MODEL_OUTPUT_ONLY.value or any(
            getattr(candidate, name, "NONE") != "NONE"
            for name in ("truth_authority", "semantic_regime_authority", "model_switch_authority", "qualification_authority")
        ):
            raise ValueError("PROJECTION_CONDITIONED_ROUTING_CANDIDATE_AUTHORITY_ESCALATION")
        self.projection_routing_candidates.setdefault(candidate.candidate_id, candidate)

    def add_projection_conditioned_binding(self, binding: Any) -> None:
        if any(
            getattr(binding, name, "NONE") != "NONE"
            for name in ("truth_authority", "semantic_regime_authority", "model_switch_authority", "execution_authority", "self_qualification_authority")
        ):
            raise ValueError("PROJECTION_CONDITIONED_ROUTING_BINDING_AUTHORITY_ESCALATION")
        self.projection_conditioned_bindings[binding.binding_id] = binding


def assemble_single_conflict_epistemic_relation_sets(
    hypotheses: Iterable[ActionOutcomeAlternativeHypothesis],
    *, background_relations: Iterable[RehearsalTransitionRelation] = (),
) -> tuple[tuple[RehearsalTransitionRelation, ...], ...]:
    """Project exactly one recurrent outcome conflict into ephemeral model alternatives.

    This function deliberately refuses multiple conflict loci.  Without evidence
    coupling choices across loci, a Cartesian product would invent coherent worlds
    that the experience does not contain.  Returned edges remain proposal-only and
    gain no truth, qualification, causal, independence, or execution authority.
    """
    rows=tuple(hypotheses)
    if len(rows)<2:
        return ()
    groups: dict[tuple[Any, ...], list[ActionOutcomeAlternativeHypothesis]] = defaultdict(list)
    for h in rows:
        key=(
            h.start_state_id,h.capability_id,int(h.capability_epoch),h.frame_epochs,
            h.episode_schema_epochs,h.value_epoch,h.topology_epochs,h.coordination_epochs,
            h.evidence_premise_epochs,h.evidence_premise_signatures,
        )
        groups[key].append(h)
    if len(groups)!=1:
        return ()
    key, modes=next(iter(groups.items()))
    if len(modes)<2 or len(key[3])!=1 or len(key[4])!=1 or len(key[6])>1 or len(key[7])>1:
        return ()
    mode_keys={(h.next_state_id,round(float(h.value_effect),3)) for h in modes}
    if len(mode_keys)!=len(modes):
        return ()
    background=tuple(background_relations)
    conflict_slot=(key[0],key[1])
    seen=set()
    for rel in background:
        slot=(rel.state_id,rel.capability_id)
        if slot==conflict_slot or slot in seen:
            return ()
        seen.add(slot)
        if rel.value_epoch is None or rel.value_epoch != key[5]:
            return ()
    out=[]
    for h in sorted(modes,key=lambda x:(x.next_state_id,round(float(x.value_effect),3),x.hypothesis_id)):
        conflict_edge=RehearsalTransitionRelation(
            state_id=h.start_state_id,capability_id=h.capability_id,next_state_id=h.next_state_id,
            value_effect=float(h.value_effect),support=int(h.mode_support),
            consistency=float(h.mode_support)/float(h.group_support),
            source_evidence_ids=tuple(h.source_evidence_ids),capability_epoch=int(h.capability_epoch),
            frame_epoch=h.frame_epochs[0],episode_schema_epoch=h.episode_schema_epochs[0],
            topology_epoch=h.topology_epochs[0] if h.topology_epochs else None,
            coordination_epoch=h.coordination_epochs[0] if h.coordination_epochs else None,
            authority="PROPOSAL_ONLY_RELATIONAL_ALTERNATIVE",truth_authority="NONE",
            semantic_state_authority="NONE",evidence_premise_epochs=h.evidence_premise_epochs,
            evidence_premise_signatures=h.evidence_premise_signatures,value_epoch=h.value_epoch,
        )
        out.append(tuple(background)+(conflict_edge,))
    return tuple(out)



def assemble_successor_coupled_epistemic_relation_sets(
    hypotheses: Iterable[ActionOutcomeAlternativeHypothesis],
    couplings: Iterable[ActionOutcomeSuccessorCouplingCandidate],
    *, background_relations: Iterable[RehearsalTransitionRelation] = (),
) -> tuple[tuple[RehearsalTransitionRelation, ...], ...]:
    """Assemble exactly two recurrent conflict loci from observed successor coupling.

    A complete one-to-one coupling between the modes at two distinct action slots can
    support bounded paired alternatives. Missing, duplicate, branching, or cross-slot
    coupling abstains rather than creating a Cartesian product. Returned relations are
    proposal-only and inherit no truth, qualification, causal, independence, model-set,
    or execution authority.
    """
    hs = tuple(hypotheses)
    cs = tuple(couplings)
    by_id = {h.hypothesis_id: h for h in hs}

    def locus_key(h: ActionOutcomeAlternativeHypothesis) -> tuple[Any, ...]:
        return (
            h.start_state_id, h.capability_id, int(h.capability_epoch), h.frame_epochs,
            h.episode_schema_epochs, h.value_epoch, h.topology_epochs, h.coordination_epochs,
            h.evidence_premise_epochs, h.evidence_premise_signatures,
        )

    loci: dict[tuple[Any, ...], list[ActionOutcomeAlternativeHypothesis]] = defaultdict(list)
    for h in hs:
        loci[locus_key(h)].append(h)
    conflict_loci = {key: rows for key, rows in loci.items() if len(rows) >= 2}
    if len(conflict_loci) != 2 or not cs:
        return ()
    locus_keys = set(conflict_loci)
    pairs = []
    for c in cs:
        first = by_id.get(c.first_hypothesis_id)
        second = by_id.get(c.second_hypothesis_id)
        if first is None or second is None:
            return ()
        first_locus = locus_key(first)
        second_locus = locus_key(second)
        if first_locus == second_locus or {first_locus, second_locus} != locus_keys:
            return ()
        if first.value_epoch != second.value_epoch:
            return ()
        pairs.append((first, second))
    first_counts = Counter(x.hypothesis_id for x, _ in pairs)
    second_counts = Counter(y.hypothesis_id for _, y in pairs)
    oriented_first = {x.hypothesis_id for x, _ in pairs}
    oriented_second = {y.hypothesis_id for _, y in pairs}
    locus_a, locus_b = tuple(locus_keys)
    ids_a = {h.hypothesis_id for h in conflict_loci[locus_a]}
    ids_b = {h.hypothesis_id for h in conflict_loci[locus_b]}
    orientation_ok = (oriented_first == ids_a and oriented_second == ids_b) or (oriented_first == ids_b and oriented_second == ids_a)
    if not orientation_ok or any(v != 1 for v in first_counts.values()) or any(v != 1 for v in second_counts.values()):
        return ()
    if len(pairs) != len(conflict_loci[locus_a]) or len(pairs) != len(conflict_loci[locus_b]):
        return ()

    def relation(h: ActionOutcomeAlternativeHypothesis) -> RehearsalTransitionRelation | None:
        if len(h.frame_epochs) != 1 or len(h.episode_schema_epochs) != 1 or len(h.topology_epochs) > 1 or len(h.coordination_epochs) > 1:
            return None
        return RehearsalTransitionRelation(
            state_id=h.start_state_id, capability_id=h.capability_id, next_state_id=h.next_state_id,
            value_effect=float(h.value_effect), support=int(h.mode_support),
            consistency=float(h.mode_support) / float(h.group_support),
            source_evidence_ids=tuple(h.source_evidence_ids), capability_epoch=int(h.capability_epoch),
            frame_epoch=h.frame_epochs[0], episode_schema_epoch=h.episode_schema_epochs[0],
            topology_epoch=h.topology_epochs[0] if h.topology_epochs else None,
            coordination_epoch=h.coordination_epochs[0] if h.coordination_epochs else None,
            authority="PROPOSAL_ONLY_RELATIONAL_ALTERNATIVE", truth_authority="NONE",
            semantic_state_authority="NONE", evidence_premise_epochs=h.evidence_premise_epochs,
            evidence_premise_signatures=h.evidence_premise_signatures, value_epoch=h.value_epoch,
        )

    background = tuple(background_relations)
    paired_slots = {(h.start_state_id, h.capability_id) for pair in pairs for h in pair}
    seen_background = set()
    required_value_epoch = pairs[0][0].value_epoch if pairs else None
    if required_value_epoch is None:
        return ()
    for rel in background:
        slot = (rel.state_id, rel.capability_id)
        if slot in paired_slots or slot in seen_background:
            return ()
        seen_background.add(slot)
        if rel.value_epoch is None or rel.value_epoch != required_value_epoch:
            return ()

    out = []
    for first, second in sorted(pairs, key=lambda p: (p[0].hypothesis_id, p[1].hypothesis_id)):
        a = relation(first)
        b = relation(second)
        if a is None or b is None:
            return ()
        out.append((a, b) + background)
    return tuple(out)


def assemble_three_locus_chain_epistemic_relation_sets(
    hypotheses: Iterable[ActionOutcomeAlternativeHypothesis],
    chains: Iterable[ActionOutcomeThreeLocusChainCandidate],
    *, background_relations: Iterable[RehearsalTransitionRelation] = (),
) -> tuple[tuple[RehearsalTransitionRelation, ...], ...]:
    """Assemble exactly three conflict loci only from recurrent complete chains."""
    hs = tuple(hypotheses)
    cs = tuple(chains)
    by_id = {h.hypothesis_id: h for h in hs}
    if not cs:
        return ()

    def locus_key(h: ActionOutcomeAlternativeHypothesis) -> tuple[Any, ...]:
        return (
            h.start_state_id, h.capability_id, int(h.capability_epoch), h.frame_epochs,
            h.episode_schema_epochs, h.value_epoch, h.topology_epochs, h.coordination_epochs,
            h.evidence_premise_epochs, h.evidence_premise_signatures,
        )

    loci: dict[tuple[Any, ...], list[ActionOutcomeAlternativeHypothesis]] = defaultdict(list)
    for h in hs:
        loci[locus_key(h)].append(h)
    conflicts = {k: v for k, v in loci.items() if len(v) >= 2}
    if len(conflicts) != 3:
        return ()
    conflict_keys = set(conflicts)
    seen_ids = Counter()
    order = None
    resolved = []
    for c in cs:
        if any(i not in by_id for i in c.hypothesis_ids):
            return ()
        triple = tuple(by_id[i] for i in c.hypothesis_ids)
        keys = tuple(locus_key(h) for h in triple)
        if len(set(keys)) != 3 or set(keys) != conflict_keys:
            return ()
        if order is None:
            order = keys
        elif keys != order:
            return ()
        if len({h.value_epoch for h in triple}) != 1:
            return ()
        for h in triple:
            seen_ids[h.hypothesis_id] += 1
        resolved.append(triple)
    expected = {h.hypothesis_id for rows in conflicts.values() for h in rows}
    if set(seen_ids) != expected or any(v != 1 for v in seen_ids.values()):
        return ()
    if any(len(rows) != len(cs) for rows in conflicts.values()):
        return ()

    def relation(h: ActionOutcomeAlternativeHypothesis) -> RehearsalTransitionRelation | None:
        if len(h.frame_epochs) != 1 or len(h.episode_schema_epochs) != 1 or len(h.topology_epochs) > 1 or len(h.coordination_epochs) > 1:
            return None
        return RehearsalTransitionRelation(
            state_id=h.start_state_id, capability_id=h.capability_id, next_state_id=h.next_state_id,
            value_effect=float(h.value_effect), support=int(h.mode_support),
            consistency=float(h.mode_support) / float(h.group_support),
            source_evidence_ids=tuple(h.source_evidence_ids), capability_epoch=int(h.capability_epoch),
            frame_epoch=h.frame_epochs[0], episode_schema_epoch=h.episode_schema_epochs[0],
            topology_epoch=h.topology_epochs[0] if h.topology_epochs else None,
            coordination_epoch=h.coordination_epochs[0] if h.coordination_epochs else None,
            authority="PROPOSAL_ONLY_RELATIONAL_ALTERNATIVE", truth_authority="NONE",
            semantic_state_authority="NONE", evidence_premise_epochs=h.evidence_premise_epochs,
            evidence_premise_signatures=h.evidence_premise_signatures, value_epoch=h.value_epoch,
        )

    background = tuple(background_relations)
    conflict_slots = {(h.start_state_id, h.capability_id) for triple in resolved for h in triple}
    required_value_epoch = resolved[0][0].value_epoch if resolved else None
    seen_background = set()
    if required_value_epoch is None:
        return ()
    for rel in background:
        slot = (rel.state_id, rel.capability_id)
        if slot in conflict_slots or slot in seen_background:
            return ()
        seen_background.add(slot)
        if rel.value_epoch is None or rel.value_epoch != required_value_epoch:
            return ()

    out = []
    for triple in sorted(resolved, key=lambda t: tuple(h.hypothesis_id for h in t)):
        model = tuple(relation(h) for h in triple)
        if any(x is None for x in model):
            return ()
        out.append(model + background)
    return tuple(out)


def nominate_action_outcome_candidates(
    experiences: Iterable[ActionOutcomeExperience], *, min_support: int = 8, min_consistency: float = 0.78,
    effect_round_digits: int = 3,
) -> tuple[ActionOutcomePredictiveCandidate, ...]:
    if min_support < 2:
        raise ValueError("ACTION_OUTCOME_MIN_SUPPORT_MUST_EXCEED_ONE")
    if not (0.5 < float(min_consistency) <= 1.0):
        raise ValueError("ACTION_OUTCOME_INVALID_CONSISTENCY_GATE")
    rows = tuple(experiences)
    groups: dict[tuple[Any, ...], list[ActionOutcomeExperience]] = defaultdict(list)
    for r in rows:
        key = (
            r.start_state_id, r.capability_id, int(r.capability_epoch), r.frame_epochs,
            r.episode_schema_epochs, r.value_epoch, r.topology_epochs, r.coordination_epochs, r.evidence_premise_epochs, r.evidence_premise_signatures,
        )
        groups[key].append(r)
    out: list[ActionOutcomePredictiveCandidate] = []
    for key, rs in groups.items():
        if len(rs) < min_support:
            continue
        buckets = Counter((r.actual_next_state_id, round(float(r.actual_value_effect), effect_round_digits)) for r in rs)
        (next_state, effect), count = sorted(buckets.items(), key=lambda kv: (-kv[1], kv[0]))[0]
        consistency = count / len(rs)
        if consistency < min_consistency:
            continue
        payload = {
            "start_state_id": key[0], "capability_id": key[1], "next_state_id": next_state,
            "value_effect": float(effect), "capability_epoch": key[2], "frame_epochs": key[3],
            "episode_schema_epochs": key[4], "value_epoch": key[5], "topology_epochs": key[6],
            "coordination_epochs": key[7], "evidence_premise_epochs": key[8], "evidence_premise_signatures": key[9],
        }
        cid = "ACTION-LAW-CAND-" + _digest(payload)[:20]
        out.append(ActionOutcomePredictiveCandidate(
            candidate_id=cid, start_state_id=key[0], capability_id=key[1], next_state_id=next_state,
            value_effect=float(effect), support=len(rs), consistency=consistency,
            source_evidence_ids=tuple(sorted(r.evidence_id for r in rs)), capability_epoch=key[2],
            frame_epochs=key[3], episode_schema_epochs=key[4], value_epoch=key[5],
            topology_epochs=key[6], coordination_epochs=key[7], evidence_premise_epochs=key[8], evidence_premise_signatures=key[9],
        ))
    return tuple(sorted(out, key=lambda c: (c.start_state_id, c.capability_id, -c.consistency, c.candidate_id)))


def _qualification_row(ledger: EvidenceLedger, ref: EvidenceRef) -> dict[str, Any] | None:
    row = ledger.get(ref.evidence_id)
    if row is None or row["sha256"] != ref.sha256:
        return None
    payload = row.get("payload")
    if not isinstance(payload, dict) or payload.get("kind") != "ACTION_OUTCOME_HOLDOUT":
        return None
    return payload


def evaluate_action_outcome_holdout(
    candidate: ActionOutcomePredictiveCandidate, refs: Iterable[EvidenceRef], ledger: EvidenceLedger,
) -> tuple[int, float]:
    usable = []
    for ref in refs:
        p = _qualification_row(ledger, ref)
        if p is None:
            continue
        if (
            str(p.get("start_state_id")) == candidate.start_state_id
            and str(p.get("capability_id")) == candidate.capability_id
            and int(p.get("capability_epoch", -1)) == candidate.capability_epoch
            and tuple((str(a), int(b)) for a, b in p.get("frame_epochs", ())) == candidate.frame_epochs
            and tuple((str(a), int(b)) for a, b in p.get("episode_schema_epochs", ())) == candidate.episode_schema_epochs
            and (str(p.get("value_epoch", ["", -1])[0]), int(p.get("value_epoch", ["", -1])[1])) == candidate.value_epoch
            and tuple((str(a), int(b)) for a, b in p.get("topology_epochs", ())) == candidate.topology_epochs
            and tuple((str(a), int(b)) for a, b in p.get("coordination_epochs", ())) == candidate.coordination_epochs
            and tuple((str(a), int(b)) for a, b in p.get("evidence_premise_epochs", ())) == candidate.evidence_premise_epochs
            and tuple((str(a), str(b)) for a, b in p.get("evidence_premise_signatures", ())) == candidate.evidence_premise_signatures
        ):
            usable.append(p)
    if not usable:
        return 0, 0.0
    matches = sum(
        str(p.get("actual_next_state_id")) == candidate.next_state_id
        and round(float(p.get("actual_value_effect")), 3) == round(float(candidate.value_effect), 3)
        for p in usable
    )
    return len(usable), matches / len(usable)


class ExternalActionOutcomeRelationQualifier:
    """Harness-side qualifier. It cannot be instantiated as Microseed authority."""
    def __init__(self, ledger: EvidenceLedger, *, qualifier_id: str = "HSP-EXTERNAL-ACTION-OUTCOME-QUALIFIER"):
        if not qualifier_id or qualifier_id.upper().startswith("MICROSEED"):
            raise ValueError("qualifier_id must identify an external qualification boundary")
        self.ledger = ledger
        self.qualifier_id = qualifier_id

    def qualify(
        self, candidate: ActionOutcomePredictiveCandidate, *, qualification_evidence: Iterable[EvidenceRef],
        min_support: int = 12, min_accuracy: float = 0.80,
    ) -> ActionOutcomeRelationQualificationTicket:
        refs = tuple(qualification_evidence)
        decision = FixedQualifier(self.ledger).decide(refs, Authority.REFERENCE_ONLY)
        support, accuracy = evaluate_action_outcome_holdout(candidate, refs, self.ledger)
        state = decision.state
        reason = decision.reason
        if set(candidate.source_evidence_ids) & {r.evidence_id for r in refs}:
            state, reason = QualificationState.REJECTED, "PROPOSAL_QUALIFICATION_EVIDENCE_OVERLAP"
        elif state in {QualificationState.SHADOW_QUALIFIED, QualificationState.QUALIFIED}:
            if support < int(min_support):
                state, reason = QualificationState.REJECTED, "INSUFFICIENT_INDEPENDENT_HOLDOUT"
            elif accuracy < float(min_accuracy):
                state, reason = QualificationState.REJECTED, f"HOLDOUT_ACCURACY_BELOW_BOUND:{accuracy:.6f}"
            else:
                reason = f"INDEPENDENT_HOLDOUT_QUALIFIED:{accuracy:.6f}"
        return ActionOutcomeRelationQualificationTicket(
            candidate_id=candidate.candidate_id, candidate_sha256=candidate.digest(), state=state,
            qualifier_id=self.qualifier_id, reason=reason, qualification_evidence=refs,
            holdout_support=support, holdout_accuracy=accuracy,
        )


def validate_external_action_outcome_ticket(
    candidate: ActionOutcomePredictiveCandidate, ticket: ActionOutcomeRelationQualificationTicket,
    ledger: EvidenceLedger, *, min_support: int = 12, min_accuracy: float = 0.80,
) -> tuple[bool, str]:
    if not ticket.qualifier_id or ticket.qualifier_id.upper().startswith("MICROSEED"):
        return False, "QUALIFIER_NOT_EXTERNAL"
    if ticket.candidate_id != candidate.candidate_id or ticket.candidate_sha256 != candidate.digest():
        return False, "CANDIDATE_BINDING_MISMATCH"
    if not ticket.qualification_evidence:
        return False, "NO_QUALIFICATION_EVIDENCE"
    if set(candidate.source_evidence_ids) & {r.evidence_id for r in ticket.qualification_evidence}:
        return False, "PROPOSAL_QUALIFICATION_EVIDENCE_OVERLAP"
    decision = FixedQualifier(ledger).decide(ticket.qualification_evidence, Authority.REFERENCE_ONLY)
    support, accuracy = evaluate_action_outcome_holdout(candidate, ticket.qualification_evidence, ledger)
    if support != ticket.holdout_support or abs(accuracy - ticket.holdout_accuracy) > 1e-12:
        return False, "HOLDOUT_METRICS_MISMATCH"
    if support < int(min_support):
        return False, "INSUFFICIENT_INDEPENDENT_HOLDOUT"
    if accuracy < float(min_accuracy):
        return False, "HOLDOUT_ACCURACY_BELOW_BOUND"
    if ticket.state not in {QualificationState.SHADOW_QUALIFIED, QualificationState.QUALIFIED}:
        return False, f"NOT_ADMISSIBLE:{ticket.state.value}"
    if decision.state not in {QualificationState.SHADOW_QUALIFIED, QualificationState.QUALIFIED}:
        return False, "QUALIFICATION_EVIDENCE_NOT_SUPPORTIVE"
    return True, "VALID_EXTERNAL_ACTION_OUTCOME_QUALIFICATION"


@dataclass(frozen=True)
class ProjectionConditionedRelationCandidate:
    """Proposal-only binding from one already-qualified opaque projection to learned relations.

    The projection is the selector substrate. This object does not discover a
    second state system and carries no semantic regime, truth, switch, or
    qualification authority. It only proposes which existing predictive relation
    should be used for an action inside one explicitly bounded task/channel/horizon
    scope, with sparse bucket-specific overrides over a default relation map.
    """

    candidate_id: str
    projection_id: str
    projection_epoch: int
    projection_signature_sha256: str
    task_id: str
    action_ids: tuple[str, ...]
    channel_ids: tuple[str, ...]
    horizon: int
    default_action_relations: tuple[tuple[str, str], ...]
    bucket_action_overrides: tuple[tuple[str, str, str], ...]
    source_evidence_ids: tuple[str, ...]
    authority: str = Authority.MODEL_OUTPUT_ONLY.value
    truth_authority: str = "NONE"
    semantic_regime_authority: str = "NONE"
    model_switch_authority: str = "NONE"
    qualification_authority: str = "NONE"

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.projection_id or int(self.projection_epoch) < 0:
            raise ValueError("INVALID_PROJECTION_CONDITIONED_ROUTING_CANDIDATE")
        if len(self.projection_signature_sha256) != 64:
            raise ValueError("PROJECTION_CONDITIONED_ROUTING_REQUIRES_PROJECTION_SIGNATURE")
        if not self.task_id or not self.action_ids or not self.channel_ids or int(self.horizon) < 1:
            raise ValueError("PROJECTION_CONDITIONED_ROUTING_REQUIRES_BOUNDED_SCOPE")
        if len(set(self.action_ids)) != len(self.action_ids) or len(set(self.channel_ids)) != len(self.channel_ids):
            raise ValueError("PROJECTION_CONDITIONED_ROUTING_SCOPE_DUPLICATE")
        defaults = dict(self.default_action_relations)
        if set(defaults) != set(self.action_ids):
            raise ValueError("PROJECTION_CONDITIONED_ROUTING_REQUIRES_DEFAULT_FOR_EACH_ACTION")
        if len(defaults) != len(self.default_action_relations):
            raise ValueError("PROJECTION_CONDITIONED_ROUTING_DUPLICATE_DEFAULT")
        seen: set[tuple[str, str]] = set()
        for bucket, action, relation_id in self.bucket_action_overrides:
            if not bucket or action not in self.action_ids or not relation_id:
                raise ValueError("INVALID_PROJECTION_CONDITIONED_ROUTING_OVERRIDE")
            key = (bucket, action)
            if key in seen:
                raise ValueError("PROJECTION_CONDITIONED_ROUTING_DUPLICATE_OVERRIDE")
            seen.add(key)
        if self.authority != Authority.MODEL_OUTPUT_ONLY.value or any(
            x != "NONE" for x in (
                self.truth_authority, self.semantic_regime_authority,
                self.model_switch_authority, self.qualification_authority,
            )
        ):
            raise ValueError("PROJECTION_CONDITIONED_ROUTING_CANDIDATE_AUTHORITY_ESCALATION")
        object.__setattr__(self, "projection_epoch", int(self.projection_epoch))
        object.__setattr__(self, "horizon", int(self.horizon))
        object.__setattr__(self, "action_ids", tuple(str(x) for x in self.action_ids))
        object.__setattr__(self, "channel_ids", tuple(str(x) for x in self.channel_ids))
        object.__setattr__(self, "default_action_relations", tuple((str(a), str(r)) for a, r in self.default_action_relations))
        object.__setattr__(self, "bucket_action_overrides", tuple((str(b), str(a), str(r)) for b, a, r in self.bucket_action_overrides))
        object.__setattr__(self, "source_evidence_ids", tuple(str(x) for x in self.source_evidence_ids))

    def relation_id_for(self, bucket_id: str, action_id: str) -> str | None:
        for bucket, action, relation_id in self.bucket_action_overrides:
            if bucket == bucket_id and action == action_id:
                return relation_id
        return dict(self.default_action_relations).get(action_id)

    def relation_ids(self) -> tuple[str, ...]:
        return tuple(sorted(set(dict(self.default_action_relations).values()) | {r for _, _, r in self.bucket_action_overrides}))

    def signature_payload(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("candidate_id", None)
        d["source_evidence_ids"] = []
        return d

    def digest(self) -> str:
        return _digest(self.signature_payload())

    def serializable(self) -> dict[str, Any]:
        d = asdict(self)
        d["action_ids"] = list(self.action_ids)
        d["channel_ids"] = list(self.channel_ids)
        d["default_action_relations"] = [list(x) for x in self.default_action_relations]
        d["bucket_action_overrides"] = [list(x) for x in self.bucket_action_overrides]
        d["source_evidence_ids"] = list(self.source_evidence_ids)
        d["candidate_sha256"] = self.digest()
        return d

    @classmethod
    def from_serializable(cls, d: dict[str, Any]) -> "ProjectionConditionedRelationCandidate":
        x = dict(d)
        x.pop("candidate_sha256", None)
        x["action_ids"] = tuple(str(v) for v in x.get("action_ids", ()))
        x["channel_ids"] = tuple(str(v) for v in x.get("channel_ids", ()))
        x["default_action_relations"] = tuple((str(a), str(r)) for a, r in x.get("default_action_relations", ()))
        x["bucket_action_overrides"] = tuple((str(b), str(a), str(r)) for b, a, r in x.get("bucket_action_overrides", ()))
        x["source_evidence_ids"] = tuple(str(v) for v in x.get("source_evidence_ids", ()))
        return cls(**x)


@dataclass(frozen=True)
class ProjectionConditionedRelationQualificationTicket:
    candidate_id: str
    candidate_sha256: str
    state: QualificationState
    qualifier_id: str
    reason: str
    qualification_evidence: tuple[EvidenceRef, ...]
    holdout_support: int
    holdout_accuracy: float
    holdout_coverage: float
    qualified_bucket_ids: tuple[str, ...]


@dataclass(frozen=True)
class QualifiedProjectionConditionedRelationBinding:
    binding_id: str
    candidate_id: str
    candidate_sha256: str
    projection_id: str
    projection_epoch: int
    projection_signature_sha256: str
    task_id: str
    action_ids: tuple[str, ...]
    channel_ids: tuple[str, ...]
    horizon: int
    default_action_relations: tuple[tuple[str, str], ...]
    bucket_action_overrides: tuple[tuple[str, str, str], ...]
    source_evidence_ids: tuple[str, ...]
    qualification_evidence_ids: tuple[str, ...]
    holdout_support: int
    holdout_accuracy: float
    holdout_coverage: float
    qualified_bucket_ids: tuple[str, ...]
    authority: str = "EVIDENCE_BOUND_PROJECTION_CONDITIONED_RELATION_ROUTING_ONLY"
    truth_authority: str = "NONE"
    semantic_regime_authority: str = "NONE"
    model_switch_authority: str = "NONE"
    execution_authority: str = "NONE"
    self_qualification_authority: str = "NONE"

    def __post_init__(self) -> None:
        if any(x != "NONE" for x in (
            self.truth_authority, self.semantic_regime_authority, self.model_switch_authority,
            self.execution_authority, self.self_qualification_authority,
        )):
            raise ValueError("PROJECTION_CONDITIONED_ROUTING_BINDING_AUTHORITY_ESCALATION")
        object.__setattr__(self, "projection_epoch", int(self.projection_epoch))
        object.__setattr__(self, "horizon", int(self.horizon))
        object.__setattr__(self, "action_ids", tuple(str(x) for x in self.action_ids))
        object.__setattr__(self, "channel_ids", tuple(str(x) for x in self.channel_ids))
        object.__setattr__(self, "default_action_relations", tuple((str(a), str(r)) for a, r in self.default_action_relations))
        object.__setattr__(self, "bucket_action_overrides", tuple((str(b), str(a), str(r)) for b, a, r in self.bucket_action_overrides))
        object.__setattr__(self, "source_evidence_ids", tuple(str(x) for x in self.source_evidence_ids))
        object.__setattr__(self, "qualification_evidence_ids", tuple(str(x) for x in self.qualification_evidence_ids))
        object.__setattr__(self, "qualified_bucket_ids", tuple(sorted(set(str(x) for x in self.qualified_bucket_ids))))
        if not self.qualified_bucket_ids:
            raise ValueError("PROJECTION_CONDITIONED_ROUTING_REQUIRES_QUALIFIED_BUCKET_SUPPORT")

    def relation_id_for(self, bucket_id: str, action_id: str) -> str | None:
        for bucket, action, relation_id in self.bucket_action_overrides:
            if bucket == bucket_id and action == action_id:
                return relation_id
        return dict(self.default_action_relations).get(action_id)

    def relation_ids(self) -> tuple[str, ...]:
        return tuple(sorted(set(dict(self.default_action_relations).values()) | {r for _, _, r in self.bucket_action_overrides}))

    def serializable(self) -> dict[str, Any]:
        d = asdict(self)
        d["action_ids"] = list(self.action_ids)
        d["channel_ids"] = list(self.channel_ids)
        d["default_action_relations"] = [list(x) for x in self.default_action_relations]
        d["bucket_action_overrides"] = [list(x) for x in self.bucket_action_overrides]
        d["source_evidence_ids"] = list(self.source_evidence_ids)
        d["qualification_evidence_ids"] = list(self.qualification_evidence_ids)
        d["qualified_bucket_ids"] = list(self.qualified_bucket_ids)
        return d

    @classmethod
    def from_serializable(cls, d: dict[str, Any]) -> "QualifiedProjectionConditionedRelationBinding":
        x = dict(d)
        x["action_ids"] = tuple(str(v) for v in x.get("action_ids", ()))
        x["channel_ids"] = tuple(str(v) for v in x.get("channel_ids", ()))
        x["default_action_relations"] = tuple((str(a), str(r)) for a, r in x.get("default_action_relations", ()))
        x["bucket_action_overrides"] = tuple((str(b), str(a), str(r)) for b, a, r in x.get("bucket_action_overrides", ()))
        x["source_evidence_ids"] = tuple(str(v) for v in x.get("source_evidence_ids", ()))
        x["qualification_evidence_ids"] = tuple(str(v) for v in x.get("qualification_evidence_ids", ()))
        x["qualified_bucket_ids"] = tuple(str(v) for v in x.get("qualified_bucket_ids", ()))
        return cls(**x)


def projection_conditioned_hypothesis_surface_digest(
    binding: QualifiedProjectionConditionedRelationBinding,
    relations: Mapping[str, QualifiedActionOutcomePredictiveRelation],
) -> str:
    """Content identity for one bounded qualified projection-conditioned model surface.

    Qualification/source evidence identify justification, not hypothesis semantics.
    The digest therefore binds projection content, bounded routing semantics, and
    the candidate semantic identity of every routed relation without changing merely
    because additional supporting evidence was accumulated.  It grants no truth,
    currentness, model-switch, or deficit-transition authority.
    """
    relation_semantics: list[tuple[str, str]] = []
    for relation_id in binding.relation_ids():
        relation = relations.get(relation_id)
        if relation is None:
            raise ValueError(f"PROJECTION_CONDITIONED_HYPOTHESIS_RELATION_NOT_FOUND:{relation_id}")
        relation_semantics.append((str(relation_id), str(relation.candidate_sha256)))
    payload = {
        "projection_id": binding.projection_id,
        "projection_epoch": int(binding.projection_epoch),
        "projection_signature_sha256": binding.projection_signature_sha256,
        "routing_candidate_sha256": binding.candidate_sha256,
        "task_id": binding.task_id,
        "action_ids": list(binding.action_ids),
        "channel_ids": list(binding.channel_ids),
        "horizon": int(binding.horizon),
        "default_action_relations": [list(x) for x in binding.default_action_relations],
        "bucket_action_overrides": [list(x) for x in binding.bucket_action_overrides],
        "qualified_bucket_ids": list(binding.qualified_bucket_ids),
        "relation_candidate_semantics": [list(x) for x in sorted(relation_semantics)],
    }
    return _digest(payload)


def evaluate_projection_conditioned_relation_holdout(
    candidate: ProjectionConditionedRelationCandidate,
    refs: Iterable[EvidenceRef],
    ledger: EvidenceLedger,
    relations: Mapping[str, QualifiedActionOutcomePredictiveRelation],
) -> tuple[int, float, float]:
    refs = tuple(refs)
    relevant = []
    correct = 0
    covered = 0
    for ref in refs:
        row = ledger.get(ref.evidence_id)
        if row is None or row["sha256"] != ref.sha256:
            continue
        payload = row.get("payload", {})
        if payload.get("kind") != "PROJECTION_CONDITIONED_ACTION_OUTCOME_HOLDOUT":
            continue
        if str(payload.get("projection_id", "")) != candidate.projection_id:
            continue
        if int(payload.get("projection_epoch", -1)) != candidate.projection_epoch:
            continue
        if str(payload.get("projection_signature_sha256", "")) != candidate.projection_signature_sha256:
            continue
        if str(payload.get("task_id", "")) != candidate.task_id:
            continue
        if int(payload.get("horizon", -1)) != candidate.horizon:
            continue
        action_id = str(payload.get("action_id", ""))
        channel_id = str(payload.get("channel_id", ""))
        bucket_id = str(payload.get("projection_bucket_id", ""))
        if action_id not in candidate.action_ids or channel_id not in candidate.channel_ids or not bucket_id:
            continue
        relevant.append(payload)
        relation_id = candidate.relation_id_for(bucket_id, action_id)
        relation = relations.get(relation_id or "")
        if relation is None:
            continue
        covered += 1
        observed = (
            str(payload.get("actual_next_state_id", "")),
            round(float(payload.get("actual_value_effect", 0.0)), 3),
        )
        predicted = (relation.next_state_id, round(float(relation.value_effect), 3))
        if observed == predicted:
            correct += 1
    support = len(relevant)
    accuracy = correct / support if support else 0.0
    coverage = covered / support if support else 0.0
    return support, accuracy, coverage


def projection_conditioned_holdout_bucket_ids(
    candidate: ProjectionConditionedRelationCandidate, refs: Iterable[EvidenceRef], ledger: EvidenceLedger
) -> tuple[str, ...]:
    buckets: set[str] = set()
    for ref in refs:
        row=ledger.get(ref.evidence_id)
        if row is None or row["sha256"] != ref.sha256:
            continue
        payload=row.get("payload",{})
        if payload.get("kind") != "PROJECTION_CONDITIONED_ACTION_OUTCOME_HOLDOUT":
            continue
        if str(payload.get("projection_id","")) != candidate.projection_id or int(payload.get("projection_epoch",-1)) != candidate.projection_epoch:
            continue
        if str(payload.get("projection_signature_sha256","")) != candidate.projection_signature_sha256:
            continue
        if str(payload.get("task_id","")) != candidate.task_id or int(payload.get("horizon",-1)) != candidate.horizon:
            continue
        if str(payload.get("action_id","")) not in candidate.action_ids or str(payload.get("channel_id","")) not in candidate.channel_ids:
            continue
        bucket=str(payload.get("projection_bucket_id",""))
        if bucket:
            buckets.add(bucket)
    return tuple(sorted(buckets))


class ExternalProjectionConditionedRelationQualifier:
    """Harness-side qualifier for projection-conditioned relation routing.

    It does not qualify the projection or the relations themselves. Those are
    pre-existing independently qualified objects. This only qualifies the bounded
    routing/binding claim on disjoint holdout evidence.
    """

    def __init__(self, ledger: EvidenceLedger, *, qualifier_id: str = "HSP-EXTERNAL-PROJECTION-CONDITIONED-ROUTING-QUALIFIER"):
        if not qualifier_id or qualifier_id.upper().startswith("MICROSEED"):
            raise ValueError("qualifier_id must identify an external qualification boundary")
        self.ledger = ledger
        self.qualifier_id = qualifier_id

    def qualify(
        self,
        candidate: ProjectionConditionedRelationCandidate,
        *,
        qualification_evidence: Iterable[EvidenceRef],
        relations: Mapping[str, QualifiedActionOutcomePredictiveRelation],
        min_support: int = 12,
        min_accuracy: float = 0.90,
    ) -> ProjectionConditionedRelationQualificationTicket:
        refs = tuple(qualification_evidence)
        decision = FixedQualifier(self.ledger).decide(refs, Authority.REFERENCE_ONLY)
        support, accuracy, coverage = evaluate_projection_conditioned_relation_holdout(candidate, refs, self.ledger, relations)
        qualified_bucket_ids = projection_conditioned_holdout_bucket_ids(candidate, refs, self.ledger)
        state, reason = decision.state, decision.reason
        qids = {r.evidence_id for r in refs}
        relation_ancestry: set[str] = set()
        for relation_id in candidate.relation_ids():
            relation = relations.get(relation_id)
            if relation is not None:
                relation_ancestry.update(relation.source_evidence_ids)
                relation_ancestry.update(relation.qualification_evidence_ids)
        if set(candidate.source_evidence_ids) & qids:
            state, reason = QualificationState.REJECTED, "ROUTING_PROPOSAL_QUALIFICATION_EVIDENCE_OVERLAP"
        elif relation_ancestry & qids:
            state, reason = QualificationState.REJECTED, "ROUTING_QUALIFICATION_RELATION_EVIDENCE_OVERLAP"
        elif state in {QualificationState.SHADOW_QUALIFIED, QualificationState.QUALIFIED}:
            if support < int(min_support):
                state, reason = QualificationState.REJECTED, "INSUFFICIENT_INDEPENDENT_ROUTING_HOLDOUT"
            elif coverage < 1.0:
                state, reason = QualificationState.REJECTED, f"ROUTING_HOLDOUT_COVERAGE_INCOMPLETE:{coverage:.6f}"
            elif accuracy < float(min_accuracy):
                state, reason = QualificationState.REJECTED, f"ROUTING_HOLDOUT_ACCURACY_BELOW_BOUND:{accuracy:.6f}"
            else:
                reason = f"INDEPENDENT_PROJECTION_CONDITIONED_ROUTING_QUALIFIED:{accuracy:.6f}"
        return ProjectionConditionedRelationQualificationTicket(
            candidate_id=candidate.candidate_id,
            candidate_sha256=candidate.digest(),
            state=state,
            qualifier_id=self.qualifier_id,
            reason=reason,
            qualification_evidence=refs,
            holdout_support=support,
            holdout_accuracy=accuracy,
            holdout_coverage=coverage,
            qualified_bucket_ids=qualified_bucket_ids,
        )


def validate_external_projection_conditioned_relation_ticket(
    candidate: ProjectionConditionedRelationCandidate,
    ticket: ProjectionConditionedRelationQualificationTicket,
    ledger: EvidenceLedger,
    relations: Mapping[str, QualifiedActionOutcomePredictiveRelation],
    *,
    min_support: int = 12,
    min_accuracy: float = 0.90,
) -> tuple[bool, str]:
    if not ticket.qualifier_id or ticket.qualifier_id.upper().startswith("MICROSEED"):
        return False, "QUALIFIER_NOT_EXTERNAL"
    if ticket.candidate_id != candidate.candidate_id or ticket.candidate_sha256 != candidate.digest():
        return False, "CANDIDATE_BINDING_MISMATCH"
    if not ticket.qualification_evidence:
        return False, "NO_QUALIFICATION_EVIDENCE"
    qids = {r.evidence_id for r in ticket.qualification_evidence}
    if set(candidate.source_evidence_ids) & qids:
        return False, "ROUTING_PROPOSAL_QUALIFICATION_EVIDENCE_OVERLAP"
    relation_ancestry: set[str] = set()
    for relation_id in candidate.relation_ids():
        relation = relations.get(relation_id)
        if relation is None:
            return False, f"ROUTING_RELATION_NOT_FOUND:{relation_id}"
        relation_ancestry.update(relation.source_evidence_ids)
        relation_ancestry.update(relation.qualification_evidence_ids)
    if relation_ancestry & qids:
        return False, "ROUTING_QUALIFICATION_RELATION_EVIDENCE_OVERLAP"
    decision = FixedQualifier(ledger).decide(ticket.qualification_evidence, Authority.REFERENCE_ONLY)
    support, accuracy, coverage = evaluate_projection_conditioned_relation_holdout(candidate, ticket.qualification_evidence, ledger, relations)
    qualified_bucket_ids = projection_conditioned_holdout_bucket_ids(candidate, ticket.qualification_evidence, ledger)
    if tuple(sorted(ticket.qualified_bucket_ids)) != qualified_bucket_ids:
        return False, "ROUTING_QUALIFIED_BUCKET_SET_MISMATCH"
    if (support, accuracy, coverage) != (ticket.holdout_support, ticket.holdout_accuracy, ticket.holdout_coverage):
        return False, "ROUTING_HOLDOUT_METRICS_MISMATCH"
    if support < int(min_support):
        return False, "INSUFFICIENT_INDEPENDENT_ROUTING_HOLDOUT"
    if coverage < 1.0:
        return False, "ROUTING_HOLDOUT_COVERAGE_INCOMPLETE"
    if accuracy < float(min_accuracy):
        return False, "ROUTING_HOLDOUT_ACCURACY_BELOW_BOUND"
    if ticket.state not in {QualificationState.SHADOW_QUALIFIED, QualificationState.QUALIFIED}:
        return False, f"NOT_ADMISSIBLE:{ticket.state.value}"
    if decision.state not in {QualificationState.SHADOW_QUALIFIED, QualificationState.QUALIFIED}:
        return False, "QUALIFICATION_EVIDENCE_NOT_SUPPORTIVE"
    return True, "VALID_EXTERNAL_PROJECTION_CONDITIONED_RELATION_QUALIFICATION"
