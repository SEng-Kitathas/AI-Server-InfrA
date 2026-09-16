from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any, Mapping

from ..evidence.ledger import canonical_json, sha256_bytes
from ..runtime.capabilities import CapabilityRegistry
from ..runtime.types import Authority, QualificationState, QueryObligation
from .action_closure import ActionExecutionRecord, ActionOutcomeRecord, BoundedActionIntent
from .relational_algebra import OpaqueActionCompositionCandidate


def _sha256_token(value: str, *, error: str) -> str:
    v=str(value).lower()
    if len(v)!=64 or any(c not in '0123456789abcdef' for c in v):
        raise ValueError(error)
    return v


@dataclass(frozen=True)
class GeneratedEpistemicProgramCandidate:
    """Proposal-only ordered program generated from represented relational evidence.

    The carrier says only that an ordered primitive sequence is a current represented
    epistemic-program witness under the bound relation/frame ancestry. It does not
    establish physical closure, generator novelty, truth, qualification, feasibility,
    selection, or execution authority.
    """
    candidate_id: str
    steps: tuple[str, ...]
    source_relation_digests: tuple[str, ...]
    frame_epochs: tuple[tuple[str, int], ...]
    assistance_ancestry: tuple[str, ...] = (
        "REPRESENTED_RELATIONAL_ALTERNATIVE_SURFACE",
        "QUERY_LOCAL_REPRESENTED_REACHABILITY_SEARCH",
    )
    proposal_authority: str = "NONE"
    qualification_authority: str = "NONE"
    truth_authority: str = "NONE"
    execution_authority: str = "NONE"
    semantic_action_authority: str = "NONE"
    closure_authority: str = "NONE"

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.steps or not self.source_relation_digests:
            raise ValueError("INCOMPLETE_GENERATED_EPISTEMIC_PROGRAM_CANDIDATE")
        if any(not step for step in self.steps):
            raise ValueError("GENERATED_EPISTEMIC_PROGRAM_EMPTY_STEP")
        for digest in self.source_relation_digests:
            _sha256_token(digest, error="GENERATED_PROGRAM_RELATION_DIGEST_REQUIRED")
        if any(int(epoch) < 0 or not fid for fid, epoch in self.frame_epochs):
            raise ValueError("GENERATED_PROGRAM_FRAME_ANCESTRY_INVALID")
        if any(x != "NONE" for x in (
            self.proposal_authority, self.qualification_authority, self.truth_authority,
            self.execution_authority, self.semantic_action_authority, self.closure_authority,
        )):
            raise ValueError("GENERATED_EPISTEMIC_PROGRAM_AUTHORITY_ESCALATION")

    def serializable(self) -> dict[str, Any]:
        d=asdict(self); d["steps"]=list(self.steps); d["source_relation_digests"]=list(self.source_relation_digests); d["frame_epochs"]=[list(x) for x in self.frame_epochs]; d["assistance_ancestry"]=list(self.assistance_ancestry); return d

    def digest(self) -> str:
        payload=self.serializable().copy(); payload.pop("candidate_id",None)
        return sha256_bytes(canonical_json(payload))


