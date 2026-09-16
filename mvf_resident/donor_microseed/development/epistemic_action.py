from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib, json
from typing import Any, Mapping

from ..runtime.capabilities import CapabilityRegistry
from ..runtime.commitment import RelationalCommitment, TernaryCommitment, conjoin_required_commitments
from ..runtime.types import Authority, FeasibilityState, QualificationState, QueryObligation
from .action_closure import BoundedActionIntent, OpaqueControlStateWitness
from .commitment_adapters import project_feasibility, project_qualification_state
from .epistemic import EpistemicBearingKind, EpistemicDeficitRecord, EpistemicDeficitState
from .epistemic_program import EpistemicProgramTrial, GeneratedEpistemicProgramCandidate
from .recruitment import RecruitmentOption
from .rehearsal import RehearsalTransitionRelation
from .epistemic_priority import derive_regulatory_decision_bearing_commitment, derive_program_trace_discrimination_commitment


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def feasibility_digest(option: RecruitmentOption) -> str:
    """Content identity for the caller-supplied feasibility input only.

    This does not establish that the feasibility claim is grounded or current in
    the physical world. It only prevents nomination-time feasibility content from
    silently changing while an intent is reused.
    """
    return _sha(option.serializable())




@dataclass(frozen=True)
class EpistemicDecisionBearingContext:
    """Ephemeral ingredients for re-deriving whether evidence can change a current regulatory decision.

    Relation rows remain model/representation inputs with zero authority.  Feasibility
    routes name ordinary current DERIVED_READ_ONLY capabilities; no FEASIBLE token is
    accepted directly on this endogenous route.
    """
    relation_sets: tuple[tuple[RehearsalTransitionRelation, ...], ...]
    feasibility_routes: tuple[tuple[str, str, QueryObligation], ...]
    authority: str = "NONE"
    execution_authority: str = "NONE"
    truth_authority: str = "NONE"

    def __post_init__(self) -> None:
        if any(x != "NONE" for x in (self.authority, self.execution_authority, self.truth_authority)):
            raise ValueError("EPISTEMIC_DECISION_CONTEXT_AUTHORITY_ESCALATION")

def derive_epistemic_program_relation_ancestry_status(
    *, trial: EpistemicProgramTrial, decision_context: EpistemicDecisionBearingContext,
) -> tuple[bool, str, tuple[str, ...]]:
    """Check that a generated trial is interpreted against the surface that earned it.

    Legacy composition trials predate explicit source-relation ancestry and therefore
    retain their historical behavior. Generated trials carry the exact relation digests
    traversed when the program was formed. A later caller may not substitute a different
    relation surface and reinterpret the same physical outcome or re-earn priority.
    """
    expected = tuple(sorted(trial.source_relation_digests))
    if not expected:
        return True, "PROGRAM_RELATION_ANCESTRY_LEGACY_UNBOUND", ()
    observed: set[str] = set()
    for rows in decision_context.relation_sets:
        lookup = {(r.state_id, r.capability_id): r for r in rows}
        cur = str(trial.start_state_id)
        for action in trial.steps:
            rel = lookup.get((cur, action))
            if rel is None:
                return False, "PROGRAM_RELATION_ANCESTRY_INCOMPLETE", tuple(sorted(observed))
            observed.add(rel.digest())
            cur = rel.next_state_id
    actual = tuple(sorted(observed))
    if actual != expected:
        return False, "PROGRAM_RELATION_ANCESTRY_MISMATCH", actual
    return True, "PROGRAM_RELATION_ANCESTRY_CURRENT", actual


