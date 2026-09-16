from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib, json, math
from typing import Any

from ..runtime.commitment import RelationalCommitment, TernaryCommitment
from ..runtime.types import Authority

@dataclass(frozen=True)
class OpaqueControlStateWitness:
    state_id: str
    evidence_id: str
    authority: str = Authority.OBSERVATION_ONLY.value
    semantic_state_authority: str = "NONE"
    def serializable(self) -> dict[str, Any]: return asdict(self)

@dataclass(frozen=True)
class BoundedActionIntent:
    intent_id: str
    proposal_id: str | None
    proposal_digest: str | None
    action_commitment: RelationalCommitment
    capability_id: str
    capability_epoch: int
    start_state_id: str
    control_state_evidence_id: str
    expected_next_state_id: str | None
    expected_value_effect: float | None
    value_epoch: tuple[str,int] | None
    obligation_id: str
    operational_scope_id: str | None
    basis_kind: str = "SINGLE_VALUE_REHEARSAL"
    required_value_epochs: tuple[tuple[str,int], ...] = ()
    derivation_parameters: tuple[tuple[str,int|float], ...] = ()
    authority: str = Authority.MODEL_OUTPUT_ONLY.value
    execution_authority: str = "NONE"
    truth_authority: str = "NONE"
    semantic_intention_authority: str = "NONE"
    def serializable(self) -> dict[str, Any]:
        d=asdict(self); d['action_commitment']=self.action_commitment.serializable()
        d['value_epoch']=None if self.value_epoch is None else list(self.value_epoch)
        d['required_value_epochs']=[list(x) for x in self.required_value_epochs]
        d['derivation_parameters']=[list(x) for x in self.derivation_parameters]
        return d
    @classmethod
    def from_serializable(cls,d):
        ve=d.get('value_epoch')
        return cls(intent_id=str(d['intent_id']),proposal_id=None if d.get('proposal_id') is None else str(d['proposal_id']),
            proposal_digest=None if d.get('proposal_digest') is None else str(d['proposal_digest']),
            action_commitment=RelationalCommitment.from_serializable(d['action_commitment']),capability_id=str(d['capability_id']),
            capability_epoch=int(d['capability_epoch']),start_state_id=str(d['start_state_id']),control_state_evidence_id=str(d['control_state_evidence_id']),
            expected_next_state_id=None if d.get('expected_next_state_id') is None else str(d['expected_next_state_id']),
            expected_value_effect=None if d.get('expected_value_effect') is None else float(d['expected_value_effect']),
            value_epoch=None if ve is None else (str(ve[0]),int(ve[1])),obligation_id=str(d['obligation_id']),
            operational_scope_id=d.get('operational_scope_id'),basis_kind=str(d.get('basis_kind','SINGLE_VALUE_REHEARSAL')),
            required_value_epochs=tuple((str(x[0]),int(x[1])) for x in d.get('required_value_epochs',())),
            derivation_parameters=tuple((str(x[0]),x[1]) for x in d.get('derivation_parameters',())),
            authority=str(d.get('authority',Authority.MODEL_OUTPUT_ONLY.value)),execution_authority=str(d.get('execution_authority','NONE')),
            truth_authority=str(d.get('truth_authority','NONE')),semantic_intention_authority=str(d.get('semantic_intention_authority','NONE')))

@dataclass(frozen=True)
class ActionExecutionRecord:
    execution_id: str
    intent_id: str
    capability_id: str
    capability_epoch: int
    start_state_id: str
    handler_result_sha256: str
    execution_commitment_id: str | None = None
    execution_premise_ids: tuple[str,...] = ()
    authority: str = Authority.EFFECT.value
    observation_authority: str = "NONE"
    truth_authority: str = "NONE"
    def serializable(self):
        d=asdict(self); d['execution_premise_ids']=list(self.execution_premise_ids); return d
    @classmethod
    def from_serializable(cls,d):
        return cls(execution_id=str(d['execution_id']),intent_id=str(d['intent_id']),capability_id=str(d['capability_id']),
            capability_epoch=int(d['capability_epoch']),start_state_id=str(d['start_state_id']),handler_result_sha256=str(d['handler_result_sha256']),
            execution_commitment_id=None if d.get('execution_commitment_id') is None else str(d['execution_commitment_id']),
            execution_premise_ids=tuple(str(x) for x in d.get('execution_premise_ids',())),authority=str(d.get('authority',Authority.EFFECT.value)),
            observation_authority=str(d.get('observation_authority','NONE')),truth_authority=str(d.get('truth_authority','NONE')))

