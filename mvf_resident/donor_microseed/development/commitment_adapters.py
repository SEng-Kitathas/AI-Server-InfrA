from __future__ import annotations
from ..runtime.commitment import RelationalCommitment, TernaryCommitment
from ..runtime.types import EpistemicStatus, FeasibilityState, QualificationState
from .epistemic import EpistemicDeficitState

def _q(**items: object) -> tuple[tuple[str, str], ...]:
    return tuple((str(k), str(v.value if hasattr(v, "value") else v)) for k, v in items.items())

def project_feasibility(state: FeasibilityState, *, commitment_id: str, target_id: str, premise_ids: tuple[str,...]=()) -> RelationalCommitment:
    state=FeasibilityState(state)
    stance={FeasibilityState.FEASIBLE:TernaryCommitment.YES,FeasibilityState.REFUSED:TernaryCommitment.NO,FeasibilityState.UNKNOWN:TernaryCommitment.UNKNOWN}[state]
    return RelationalCommitment(commitment_id,target_id,stance,reason=state.value,qualifiers=_q(native_type="FeasibilityState",native_state=state),premise_ids=premise_ids)

def project_epistemic_status(status: EpistemicStatus, *, commitment_id: str, target_id: str, premise_ids: tuple[str,...]=()) -> RelationalCommitment:
    status=EpistemicStatus(status)
    if status in {EpistemicStatus.PROVED,EpistemicStatus.PRESSURE_SUPPORTED,EpistemicStatus.NARROWED}: stance,app=TernaryCommitment.YES,TernaryCommitment.YES
    elif status in {EpistemicStatus.VIOLATED,EpistemicStatus.UNSUPPORTED}: stance,app=TernaryCommitment.NO,TernaryCommitment.YES
    elif status==EpistemicStatus.NOT_APPLICABLE: stance,app=TernaryCommitment.UNKNOWN,TernaryCommitment.NO
    else: stance,app=TernaryCommitment.UNKNOWN,TernaryCommitment.YES
    return RelationalCommitment(commitment_id,target_id,stance,applicability=app,reason=status.value,qualifiers=_q(native_type="EpistemicStatus",native_state=status),premise_ids=premise_ids)

def project_qualification_state(state: QualificationState, *, commitment_id: str, target_id: str, premise_ids: tuple[str,...]=()) -> RelationalCommitment:
    state=QualificationState(state)
    if state in {QualificationState.QUALIFIED,QualificationState.SHADOW_QUALIFIED}: stance=TernaryCommitment.YES
    elif state==QualificationState.REJECTED: stance=TernaryCommitment.NO
    else: stance=TernaryCommitment.UNKNOWN
    currentness="STALE" if state==QualificationState.STALE else "CURRENT"
    return RelationalCommitment(commitment_id,target_id,stance,reason=state.value,qualifiers=_q(native_type="QualificationState",lifecycle=state,currentness=currentness,qualification_authority="UNCHANGED_NATIVE_BOUNDARY"),premise_ids=premise_ids)

def project_epistemic_deficit_state(state: EpistemicDeficitState, *, commitment_id: str, target_id: str, premise_ids: tuple[str,...]=()) -> RelationalCommitment:
    state=EpistemicDeficitState(state)
    return RelationalCommitment(commitment_id,target_id,TernaryCommitment.UNKNOWN,reason=state.value,qualifiers=_q(native_type="EpistemicDeficitState",epistemic_lifecycle=state,historical_unknown="PRESERVED"),premise_ids=premise_ids)