@dataclass(frozen=True)
class EpistemicProgramStepBearingWitness:
    """Content-bound bearing of one actual program-step outcome on live represented alternatives.

    This is a proposal/relevance witness only.  It reuses the older bounded epistemic
    bearing invariant (outside every represented prediction => model-space challenge)
    without importing the projection/contrast registry architecture.
    """

    witness_id: str
    trial_id: str
    prior_trial_digest: str
    advanced_trial_digest: str
    step_index: int
    capability_id: str
    start_state_id: str
    outcome_evidence_id: str
    actual_next_state_id: str
    represented_next_states: tuple[str, ...]
    kind: EpistemicBearingKind
    bearing_authority: str = "BOUNDED_PROGRAM_STEP_BEARING_ONLY"
    truth_authority: str = "NONE"
    answer_authority: str = "NONE"
    model_replacement_authority: str = "NONE"
    execution_authority: str = "NONE"

    def __post_init__(self) -> None:
        if any(x != "NONE" for x in (
            self.truth_authority, self.answer_authority, self.model_replacement_authority, self.execution_authority,
        )):
            raise ValueError("EPISTEMIC_PROGRAM_STEP_BEARING_AUTHORITY_ESCALATION")

    def serializable(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        d["represented_next_states"] = list(self.represented_next_states)
        return d


@dataclass(frozen=True)
class EpistemicStepExecutionContext:
    """Ephemeral execution-time premises for one epistemic program step.

    The context carries no authority and is intentionally not a program registry.
    Legacy research callers may re-supply a typed RecruitmentOption.  The
    grounded route instead supplies only an ordinary feasibility capability +
    exact obligation; the option is freshly derived from that capability at the
    execution boundary.
    """

    trial: EpistemicProgramTrial
    feasibility: RecruitmentOption | None = None
    feasibility_capability_id: str | None = None
    feasibility_obligation: QueryObligation | None = None
    decision_context: EpistemicDecisionBearingContext | None = None
    authority: str = "NONE"
    truth_authority: str = "NONE"
    execution_authority: str = "NONE"

    def __post_init__(self) -> None:
        if any(x != "NONE" for x in (self.authority, self.truth_authority, self.execution_authority)):
            raise ValueError("EPISTEMIC_STEP_CONTEXT_AUTHORITY_ESCALATION")
        legacy = self.feasibility is not None
        grounded = self.feasibility_capability_id is not None or self.feasibility_obligation is not None
        if legacy and grounded:
            raise ValueError("EPISTEMIC_STEP_FEASIBILITY_ROUTE_AMBIGUOUS")
        if grounded and (not self.feasibility_capability_id or self.feasibility_obligation is None):
            raise ValueError("GROUNDED_FEASIBILITY_ROUTE_INCOMPLETE")


def derive_current_epistemic_feasibility_routes(
    *,
    capabilities: CapabilityRegistry,
    operational_scope_id: str | None,
) -> tuple[tuple[str, str, QueryObligation], ...]:
    """Derive an ephemeral feasibility-route surface from live capability contracts.

    The registry already owns capability identity, dependency ancestry, authority,
    qualification/currentness, query binding, operational scope, and runtime
    handlers.  This adapter merely projects those existing contracts into the
    route tuple consumed by the epistemic decision machinery.

    It creates no route registry, chooses no route, invokes no handler, and grants
    no feasibility/truth/execution authority.  Multiple eligible routes are
    preserved so downstream arbitration cannot acquire pick-first authority.
    """
    routes: list[tuple[str, str, QueryObligation]] = []
    for fid, cap in sorted(capabilities.contracts.items()):
        if cap.authority != Authority.DERIVED_READ_ONLY:
            continue
        if cap.qualification not in {QualificationState.QUALIFIED, QualificationState.SHADOW_QUALIFIED}:
            continue
        if cap.currentness != "CURRENT":
            continue
        target = str(cap.boundary.get("target_capability_id", ""))
        if not target or target not in cap.dependencies:
            continue
        target_cap = capabilities.contracts.get(target)
        if target_cap is None:
            continue
        if target_cap.authority != Authority.EFFECT:
            continue
        if target_cap.qualification not in {QualificationState.QUALIFIED, QualificationState.SHADOW_QUALIFIED}:
            continue
        if target_cap.currentness != "CURRENT":
            continue
        # Route and target must inhabit the same requested opaque operational scope.
        if cap.operational_scope_id != operational_scope_id:
            continue
        if target_cap.operational_scope_id not in {None, operational_scope_id}:
            continue
        if not cap.query_obligation_id:
            continue
        routes.append((
            target,
            fid,
            QueryObligation(
                cap.query_obligation_id,
                cap.purpose,
                required_authority=Authority.DERIVED_READ_ONLY,
                witness_predicate=cap.witness_predicate,
                operational_scope_id=cap.operational_scope_id,
            ),
        ))
    return tuple(routes)


def derive_current_grounded_feasibility_surface(
    *,
    capabilities: CapabilityRegistry,
    operational_scope_id: str | None,
) -> tuple[tuple[RecruitmentOption, ...], dict[str, dict[str, object]]]:
    """Ground the current contract-derived feasibility surface exactly once.

    Agreement among multiple routes may project the same bounded feasibility
    state, but it grants no evidence-independence or truth authority.  Route
    disagreement is preserved as UNKNOWN rather than resolved by order, count,
    or ranking.  This is an ephemeral arbitration-cycle view only.
    """
    routes = derive_current_epistemic_feasibility_routes(
        capabilities=capabilities, operational_scope_id=operational_scope_id,
    )
    grouped: dict[str, list[tuple[str, QueryObligation]]] = {}
    for target, fid, obligation in routes:
        grouped.setdefault(target, []).append((fid, obligation))

    options: list[RecruitmentOption] = []
    basis: dict[str, dict[str, object]] = {}
    for target in sorted(grouped):
        rows: list[tuple[str, RecruitmentOption, dict[str, str]]] = []
        for fid, obligation in grouped[target]:
            option, detail = derive_grounded_feasibility_option(
                target_capability_id=target, feasibility_capability_id=fid,
                feasibility_obligation=obligation, capabilities=capabilities,
            )
            rows.append((fid, option, detail))
        states = {row[1].feasibility for row in rows}
        marker_ids = tuple(sorted({eid for _, option, _ in rows for eid in option.model_evidence_ids}))
        if len(states) == 1:
            state = next(iter(states))
            reason = "ROUTE_AGREEMENT_WITHOUT_INDEPENDENCE_GAIN" if len(rows) > 1 else "SINGLE_CURRENT_ROUTE"
        else:
            state = FeasibilityState.UNKNOWN
            reason = "CURRENT_FEASIBILITY_ROUTE_DISAGREEMENT"
        options.append(RecruitmentOption(target, state, model_evidence_ids=marker_ids))
        basis[target] = {
            "status": "CURRENT_BOUNDED_FEASIBILITY_SURFACE",
            "reason": reason,
            "feasibility": state.value,
            "route_ids": tuple(fid for fid, _, _ in rows),
            "route_results": tuple((fid, option.feasibility.value) for fid, option, _ in rows),
            "evidence_independence_authority": "NONE",
            "truth_authority": "NONE",
            "execution_authority": "NONE",
        }
    return tuple(options), basis


def derive_grounded_feasibility_option(
    *,
    target_capability_id: str,
    feasibility_capability_id: str,
    feasibility_obligation: QueryObligation,
    capabilities: CapabilityRegistry,
) -> tuple[RecruitmentOption, dict[str, str]]:
    """Invoke one ordinary current DERIVED_READ_ONLY feasibility capability.

    This adapter does not establish global safety or physical truth.  It only
    turns a query/scoped/current capability result into the existing typed
    FeasibilityState surface.  The feasibility capability must content-bind the
    exact EFFECT capability it speaks about and depend on that capability so
    ordinary invalidation/currentness remains authoritative.
    """
    fid = str(feasibility_capability_id)
    target = str(target_capability_id)
    cap = capabilities.contracts.get(fid)
    marker_ids: tuple[str, ...] = ()
    if cap is not None:
        marker_ids = (
            f"FEASIBILITY_CAPABILITY:{fid}@{capabilities.epochs.get(fid, -1)}",
            f"FEASIBILITY_CAPABILITY_SIGNATURE:{cap.computed_signature_sha256()}",
        )
    def _unknown(reason: str) -> tuple[RecruitmentOption, dict[str, str]]:
        return RecruitmentOption(target, FeasibilityState.UNKNOWN, model_evidence_ids=marker_ids), {
            "status": "UNKNOWN_INCOMPLETE", "reason": reason, "feasibility_capability_id": fid,
        }
    if cap is None:
        return _unknown("FEASIBILITY_CAPABILITY_NOT_FOUND")
    if cap.authority != Authority.DERIVED_READ_ONLY:
        return _unknown("FEASIBILITY_CAPABILITY_REQUIRES_DERIVED_READ_ONLY")
    if cap.qualification not in {QualificationState.QUALIFIED, QualificationState.SHADOW_QUALIFIED} or cap.currentness != "CURRENT":
        return _unknown("FEASIBILITY_CAPABILITY_NOT_CURRENT")
    if str(cap.boundary.get("target_capability_id", "")) != target:
        return _unknown("FEASIBILITY_CAPABILITY_TARGET_MISMATCH")
    if target not in cap.dependencies:
        return _unknown("FEASIBILITY_CAPABILITY_TARGET_DEPENDENCY_MISSING")
    result = capabilities.invoke(fid, feasibility_obligation)
    if result.get("status") != "CAPABILITY_RESULT" or result.get("authority") != Authority.DERIVED_READ_ONLY.value:
        return _unknown(str(result.get("reason", result.get("status", "FEASIBILITY_CAPABILITY_NO_RESULT"))))
    value = result.get("value")
    raw = value.get("feasibility") if isinstance(value, dict) else value
    try:
        state = FeasibilityState(raw)
    except Exception:
        return _unknown("FEASIBILITY_CAPABILITY_RESULT_NOT_TYPED")
    option = RecruitmentOption(target, state, model_evidence_ids=marker_ids)
    return option, {
        "status": "CURRENT_BOUNDED_FEASIBILITY",
        "reason": str(value.get("reason", state.value)) if isinstance(value, dict) else state.value,
        "feasibility_capability_id": fid,
        "feasibility_capability_epoch": str(capabilities.epochs[fid]),
        "feasibility_capability_signature": cap.computed_signature_sha256(),
        "feasibility": state.value,
    }


def derive_current_decision_bearing_commitment_from_grounded_surface(
    *,
    trial: EpistemicProgramTrial,
    deficit: EpistemicDeficitRecord | None,
    decision_context: EpistemicDecisionBearingContext,
    feasibility_options: tuple[RecruitmentOption, ...],
    capabilities: CapabilityRegistry,
    values,
    current_frame_epochs: Mapping[str, int],
    current_episode_epochs: Mapping[str, int],
    current_topology_epochs: Mapping[str, int],
    current_coordination_epochs: Mapping[str, int],
) -> RelationalCommitment:
    """Re-use the existing priority owner over one already-grounded cycle surface.

    This avoids re-invoking feasibility capabilities independently for each
    candidate during one arbitration cycle.
    """
    ancestry_ok, ancestry_reason, _ = derive_epistemic_program_relation_ancestry_status(
        trial=trial, decision_context=decision_context,
    )
    if not ancestry_ok:
        return RelationalCommitment(
            _sha({"program_relation_ancestry": ancestry_reason, "trial": trial.trial_id}),
            f"epistemic-program:{trial.trial_id}:decision-bearing",
            TernaryCommitment.UNKNOWN, binding=TernaryCommitment.UNKNOWN,
            reason=ancestry_reason, qualifiers=(("authority_gain", "NONE"),),
            premise_ids=(trial.trial_id,),
        )
    relation_sets = tuple(
        {(r.state_id, r.capability_id): r for r in rows}
        for rows in decision_context.relation_sets
    )
    return derive_regulatory_decision_bearing_commitment(
        deficit=deficit, values=values, relation_sets=relation_sets,
        options=feasibility_options, start_state_id=_expected_state(trial)[0],
        current_capability_epochs=dict(capabilities.epochs),
        current_capability_signatures={cid: contract.computed_signature_sha256() for cid, contract in capabilities.contracts.items()},
        current_frame_epochs=current_frame_epochs, current_episode_epochs=current_episode_epochs,
        current_topology_epochs=current_topology_epochs, current_coordination_epochs=current_coordination_epochs,
    )


def derive_epistemic_program_step_outcome_bearing(
    *, prior_trial: EpistemicProgramTrial, advanced_trial: EpistemicProgramTrial,
    decision_context: EpistemicDecisionBearingContext,
) -> tuple[str, EpistemicProgramStepBearingWitness | None]:
    """Classify one actual program-step result against the live represented alternatives.

    A fully represented actual outcome outside every predicted next state is a bounded
    MODEL_SPACE_CHALLENGE.  Matching one branch of a divergent prediction set is
    DISCRIMINATES_LIVE_SET.  Matching unanimous prediction is non-discriminating.
    Missing represented rows remain unresolved and cannot earn a challenge.
    """
    if prior_trial.trial_id != advanced_trial.trial_id or prior_trial.steps != advanced_trial.steps:
        return "PROGRAM_TRIAL_LINEAGE_MISMATCH", None
    if len(advanced_trial.step_records) != len(prior_trial.step_records) + 1:
        return "EXACTLY_ONE_ADVANCED_PROGRAM_STEP_REQUIRED", None
    if advanced_trial.step_records[:-1] != prior_trial.step_records:
        return "PROGRAM_TRIAL_HISTORY_MISMATCH", None
    idx = len(prior_trial.step_records)
    if idx >= len(prior_trial.steps):
        return "PROGRAM_STEP_OVERFLOW", None
    rec = advanced_trial.step_records[-1]
    expected_action = prior_trial.steps[idx]
    if rec.step_index != idx or rec.capability_id != expected_action:
        return "PROGRAM_STEP_RECORD_MISMATCH", None
    ancestry_ok, ancestry_reason, _ = derive_epistemic_program_relation_ancestry_status(
        trial=prior_trial, decision_context=decision_context,
    )
    if not ancestry_ok:
        return ancestry_reason, None
    start_state = prior_trial.start_state_id if idx == 0 else prior_trial.step_records[-1].actual_next_state_id
    predictions: list[str] = []
    for rows in decision_context.relation_sets:
        lookup = {(r.state_id, r.capability_id): r for r in rows}
        rel = lookup.get((start_state, expected_action))
        if rel is None:
            return "REPRESENTED_PROGRAM_STEP_BEARING_INCOMPLETE", None
        predictions.append(rel.next_state_id)
    if len(predictions) < 2:
        return "MULTIPLE_REPRESENTED_ALTERNATIVES_REQUIRED", None
    unique = set(predictions)
    if rec.actual_next_state_id not in unique:
        kind = EpistemicBearingKind.MODEL_SPACE_CHALLENGE
    elif len(unique) > 1:
        kind = EpistemicBearingKind.DISCRIMINATES_LIVE_SET
    else:
        kind = EpistemicBearingKind.CONSENSUS_NONDISCRIMINATING
    payload = {
        "trial_id": prior_trial.trial_id, "prior_trial_digest": prior_trial.digest(),
        "advanced_trial_digest": advanced_trial.digest(), "step_index": idx,
        "capability_id": expected_action, "start_state_id": start_state,
        "outcome_evidence_id": rec.outcome_evidence_id, "actual_next_state_id": rec.actual_next_state_id,
        "represented_next_states": predictions, "kind": kind.value,
    }
    witness = EpistemicProgramStepBearingWitness(
        witness_id="program-step-bearing-" + _sha(payload)[:24],
        trial_id=prior_trial.trial_id, prior_trial_digest=prior_trial.digest(),
        advanced_trial_digest=advanced_trial.digest(), step_index=idx, capability_id=expected_action,
        start_state_id=start_state, outcome_evidence_id=rec.outcome_evidence_id,
        actual_next_state_id=rec.actual_next_state_id, represented_next_states=tuple(predictions), kind=kind,
    )
    return kind.value, witness


def derive_program_observable_trace_signature(
    *, trial: EpistemicProgramTrial, decision_context: EpistemicDecisionBearingContext,
) -> tuple[tuple[str, ...], ...] | None:
    """Return the represented remaining-program traces from the current trial state.

    This exposes structure already computed by the program-information owner.  It is
    representation-only: equality here is not physical generator identity, execution
    equivalence, causal identity, truth, or generated-affordance closure. Missing
    represented transitions leave the signature unresolved.
    """
    idx = len(trial.step_records)
    if trial.status != "OPEN" or idx >= len(trial.steps):
        return None
    state = trial.start_state_id if idx == 0 else trial.step_records[-1].actual_next_state_id
    remaining = trial.steps[idx:]
    traces: list[tuple[str, ...]] = []
    for rows in decision_context.relation_sets:
        lookup = {(r.state_id, r.capability_id): r for r in rows}
        cur = state
        trace: list[str] = []
        for action in remaining:
            rel = lookup.get((cur, action))
            if rel is None:
                return None
            cur = rel.next_state_id
            trace.append(cur)
        traces.append(tuple(trace))
    return tuple(traces) if len(traces) >= 2 else None


def derive_program_observable_partition(
    *, trial: EpistemicProgramTrial, decision_context: EpistemicDecisionBearingContext,
) -> tuple[tuple[int, ...], ...] | None:
    """Return the partition of live alternatives induced by the remaining program trace.

    The partition is structural only.  It grants no ranking, selection, truth, or
    execution authority. Missing trace rows leave the partition unresolved.
    """
    traces = derive_program_observable_trace_signature(trial=trial, decision_context=decision_context)
    if traces is None:
        return None
    groups: dict[tuple[str, ...], list[int]] = {}
    for index, trace in enumerate(traces):
        groups.setdefault(trace, []).append(index)
    return tuple(sorted((tuple(indices) for indices in groups.values()), key=lambda x: x))


def derive_current_epistemic_effect_action_tokens(
    *, capabilities: CapabilityRegistry, obligation: QueryObligation,
) -> tuple[str, ...]:
    """Project the current primitive EFFECT action alphabet for one exact obligation.

    CapabilityRegistry remains the owner of capability identity/currentness/authority.
    This function creates no generator registry and does not claim feasibility or
    physical-effect correctness.
    """
    out: list[str] = []
    for cid, cap in sorted(capabilities.contracts.items()):
        if cap.authority != Authority.EFFECT:
            continue
        if cap.qualification not in {QualificationState.QUALIFIED, QualificationState.SHADOW_QUALIFIED}:
            continue
        if cap.currentness != "CURRENT" or cap.handler is None:
            continue
        if cap.query_obligation_id and cap.query_obligation_id != obligation.obligation_id:
            continue
        if cap.operational_scope_id and cap.operational_scope_id != obligation.operational_scope_id:
            continue
        out.append(cid)
    return tuple(out)


def search_current_represented_discriminating_programs(
    *,
    decision_context: EpistemicDecisionBearingContext,
    start_state_id: str,
    capabilities: CapabilityRegistry,
    obligation: QueryObligation,
    max_nodes: int = 64,
) -> dict[str, Any]:
    """Run query-local represented program search over the registry-owned EFFECT alphabet."""
    actions = derive_current_epistemic_effect_action_tokens(capabilities=capabilities, obligation=obligation)
    result = dict(search_represented_discriminating_programs(
        decision_context=decision_context, start_state_id=start_state_id,
        action_tokens=actions, max_nodes=max_nodes,
    ))
    result["generator_tokens"] = actions
    result["generator_surface_authority"] = "CURRENT_CAPABILITY_CONTRACTS_ONLY"
    return result


def derive_current_generated_epistemic_program_candidates(
    *,
    decision_context: EpistemicDecisionBearingContext,
    start_state_id: str,
    capabilities: CapabilityRegistry,
    obligation: QueryObligation,
    max_nodes: int = 64,
) -> dict[str, Any]:
    """Generate content-bound program candidates from the internally derived search surface."""
    search = search_current_represented_discriminating_programs(
        decision_context=decision_context, start_state_id=start_state_id,
        capabilities=capabilities, obligation=obligation, max_nodes=max_nodes,
    )
    if search.get("status") != "REPRESENTED_INFORMATIVE_PROGRAMS_FOUND":
        return {**search, "candidates": ()}
    lookups = tuple({(r.state_id, r.capability_id): r for r in rows} for rows in decision_context.relation_sets)
    candidates: list[GeneratedEpistemicProgramCandidate] = []
    for steps in search.get("programs", ()):
        relation_digests: set[str] = set()
        frame_epochs: set[tuple[str, int]] = set()
        complete = True
        for lookup in lookups:
            cur = str(start_state_id)
            for action in steps:
                rel = lookup.get((cur, action))
                if rel is None:
                    complete = False
                    break
                relation_digests.add(rel.digest())
                frame_epochs.add(rel.frame_epoch)
                cur = rel.next_state_id
            if not complete:
                break
        if not complete or not relation_digests:
            continue
        temp = GeneratedEpistemicProgramCandidate(
            candidate_id="GENERATED-TEMP", steps=tuple(steps),
            source_relation_digests=tuple(sorted(relation_digests)),
            frame_epochs=tuple(sorted(frame_epochs)),
        )
        digest = temp.digest()
        candidates.append(GeneratedEpistemicProgramCandidate(
            candidate_id="generated-epistemic-program-" + digest[:20],
            steps=temp.steps, source_relation_digests=temp.source_relation_digests,
            frame_epochs=temp.frame_epochs, assistance_ancestry=temp.assistance_ancestry,
        ))
    return {**search, "candidates": tuple(candidates), "candidate_count": len(candidates)}


def search_represented_discriminating_programs(
    *,
    decision_context: EpistemicDecisionBearingContext,
    start_state_id: str,
    action_tokens: tuple[str, ...],
    max_nodes: int = 64,
) -> dict[str, Any]:
    """Search query-local represented reachability without a program-depth knob.

    While every live alternative predicts the same next opaque state, that common
    state is one nondiscriminating search node.  An action whose predicted next
    states diverge yields a proposal-only program witness.  Revisited common states
    are extensional aliases for this current query and are not re-expanded.

    This is *not* physical/generated-affordance closure: the relational alternatives,
    action token set and state identity are represented inputs.  Budget exhaustion
    is reported separately from an exhausted represented fixpoint.
    """
    if int(max_nodes) < 1:
        raise ValueError("REPRESENTED_PROGRAM_SEARCH_REQUIRES_POSITIVE_NODE_BUDGET")
    actions = tuple(sorted(set(str(x) for x in action_tokens if str(x))))
    if not actions or len(decision_context.relation_sets) < 2:
        return {
            "status": "UNKNOWN_INCOMPLETE", "reason": "MULTIPLE_ALTERNATIVES_AND_ACTION_TOKENS_REQUIRED",
            "programs": (), "nodes_expanded": 0, "visited_common_states": (),
            "truth_authority": "NONE", "execution_authority": "NONE", "closure_authority": "NONE",
        }
    lookups = tuple({(r.state_id, r.capability_id): r for r in rows} for rows in decision_context.relation_sets)
    queue: list[tuple[str, tuple[str, ...]]] = [(str(start_state_id), ())]
    visited = {str(start_state_id)}
    programs: set[tuple[str, ...]] = set()
    nodes = 0
    unresolved_edges = 0
    while queue:
        if nodes >= int(max_nodes):
            return {
                "status": "SEARCH_BUDGET_EXHAUSTED_NOT_SATURATED", "reason": "REPRESENTED_PROGRAM_NODE_BUDGET_EXHAUSTED",
                "programs": tuple(sorted(programs)), "nodes_expanded": nodes,
                "visited_common_states": tuple(sorted(visited)), "unresolved_edges": unresolved_edges,
                "truth_authority": "NONE", "execution_authority": "NONE", "closure_authority": "NONE",
            }
        state, prefix = queue.pop(0)
        nodes += 1
        for action in actions:
            rels = tuple(lookup.get((state, action)) for lookup in lookups)
            if any(rel is None for rel in rels):
                unresolved_edges += 1
                continue
            next_states = tuple(rel.next_state_id for rel in rels if rel is not None)
            word = prefix + (action,)
            if len(set(next_states)) > 1:
                programs.add(word)
                continue
            nxt = next_states[0]
            if nxt not in visited:
                visited.add(nxt)
                queue.append((nxt, word))
    if programs:
        return {
            "status": "REPRESENTED_INFORMATIVE_PROGRAMS_FOUND",
            "reason": "REPRESENTED_DISCRIMINATING_WITNESS_FOUND",
            "programs": tuple(sorted(programs)), "nodes_expanded": nodes,
            "visited_common_states": tuple(sorted(visited)), "unresolved_edges": unresolved_edges,
            "search_complete": unresolved_edges == 0,
            "truth_authority": "NONE", "execution_authority": "NONE",
            "closure_authority": "REPRESENTED_QUERY_LOCAL_ONLY" if unresolved_edges == 0 else "NONE",
            "generator_equivalence_authority": "NONE", "physical_affordance_closure_authority": "NONE",
        }
    if unresolved_edges:
        return {
            "status": "REPRESENTED_REACHABILITY_INCOMPLETE",
            "reason": "CURRENT_GENERATOR_TRANSITION_UNREPRESENTED",
            "programs": (), "nodes_expanded": nodes,
            "visited_common_states": tuple(sorted(visited)), "unresolved_edges": unresolved_edges,
            "search_complete": False,
            "truth_authority": "NONE", "execution_authority": "NONE", "closure_authority": "NONE",
            "generator_equivalence_authority": "NONE", "physical_affordance_closure_authority": "NONE",
        }
    return {
        "status": "REPRESENTED_REACHABILITY_FIXPOINT_NO_DISCRIMINATOR",
        "reason": "NO_DISCRIMINATOR_IN_REPRESENTED_REACHABILITY_FIXPOINT",
        "programs": (), "nodes_expanded": nodes,
        "visited_common_states": tuple(sorted(visited)), "unresolved_edges": 0,
        "search_complete": True,
        "truth_authority": "NONE", "execution_authority": "NONE",
        "closure_authority": "REPRESENTED_QUERY_LOCAL_ONLY",
    }


def program_partition_strictly_refines(
    left: tuple[tuple[int, ...], ...], right: tuple[tuple[int, ...], ...],
) -> bool:
    """True only when ``left`` is a strict set-partition refinement of ``right``."""
    if left == right:
        return False
    lsets = tuple(set(x) for x in left)
    rsets = tuple(set(x) for x in right)
    universe_left = set().union(*lsets) if lsets else set()
    universe_right = set().union(*rsets) if rsets else set()
    if universe_left != universe_right:
        return False
    return all(any(block <= parent for parent in rsets) for block in lsets)


def derive_current_decision_bearing_commitment(
    *,
    trial: EpistemicProgramTrial,
    deficit: EpistemicDeficitRecord | None,
    decision_context: EpistemicDecisionBearingContext,
    capabilities: CapabilityRegistry,
    values,
    current_frame_epochs: Mapping[str, int],
    current_episode_epochs: Mapping[str, int],
    current_topology_epochs: Mapping[str, int],
    current_coordination_epochs: Mapping[str, int],
) -> RelationalCommitment:
    ancestry_ok, ancestry_reason, _ = derive_epistemic_program_relation_ancestry_status(
        trial=trial, decision_context=decision_context,
    )
    if not ancestry_ok:
        return RelationalCommitment(
            _sha({"program_relation_ancestry": ancestry_reason, "trial": trial.trial_id}),
            f"epistemic-program:{trial.trial_id}:decision-bearing",
            TernaryCommitment.UNKNOWN, binding=TernaryCommitment.UNKNOWN,
            reason=ancestry_reason, qualifiers=(("authority_gain", "NONE"),),
            premise_ids=(trial.trial_id,),
        )
    options = []
    for target, fid, fob in decision_context.feasibility_routes:
        option, _ = derive_grounded_feasibility_option(
            target_capability_id=target, feasibility_capability_id=fid,
            feasibility_obligation=fob, capabilities=capabilities,
        )
        options.append(option)
    relation_sets = tuple(
        {(r.state_id, r.capability_id): r for r in rows}
        for rows in decision_context.relation_sets
    )
    return derive_regulatory_decision_bearing_commitment(
        deficit=deficit, values=values, relation_sets=relation_sets, options=tuple(options),
        start_state_id=_expected_state(trial)[0],
        current_capability_epochs=dict(capabilities.epochs),
        current_capability_signatures={cid: contract.computed_signature_sha256() for cid, contract in capabilities.contracts.items()},
        current_frame_epochs=current_frame_epochs, current_episode_epochs=current_episode_epochs,
        current_topology_epochs=current_topology_epochs, current_coordination_epochs=current_coordination_epochs,
    )


def derive_current_program_discrimination_commitment(*, trial: EpistemicProgramTrial, decision_context: EpistemicDecisionBearingContext, decision_bearing_commitment: RelationalCommitment) -> RelationalCommitment:
    ancestry_ok, ancestry_reason, _ = derive_epistemic_program_relation_ancestry_status(
        trial=trial, decision_context=decision_context,
    )
    if not ancestry_ok:
        return RelationalCommitment(
            _sha({"program_relation_ancestry": ancestry_reason, "trial": trial.trial_id, "kind": "information"}),
            f"epistemic-program:{trial.trial_id}:information",
            TernaryCommitment.UNKNOWN, binding=TernaryCommitment.UNKNOWN,
            reason=ancestry_reason, qualifiers=(("authority_gain", "NONE"),),
            premise_ids=(trial.trial_id, decision_bearing_commitment.commitment_id),
        )
    relation_sets=tuple({(r.state_id,r.capability_id):r for r in rows} for rows in decision_context.relation_sets)
    return derive_program_trace_discrimination_commitment(trial=trial,relation_sets=relation_sets,decision_bearing_commitment=decision_bearing_commitment)


def _expected_state(trial: EpistemicProgramTrial) -> tuple[str, str]:
    if not trial.step_records:
        return trial.start_state_id, trial.start_state_evidence_id
    last = trial.step_records[-1]
    return last.actual_next_state_id, last.outcome_evidence_id


def _route_commitment(
    *,
    trial: EpistemicProgramTrial,
    capabilities: CapabilityRegistry,
    obligation: QueryObligation,
    current_frame_epochs: Mapping[str, int],
    current_state: OpaqueControlStateWitness | None,
) -> RelationalCommitment:
    idx = len(trial.step_records)
    target = f"epistemic-program:{trial.trial_id}:step:{idx}"
    if trial.status != "OPEN" or idx >= len(trial.steps):
        return RelationalCommitment(
            _sha({"route": target, "status": trial.status}), target,
            TernaryCommitment.NO, reason="EPISTEMIC_PROGRAM_NOT_OPEN",
            qualifiers=(("authority_gain", "NONE"),), premise_ids=(trial.trial_id,),
        )
    expected_state, expected_evidence = _expected_state(trial)
    if current_state is None:
        return RelationalCommitment(
            _sha({"route": target, "state": "missing"}), target,
            TernaryCommitment.UNKNOWN, binding=TernaryCommitment.UNKNOWN,
            reason="CURRENT_CONTROL_STATE_REQUIRED", qualifiers=(("authority_gain", "NONE"),),
            premise_ids=(trial.trial_id,),
        )
    if current_state.state_id != expected_state or current_state.evidence_id != expected_evidence:
        return RelationalCommitment(
            _sha({"route": target, "state": current_state.serializable()}), target,
            TernaryCommitment.UNKNOWN, applicability=TernaryCommitment.NO,
            reason="EPISTEMIC_PROGRAM_CONTROL_STATE_NOT_APPLICABLE",
            qualifiers=(("authority_gain", "NONE"),), premise_ids=(trial.trial_id,),
        )
    if obligation.required_authority != Authority.EFFECT or obligation.obligation_id != trial.obligation_id or obligation.operational_scope_id != trial.operational_scope_id:
        return RelationalCommitment(
            _sha({"route": target, "obligation": obligation.obligation_id, "scope": obligation.operational_scope_id}), target,
            TernaryCommitment.NO, reason="EPISTEMIC_PROGRAM_OBLIGATION_OR_SCOPE_DRIFT",
            qualifiers=(("authority_gain", "NONE"),), premise_ids=(trial.trial_id,),
        )
    for fid, epoch in trial.frame_epochs:
        if current_frame_epochs.get(fid) != epoch:
            return RelationalCommitment(
                _sha({"route": target, "frame": fid, "epoch": current_frame_epochs.get(fid)}), target,
                TernaryCommitment.UNKNOWN, reason=f"EPISTEMIC_PROGRAM_FRAME_DRIFT:{fid}",
                qualifiers=(("authority_gain", "NONE"),), premise_ids=(trial.trial_id,),
            )
    epochs = dict(trial.capability_epochs)
    sigs = dict(trial.capability_signatures)
    cid = trial.steps[idx]
    cap = capabilities.contracts.get(cid)
    if cap is None:
        return RelationalCommitment(
            _sha({"route": target, "cap": cid, "missing": True}), target,
            TernaryCommitment.UNKNOWN, reason=f"EPISTEMIC_PROGRAM_COMPONENT_MISSING:{cid}",
            qualifiers=(("authority_gain", "NONE"),), premise_ids=(trial.trial_id,),
        )
    q = project_qualification_state(
        cap.qualification,
        commitment_id=_sha({"qualification": cid, "epoch": capabilities.epochs.get(cid)}),
        target_id=f"capability:{cid}:qualification",
        premise_ids=(cid,),
    )
    if not q.licenses_yes() or cap.currentness != "CURRENT" or capabilities.epochs.get(cid) != epochs.get(cid) or cap.computed_signature_sha256() != sigs.get(cid):
        return RelationalCommitment(
            _sha({"route": target, "cap": cid, "current": False}), target,
            TernaryCommitment.UNKNOWN, reason=f"EPISTEMIC_PROGRAM_COMPONENT_NOT_CURRENT:{cid}",
            qualifiers=(("authority_gain", "NONE"),), premise_ids=(trial.trial_id, cid),
        )
    if cap.authority != Authority.EFFECT:
        return RelationalCommitment(
            _sha({"route": target, "cap": cid, "authority": cap.authority.value}), target,
            TernaryCommitment.NO, reason=f"EPISTEMIC_PROGRAM_COMPONENT_NOT_EFFECT:{cid}",
            qualifiers=(("authority_gain", "NONE"),), premise_ids=(trial.trial_id, cid),
        )
    if cap.query_obligation_id and cap.query_obligation_id != obligation.obligation_id:
        return RelationalCommitment(
            _sha({"route": target, "cap": cid, "query": obligation.obligation_id}), target,
            TernaryCommitment.NO, reason=f"QUERY_OBLIGATION_MISMATCH:{cid}",
            qualifiers=(("authority_gain", "NONE"),), premise_ids=(trial.trial_id, cid),
        )
    if cap.operational_scope_id and cap.operational_scope_id != obligation.operational_scope_id:
        return RelationalCommitment(
            _sha({"route": target, "cap": cid, "scope": obligation.operational_scope_id}), target,
            TernaryCommitment.NO, reason=f"OPERATIONAL_SCOPE_MISMATCH:{cid}",
            qualifiers=(("authority_gain", "NONE"),), premise_ids=(trial.trial_id, cid),
        )
    return RelationalCommitment(
        _sha({"route": target, "trial": trial.digest(), "state": current_state.serializable(), "cap": cid, "signature": sigs[cid]}),
        target, TernaryCommitment.YES, reason="EPISTEMIC_PROGRAM_CURRENT_ROUTE",
        qualifiers=(("authority_gain", "NONE"), ("execution_authority", "NONE"), ("truth_authority", "NONE")),
        premise_ids=(trial.trial_id, cid),
    )


def derive_epistemic_program_step_commitment(
    *,
    trial: EpistemicProgramTrial,
    deficit: EpistemicDeficitRecord | None,
    feasibility: RecruitmentOption,
    capabilities: CapabilityRegistry,
    obligation: QueryObligation,
    current_frame_epochs: Mapping[str, int],
    current_state: OpaqueControlStateWitness | None,
    priority_commitment: RelationalCommitment | None = None,
    information_commitment: RelationalCommitment | None = None,
) -> RelationalCommitment:
    idx = len(trial.step_records)
    target = f"epistemic-program:{trial.trial_id}:step:{idx}"
    expected_cid = trial.steps[idx] if trial.status == "OPEN" and idx < len(trial.steps) else "NONE"

    if deficit is None or deficit.deficit_id != trial.deficit_id:
        need = RelationalCommitment(
            _sha({"need": target, "deficit": None}), target,
            TernaryCommitment.UNKNOWN, binding=TernaryCommitment.UNKNOWN,
            reason="EPISTEMIC_DEFICIT_NOT_FOUND", qualifiers=(("authority_gain", "NONE"),),
        )
    elif deficit.state != EpistemicDeficitState.ACTION_LIMITED:
        need = RelationalCommitment(
            _sha({"need": target, "state": deficit.state.value}), target,
            TernaryCommitment.UNKNOWN, reason=f"EPISTEMIC_DEFICIT_NOT_ACTION_LIMITED:{deficit.state.value}",
            qualifiers=(("authority_gain", "NONE"),), premise_ids=(deficit.deficit_id,),
        )
    elif deficit.missing_discriminator_signature_sha256 != trial.discrimination_signature_sha256:
        need = RelationalCommitment(
            _sha({"need": target, "disc": deficit.missing_discriminator_signature_sha256}), target,
            TernaryCommitment.UNKNOWN, reason="EPISTEMIC_DISCRIMINATION_SIGNATURE_MISMATCH",
            qualifiers=(("authority_gain", "NONE"),), premise_ids=(deficit.deficit_id,),
        )
    else:
        need = RelationalCommitment(
            _sha({"need": target, "deficit": deficit.serializable(), "trial": trial.digest()}), target,
            TernaryCommitment.YES, reason="CURRENT_ACTION_LIMITED_DISCRIMINATION_NEED",
            qualifiers=(("authority_gain", "NONE"), ("semantic_goal_authority", "NONE"), ("truth_authority", "NONE")),
            premise_ids=(deficit.deficit_id, deficit.unknown_evidence_id),
        )

    if feasibility.capability_id != expected_cid:
        feas = RelationalCommitment(
            _sha({"feas": target, "cap": feasibility.capability_id}), target,
            TernaryCommitment.NO, reason="FEASIBILITY_INPUT_FOR_WRONG_COMPONENT",
            qualifiers=(("authority_gain", "NONE"),), premise_ids=tuple(feasibility.model_evidence_ids),
        )
    else:
        feas = project_feasibility(
            feasibility.feasibility,
            commitment_id=_sha({"feasibility": target, "content": feasibility.serializable()}),
            target_id=target,
            premise_ids=tuple(feasibility.model_evidence_ids),
        )

    route = _route_commitment(
        trial=trial, capabilities=capabilities, obligation=obligation,
        current_frame_epochs=current_frame_epochs, current_state=current_state,
    )
    if priority_commitment is None:
        required=(need,feas,route)
    elif information_commitment is None:
        required=(need,priority_commitment,feas,route)
    else:
        required=(need,priority_commitment,information_commitment,feas,route)
    combined = conjoin_required_commitments(
        required, commitment_id=_sha({"epistemic-step": target, "premises": [x.commitment_id for x in required]}),
        target_id=target, reason_prefix="EPISTEMIC_PROGRAM_STEP",
    )
    return RelationalCommitment(
        commitment_id=combined.commitment_id,
        target_id=combined.target_id,
        commitment=combined.commitment,
        binding=combined.binding,
        applicability=combined.applicability,
        reason=combined.reason,
        qualifiers=combined.qualifiers + (
            ("trial_id", trial.trial_id),
            ("trial_digest", trial.digest()),
            ("deficit_id", trial.deficit_id),
            ("question_key", "" if deficit is None else deficit.question_key),
            ("step_index", str(idx)),
            ("expected_capability_id", expected_cid),
            ("feasibility_digest", feasibility_digest(feasibility)),
            ("proposal_authority", "NONE"),
            ("execution_authority", "NONE"),
            ("truth_authority", "NONE"),
            ("semantic_goal_authority", "NONE"),
        ),
        premise_ids=combined.premise_ids,
    )


def nominate_epistemic_program_step_intent(
    *,
    trial: EpistemicProgramTrial,
    deficit: EpistemicDeficitRecord | None,
    feasibility: RecruitmentOption,
    capabilities: CapabilityRegistry,
    obligation: QueryObligation,
    current_frame_epochs: Mapping[str, int],
    current_state: OpaqueControlStateWitness | None,
    priority_commitment: RelationalCommitment | None = None,
    information_commitment: RelationalCommitment | None = None,
) -> tuple[BoundedActionIntent | None, RelationalCommitment]:
    commitment = derive_epistemic_program_step_commitment(
        trial=trial, deficit=deficit, feasibility=feasibility, capabilities=capabilities,
        obligation=obligation, current_frame_epochs=current_frame_epochs, current_state=current_state,
        priority_commitment=priority_commitment, information_commitment=information_commitment,
    )
    if not commitment.licenses_yes() or current_state is None:
        return None, commitment
    idx = len(trial.step_records)
    cid = trial.steps[idx]
    payload = {
        "basis": "EPISTEMIC_PROGRAM_STEP",
        "trial": trial.trial_id,
        "trial_digest": trial.digest(),
        "commitment": commitment.commitment_id,
        "capability": cid,
        "capability_epoch": capabilities.epochs[cid],
        "state": current_state.serializable(),
        "obligation": obligation.obligation_id,
        "scope": obligation.operational_scope_id,
    }
    intent_id = "ACTION-INTENT-" + _sha(payload)[:24]
    return BoundedActionIntent(
        intent_id=intent_id,
        proposal_id=trial.trial_id,
        proposal_digest=trial.digest(),
        action_commitment=commitment,
        capability_id=cid,
        capability_epoch=capabilities.epochs[cid],
        start_state_id=current_state.state_id,
        control_state_evidence_id=current_state.evidence_id,
        expected_next_state_id=None,
        expected_value_effect=None,
        value_epoch=None,
        obligation_id=obligation.obligation_id,
        operational_scope_id=obligation.operational_scope_id,
        basis_kind="EPISTEMIC_PROGRAM_STEP",
        authority=Authority.MODEL_OUTPUT_ONLY.value,
        execution_authority="NONE",
        truth_authority="NONE",
        semantic_intention_authority="NONE",
    ), commitment
