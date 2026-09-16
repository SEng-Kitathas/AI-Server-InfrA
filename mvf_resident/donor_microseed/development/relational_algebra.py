from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from ..evidence.ledger import canonical_json, sha256_bytes


@dataclass(frozen=True)
class OpaqueTransitionSample:
    """One admitted opaque action transition for proposal-only relation discovery.

    Tokens are intentionally uninterpreted. `origin_id` is only a declared
    physical/evidence-origin handle used to prevent trivial replay inflation;
    it does not grant evidence-independence authority.
    """

    sample_id: str
    origin_id: str
    start_token: str
    action_token: str
    end_token: str
    frame_id: str
    frame_epoch: int

    def __post_init__(self) -> None:
        if not all((self.sample_id, self.origin_id, self.start_token, self.action_token, self.end_token, self.frame_id)):
            raise ValueError("INCOMPLETE_OPAQUE_TRANSITION_SAMPLE")
        if int(self.frame_epoch) < 0:
            raise ValueError("OPAQUE_TRANSITION_REQUIRES_FRAME_CURRENTNESS")
        object.__setattr__(self, "frame_epoch", int(self.frame_epoch))

    def serializable(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OpaqueActionCompositionCandidate:
    """Proposal-only endpoint-equivalence relation over already-observed actions."""

    candidate_id: str
    direct_action_token: str
    first_action_token: str
    second_action_token: str
    positive_support: int
    observed_counterexamples: int
    source_sample_ids: tuple[str, ...]
    support_origin_signatures: tuple[str, ...]
    frame_epochs: tuple[tuple[str, int], ...]
    assistance_ancestry: tuple[str, ...]
    proposal_authority: str = "NONE"
    qualification_authority: str = "NONE"
    semantic_action_authority: str = "NONE"
    truth_authority: str = "NONE"
    execution_authority: str = "NONE"
    evidence_independence_authority: str = "NONE"

    def __post_init__(self) -> None:
        if not self.candidate_id or not all((self.direct_action_token, self.first_action_token, self.second_action_token)):
            raise ValueError("INCOMPLETE_OPAQUE_ACTION_COMPOSITION_CANDIDATE")
        if int(self.positive_support) < 1 or int(self.observed_counterexamples) != 0:
            raise ValueError("COMPOSITION_CANDIDATE_REQUIRES_POSITIVE_COUNTEREXAMPLE_FREE_BASIS")
        if any(
            x != "NONE"
            for x in (
                self.proposal_authority,
                self.qualification_authority,
                self.semantic_action_authority,
                self.truth_authority,
                self.execution_authority,
                self.evidence_independence_authority,
            )
        ):
            raise ValueError("OPAQUE_COMPOSITION_CANDIDATE_AUTHORITY_ESCALATION")

    def signature_payload(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("candidate_id", None)
        d["source_sample_ids"] = []
        return d

    def digest(self) -> str:
        return sha256_bytes(canonical_json(self.signature_payload()))

    def serializable(self) -> dict[str, Any]:
        d = asdict(self)
        d["frame_epochs"] = [list(x) for x in self.frame_epochs]
        d["candidate_sha256"] = self.digest()
        return d


@dataclass(frozen=True)
class OpaqueTransitionConflictCandidate:
    """Proposal-only recurrent extensional conflict in one opaque state/action slot.

    This says only that the current coarse transition representation has recurrent
    incompatible observed endpoints. It does not identify whether the explanation
    is state aliasing, a missing primitive/generator, drift, noise, or any other
    causal story. Distinct ``origin_id`` values prevent literal replay inflation
    but do not establish physical/evidential independence.
    """

    conflict_id: str
    start_token: str
    action_token: str
    outcome_supports: tuple[tuple[str, int], ...]
    source_sample_ids: tuple[str, ...]
    support_origin_ids: tuple[str, ...]
    frame_epoch: tuple[str, int]
    proposal_authority: str = "NONE"
    truth_authority: str = "NONE"
    causal_explanation_authority: str = "NONE"
    state_alias_authority: str = "NONE"
    generator_authority: str = "NONE"
    evidence_independence_authority: str = "NONE"

    def __post_init__(self) -> None:
        if not self.conflict_id or not self.start_token or not self.action_token:
            raise ValueError("INCOMPLETE_OPAQUE_TRANSITION_CONFLICT")
        if len(self.outcome_supports) < 2 or any(int(n) < 2 for _, n in self.outcome_supports):
            raise ValueError("OPAQUE_TRANSITION_CONFLICT_REQUIRES_RECURRENT_DISTINCT_OUTCOMES")
        if any(
            x != "NONE" for x in (
                self.proposal_authority, self.truth_authority, self.causal_explanation_authority,
                self.state_alias_authority, self.generator_authority, self.evidence_independence_authority,
            )
        ):
            raise ValueError("OPAQUE_TRANSITION_CONFLICT_AUTHORITY_ESCALATION")

    def serializable(self) -> dict[str, Any]:
        d=asdict(self); d["outcome_supports"]=[list(x) for x in self.outcome_supports]; d["frame_epoch"]=list(self.frame_epoch); return d


def discover_opaque_transition_conflicts(
    samples: Iterable[OpaqueTransitionSample],
) -> tuple[OpaqueTransitionConflictCandidate, ...]:
    """Surface recurrent extensional conflicts without explaining them.

    The support floor is deliberately fixed at two distinct declared origin
    handles per endpoint. This is structural anti-replay recurrence only; it is
    not evidence-independence authority and is not caller-tunable through this
    owner. Frames never pool.
    """
    groups: dict[tuple[str, int, str, str], list[OpaqueTransitionSample]] = defaultdict(list)
    for row in samples:
        groups[(row.frame_id, row.frame_epoch, row.start_token, row.action_token)].append(row)
    out=[]
    for (fid, epoch, start, action), rows in sorted(groups.items()):
        by_end: dict[str, set[str]] = defaultdict(set)
        sample_ids: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            by_end[row.end_token].add(row.origin_id)
            sample_ids[row.end_token].add(row.sample_id)
        recurrent=tuple(sorted((end,len(origins)) for end,origins in by_end.items() if len(origins)>=2))
        if len(recurrent)<2:
            continue
        included={end for end,_ in recurrent}
        origins=tuple(sorted({origin for end in included for origin in by_end[end]}))
        sources=tuple(sorted({sid for end in included for sid in sample_ids[end]}))
        basis={"frame":[fid,epoch],"start":start,"action":action,"outcomes":[list(x) for x in recurrent]}
        out.append(OpaqueTransitionConflictCandidate(
            conflict_id="opaque-transition-conflict-"+sha256_bytes(canonical_json(basis))[:20],
            start_token=start, action_token=action, outcome_supports=recurrent,
            source_sample_ids=sources, support_origin_ids=origins, frame_epoch=(fid,epoch),
        ))
    return tuple(out)



@dataclass(frozen=True)
class OpaqueOneStepVisibleHistoryRefinementCandidate:
    """Proposal-only refinement of one coarse slot by previous visible state.

    The candidate is earned only when recurrent admitted transition pairs show that
    distinct previous *visible-state* contexts make the same current state/action
    slot consistently lead to different endpoints. Previous action identity is
    deliberately ignored, so actuator-handle aliases cannot manufacture context.
    This does not assert hidden-state existence, causal explanation, truth, or a
    license to increase history depth.
    """

    refinement_id: str
    start_token: str
    action_token: str
    context_outcomes: tuple[tuple[str, str, int], ...]
    source_sample_ids: tuple[str, ...]
    support_origin_ids: tuple[str, ...]
    frame_epoch: tuple[str, int]
    context_basis: str = "PREVIOUS_VISIBLE_STATE_ONLY"
    proposal_authority: str = "NONE"
    truth_authority: str = "NONE"
    hidden_state_authority: str = "NONE"
    causal_explanation_authority: str = "NONE"
    previous_action_identity_authority: str = "NONE"
    evidence_independence_authority: str = "NONE"
    history_depth_extension_authority: str = "NONE"

    def __post_init__(self) -> None:
        if not self.refinement_id or not self.start_token or not self.action_token:
            raise ValueError("INCOMPLETE_ONE_STEP_VISIBLE_HISTORY_REFINEMENT")
        if len(self.context_outcomes) < 2 or len({end for _, end, _ in self.context_outcomes}) < 2:
            raise ValueError("ONE_STEP_REFINEMENT_REQUIRES_DISTINCT_CONTEXT_OUTCOMES")
        if any(int(n) < 2 for _, _, n in self.context_outcomes):
            raise ValueError("ONE_STEP_REFINEMENT_REQUIRES_RECURRENT_CONTEXT_SUPPORT")
        if self.context_basis != "PREVIOUS_VISIBLE_STATE_ONLY":
            raise ValueError("ONE_STEP_REFINEMENT_CONTEXT_BASIS_DRIFT")
        if any(x != "NONE" for x in (
            self.proposal_authority, self.truth_authority, self.hidden_state_authority,
            self.causal_explanation_authority, self.previous_action_identity_authority,
            self.evidence_independence_authority, self.history_depth_extension_authority,
        )):
            raise ValueError("ONE_STEP_VISIBLE_HISTORY_REFINEMENT_AUTHORITY_ESCALATION")

    @property
    def candidate_id(self) -> str:
        # Structural compatibility with the existing external projection qualifier.
        # The refinement remains its own proposal type; this alias grants no admission.
        return self.refinement_id

    def signature_payload(self) -> dict[str, Any]:
        d=self.serializable()
        return d

    def digest(self) -> str:
        return sha256_bytes(canonical_json(self.signature_payload()))

    def serializable(self) -> dict[str, Any]:
        d=asdict(self); d["context_outcomes"]=[list(x) for x in self.context_outcomes]; d["frame_epoch"]=list(self.frame_epoch); return d


def discover_one_step_visible_history_refinements(
    predecessor_current_pairs: Iterable[tuple[OpaqueTransitionSample, OpaqueTransitionSample]],
) -> tuple[OpaqueOneStepVisibleHistoryRefinementCandidate, ...]:
    """Discover strictly bounded previous-visible-state refinements.

    Every current row in a candidate slot must have an authenticated predecessor
    pair in the same frame, each previous-visible-state context must be recurrent
    on at least two distinct current origin handles, and each context must be
    endpoint-unanimous. Any within-context conflict keeps that slot unresolved.
    """
    groups: dict[tuple[str,int,str,str], list[tuple[OpaqueTransitionSample,OpaqueTransitionSample]]] = defaultdict(list)
    for prev, cur in predecessor_current_pairs:
        if (prev.frame_id,prev.frame_epoch)!=(cur.frame_id,cur.frame_epoch):
            continue
        if prev.end_token != cur.start_token:
            continue
        groups[(cur.frame_id,cur.frame_epoch,cur.start_token,cur.action_token)].append((prev,cur))
    out=[]
    for (fid,epoch,start,action), rows in sorted(groups.items()):
        by_context: dict[str, dict[str,set[str]]] = defaultdict(lambda: defaultdict(set))
        samples:set[str]=set(); origins:set[str]=set()
        for prev,cur in rows:
            by_context[prev.start_token][cur.end_token].add(cur.origin_id)
            samples.update((prev.sample_id,cur.sample_id)); origins.add(cur.origin_id)
        contexts=[]; invalid=False
        for context, endpoints in sorted(by_context.items()):
            recurrent=[(end,len(ids)) for end,ids in sorted(endpoints.items()) if len(ids)>=2]
            # Any more than one observed endpoint in one visible context means one-step
            # visible history has not resolved the coarse conflict. One-off endpoints
            # also keep the context incomplete rather than being discarded.
            if len(endpoints)!=1 or len(recurrent)!=1:
                invalid=True; break
            contexts.append((context,recurrent[0][0],recurrent[0][1]))
        if invalid or len(contexts)<2 or len({end for _,end,_ in contexts})<2:
            continue
        basis={"frame":[fid,epoch],"start":start,"action":action,"contexts":[list(x) for x in contexts]}
        out.append(OpaqueOneStepVisibleHistoryRefinementCandidate(
            refinement_id="opaque-one-step-refinement-"+sha256_bytes(canonical_json(basis))[:20],
            start_token=start,action_token=action,context_outcomes=tuple(contexts),
            source_sample_ids=tuple(sorted(samples)),support_origin_ids=tuple(sorted(origins)),
            frame_epoch=(fid,epoch),
        ))
    return tuple(out)

def _unanimous_lookup(samples: tuple[OpaqueTransitionSample, ...]) -> dict[tuple[str, str], OpaqueTransitionSample]:
    groups: dict[tuple[str, str], list[OpaqueTransitionSample]] = defaultdict(list)
    for row in samples:
        groups[(row.start_token, row.action_token)].append(row)
    out: dict[tuple[str, str], OpaqueTransitionSample] = {}
    for key, rows in groups.items():
        if len({row.end_token for row in rows}) == 1:
            out[key] = rows[0]
    return out


def _origin_signature(*rows: OpaqueTransitionSample) -> str:
    return sha256_bytes(canonical_json(sorted({row.origin_id for row in rows})))


def discover_opaque_action_composition_candidates(
    samples: Iterable[OpaqueTransitionSample],
    *,
    min_positive_support: int = 2,
) -> tuple[OpaqueActionCompositionCandidate, ...]:
    """Nominate exact two-step action-composition relations from opaque endpoints.

    The bounded grammar asks only whether `first` then `second` reaches the same
    opaque endpoint as an already-observed `direct` action from the same start.
    Any observed counterexample blocks a global candidate. Nothing here qualifies
    the relation, names action semantics, establishes evidence independence, or
    creates an executable action.
    """

    rows = tuple(samples)
    if not rows or int(min_positive_support) < 1:
        return ()
    frame_epochs = {(row.frame_id, row.frame_epoch) for row in rows}
    if len(frame_epochs) != 1:
        return ()
    lookup = _unanimous_lookup(rows)
    states = sorted({row.start_token for row in rows} | {row.end_token for row in rows})
    actions = sorted({row.action_token for row in rows})
    stats: dict[tuple[str, str, str], dict[str, set[str]]] = defaultdict(lambda: {"yes": set(), "no": set(), "samples": set()})
    for start in states:
        for direct in actions:
            direct_row = lookup.get((start, direct))
            if direct_row is None:
                continue
            for first in actions:
                first_row = lookup.get((start, first))
                if first_row is None:
                    continue
                for second in actions:
                    second_row = lookup.get((first_row.end_token, second))
                    if second_row is None:
                        continue
                    bucket = "yes" if second_row.end_token == direct_row.end_token else "no"
                    rec = stats[(direct, first, second)]
                    rec[bucket].add(_origin_signature(direct_row, first_row, second_row))
                    rec["samples"].update((direct_row.sample_id, first_row.sample_id, second_row.sample_id))
    out: list[OpaqueActionCompositionCandidate] = []
    for (direct, first, second), rec in sorted(stats.items()):
        positive = len(rec["yes"])
        negative = len(rec["no"])
        if positive < int(min_positive_support) or negative:
            continue
        payload = {
            "direct": direct,
            "first": first,
            "second": second,
            "positive_support": positive,
            "frame_epochs": sorted(frame_epochs),
        }
        out.append(OpaqueActionCompositionCandidate(
            candidate_id="opaque-comp-" + sha256_bytes(canonical_json(payload))[:20],
            direct_action_token=direct,
            first_action_token=first,
            second_action_token=second,
            positive_support=positive,
            observed_counterexamples=0,
            source_sample_ids=tuple(sorted(rec["samples"])),
            support_origin_signatures=tuple(sorted(rec["yes"])),
            frame_epochs=tuple(sorted(frame_epochs)),
            assistance_ancestry=(
                "SUPPLIED_STABLE_OPAQUE_EVENT_ACTION_EFFECT_BINDING",
                "FIXED_TWO_STEP_COMPOSITION_GRAMMAR",
                "ENDPOINT_EQUALITY_ONLY",
                "DECLARED_ORIGIN_DEDUPLICATION_WITHOUT_INDEPENDENCE_AUTHORITY",
            ),
        ))
    return tuple(out)


def predict_opaque_action_composition(
    start_token: str,
    direct_action_token: str,
    candidates: Iterable[OpaqueActionCompositionCandidate],
    samples: Iterable[OpaqueTransitionSample],
) -> dict[str, Any]:
    rows = tuple(samples)
    lookup = _unanimous_lookup(rows)
    frame_epochs = {(row.frame_id, row.frame_epoch) for row in rows}
    predictions: list[tuple[str, str]] = []
    for candidate in candidates:
        if candidate.direct_action_token != direct_action_token:
            continue
        if set(candidate.frame_epochs) != frame_epochs:
            continue
        first = lookup.get((str(start_token), candidate.first_action_token))
        if first is None:
            continue
        second = lookup.get((first.end_token, candidate.second_action_token))
        if second is None:
            continue
        predictions.append((candidate.candidate_id, second.end_token))
    values = {value for _, value in predictions}
    if len(values) == 1:
        return {
            "status": "RELATIONAL_PREDICTION",
            "prediction": next(iter(values)),
            "candidate_ids": [cid for cid, _ in predictions],
            "authority": "MODEL_OUTPUT_ONLY",
            "truth_authority": "NONE",
            "execution_authority": "NONE",
        }
    return {
        "status": "UNKNOWN_INCOMPLETE",
        "reason": "RELATIONAL_DISAGREEMENT" if len(values) > 1 else "NO_APPLICABLE_RELATION",
        "prediction": None,
        "candidate_ids": [cid for cid, _ in predictions],
        "authority": "NONE",
        "truth_authority": "NONE",
        "execution_authority": "NONE",
    }
