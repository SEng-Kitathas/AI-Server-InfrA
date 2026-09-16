from __future__ import annotations
import hashlib, json
from typing import Iterable, Mapping

from ..runtime.commitment import RelationalCommitment, TernaryCommitment
from .epistemic import EpistemicDeficitRecord, EpistemicDeficitState
from .recruitment import RecruitmentOption
from .rehearsal import CounterfactualRehearsalConfig, RehearsalTransitionRelation, propose_counterfactual_rehearsal
from .value import ValueVariableRegistry


def _sha(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def derive_regulatory_decision_bearing_commitment(
    *,
    deficit: EpistemicDeficitRecord | None,
    values: ValueVariableRegistry,
    relation_sets: Iterable[Mapping[tuple[str, str], RehearsalTransitionRelation]],
    options: Iterable[RecruitmentOption],
    start_state_id: str,
    current_capability_epochs: Mapping[str, int],
    current_frame_epochs: Mapping[str, int],
    current_episode_epochs: Mapping[str, int],
    current_topology_epochs: Mapping[str, int] | None = None,
    current_coordination_epochs: Mapping[str, int] | None = None,
    current_capability_signatures: Mapping[str, str] | None = None,
) -> RelationalCommitment:
    """Derive bounded normative priority from current regulatory decision divergence.

    This is not curiosity and not a scheduler.  It asks only whether the supplied
    live relational alternatives would choose different *currently executable*
    first actions under one current constitutional regulatory pressure.  The
    result grants no truth, semantic-goal, selection, or execution authority.
    """
    target = "epistemic-decision-bearing:" + ("NONE" if deficit is None else deficit.deficit_id)
    qnone = (("authority_gain", "NONE"), ("execution_authority", "NONE"), ("truth_authority", "NONE"), ("semantic_goal_authority", "NONE"))
    if deficit is None or deficit.state != EpistemicDeficitState.ACTION_LIMITED:
        return RelationalCommitment(_sha({"target": target, "deficit": None}), target, TernaryCommitment.UNKNOWN, reason="ACTION_LIMITED_DEFICIT_REQUIRED", qualifiers=qnone)
    value_anchors = [a for a in deficit.premise_anchors if a.kind == "VALUE"]
    if len(value_anchors) != 1:
        return RelationalCommitment(_sha({"target": target, "anchors": [a.serializable() for a in deficit.premise_anchors]}), target, TernaryCommitment.UNKNOWN, reason="EXACT_CURRENT_VALUE_ANCHOR_REQUIRED", qualifiers=qnone, premise_ids=(deficit.deficit_id,))
    anchor = value_anchors[0]
    if not values.is_current(anchor.object_id, anchor.epoch):
        return RelationalCommitment(_sha({"target": target, "value": anchor.serializable(), "current": False}), target, TernaryCommitment.UNKNOWN, reason="VALUE_PREMISE_NOT_CURRENT", qualifiers=qnone, premise_ids=(deficit.deficit_id, anchor.object_id))
    pressure = values.pressure(anchor.object_id)
    if pressure.get("status") != "CURRENT":
        return RelationalCommitment(_sha({"target": target, "pressure": pressure}), target, TernaryCommitment.UNKNOWN, reason="CURRENT_VALUE_OBSERVATION_REQUIRED", qualifiers=qnone, premise_ids=(deficit.deficit_id, anchor.object_id))
    if float(pressure.get("pressure_magnitude", 0.0)) <= 0.0:
        return RelationalCommitment(_sha({"target": target, "pressure": pressure}), target, TernaryCommitment.NO, reason="NO_CURRENT_REGULATORY_PRESSURE", qualifiers=qnone, premise_ids=(deficit.deficit_id, anchor.object_id))

    rows = tuple(dict(x) for x in relation_sets)
    if len(rows) < 2:
        return RelationalCommitment(_sha({"target": target, "alternatives": len(rows)}), target, TernaryCommitment.UNKNOWN, reason="MULTIPLE_LIVE_RELATIONAL_ALTERNATIVES_REQUIRED", qualifiers=qnone, premise_ids=(deficit.deficit_id,))

    tcur = current_topology_epochs or {}
    ccur = current_coordination_epochs or {}
    sigcur = current_capability_signatures or {}
    for rs in rows:
        for rel in rs.values():
            if rel.value_epoch is not None and rel.value_epoch != (anchor.object_id, anchor.epoch):
                return RelationalCommitment(_sha({"target": target, "relation_value_epoch": rel.value_epoch, "required_value_epoch": (anchor.object_id, anchor.epoch)}), target, TernaryCommitment.UNKNOWN, reason=f"RELATIONAL_ALTERNATIVE_VALUE_COORDINATE_MISMATCH:{rel.value_epoch[0]}", qualifiers=qnone, premise_ids=(deficit.deficit_id,))
            if current_capability_epochs.get(rel.capability_id) != rel.capability_epoch:
                return RelationalCommitment(_sha({"target": target, "capability": rel.capability_id}), target, TernaryCommitment.UNKNOWN, reason=f"RELATIONAL_ALTERNATIVE_CAPABILITY_EPOCH_DRIFT:{rel.capability_id}", qualifiers=qnone, premise_ids=(deficit.deficit_id,))
            if current_frame_epochs.get(rel.frame_epoch[0]) != rel.frame_epoch[1]:
                return RelationalCommitment(_sha({"target": target, "frame": rel.frame_epoch}), target, TernaryCommitment.UNKNOWN, reason=f"RELATIONAL_ALTERNATIVE_FRAME_EPOCH_DRIFT:{rel.frame_epoch[0]}", qualifiers=qnone, premise_ids=(deficit.deficit_id,))
            if current_episode_epochs.get(rel.episode_schema_epoch[0]) != rel.episode_schema_epoch[1]:
                return RelationalCommitment(_sha({"target": target, "episode": rel.episode_schema_epoch}), target, TernaryCommitment.UNKNOWN, reason=f"RELATIONAL_ALTERNATIVE_EPISODE_EPOCH_DRIFT:{rel.episode_schema_epoch[0]}", qualifiers=qnone, premise_ids=(deficit.deficit_id,))
            if rel.topology_epoch is not None and tcur.get(rel.topology_epoch[0]) != rel.topology_epoch[1]:
                return RelationalCommitment(_sha({"target": target, "topology": rel.topology_epoch}), target, TernaryCommitment.UNKNOWN, reason=f"RELATIONAL_ALTERNATIVE_TOPOLOGY_EPOCH_DRIFT:{rel.topology_epoch[0]}", qualifiers=qnone, premise_ids=(deficit.deficit_id,))
            if rel.coordination_epoch is not None and ccur.get(rel.coordination_epoch[0]) != rel.coordination_epoch[1]:
                return RelationalCommitment(_sha({"target": target, "coordination": rel.coordination_epoch}), target, TernaryCommitment.UNKNOWN, reason=f"RELATIONAL_ALTERNATIVE_COORDINATION_EPOCH_DRIFT:{rel.coordination_epoch[0]}", qualifiers=qnone, premise_ids=(deficit.deficit_id,))
            for cid, epoch in rel.evidence_premise_epochs:
                if current_capability_epochs.get(cid) != epoch:
                    return RelationalCommitment(_sha({"target": target, "evidence_premise_epoch": (cid, epoch)}), target, TernaryCommitment.UNKNOWN, reason=f"RELATIONAL_ALTERNATIVE_EVIDENCE_PREMISE_EPOCH_DRIFT:{cid}", qualifiers=qnone, premise_ids=(deficit.deficit_id,))
            for cid, signature in rel.evidence_premise_signatures:
                if sigcur.get(cid) != signature:
                    return RelationalCommitment(_sha({"target": target, "evidence_premise_signature": (cid, signature)}), target, TernaryCommitment.UNKNOWN, reason=f"RELATIONAL_ALTERNATIVE_EVIDENCE_PREMISE_SIGNATURE_DRIFT:{cid}", qualifiers=qnone, premise_ids=(deficit.deficit_id,))

    contract = values.contracts[anchor.object_id]
    latest = values.latest.get(anchor.object_id)
    if latest is None or latest[0] != anchor.epoch:
        return RelationalCommitment(_sha({"target": target, "latest": latest}), target, TernaryCommitment.UNKNOWN, reason="CURRENT_VALUE_OBSERVATION_REQUIRED", qualifiers=qnone, premise_ids=(deficit.deficit_id, anchor.object_id))
    cfg = CounterfactualRehearsalConfig(max_horizon=1, max_nodes=64, min_support=1, min_consistency=0.99)
    opts = tuple(options)
    first_actions: list[str] = []
    proposal_digests: list[str] = []
    for rs in rows:
        p = propose_counterfactual_rehearsal(
            rs, start_state_id=str(start_state_id), start_value=float(latest[1]),
            viable_low=float(contract.viable_low), viable_high=float(contract.viable_high),
            value_epoch=(anchor.object_id, anchor.epoch), options=opts, cfg=cfg,
        )
        if p is None or not p.sequence:
            return RelationalCommitment(_sha({"target": target, "proposal": None}), target, TernaryCommitment.UNKNOWN, reason="HYPOTHESIS_CONDITIONED_EXECUTABLE_ACTION_UNRESOLVED", qualifiers=qnone, premise_ids=(deficit.deficit_id, anchor.object_id))
        first_actions.append(p.sequence[0]); proposal_digests.append(p.digest())
    stance = TernaryCommitment.YES if len(set(first_actions)) > 1 else TernaryCommitment.NO
    reason = "DISCRIMINATION_CAN_CHANGE_CURRENT_REGULATORY_ACTION" if stance == TernaryCommitment.YES else "DISCRIMINATION_CANNOT_CHANGE_CURRENT_EXECUTABLE_ACTION"
    cid = _sha({"target": target, "deficit": deficit.serializable(), "pressure": pressure, "first_actions": first_actions, "proposals": proposal_digests, "options": [o.serializable() for o in opts]})
    return RelationalCommitment(
        cid, target, stance, reason=reason,
        qualifiers=qnone + (("first_actions", "|".join(first_actions)), ("value_id", anchor.object_id), ("value_epoch", str(anchor.epoch))),
        premise_ids=(deficit.deficit_id, deficit.unknown_evidence_id, anchor.object_id),
    )


def derive_program_trace_discrimination_commitment(
    *,
    trial,
    relation_sets: Iterable[Mapping[tuple[str, str], RehearsalTransitionRelation]],
    decision_bearing_commitment: RelationalCommitment,
) -> RelationalCommitment:
    """Ask whether the remaining embodied program can change observable evidence.

    The relation alternatives are representation-only inputs.  This adapter does
    not select, schedule, execute, or qualify anything.  It only compares the
    *observable opaque state traces* predicted by the already-represented
    remaining program under the same live alternatives whose currentness was
    established by ``decision_bearing_commitment``.
    """
    idx=len(trial.step_records)
    target=f"epistemic-program-information:{trial.trial_id}:step:{idx}"
    qnone=(("authority_gain","NONE"),("execution_authority","NONE"),("truth_authority","NONE"),("selection_authority","NONE"))
    if not decision_bearing_commitment.licenses_yes():
        return RelationalCommitment(_sha({"target":target,"priority":decision_bearing_commitment.commitment_id}),target,TernaryCommitment.UNKNOWN,reason="CURRENT_DECISION_BEARING_PREMISE_REQUIRED",qualifiers=qnone,premise_ids=(decision_bearing_commitment.commitment_id,))
    if trial.status!="OPEN" or idx>=len(trial.steps):
        return RelationalCommitment(_sha({"target":target,"trial":trial.digest()}),target,TernaryCommitment.NO,reason="NO_OPEN_PROGRAM_REMAINDER",qualifiers=qnone,premise_ids=(trial.trial_id,decision_bearing_commitment.commitment_id))
    state=trial.start_state_id if idx==0 else trial.step_records[-1].actual_next_state_id
    remaining=trial.steps[idx:]
    rows=tuple(dict(x) for x in relation_sets)
    if len(rows)<2:
        return RelationalCommitment(_sha({"target":target,"alternatives":len(rows)}),target,TernaryCommitment.UNKNOWN,reason="MULTIPLE_LIVE_RELATIONAL_ALTERNATIVES_REQUIRED",qualifiers=qnone,premise_ids=(trial.trial_id,decision_bearing_commitment.commitment_id))
    traces=[]
    for rs in rows:
        cur=state; trace=[]
        for action in remaining:
            rel=rs.get((cur,action))
            if rel is None:
                return RelationalCommitment(_sha({"target":target,"missing":[cur,action]}),target,TernaryCommitment.UNKNOWN,reason=f"PROGRAM_OBSERVABLE_TRACE_UNRESOLVED:{cur}:{action}",qualifiers=qnone,premise_ids=(trial.trial_id,decision_bearing_commitment.commitment_id))
            cur=rel.next_state_id; trace.append(cur)
        traces.append(tuple(trace))
    stance=TernaryCommitment.YES if len(set(traces))>1 else TernaryCommitment.NO
    reason="PROGRAM_CAN_CHANGE_OBSERVABLE_EVIDENCE" if stance==TernaryCommitment.YES else "PROGRAM_CANNOT_CHANGE_OBSERVABLE_EVIDENCE"
    return RelationalCommitment(
        _sha({"target":target,"trial":trial.digest(),"traces":traces,"priority":decision_bearing_commitment.commitment_id}),target,stance,reason=reason,
        qualifiers=qnone+(("predicted_trace_count",str(len(set(traces)))),),
        premise_ids=(trial.trial_id,decision_bearing_commitment.commitment_id),
    )