@dataclass(frozen=True)
class EpistemicProgramStepRecord:
    step_index: int
    capability_id: str
    capability_epoch: int
    intent_id: str
    execution_id: str
    outcome_id: str
    outcome_evidence_id: str
    actual_next_state_id: str
    prediction_commitment: str

    def serializable(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EpistemicProgramTrial:
    """Proposal-only binding over ordinary, already-executed action records.

    This object does not execute, schedule, qualify, infer physical actuator
    identity, or grant truth. It only preserves that a selected relational
    discriminator was attempted as one ordered epistemic trial.
    """

    trial_id: str
    deficit_id: str
    discrimination_signature_sha256: str
    relation_candidate_id: str
    relation_candidate_sha256: str
    steps: tuple[str, ...]
    capability_epochs: tuple[tuple[str, int], ...]
    capability_signatures: tuple[tuple[str, str], ...]
    frame_epochs: tuple[tuple[str, int], ...]
    obligation_id: str
    operational_scope_id: str | None
    start_state_id: str
    start_state_evidence_id: str
    # Generated programs bind the exact represented relation ancestry that earned
    # the ordered word. Legacy two-step composition trials leave this empty so
    # their historical identity/serialization remains unchanged.
    source_relation_digests: tuple[str, ...] = ()
    step_records: tuple[EpistemicProgramStepRecord, ...] = ()
    status: str = 'OPEN'
    invalid_reason: str | None = None
    proposal_authority: str = 'NONE'
    qualification_authority: str = 'NONE'
    truth_authority: str = 'NONE'
    execution_authority: str = 'NONE'
    semantic_action_authority: str = 'NONE'

    def __post_init__(self) -> None:
        _sha256_token(self.discrimination_signature_sha256,error='PROGRAM_DISCRIMINATION_SIGNATURE_REQUIRED')
        _sha256_token(self.relation_candidate_sha256,error='PROGRAM_RELATION_SIGNATURE_REQUIRED')
        for digest in self.source_relation_digests:
            _sha256_token(digest,error='PROGRAM_SOURCE_RELATION_DIGEST_REQUIRED')
        if not self.trial_id or not self.deficit_id or not self.relation_candidate_id or not self.steps or not self.start_state_id or not self.start_state_evidence_id:
            raise ValueError('INCOMPLETE_EPISTEMIC_PROGRAM_TRIAL')
        if self.status not in {'OPEN','COMPLETE','INVALID'}:
            raise ValueError('UNKNOWN_EPISTEMIC_PROGRAM_TRIAL_STATUS')
        if self.status=='INVALID' and not self.invalid_reason:
            raise ValueError('INVALID_PROGRAM_TRIAL_REQUIRES_REASON')
        if self.status!='INVALID' and self.invalid_reason is not None:
            raise ValueError('NONINVALID_PROGRAM_TRIAL_CANNOT_CARRY_INVALID_REASON')
        if any(x!='NONE' for x in (self.proposal_authority,self.qualification_authority,self.truth_authority,self.execution_authority,self.semantic_action_authority)):
            raise ValueError('EPISTEMIC_PROGRAM_TRIAL_AUTHORITY_ESCALATION')

    def serializable(self) -> dict[str, Any]:
        d=asdict(self)
        d['steps']=list(self.steps)
        d['capability_epochs']=[list(x) for x in self.capability_epochs]
        d['capability_signatures']=[list(x) for x in self.capability_signatures]
        d['frame_epochs']=[list(x) for x in self.frame_epochs]
        if self.source_relation_digests:
            d['source_relation_digests']=list(self.source_relation_digests)
        else:
            d.pop('source_relation_digests',None)
        d['step_records']=[x.serializable() for x in self.step_records]
        return d

    def digest(self) -> str:
        payload=self.serializable().copy(); payload.pop('trial_id',None)
        return sha256_bytes(canonical_json(payload))


def _route_problem(
    steps: tuple[str, ...], capabilities: CapabilityRegistry, obligation: QueryObligation,
) -> str | None:
    for cid in steps:
        c=capabilities.contracts.get(cid)
        if c is None: return f'NO_PATH:{cid}'
        if c.qualification not in {QualificationState.QUALIFIED,QualificationState.SHADOW_QUALIFIED} or c.currentness!='CURRENT':
            return f'CAPABILITY_NOT_CURRENT:{cid}'
        if c.authority!=Authority.EFFECT: return f'CAPABILITY_NOT_EFFECT_AUTHORIZED:{cid}'
        if c.query_obligation_id and c.query_obligation_id!=obligation.obligation_id: return f'QUERY_OBLIGATION_MISMATCH:{cid}'
        if c.operational_scope_id and c.operational_scope_id!=obligation.operational_scope_id: return f'OPERATIONAL_SCOPE_MISMATCH:{cid}'
        if c.handler is None: return f'NO_HANDLER:{cid}'
    return None


def _begin_epistemic_program_trial_from_steps(
    *, steps: tuple[str, ...], relation_candidate_id: str, relation_candidate_sha256: str,
    frame_epochs: tuple[tuple[str, int], ...], deficit_id: str,
    discrimination_signature_sha256: str, capabilities: CapabilityRegistry,
    obligation: QueryObligation, current_frame_epochs: Mapping[str, int],
    start_state_id: str, start_state_evidence_id: str,
    source_relation_digests: tuple[str, ...] = (),
) -> EpistemicProgramTrial:
    problem=_route_problem(steps,capabilities,obligation)
    if problem: raise ValueError(problem)
    for fid,epoch in frame_epochs:
        if current_frame_epochs.get(fid)!=epoch:
            raise ValueError(f'RELATIONAL_FRAME_NOT_CURRENT:{fid}@{epoch}')
    epochs=tuple((cid,capabilities.epochs[cid]) for cid in steps)
    sigs=tuple((cid,capabilities.contracts[cid].computed_signature_sha256()) for cid in steps)
    disc=_sha256_token(discrimination_signature_sha256,error='PROGRAM_DISCRIMINATION_SIGNATURE_REQUIRED')
    relsha=_sha256_token(relation_candidate_sha256,error='PROGRAM_RELATION_SIGNATURE_REQUIRED')
    payload={'deficit_id':deficit_id,'discrimination':disc,'relation':relsha,'steps':steps,'epochs':epochs,'signatures':sigs,'frames':frame_epochs,'obligation':obligation.obligation_id,'scope':obligation.operational_scope_id,'start_state_id':start_state_id,'start_state_evidence_id':start_state_evidence_id}
    return EpistemicProgramTrial(
        trial_id='epistemic-program-'+sha256_bytes(canonical_json(payload))[:24],
        deficit_id=str(deficit_id), discrimination_signature_sha256=disc,
        relation_candidate_id=str(relation_candidate_id), relation_candidate_sha256=relsha,
        steps=steps, capability_epochs=epochs, capability_signatures=sigs,
        frame_epochs=frame_epochs, obligation_id=obligation.obligation_id,
        operational_scope_id=obligation.operational_scope_id, start_state_id=str(start_state_id), start_state_evidence_id=str(start_state_evidence_id),
        source_relation_digests=tuple(sorted(source_relation_digests)),
    )


def begin_epistemic_program_trial(
    candidate: OpaqueActionCompositionCandidate,
    *,
    deficit_id: str,
    discrimination_signature_sha256: str,
    capabilities: CapabilityRegistry,
    obligation: QueryObligation,
    current_frame_epochs: Mapping[str, int],
    start_state_id: str,
    start_state_evidence_id: str,
) -> EpistemicProgramTrial:
    if any(x!='NONE' for x in (candidate.execution_authority,candidate.truth_authority,candidate.qualification_authority)):
        raise ValueError('RELATIONAL_CANDIDATE_AUTHORITY_ESCALATION')
    return _begin_epistemic_program_trial_from_steps(
        steps=(candidate.first_action_token,candidate.second_action_token),
        relation_candidate_id=candidate.candidate_id, relation_candidate_sha256=candidate.digest(),
        frame_epochs=candidate.frame_epochs, deficit_id=deficit_id,
        discrimination_signature_sha256=discrimination_signature_sha256, capabilities=capabilities,
        obligation=obligation, current_frame_epochs=current_frame_epochs,
        start_state_id=start_state_id, start_state_evidence_id=start_state_evidence_id,
    )


def begin_generated_epistemic_program_trial(
    candidate: GeneratedEpistemicProgramCandidate,
    *,
    deficit_id: str, discrimination_signature_sha256: str, capabilities: CapabilityRegistry,
    obligation: QueryObligation, current_frame_epochs: Mapping[str, int],
    start_state_id: str, start_state_evidence_id: str,
) -> EpistemicProgramTrial:
    if any(x!='NONE' for x in (candidate.execution_authority,candidate.truth_authority,candidate.qualification_authority,candidate.closure_authority)):
        raise ValueError('GENERATED_EPISTEMIC_PROGRAM_AUTHORITY_ESCALATION')
    return _begin_epistemic_program_trial_from_steps(
        steps=tuple(candidate.steps), relation_candidate_id=candidate.candidate_id,
        relation_candidate_sha256=candidate.digest(), frame_epochs=candidate.frame_epochs,
        deficit_id=deficit_id, discrimination_signature_sha256=discrimination_signature_sha256,
        capabilities=capabilities, obligation=obligation, current_frame_epochs=current_frame_epochs,
        start_state_id=start_state_id, start_state_evidence_id=start_state_evidence_id,
        source_relation_digests=tuple(candidate.source_relation_digests),
    )


def advance_epistemic_program_trial(
    trial: EpistemicProgramTrial,
    *,
    intent: BoundedActionIntent,
    execution: ActionExecutionRecord,
    outcome: ActionOutcomeRecord,
    capabilities: CapabilityRegistry,
    current_frame_epochs: Mapping[str, int],
) -> EpistemicProgramTrial:
    if trial.status!='OPEN': return trial
    index=len(trial.step_records)
    if index>=len(trial.steps): return replace(trial,status='INVALID',invalid_reason='PROGRAM_STEP_OVERFLOW')
    expected=trial.steps[index]
    expected_state = trial.start_state_id if index == 0 else trial.step_records[-1].actual_next_state_id
    expected_state_evidence = trial.start_state_evidence_id if index == 0 else trial.step_records[-1].outcome_evidence_id
    if intent.start_state_id != expected_state or intent.control_state_evidence_id != expected_state_evidence:
        return replace(trial,status='INVALID',invalid_reason='PROGRAM_CONTROL_STATE_CONTINUITY_VIOLATION')
    current_epochs=dict(trial.capability_epochs); current_sigs=dict(trial.capability_signatures)
    for cid in trial.steps:
        c=capabilities.contracts.get(cid)
        if c is None or c.qualification not in {QualificationState.QUALIFIED,QualificationState.SHADOW_QUALIFIED} or c.currentness!='CURRENT':
            return replace(trial,status='INVALID',invalid_reason=f'PROGRAM_COMPONENT_NOT_CURRENT:{cid}')
        if capabilities.epochs.get(cid)!=current_epochs[cid] or c.computed_signature_sha256()!=current_sigs[cid]:
            return replace(trial,status='INVALID',invalid_reason=f'PROGRAM_COMPONENT_DRIFT:{cid}')
    for fid,epoch in trial.frame_epochs:
        if current_frame_epochs.get(fid)!=epoch:
            return replace(trial,status='INVALID',invalid_reason=f'PROGRAM_FRAME_DRIFT:{fid}')
    if intent.capability_id!=expected:
        return replace(trial,status='INVALID',invalid_reason=f'PROGRAM_STEP_DEVIATION:EXPECTED:{expected}:GOT:{intent.capability_id}')
    if intent.obligation_id!=trial.obligation_id or intent.operational_scope_id!=trial.operational_scope_id:
        return replace(trial,status='INVALID',invalid_reason='PROGRAM_STEP_OBLIGATION_OR_SCOPE_DRIFT')
    if execution.intent_id!=intent.intent_id or execution.capability_id!=expected or execution.capability_epoch!=current_epochs[expected]:
        return replace(trial,status='INVALID',invalid_reason='PROGRAM_EXECUTION_RECORD_MISMATCH')
    if outcome.execution_id!=execution.execution_id:
        return replace(trial,status='INVALID',invalid_reason='PROGRAM_OUTCOME_EXECUTION_MISMATCH')
    if any(r.execution_id==execution.execution_id or r.outcome_evidence_id==outcome.evidence_id for r in trial.step_records):
        return replace(trial,status='INVALID',invalid_reason='PROGRAM_STEP_REPLAY')
    record=EpistemicProgramStepRecord(
        step_index=index,capability_id=expected,capability_epoch=execution.capability_epoch,
        intent_id=intent.intent_id,execution_id=execution.execution_id,outcome_id=outcome.outcome_id,
        outcome_evidence_id=outcome.evidence_id,actual_next_state_id=outcome.actual_next_state_id,
        prediction_commitment=outcome.prediction_commitment.commitment.value,
    )
    records=trial.step_records+(record,)
    return replace(trial,step_records=records,status='COMPLETE' if len(records)==len(trial.steps) else 'OPEN')


def completed_program_evidence_payload(trial: EpistemicProgramTrial) -> dict[str, Any]:
    if trial.status!='COMPLETE': raise ValueError('PROGRAM_TRIAL_NOT_COMPLETE')
    return {
        'trial_id':trial.trial_id,'trial_sha256':trial.digest(),'deficit_id':trial.deficit_id,
        'discrimination_signature_sha256':trial.discrimination_signature_sha256,
        'relation_candidate_id':trial.relation_candidate_id,'relation_candidate_sha256':trial.relation_candidate_sha256,
        'steps':list(trial.steps),'step_records':[x.serializable() for x in trial.step_records],
        'truth_authority':'NONE','execution_authority_gain':'NONE','qualification_authority':'NONE',
        'physical_actuator_identity_authority':'NONE',
    }