@dataclass(frozen=True)
class ActionOutcomeCoordinate:
    value_id: str
    value_epoch: int
    observed_value: float
    actual_value_effect: float
    frame_epochs: tuple[tuple[str, int], ...] = ()
    episode_schema_epochs: tuple[tuple[str, int], ...] = ()
    topology_epochs: tuple[tuple[str, int], ...] = ()
    coordination_epochs: tuple[tuple[str, int], ...] = ()
    source_trace_ids: tuple[str, ...] = ()
    learning_ancestry_status: str = "CURRENT"
    truth_authority: str = "NONE"
    semantic_goal_authority: str = "NONE"

    def serializable(self) -> dict[str, Any]:
        d = asdict(self)
        for key in ("frame_epochs", "episode_schema_epochs", "topology_epochs", "coordination_epochs"):
            d[key] = [list(x) for x in d[key]]
        d["source_trace_ids"] = list(self.source_trace_ids)
        return d

    @classmethod
    def from_serializable(cls, d: dict[str, Any]) -> "ActionOutcomeCoordinate":
        return cls(
            value_id=str(d["value_id"]),
            value_epoch=int(d["value_epoch"]),
            observed_value=float(d["observed_value"]),
            actual_value_effect=float(d["actual_value_effect"]),
            frame_epochs=tuple((str(a), int(b)) for a, b in d.get("frame_epochs", ())),
            episode_schema_epochs=tuple((str(a), int(b)) for a, b in d.get("episode_schema_epochs", ())),
            topology_epochs=tuple((str(a), int(b)) for a, b in d.get("topology_epochs", ())),
            coordination_epochs=tuple((str(a), int(b)) for a, b in d.get("coordination_epochs", ())),
            source_trace_ids=tuple(str(x) for x in d.get("source_trace_ids", ())),
            learning_ancestry_status=str(d.get("learning_ancestry_status", "CURRENT")),
            truth_authority=str(d.get("truth_authority", "NONE")),
            semantic_goal_authority=str(d.get("semantic_goal_authority", "NONE")),
        )


@dataclass(frozen=True)
class ActionOutcomeRecord:
    outcome_id: str
    execution_id: str
    evidence_id: str
    actual_next_state_id: str
    observed_value: float | None
    value_id: str | None
    prediction_commitment: RelationalCommitment
    actual_value_effect: float | None = None
    value_outcomes: tuple[ActionOutcomeCoordinate, ...] = ()
    state_only: bool = False
    requires_redeliberation: bool = True
    execution_authority_gain: str = "NONE"
    qualification_authority: str = "NONE"
    truth_authority: str = "NONE"

    def __post_init__(self) -> None:
        if self.state_only:
            if self.value_outcomes or self.value_id is not None or self.observed_value is not None or self.actual_value_effect is not None:
                raise ValueError("ACTION_OUTCOME_STATE_ONLY_MIXED_VALUE_REPRESENTATION")
        elif self.value_outcomes:
            if self.value_id is not None or self.observed_value is not None or self.actual_value_effect is not None:
                raise ValueError("ACTION_OUTCOME_MIXED_VALUE_REPRESENTATION")
            value_ids = [row.value_id for row in self.value_outcomes]
            if len(value_ids) != len(set(value_ids)):
                raise ValueError("ACTION_OUTCOME_DUPLICATE_VALUE_COORDINATE")
        elif self.value_id is None or self.observed_value is None:
            raise ValueError("ACTION_OUTCOME_VALUE_REPRESENTATION_MISSING")

    def serializable(self):
        d=asdict(self)
        d['prediction_commitment']=self.prediction_commitment.serializable()
        if self.value_outcomes:
            d['value_outcomes']=[row.serializable() for row in self.value_outcomes]
        else:
            d.pop('value_outcomes',None)
        return d

    @classmethod
    def from_serializable(cls,d):
        observed=d.get('observed_value')
        value_id=d.get('value_id')
        return cls(outcome_id=str(d['outcome_id']),execution_id=str(d['execution_id']),evidence_id=str(d['evidence_id']),
            actual_next_state_id=str(d['actual_next_state_id']),observed_value=None if observed is None else float(observed),
            value_id=None if value_id is None else str(value_id),
            actual_value_effect=None if d.get('actual_value_effect') is None else float(d.get('actual_value_effect')),
            value_outcomes=tuple(ActionOutcomeCoordinate.from_serializable(x) for x in d.get('value_outcomes',())),
            state_only=bool(d.get('state_only',False)),
            prediction_commitment=RelationalCommitment.from_serializable(d['prediction_commitment']),
            requires_redeliberation=bool(d.get('requires_redeliberation',True)),execution_authority_gain=str(d.get('execution_authority_gain','NONE')),
            qualification_authority=str(d.get('qualification_authority','NONE')),truth_authority=str(d.get('truth_authority','NONE')))


def build_multi_value_outcome_coordinates(
    required_value_epochs: tuple[tuple[str, int], ...],
    capability_id: str,
    observed_values: dict[str, float],
    pre_values: dict[str, float],
    effect_witnesses: dict[str, dict[str, Any]],
    operational_traces: dict[str, Any],
) -> tuple[tuple[ActionOutcomeCoordinate, ...], dict[str, float]]:
    """Project one physical execution into coordinate experience rows.

    Actual observed effects are the learning labels. Effect witnesses contribute
    only the already-earned frame/episode ancestry needed by the scalar learner.
    Missing or ambiguous ancestry withholds that coordinate from learning rather
    than fabricating a complete vector.
    """
    coordinates: list[ActionOutcomeCoordinate] = []
    actual_effects: dict[str, float] = {}
    for value_id, value_epoch in required_value_epochs:
        if value_id not in observed_values:
            continue
        observed = observed_values[value_id]
        actual_effect = round(observed - pre_values[value_id], 3)
        actual_effects[value_id] = actual_effect
        witness = effect_witnesses.get(f"{capability_id}::{value_id}", {})
        frame_epochs: tuple[tuple[str, int], ...] = ()
        episode_epochs: tuple[tuple[str, int], ...] = ()
        topology_epochs: tuple[tuple[str, int], ...] = ()
        coordination_epochs: tuple[tuple[str, int], ...] = ()
        source_trace_ids: tuple[str, ...] = ()
        ancestry_status = "UNKNOWN_CURRENT_EFFECT_ANCESTRY"
        if witness.get("status") == "CURRENT_EFFECT":
            source_trace_ids = tuple(str(x) for x in witness.get("source_trace_ids", ()))
            traces = [operational_traces.get(trace_id) for trace_id in source_trace_ids]
            traces = [trace for trace in traces if trace is not None]
            if traces:
                frame_shapes = {
                    ((trace.frame_id, int(trace.frame_epoch)),)
                    for trace in traces
                    if trace.frame_id is not None and trace.frame_epoch is not None
                }
                episode_shapes = {
                    ((trace.episode_schema_id, int(trace.episode_schema_epoch)),)
                    for trace in traces
                    if trace.episode_schema_id is not None and trace.episode_schema_epoch is not None
                }
                topology_shapes = {tuple(trace.topology_epochs) for trace in traces}
                coordination_shapes = {tuple(trace.coordination_epochs) for trace in traces}
                if len(frame_shapes) == len(episode_shapes) == len(topology_shapes) == len(coordination_shapes) == 1:
                    frame_epochs = next(iter(frame_shapes))
                    episode_epochs = next(iter(episode_shapes))
                    topology_epochs = next(iter(topology_shapes))
                    coordination_epochs = next(iter(coordination_shapes))
                    ancestry_status = "CURRENT"
        coordinates.append(ActionOutcomeCoordinate(
            value_id=value_id,
            value_epoch=value_epoch,
            observed_value=observed,
            actual_value_effect=actual_effect,
            frame_epochs=frame_epochs,
            episode_schema_epochs=episode_epochs,
            topology_epochs=topology_epochs,
            coordination_epochs=coordination_epochs,
            source_trace_ids=source_trace_ids,
            learning_ancestry_status=ancestry_status,
        ))
    return tuple(coordinates), actual_effects

class ActionClosureRegistry:
    """Durable bounded control-loop history; never supplies effect/truth/qualification authority."""
    def __init__(self):
        self.current_state: OpaqueControlStateWitness|None=None
        self.intents: dict[str,BoundedActionIntent]={}
        self.executions: dict[str,ActionExecutionRecord]={}
        self.outcomes: dict[str,ActionOutcomeRecord]={}
    def set_state(self,w:OpaqueControlStateWitness): self.current_state=w
    def add_intent(self,x):
        if x.intent_id in self.intents: raise ValueError('DUPLICATE_ACTION_INTENT')
        if x.execution_authority!='NONE' or x.truth_authority!='NONE' or x.semantic_intention_authority!='NONE': raise ValueError('ACTION_INTENT_AUTHORITY_ESCALATION')
        self.intents[x.intent_id]=x
    def add_execution(self,x):
        if x.execution_id in self.executions: raise ValueError('DUPLICATE_ACTION_EXECUTION')
        if any(e.intent_id==x.intent_id for e in self.executions.values()): raise ValueError('ACTION_INTENT_ALREADY_EXECUTED')
        self.executions[x.execution_id]=x
    def add_outcome(self,x):
        if x.outcome_id in self.outcomes or any(o.execution_id==x.execution_id for o in self.outcomes.values()): raise ValueError('ACTION_EXECUTION_ALREADY_HAS_OUTCOME')
        self.outcomes[x.outcome_id]=x

def stable_id(prefix:str,payload:dict)->str:
    raw=json.dumps(payload,sort_keys=True,separators=(',',':')).encode()
    return prefix+hashlib.sha256(raw).hexdigest()[:20]

def result_digest(value:Any)->str:
    try: raw=json.dumps(value,sort_keys=True,separators=(',',':'),default=repr).encode()
    except Exception: raw=repr(value).encode()
    return hashlib.sha256(raw).hexdigest()
