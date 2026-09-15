from __future__ import annotations
from dataclasses import replace
import math
from pathlib import Path
from typing import Any, Iterable
from .commitment import TernaryCommitment, RelationalCommitment, conjoin_required_commitments
from .types import (
    Authority, CapabilityContract, EpistemicStatus, Observation,
    QualificationState, QueryObligation, OperationalFrameContract, EpisodeSchemaContract,
    ValueVariableContract, FeasibilityState, RecruitmentTopologyContract, OperationalCounterpartyContract,
    OperationalCoordinationContract,
)
from .capabilities import CapabilityRegistry
from .composer import compose_capabilities
from .observation import currentness
from ..evidence.ledger import EvidenceLedger
from ..evidence.authority import FixedQualifier
from ..development.registry import DevelopmentRegistry, DevelopmentRecord
from ..development.path import DevelopmentPath
from ..development.commitment_adapters import (
    project_feasibility, project_epistemic_status, project_qualification_state, project_epistemic_deficit_state,
)
from ..development.capability_admission import (
    CapabilityCandidate,
    CapabilityQualificationTicket,
    validate_external_ticket,
)
from ..development.discovery import (
    OperationalTrace, DiscoveryConfig, discover_candidates,
    derive_value_bound_singleton_effects,
)
from ..development.projection_discovery import (
    ProjectionSample, ProjectionDiscoveryConfig, EpistemicProjectionCandidate,
    ProjectionQualificationTicket, discover_epistemic_projection_candidates as discover_projection_candidates,
    validate_external_projection_ticket,
)
from ..development.constructor_growth import (
    ConstructorAtom, ConstructorProjectionSample, ConstructorGrowthConfig, ConstructorSearchDiagnostic,
    ProjectionConstructorCandidate, ConstructorQualificationTicket,
    discover_projection_constructor_candidates as discover_constructor_candidates,
    validate_external_constructor_ticket,
)
from ..development.robust_constructor_growth import (
    RobustConstructorGrowthConfig, RobustConstructorSearchDiagnostic, RobustProjectionConstructorCandidate,
    RobustConstructorQualificationTicket, ProjectionPredictiveCurrentnessConfig, ProjectionPredictiveCurrentnessWitness,
    discover_robust_projection_constructor_candidates as discover_robust_constructor_candidates,
    validate_external_robust_constructor_ticket, assess_projection_predictive_currentness,
)
from ..development.drift_recurrence import (
    ProjectionDriftStructureConfig, ProjectionDriftStructureWitness,
    ProjectionRecurrenceConfig, ProjectionRecurrenceWitness, ProjectionRecurrenceQualificationTicket,
    assess_projection_drift_structure, assess_projection_recurrence,
    validate_external_projection_recurrence_ticket,
)
from ..development.drift_intervention import (
    DriftInterventionConfig, DriftInterventionProbe, DriftInterventionSelection, DriftInterventionWitness,
    select_drift_discriminating_intervention, assess_drift_intervention_outcomes,
)
from ..development.frame import OperationalFrameRegistry
from ..development.episode import EpisodeSchemaRegistry
from ..development.value import (
    ValueVariableRegistry,
    residual_pressure_after_effect,
)
from ..development.action_licensing import compose_multi_value_action_licenses
from ..development.recruitment import RecruitmentOption, RecruitmentProposal, RecruitmentRegistry
from ..development.rehearsal import (
    RehearsalTransitionObservation, RehearsalTransitionRelation, CounterfactualRehearsalConfig, CounterfactualRehearsalProposal,
    CounterfactualRehearsalRegistry, derive_rehearsal_transition_relations, propose_counterfactual_rehearsal,
)
from ..development.action_closure import (
    OpaqueControlStateWitness, BoundedActionIntent, ActionExecutionRecord, ActionOutcomeRecord,
    ActionClosureRegistry, build_multi_value_outcome_coordinates, stable_id as action_stable_id, result_digest as action_result_digest,
)
from ..development.action_learning import (
    ActionOutcomeExperience, ActionOutcomePredictiveCandidate, ActionOutcomeRelationQualificationTicket,
    QualifiedActionOutcomePredictiveRelation, ActionOutcomeLearningRegistry,
    ProjectionConditionedRelationCandidate, ProjectionConditionedRelationQualificationTicket,
    QualifiedProjectionConditionedRelationBinding,
    nominate_action_outcome_candidates, validate_external_action_outcome_ticket,
    validate_external_projection_conditioned_relation_ticket,
    discover_action_outcome_alternative_hypotheses, discover_action_outcome_successor_couplings,
    discover_action_outcome_three_locus_chains, assemble_three_locus_chain_epistemic_relation_sets,
    assemble_single_conflict_epistemic_relation_sets, assemble_successor_coupled_epistemic_relation_sets,
    projection_conditioned_hypothesis_surface_digest,
)
from ..development.predictive_adaptation import (
    PredictiveCurrentnessConfig, ActionOutcomePredictiveCurrentnessWitness, ActionOutcomeReplacementLink,
    assess_action_outcome_predictive_currentness as assess_action_outcome_relation_currentness,
    nominate_drift_replacement_candidates as nominate_action_outcome_replacements,
)
from ..development.topology import RecruitmentTopologyRegistry
from ..development.counterparty import OperationalCounterpartyRegistry
from ..development.coordination import OperationalCoordinationRegistry
from ..development.reentry import (
    HistoricalReentryProjection, ReentryWarrant, ReentryDecision,
    derive_historical_reentry_projection, assess_reentry,
)
from ..development.epistemic_program import GeneratedEpistemicProgramCandidate, begin_epistemic_program_trial, begin_generated_epistemic_program_trial, completed_program_evidence_payload
from ..development.relational_algebra import OpaqueActionCompositionCandidate, OpaqueTransitionSample, discover_opaque_action_composition_candidates, discover_one_step_visible_history_refinements
from ..development.epistemic_action import (
    EpistemicStepExecutionContext, EpistemicDecisionBearingContext, derive_epistemic_program_step_commitment,
    derive_grounded_feasibility_option, derive_current_program_discrimination_commitment, derive_current_decision_bearing_commitment,
    derive_current_grounded_feasibility_surface, derive_current_decision_bearing_commitment_from_grounded_surface,
    derive_program_observable_partition, program_partition_strictly_refines,
    derive_current_generated_epistemic_program_candidates, derive_epistemic_program_step_outcome_bearing,
    nominate_epistemic_program_step_intent as derive_epistemic_program_step_intent,
)
from ..development.epistemic import (
    EpistemicCurrentnessAnchor, EpistemicDeficitRecord, EpistemicDeficitRegistry, EpistemicDeficitState,
    EpistemicProjectionRecord, EpistemicProjectionRegistry, EpistemicContrastRow,
    EpistemicContrastBinding, EpistemicContrastRegistry, EpistemicBearingKind, EpistemicBearingWitness,
)
from ..persistence.store import StateStore
from ..persistence.identity import assess_continuity, continuity_witness_from_exports
from ..persistence.biography import DevelopmentalBiography, BiographyIntegrityError
from ..cognition.hypothesis import Hypothesis, HypothesisSet
from ..cognition.event_frames import infer_event_frame
from ..cognition.referents import nominate_by_boundary_coherence
from ..cognition.research_registry import RESEARCH_COMPONENTS


class Microseed:
    """Main-Dev embodiment evolved through evidence available at MS1527.

    MS1303-1327 attacks the drift-cause identifiability ceiling left by v2.0.
    v2.1 adds only bounded current-disagreement intervention selection over a
    supplied opaque probe pool plus repeated exact-outcome discrimination. Probe
    execution requires current qualified capability/frame/episode contracts and
    actual content-bound evidence; selection itself grants no execution or truth.

    A narrowed predictive candidate is not a semantic drift cause and does not
    switch/reactivate a projection. Zero current disagreement owes bounded
    abstention; a discriminator that exists but is not executable owes
    ACTION_LIMITED. This is not intervention synthesis, a learned noise model, a
    semantic regime ontology, general active learning, self-qualification,
    language, or numerical-selfhood authority.
    """

    ANCESTRAL_ENTITY_BASELINE_MS = 801
    RESEARCH_TERMINAL_MS = 1527
    INTEGRATION_EVIDENCE_THROUGH_MS = 1527
    NEXT_MS = 1528
    NEXT_STARTED = False
    FRONTIER = "ATTN-MS1527-POST-REENTRY-WHOLE-ORGANISM-HOSTILE-EMBODIMENT"
    DEFERRED_FRONTIERS = (
        "GENERAL-HIERARCHICAL-PLANNING",
        "GENERAL-CHILD-ROLE-IDENTITY",
        "CONSTITUTIONAL-VALUE-PRIOR-ORIGIN",
        "GENERAL-OVERLAP-DECONVOLUTION",
        "GENERAL-EPISODE-PARTITION-SEARCH",
        "GENERAL-ACTION-CORRESPONDENCE-SEARCH",
        "NONLINEAR-SENSORIMOTOR-FRAME",
        "GENERAL-HIGHER-ORDER-TOPOLOGY-CONSTRUCTOR-LANGUAGE",
        "TRACTABLE-ENDOGENOUS-TOPOLOGY-SEARCH",
        "GENERAL-BIOGRAPHY-MERGE-SEMANTICS",
        "SEMANTIC-SELF-OTHER-ONTOLOGY",
        "PERSISTENT-OTHER-AGENT-IDENTITY",
        "GENERAL-THEORY-OF-MIND",
        "GENERAL-MULTI-AGENT-PLANNING",
        "GENERAL-PARTNER-COMBINATION-SEARCH",
        "SEMANTIC-COMMITMENT-INTENTION-PROMISE-ONTOLOGY",
        "GENERAL-HIGHER-ORDER-JOINT-RELATION-LANGUAGE",
    )

    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.store = StateStore(self.state_dir / "state.sqlite3")
        self.evidence = EvidenceLedger(self.state_dir / "evidence.sqlite3")
        legacy_events = self.store.events()
        legacy_anchor = {
            "source_entity": "PRE_V0_6_STATESTORE",
            "legacy_store_event_count": len(legacy_events),
            "legacy_store_digest_sha256": __import__("hashlib").sha256(
                __import__("json").dumps(legacy_events, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "historical_biography_before_v0_6": "UNKNOWN_INCOMPLETE",
        }
        self.biography = DevelopmentalBiography(
            self.state_dir / "biography.sqlite3", legacy_anchor=legacy_anchor
        )
        # Fixed qualification remains a firewall used by development bookkeeping.
        # Capability admission consumes an externally issued ticket; Microseed
        # intentionally exposes no self-qualification method for its candidates.
        self.qualifier = FixedQualifier(self.evidence)
        self.development = DevelopmentRegistry(self.qualifier)
        self.path = DevelopmentPath(on_append=lambda kind, payload: self.biography.append(kind, payload))
        self.path.restore([
            {"event_type": ev.kind, "payload": ev.payload}
            for ev in self.biography.canonical_order()
        ])
        self.capability_candidates: dict[str, CapabilityCandidate] = {}
        self.recruitments = RecruitmentRegistry()
        self.counterfactual_rehearsals = CounterfactualRehearsalRegistry()
        self.action_closure = ActionClosureRegistry()
        self.action_outcome_learning = ActionOutcomeLearningRegistry()
        self.operational_traces: dict[str, OperationalTrace] = {}
        self.frames = OperationalFrameRegistry(on_invalidate=self._on_frame_invalidated)
        self.values = ValueVariableRegistry(on_invalidate=self._on_value_invalidated)
        self.episodes = EpisodeSchemaRegistry(on_invalidate=self._on_episode_schema_invalidated)
        self.topologies = RecruitmentTopologyRegistry(on_invalidate=self._on_topology_invalidated)
        self.counterparties = OperationalCounterpartyRegistry(on_invalidate=self._on_counterparty_invalidated)
        self.coordinations = OperationalCoordinationRegistry(on_invalidate=self._on_coordination_invalidated)
        self.capabilities = CapabilityRegistry(on_invalidate=self._on_capability_invalidated)
        self.epistemic_deficits = EpistemicDeficitRegistry()
        self.epistemic_projection_candidates: dict[str, EpistemicProjectionCandidate] = {}
        self.epistemic_constructor_candidates: dict[str, ProjectionConstructorCandidate] = {}
        self.robust_epistemic_constructor_candidates: dict[str, RobustProjectionConstructorCandidate] = {}
        self.epistemic_projection_recurrence_witnesses: dict[str, ProjectionRecurrenceWitness] = {}
        self.epistemic_drift_intervention_plans: dict[str, DriftInterventionSelection] = {}
        self.epistemic_drift_intervention_witnesses: dict[str, DriftInterventionWitness] = {}
        self.epistemic_projections = EpistemicProjectionRegistry()
        self.epistemic_contrasts = EpistemicContrastRegistry(self.epistemic_projections)
        self._load_operational_traces()
        self._load_epistemic_deficits()
        self._load_epistemic_projection_candidates()
        self._load_epistemic_constructor_candidates()
        self._load_robust_epistemic_constructor_candidates()
        self._load_epistemic_contrasts()
        self._load_drift_intervention_state()
        self._load_recruitment_proposals()
        self._load_counterfactual_rehearsals()
        self._load_action_closure()
        self._load_action_outcome_learning()
        self._bootstrap_research_registry()
        boot_packet = {
            "ancestral_entity_baseline_ms": self.ANCESTRAL_ENTITY_BASELINE_MS,
            "research_terminal_ms": self.RESEARCH_TERMINAL_MS,
            "integration_evidence_through_ms": self.INTEGRATION_EVIDENCE_THROUGH_MS,
            "frontier": self.FRONTIER,
        }
        self.path.append("BOOT", boot_packet)
        self.store.append("BOOT", boot_packet)

    def _load_operational_traces(self) -> None:
        """Recover trace observations from durable state without claiming selfhood."""
        for event in self.store.events():
            if event.get("kind") != "CAPABILITY_TRACE":
                continue
            trace = OperationalTrace.from_serializable(event["payload"])
            self.operational_traces[trace.trace_id] = trace

    def _load_epistemic_deficits(self) -> None:
        """Replay durable proposal/scheduling state without turning it into truth."""
        for event in self.store.events():
            kind = event.get("kind")
            payload = event.get("payload", {})
            if kind == "EPISTEMIC_DEFICIT_RECORDED":
                record = EpistemicDeficitRecord.from_serializable(payload)
                if record.deficit_id not in self.epistemic_deficits.records:
                    self.epistemic_deficits.register(record)
            elif kind == "EPISTEMIC_DEFICIT_CANDIDATE_LINKED":
                did=payload.get("deficit_id"); cid=payload.get("candidate_id")
                if did in self.epistemic_deficits.records and cid:
                    self.epistemic_deficits.link_candidate(did,cid)
            elif kind == "EPISTEMIC_DEFICIT_PROBE_BOUND":
                did=payload.get("deficit_id")
                if did in self.epistemic_deficits.records:
                    self.epistemic_deficits.bind_probe(did,payload["capability_id"],int(payload["capability_epoch"]))
            elif kind == "EPISTEMIC_DEFICIT_PROBE_EVIDENCE":
                did=payload.get("deficit_id")
                if did in self.epistemic_deficits.records and self.epistemic_deficits.records[did].state == EpistemicDeficitState.PROBE_AVAILABLE:
                    self.epistemic_deficits.record_probe_evidence(did,payload["evidence_id"])
            elif kind == "EPISTEMIC_DEFICIT_REVISIT_REQUESTED":
                did=payload.get("deficit_id")
                eid=payload.get("evidence_id")
                if did in self.epistemic_deficits.records and eid and self.epistemic_deficits.records[did].state != EpistemicDeficitState.STALE:
                    self.epistemic_deficits.request_revisit(did,eid)
            elif kind == "EPISTEMIC_DEFICIT_STALE":
                did=payload.get("deficit_id")
                if did in self.epistemic_deficits.records:
                    self.epistemic_deficits.mark_stale(did,reason=payload.get("reason","REPLAYED_STALE"),evidence_id=payload.get("evidence_id"))
            elif kind == "EPISTEMIC_DEFICIT_PREMISE_INVALIDATED":
                self.epistemic_deficits.invalidate_premise(
                    payload["premise_kind"],payload["object_id"],int(payload["new_epoch"]),
                    reason=payload.get("reason","REPLAYED_PREMISE_DRIFT"),
                    force=bool(payload.get("force",False)),
                )
            elif kind == "EPISTEMIC_DEFICIT_PROBE_INVALIDATED":
                for cid in payload.get("stale_capabilities", (payload.get("capability_id"),)):
                    if cid:
                        self.epistemic_deficits.invalidate_probe(cid)

    def _load_epistemic_projection_candidates(self) -> None:
        """Replay proposal memory without turning it into qualification."""
        for event in self.store.events():
            if event.get("kind") != "EPISTEMIC_PROJECTION_CANDIDATE_NOMINATED":
                continue
            candidate = EpistemicProjectionCandidate.from_serializable(event.get("payload", {}))
            self.epistemic_projection_candidates.setdefault(candidate.candidate_id, candidate)

    def _load_epistemic_constructor_candidates(self) -> None:
        """Replay constructor-growth proposal memory without qualification gain."""
        for event in self.store.events():
            if event.get("kind") != "EPISTEMIC_PROJECTION_CONSTRUCTOR_CANDIDATE_NOMINATED":
                continue
            candidate = ProjectionConstructorCandidate.from_serializable(event.get("payload", {}))
            self.epistemic_constructor_candidates.setdefault(candidate.candidate_id, candidate)

    def _load_robust_epistemic_constructor_candidates(self) -> None:
        """Replay robust proposal memory without qualification/currentness gain."""
        for event in self.store.events():
            if event.get("kind") != "EPISTEMIC_ROBUST_CONSTRUCTOR_CANDIDATE_NOMINATED":
                continue
            candidate = RobustProjectionConstructorCandidate.from_serializable(event.get("payload", {}))
            self.robust_epistemic_constructor_candidates.setdefault(candidate.candidate_id, candidate)

    def _load_epistemic_contrasts(self) -> None:
        """Replay supplied opaque projections, contrast bindings and bearing witnesses."""
        for event in self.store.events():
            kind=event.get("kind")
            payload=event.get("payload",{})
            if kind == "EPISTEMIC_PROJECTION_REGISTERED":
                rec=EpistemicProjectionRecord.from_serializable(payload)
                if rec.projection_id not in self.epistemic_projections.records:
                    self.epistemic_projections.register(rec)
            elif kind == "EPISTEMIC_PROJECTION_CHANGED":
                pid=payload.get("projection_id")
                if pid in self.epistemic_projections.records:
                    target_epoch=int(payload["epoch"])
                    # Event streams are ordered; tolerate legacy duplicate replay guards.
                    while self.epistemic_projections.records[pid].epoch < target_epoch:
                        self.epistemic_projections.change(
                            pid,new_signature_sha256=payload["signature_sha256"]
                        )
                    self.epistemic_contrasts.invalidate_projection(pid,target_epoch)
            elif kind == "EPISTEMIC_PROJECTION_DEPENDENCY_INVALIDATED":
                for pid in payload.get("projection_ids", ()):
                    if pid in self.epistemic_projections.records and self.epistemic_projections.records[pid].current:
                        rec = self.epistemic_projections.invalidate(pid)
                        self.epistemic_contrasts.invalidate_projection(pid, rec.epoch)
            elif kind == "EPISTEMIC_PROJECTION_PREDICTIVE_INVALIDATED":
                pid=payload.get("projection_id")
                if pid in self.epistemic_projections.records and self.epistemic_projections.records[pid].current:
                    rec=self.epistemic_projections.invalidate(pid)
                    self.epistemic_contrasts.invalidate_projection(pid,rec.epoch)
            elif kind == "EPISTEMIC_PROJECTION_RECURRENCE_ASSESSED":
                witness=ProjectionRecurrenceWitness.from_serializable(payload)
                self.epistemic_projection_recurrence_witnesses.setdefault(witness.digest(), witness)
            elif kind == "EPISTEMIC_PROJECTION_REACTIVATED":
                rec_payload=payload.get("record", {})
                rec=EpistemicProjectionRecord.from_serializable(rec_payload)
                if rec.projection_id in self.epistemic_projections.records:
                    self.epistemic_projections.records[rec.projection_id]=rec
                else:
                    self.epistemic_projections.register(rec)
            elif kind == "EPISTEMIC_CONTRAST_REGISTERED":
                binding=EpistemicContrastBinding.from_serializable(payload)
                if binding.binding_id not in self.epistemic_contrasts.bindings:
                    # A historical binding may already be stale because its projection
                    # changed later in the same event stream. At registration time its
                    # captured projection epochs must still be current.
                    self.epistemic_contrasts.register(binding)
            elif kind == "EPISTEMIC_BEARING_WITNESS_RECORDED":
                self.epistemic_contrasts.replay_witness(
                    EpistemicBearingWitness.from_serializable(payload)
                )
        # Deficit staleness is authoritative even if an older binding event predates it.
        for did,rec in self.epistemic_deficits.records.items():
            if rec.state == EpistemicDeficitState.STALE:
                self.epistemic_contrasts.invalidate_deficit(did,reason=rec.stale_reason or "REPLAYED_DEFICIT_STALE")

    def _load_drift_intervention_state(self) -> None:
        """Replay historical intervention plans/witnesses without restoring execution access."""
        for event in self.store.events():
            kind=event.get("kind"); payload=event.get("payload",{})
            if kind == "EPISTEMIC_DRIFT_INTERVENTION_PLAN_SELECTED":
                sel=DriftInterventionSelection.from_serializable(payload)
                if sel.plan_id:
                    self.epistemic_drift_intervention_plans.setdefault(sel.plan_id, sel)
            elif kind == "EPISTEMIC_DRIFT_INTERVENTION_WITNESS_RECORDED":
                wit=DriftInterventionWitness.from_serializable(payload)
                self.epistemic_drift_intervention_witnesses.setdefault(wit.witness_id, wit)

    def _load_recruitment_proposals(self) -> None:
        for event in self.store.events():
            if event.get("kind") != "RECRUITMENT_PROPOSAL":
                continue
            proposal = RecruitmentProposal.from_serializable(event["payload"])
            self.recruitments.add(proposal)

    def nominate_recruitment(
        self,
        options: Iterable[RecruitmentOption],
        selected_capability_ids: Iterable[str],
        *,
        value_ids: Iterable[str] = (),
        operational_scope_id: str | None = None,
        topology_id: str | None = None,
        role_topology_origin: str = "SUPPLIED_AND_PROVENANCED",
        assistance_ancestry: Iterable[str] = (),
    ) -> RecruitmentProposal:
        """Content-bind a model-output recruitment proposal; never certify it.

        The caller/model supplies candidate options and the selected set. The
        entity enforces typed feasibility, shared-resource conflict checks and
        current dependency epochs. The parent/child topology remains explicit
        supplied ancestry and no semantic goal or effect authority is created.
        """
        selected=tuple(selected_capability_ids)
        opts=RecruitmentRegistry.validate_inputs(options, selected)
        assistance=tuple(assistance_ancestry)
        topology_epoch=None
        if topology_id is None:
            if role_topology_origin != "SUPPLIED_AND_PROVENANCED":
                raise ValueError("RECRUITMENT_TOPOLOGY_ORIGIN_UNQUALIFIED")
            if "SUPPLIED_RECRUITMENT_TOPOLOGY" not in assistance:
                assistance=("SUPPLIED_RECRUITMENT_TOPOLOGY",) + assistance
        else:
            if role_topology_origin not in {"SUPPLIED_AND_PROVENANCED", "EXTERNALLY_QUALIFIED_OPERATIONAL_TOPOLOGY"}:
                raise ValueError("RECRUITMENT_TOPOLOGY_ORIGIN_UNQUALIFIED")
            if not self.topologies.is_current(topology_id):
                raise ValueError(f"RECRUITMENT_TOPOLOGY_NOT_CURRENT:{topology_id}")
            topology_epoch=(topology_id,self.topologies.epochs[topology_id])
            nodes=self.topologies.nodes(topology_id)
            missing=sorted(set(selected)-nodes)
            if missing:
                raise ValueError("RECRUITMENT_SELECTION_OUTSIDE_TOPOLOGY:"+",".join(missing))
            role_topology_origin="EXTERNALLY_QUALIFIED_OPERATIONAL_TOPOLOGY"
            marker=f"QUALIFIED_OPERATIONAL_RECRUITMENT_TOPOLOGY:{topology_id}@{topology_epoch[1]}"
            if marker not in assistance:
                assistance=(marker,) + assistance
        cap_epochs=[]
        for cid in selected:
            c=self.capabilities.contracts.get(cid)
            if c is None or c.qualification not in {QualificationState.QUALIFIED,QualificationState.SHADOW_QUALIFIED}:
                raise ValueError(f"RECRUITMENT_CAPABILITY_NOT_CURRENT:{cid}")
            if c.operational_scope_id and c.operational_scope_id != operational_scope_id:
                raise ValueError(f"RECRUITMENT_SCOPE_MISMATCH:{cid}")
            cap_epochs.append((cid,self.capabilities.epochs.get(cid,0)))
        value_epochs=[]
        for vid in value_ids:
            if not self.values.is_current(vid): raise ValueError(f"RECRUITMENT_VALUE_NOT_CURRENT:{vid}")
            value_epochs.append((vid,self.values.epochs[vid]))
        proto=RecruitmentProposal(
            proposal_id="PENDING", options=opts, selected_capability_ids=selected,
            capability_epochs=tuple(cap_epochs), value_epochs=tuple(value_epochs),
            topology_epoch=topology_epoch, operational_scope_id=operational_scope_id, role_topology_origin=role_topology_origin,
            assistance_ancestry=assistance,
        )
        pid="recruit-"+proto.digest()[:20]
        proposal=RecruitmentProposal(**{**proto.__dict__,"proposal_id":pid})
        self.recruitments.add(proposal)
        packet=proposal.serializable()
        self.path.append("RECRUITMENT_PROPOSAL",packet); self.store.append("RECRUITMENT_PROPOSAL",packet)
        return proposal

    def recruitment_status(self, proposal_id: str) -> dict[str, Any]:
        return self.recruitments.currentness(proposal_id,self.capabilities,self.values,self.topologies)

    def compose_recruitment(self, proposal_id: str) -> dict[str, Any]:
        return self.recruitments.compose(proposal_id,self.capabilities,self.values,self.topologies)

    def _load_counterfactual_rehearsals(self) -> None:
        """Replay rehearsal proposal history without execution or qualification gain."""
        for event in self.store.events():
            if event.get("kind") != "COUNTERFACTUAL_REHEARSAL_PROPOSAL":
                continue
            proposal = CounterfactualRehearsalProposal.from_serializable(event.get("payload", {}))
            if proposal.proposal_id not in self.counterfactual_rehearsals.proposals:
                self.counterfactual_rehearsals.add(proposal)

    def _load_action_closure(self) -> None:
        """Replay bounded action-loop history without restoring executable handlers/contracts."""
        for event in self.store.events():
            kind=event.get("kind"); payload=event.get("payload",{})
            if kind == "OPAQUE_CONTROL_STATE_OBSERVED":
                self.action_closure.set_state(OpaqueControlStateWitness(**payload))
            elif kind == "BOUNDED_ACTION_INTENT":
                x=BoundedActionIntent.from_serializable(payload)
                if x.intent_id not in self.action_closure.intents: self.action_closure.add_intent(x)
            elif kind == "BOUNDED_ACTION_EXECUTED":
                x=ActionExecutionRecord.from_serializable(payload)
                if x.execution_id not in self.action_closure.executions: self.action_closure.add_execution(x)
            elif kind == "BOUNDED_ACTION_OUTCOME":
                x=ActionOutcomeRecord.from_serializable(payload)
                if x.outcome_id not in self.action_closure.outcomes: self.action_closure.add_outcome(x)

    def _load_action_outcome_learning(self) -> None:
        """Replay experience-derived model proposals/relations without qualification or execution gain."""
        for event in self.store.events():
            kind=event.get("kind"); payload=event.get("payload",{})
            if kind == "ACTION_OUTCOME_PREDICTIVE_CANDIDATE":
                c=ActionOutcomePredictiveCandidate.from_serializable(payload)
                self.action_outcome_learning.add_candidate(c)
            elif kind == "ACTION_OUTCOME_PREDICTIVE_RELATION_QUALIFIED":
                r=QualifiedActionOutcomePredictiveRelation.from_serializable(payload)
                self.action_outcome_learning.add_relation(r)
            elif kind == "ACTION_OUTCOME_PROJECTION_ROUTING_CANDIDATE":
                c=ProjectionConditionedRelationCandidate.from_serializable(payload)
                self.action_outcome_learning.add_projection_routing_candidate(c)
            elif kind == "ACTION_OUTCOME_PROJECTION_ROUTING_QUALIFIED":
                b=QualifiedProjectionConditionedRelationBinding.from_serializable(payload)
                self.action_outcome_learning.add_projection_conditioned_binding(b)
            elif kind == "ACTION_OUTCOME_PREDICTIVE_CURRENTNESS_WITNESS":
                w=ActionOutcomePredictiveCurrentnessWitness.from_serializable(payload)
                self.action_outcome_learning.currentness_witnesses[w.relation_id]=w
            elif kind == "ACTION_OUTCOME_REPLACEMENT_LINK":
                link=ActionOutcomeReplacementLink.from_serializable(payload)
                self.action_outcome_learning.replacement_links[link.candidate_id]=link
            elif kind == "ACTION_OUTCOME_REPLACEMENT_RELATION_LINK":
                rid=str(payload.get("relation_id",""))
                if rid:
                    self.action_outcome_learning.relation_replacement_lineage[rid]={
                        "replacement_of_relation_id":str(payload.get("replacement_of_relation_id","")),
                        "drift_witness_id":str(payload.get("drift_witness_id","")),
                    }

    def _rehearsal_observation_current(self, row: RehearsalTransitionObservation) -> bool:
        cap = self.capabilities.contracts.get(row.capability_id)
        if cap is None or cap.qualification not in {QualificationState.QUALIFIED, QualificationState.SHADOW_QUALIFIED}:
            return False
        if self.capabilities.epochs.get(row.capability_id, -1) != row.capability_epoch:
            return False
        if not self.frames.is_current(row.frame_id, row.frame_epoch):
            return False
        if not self.episodes.is_current(row.episode_schema_id, row.episode_schema_epoch):
            return False
        if row.topology_id is not None:
            if row.topology_epoch is None or not self.topologies.is_current(row.topology_id, row.topology_epoch):
                return False
        elif row.topology_epoch is not None:
            return False
        if row.coordination_id is not None:
            if row.coordination_epoch is None or not self.coordinations.is_current(row.coordination_id, row.coordination_epoch):
                return False
        elif row.coordination_epoch is not None:
            return False
        return True

    def nominate_counterfactual_rehearsal(
        self, observations: Iterable[RehearsalTransitionObservation], options: Iterable[RecruitmentOption],
        *, start_state_id: str, value_id: str, config: CounterfactualRehearsalConfig = CounterfactualRehearsalConfig(),
        projection_routing_id: str | None = None, projection_bucket_id: str | None = None,
        routing_task_id: str | None = None, routing_channel_id: str | None = None,
    ) -> CounterfactualRehearsalProposal | None:
        """Nominate a bounded evidence-backed rehearsal; never execute or certify it.

        The current value variable supplies only an opaque viable-interval pressure
        coordinate. Opaque state buckets, trace boundaries, candidate vocabulary and
        finite horizon remain explicit assistance/current operational structure.
        """
        if not self.values.is_current(value_id):
            return None
        latest = self.values.latest.get(value_id)
        if latest is None or latest[0] != self.values.epochs[value_id]:
            return None
        value_contract = self.values.contracts[value_id]
        rows = tuple(observations)
        opts = tuple(options)
        option_ids = {o.capability_id for o in opts}
        if not opts:
            return None
        if any(r.capability_id not in option_ids for r in rows):
            raise ValueError("REHEARSAL_OBSERVATION_OUTSIDE_CANDIDATE_VOCABULARY")
        current_rows = tuple(r for r in rows if self._rehearsal_observation_current(r))
        relations = derive_rehearsal_transition_relations(current_rows, config)
        # Independently qualified experience-derived relations may supplement raw rows.
        # Proposal-only candidates never enter rehearsal.
        for learned in self.action_outcome_learning.relations.values():
            if learned.capability_id not in option_ids or not self._action_outcome_relation_current(learned):
                continue
            if learned.value_epoch != (value_id, self.values.epochs[value_id]):
                continue
            rr=learned.as_rehearsal_relation()
            if rr is None: continue
            relations.setdefault((rr.state_id,rr.capability_id),rr)
        # MS1453-1477: do not create a second state subsystem. An already-qualified
        # v1.7+ epistemic projection may condition which v2.5+ learned relation is
        # used. The binding may scoped-requalify an empirically stale historical
        # relation, but never a structurally stale one and never globally reactivate it.
        if projection_routing_id is not None:
            if projection_bucket_id is None or routing_task_id is None or routing_channel_id is None:
                return None
            binding=self.action_outcome_learning.projection_conditioned_bindings.get(projection_routing_id)
            if binding is None or not self._projection_conditioned_binding_current(binding):
                return None
            if routing_task_id!=binding.task_id or routing_channel_id not in binding.channel_ids or int(config.max_horizon)!=binding.horizon:
                return None
            for action_id in sorted(option_ids & set(binding.action_ids)):
                resolved=self.resolve_projection_conditioned_action_outcome_relation(
                    projection_routing_id,projection_bucket_id=str(projection_bucket_id),action_id=action_id,
                    task_id=str(routing_task_id),channel_id=str(routing_channel_id),horizon=int(config.max_horizon),
                )
                if resolved.get("status")!="CURRENT_PARTITION_SCOPED_RELATION":
                    return None
                learned=self.action_outcome_learning.relations[resolved["relation_id"]]
                if learned.value_epoch != (value_id, self.values.epochs[value_id]):
                    return None
                rr=learned.as_rehearsal_relation()
                if rr is None:
                    return None
                rr=replace(rr,source_evidence_ids=tuple(rr.source_evidence_ids)+tuple(binding.qualification_evidence_ids))
                relations[(rr.state_id,rr.capability_id)]=rr
        if not relations:
            return None
        proposal = propose_counterfactual_rehearsal(
            relations, start_state_id=start_state_id, start_value=float(latest[1]),
            viable_low=float(value_contract.viable_low), viable_high=float(value_contract.viable_high),
            value_epoch=(value_id, self.values.epochs[value_id]), options=opts, cfg=config,
        )
        if proposal is None:
            return None
        self.counterfactual_rehearsals.add(proposal)
        packet = proposal.serializable()
        self.path.append("COUNTERFACTUAL_REHEARSAL_PROPOSAL", packet)
        self.store.append("COUNTERFACTUAL_REHEARSAL_PROPOSAL", packet)
        return proposal

    def counterfactual_rehearsal_status(self, proposal_id: str) -> dict[str, Any]:
        p = self.counterfactual_rehearsals.proposals.get(proposal_id)
        if p is None:
            return {"status":"UNKNOWN_INCOMPLETE","reason":"REHEARSAL_PROPOSAL_NOT_FOUND","authority":Authority.NONE.value}
        for cid, epoch in p.capability_epochs:
            c = self.capabilities.contracts.get(cid)
            if c is None or c.qualification not in {QualificationState.QUALIFIED, QualificationState.SHADOW_QUALIFIED} or self.capabilities.epochs.get(cid,-1) != epoch:
                return {"status":"UNKNOWN_INCOMPLETE","reason":f"REHEARSAL_CAPABILITY_NOT_CURRENT:{cid}","authority":Authority.NONE.value}
        for fid, epoch in p.frame_epochs:
            if not self.frames.is_current(fid, epoch):
                return {"status":"UNKNOWN_INCOMPLETE","reason":f"REHEARSAL_FRAME_NOT_CURRENT:{fid}","authority":Authority.NONE.value}
        for sid, epoch in p.episode_schema_epochs:
            if not self.episodes.is_current(sid, epoch):
                return {"status":"UNKNOWN_INCOMPLETE","reason":f"REHEARSAL_EPISODE_NOT_CURRENT:{sid}","authority":Authority.NONE.value}
        vid, vepoch = p.value_epoch
        if not self.values.is_current(vid, vepoch):
            return {"status":"UNKNOWN_INCOMPLETE","reason":f"REHEARSAL_VALUE_NOT_CURRENT:{vid}","authority":Authority.NONE.value}
        for tid, epoch in p.topology_epochs:
            if not self.topologies.is_current(tid, epoch):
                return {"status":"UNKNOWN_INCOMPLETE","reason":f"REHEARSAL_TOPOLOGY_NOT_CURRENT:{tid}","authority":Authority.NONE.value}
        for rid, epoch in p.coordination_epochs:
            if not self.coordinations.is_current(rid, epoch):
                return {"status":"UNKNOWN_INCOMPLETE","reason":f"REHEARSAL_COORDINATION_NOT_CURRENT:{rid}","authority":Authority.NONE.value}
        return {
            "status":"CURRENT_REHEARSAL_PROPOSAL", "proposal_id":proposal_id, "sequence":list(p.sequence),
            "authority":p.authority, "truth_authority":p.truth_authority, "execution_authority":p.execution_authority,
            "qualification_authority":p.qualification_authority, "semantic_goal_authority":p.semantic_goal_authority,
        }

    def observe_opaque_control_state(self, obs: Observation, *, evidence_id: str) -> dict[str, Any]:
        """Accept one external opaque control-state observation; never infer semantic state identity."""
        if obs.authority != Authority.OBSERVATION_ONLY:
            return {"status":"UNKNOWN_INCOMPLETE","reason":"CONTROL_STATE_REQUIRES_OBSERVATION_AUTHORITY"}
        state_id=str(obs.value)
        if not state_id:
            return {"status":"UNKNOWN_INCOMPLETE","reason":"EMPTY_OPAQUE_CONTROL_STATE"}
        self.observe(obs)
        ref=self.append_evidence(evidence_id,{"capture_id":obs.capture_id,"state_id":state_id,"referent":obs.referent},EpistemicStatus.PRESSURE_SUPPORTED,source=obs.origin)
        w=OpaqueControlStateWitness(state_id=state_id,evidence_id=ref.evidence_id)
        self.action_closure.set_state(w)
        packet=w.serializable(); self.path.append("OPAQUE_CONTROL_STATE_OBSERVED",packet); self.store.append("OPAQUE_CONTROL_STATE_OBSERVED",packet)
        return {"status":"CURRENT_OPAQUE_CONTROL_STATE",**packet}

    def derive_bounded_action_commitment(self, proposal_id: str) -> RelationalCommitment:
        """Derive a premise-licensing stance for only the next action of one current rehearsal.

        YES is model-relative premise licensing only. It never grants EFFECT, truth, intention,
        qualification, or multi-step execution authority.
        """
        p=self.counterfactual_rehearsals.proposals.get(proposal_id)
        if p is None:
            return RelationalCommitment(action_stable_id("ACTION-COMMIT-",{"proposal_id":proposal_id,"missing":True}),f"rehearsal:{proposal_id}:next-action",TernaryCommitment.UNKNOWN,binding=TernaryCommitment.UNKNOWN,reason="REHEARSAL_PROPOSAL_NOT_FOUND")
        cap_id=p.sequence[0] if p.sequence else "NONE"
        target=f"capability:{cap_id}:execute"
        base={"proposal_id":proposal_id,"proposal_digest":p.digest(),"target":target}
        st=self.counterfactual_rehearsal_status(proposal_id)
        if st.get("status") != "CURRENT_REHEARSAL_PROPOSAL":
            return RelationalCommitment(action_stable_id("ACTION-COMMIT-",{**base,"status":st.get('reason')}),target,TernaryCommitment.UNKNOWN,reason=st.get("reason","REHEARSAL_NOT_CURRENT"),qualifiers=(("proposal_id",proposal_id),("authority_gain","NONE")))
        cw=self.action_closure.current_state
        if cw is None:
            return RelationalCommitment(action_stable_id("ACTION-COMMIT-",{**base,"state":"missing"}),target,TernaryCommitment.UNKNOWN,binding=TernaryCommitment.UNKNOWN,reason="NO_CURRENT_OPAQUE_CONTROL_STATE",qualifiers=(("proposal_id",proposal_id),("authority_gain","NONE")))
        if cw.state_id != p.start_state_id:
            return RelationalCommitment(action_stable_id("ACTION-COMMIT-",{**base,"state":cw.state_id}),target,TernaryCommitment.UNKNOWN,applicability=TernaryCommitment.NO,reason="REHEARSAL_START_STATE_NOT_APPLICABLE_NOW",qualifiers=(("proposal_id",proposal_id),("current_state",cw.state_id),("authority_gain","NONE")))
        if not p.sequence or len(p.predicted_state_path)<2 or len(p.predicted_step_value_effects)<1:
            return RelationalCommitment(action_stable_id("ACTION-COMMIT-",{**base,"stepwise":False}),target,TernaryCommitment.UNKNOWN,reason="STEPWISE_PREDICTION_ANCESTRY_UNAVAILABLE",qualifiers=(("proposal_id",proposal_id),("authority_gain","NONE")))
        pressure=self.values.pressure(p.value_epoch[0])
        if pressure.get("status") != "CURRENT":
            return RelationalCommitment(action_stable_id("ACTION-COMMIT-",{**base,"pressure":"unknown"}),target,TernaryCommitment.UNKNOWN,reason="REGULATORY_PRESSURE_NOT_CURRENT",qualifiers=(("proposal_id",proposal_id),("authority_gain","NONE")))
        current = float(pressure["pressure_magnitude"])
        # MS1531 research repair: value-contract currentness does not imply the
        # observed regulatory value is unchanged. Reproject the already-earned
        # effect against the current observation instead of trusting historical
        # residual pressure captured when the proposal was nominated.
        latest = self.values.latest.get(p.value_epoch[0])
        if latest is None or latest[0] != p.value_epoch[1]:
            return RelationalCommitment(
                action_stable_id("ACTION-COMMIT-", {**base, "value_state": "missing"}),
                target,
                TernaryCommitment.UNKNOWN,
                reason="REGULATORY_VALUE_STATE_NOT_CURRENT",
                qualifiers=(("proposal_id", proposal_id), ("authority_gain", "NONE")),
            )
        value_contract = self.values.contracts[p.value_epoch[0]]
        residual = residual_pressure_after_effect(
            value_contract,
            float(latest[1]),
            float(p.predicted_value_effect),
        )
        qualifiers = (
            ("proposal_id", proposal_id),
            ("control_state_evidence_id", cw.evidence_id),
            ("model_authority", p.authority),
            ("execution_authority", "NONE"),
            ("truth_authority", "NONE"),
            ("residual_basis", "CURRENT_VALUE_PLUS_EXISTING_PREDICTED_VALUE_EFFECT"),
        )
        if current <= 0.0:
            stance=TernaryCommitment.NO; reason="NO_CURRENT_REGULATORY_PRESSURE"
        elif residual < current:
            stance=TernaryCommitment.YES; reason="BOUNDED_REHEARSAL_PREDICTS_LOWER_REGULATORY_PRESSURE"
        elif residual > current:
            stance=TernaryCommitment.NO; reason="BOUNDED_REHEARSAL_PREDICTS_WORSE_REGULATORY_PRESSURE"
        else:
            stance=TernaryCommitment.UNKNOWN; reason="NO_DISCRIMINATING_REGULATORY_ADVANTAGE"
        return RelationalCommitment(action_stable_id("ACTION-COMMIT-",{**base,"state":cw.state_id,"current":current,"residual":residual}),target,stance,reason=reason,qualifiers=qualifiers,premise_ids=(proposal_id,))

    def nominate_bounded_action_intent(self, proposal_id: str, obligation: QueryObligation) -> dict[str, Any]:
        """Nominate only the first action; commitment YES still grants no execution authority."""
        cmt=self.derive_bounded_action_commitment(proposal_id)
        if not cmt.licenses_yes():
            return {"status":"ABSTAIN","reason":cmt.reason,"commitment":cmt.serializable(),"execution_authority":"NONE"}
        p=self.counterfactual_rehearsals.proposals[proposal_id]; cid=p.sequence[0]; cap=self.capabilities.contracts.get(cid)
        if cap is None or cap.qualification not in {QualificationState.QUALIFIED,QualificationState.SHADOW_QUALIFIED}:
            return {"status":"ABSTAIN","reason":"ACTION_CAPABILITY_NOT_CURRENT","commitment":cmt.serializable(),"execution_authority":"NONE"}
        if self.capabilities.epochs.get(cid,-1) != dict(p.capability_epochs).get(cid,-2):
            return {"status":"ABSTAIN","reason":"ACTION_CAPABILITY_EPOCH_DRIFT","commitment":cmt.serializable(),"execution_authority":"NONE"}
        if cap.authority != Authority.EFFECT:
            return {"status":"ABSTAIN","reason":"ACTION_REQUIRES_EFFECT_AUTHORITY","commitment":cmt.serializable(),"execution_authority":"NONE"}
        if obligation.required_authority != Authority.EFFECT:
            return {"status":"ABSTAIN","reason":"ACTION_OBLIGATION_MUST_REQUIRE_EFFECT","commitment":cmt.serializable(),"execution_authority":"NONE"}
        if cap.query_obligation_id and cap.query_obligation_id != obligation.obligation_id:
            return {"status":"ABSTAIN","reason":"QUERY_OBLIGATION_MISMATCH","commitment":cmt.serializable(),"execution_authority":"NONE"}
        if cap.operational_scope_id and cap.operational_scope_id != obligation.operational_scope_id:
            return {"status":"ABSTAIN","reason":"OPERATIONAL_SCOPE_MISMATCH","commitment":cmt.serializable(),"execution_authority":"NONE"}
        cw=self.action_closure.current_state
        payload={"proposal":p.digest(),"commitment":cmt.commitment_id,"state_evidence":cw.evidence_id,"obligation":obligation.obligation_id,"scope":obligation.operational_scope_id}
        intent=BoundedActionIntent(intent_id=action_stable_id("ACTION-INTENT-",payload),proposal_id=proposal_id,proposal_digest=p.digest(),action_commitment=cmt,capability_id=cid,capability_epoch=self.capabilities.epochs[cid],start_state_id=cw.state_id,control_state_evidence_id=cw.evidence_id,expected_next_state_id=p.predicted_state_path[1],expected_value_effect=float(p.predicted_step_value_effects[0]),value_epoch=p.value_epoch,obligation_id=obligation.obligation_id,operational_scope_id=obligation.operational_scope_id)
        self.action_closure.add_intent(intent); packet=intent.serializable(); self.path.append("BOUNDED_ACTION_INTENT",packet); self.store.append("BOUNDED_ACTION_INTENT",packet)
        return {"status":"ACTION_INTENT_NOMINATED","intent":packet,"execution_authority":"NONE"}

    def nominate_multi_value_action_intent(self, value_ids: Iterable[str], obligation: QueryObligation, *, config: DiscoveryConfig | None = None) -> dict[str, Any]:
        """Nominate one unique multi-pressure license without inventing a single-value rehearsal anchor."""
        requested=tuple(str(value_id) for value_id in value_ids); cfg=config or DiscoveryConfig()
        license_result=self.derive_multi_value_action_licenses(requested,config=cfg)
        if license_result.get("status")!="UNIQUE_ACTION_LICENSE":
            return {"status":"ABSTAIN","reason":license_result.get("overall_commitment",{}).get("reason","MULTI_VALUE_LICENSE_NOT_UNIQUE"),"license":license_result,"execution_authority":"NONE"}
        cid=license_result["licensed_action_ids"][0]
        cmt=RelationalCommitment.from_serializable(license_result["action_commitments"][cid])
        cap=self.capabilities.contracts.get(cid)
        if not cmt.licenses_yes():
            return {"status":"ABSTAIN","reason":"MULTI_VALUE_ACTION_COMMITMENT_NOT_LICENSED","license":license_result,"execution_authority":"NONE"}
        if cap is None or cap.qualification not in {QualificationState.QUALIFIED,QualificationState.SHADOW_QUALIFIED}:
            return {"status":"ABSTAIN","reason":"ACTION_CAPABILITY_NOT_CURRENT","license":license_result,"execution_authority":"NONE"}
        if cap.authority!=Authority.EFFECT or obligation.required_authority!=Authority.EFFECT:
            return {"status":"ABSTAIN","reason":"ACTION_REQUIRES_EFFECT_AUTHORITY","license":license_result,"execution_authority":"NONE"}
        if cap.query_obligation_id and cap.query_obligation_id!=obligation.obligation_id:
            return {"status":"ABSTAIN","reason":"QUERY_OBLIGATION_MISMATCH","license":license_result,"execution_authority":"NONE"}
        if cap.operational_scope_id and cap.operational_scope_id!=obligation.operational_scope_id:
            return {"status":"ABSTAIN","reason":"OPERATIONAL_SCOPE_MISMATCH","license":license_result,"execution_authority":"NONE"}
        cw=self.action_closure.current_state
        if cw is None:
            return {"status":"ABSTAIN","reason":"CURRENT_CONTROL_STATE_REQUIRED","license":license_result,"execution_authority":"NONE"}
        value_epochs=tuple((value_id,self.values.epochs[value_id]) for value_id in requested)
        params=tuple((name,getattr(cfg,name)) for name in DiscoveryConfig.__dataclass_fields__)
        payload={"basis":"MULTI_VALUE_LICENSE","commitment":cmt.commitment_id,"capability":cid,"capability_epoch":self.capabilities.epochs[cid],"value_epochs":value_epochs,"derivation_parameters":params,"state_evidence":cw.evidence_id,"obligation":obligation.obligation_id,"scope":obligation.operational_scope_id}
        intent=BoundedActionIntent(intent_id=action_stable_id("ACTION-INTENT-",payload),proposal_id=None,proposal_digest=None,action_commitment=cmt,capability_id=cid,capability_epoch=self.capabilities.epochs[cid],start_state_id=cw.state_id,control_state_evidence_id=cw.evidence_id,expected_next_state_id=None,expected_value_effect=None,value_epoch=None,obligation_id=obligation.obligation_id,operational_scope_id=obligation.operational_scope_id,basis_kind="MULTI_VALUE_LICENSE",required_value_epochs=value_epochs,derivation_parameters=params)
        self.action_closure.add_intent(intent); packet=intent.serializable(); self.path.append("BOUNDED_ACTION_INTENT",packet); self.store.append("BOUNDED_ACTION_INTENT",packet)
        return {"status":"ACTION_INTENT_NOMINATED","intent":packet,"license":license_result,"execution_authority":"NONE"}

    def nominate_epistemic_program_step_intent(self, trial, feasibility: RecruitmentOption, obligation: QueryObligation) -> dict[str, Any]:
        """Research-only: nominate exactly one current epistemic-program primitive.

        The adapter grants no execution, truth, feasibility, or semantic-goal
        authority. The same trial + feasibility premises must be supplied again
        and re-derived immediately before EFFECT.
        """
        deficit=self.epistemic_deficits.records.get(trial.deficit_id)
        intent,cmt=derive_epistemic_program_step_intent(
            trial=trial, deficit=deficit, feasibility=feasibility, capabilities=self.capabilities,
            obligation=obligation, current_frame_epochs=dict(self.frames.epochs),
            current_state=self.action_closure.current_state,
        )
        if intent is None:
            return {"status":"ABSTAIN","reason":cmt.reason,"commitment":cmt.serializable(),"execution_authority":"NONE"}
        self.action_closure.add_intent(intent)
        packet=intent.serializable(); self.path.append("BOUNDED_ACTION_INTENT",packet); self.store.append("BOUNDED_ACTION_INTENT",packet)
        return {"status":"ACTION_INTENT_NOMINATED","intent":packet,"commitment":cmt.serializable(),"execution_authority":"NONE","research_basis":"EPISTEMIC_PROGRAM_STEP"}

    def nominate_grounded_epistemic_program_step_intent(
        self, trial, feasibility_capability_id: str, feasibility_obligation: QueryObligation, obligation: QueryObligation
    ) -> dict[str, Any]:
        """Research-only: nominate one primitive using a freshly invoked ordinary feasibility capability."""
        idx=len(trial.step_records)
        if trial.status!="OPEN" or idx>=len(trial.steps):
            return {"status":"ABSTAIN","reason":"EPISTEMIC_PROGRAM_NOT_OPEN","execution_authority":"NONE"}
        option,feasibility_basis=derive_grounded_feasibility_option(
            target_capability_id=trial.steps[idx], feasibility_capability_id=feasibility_capability_id,
            feasibility_obligation=feasibility_obligation, capabilities=self.capabilities,
        )
        deficit=self.epistemic_deficits.records.get(trial.deficit_id)
        intent,cmt=derive_epistemic_program_step_intent(
            trial=trial, deficit=deficit, feasibility=option, capabilities=self.capabilities,
            obligation=obligation, current_frame_epochs=dict(self.frames.epochs),
            current_state=self.action_closure.current_state,
        )
        if intent is None:
            return {"status":"ABSTAIN","reason":cmt.reason,"commitment":cmt.serializable(),"feasibility_basis":feasibility_basis,"execution_authority":"NONE"}
        self.action_closure.add_intent(intent)
        packet=intent.serializable(); self.path.append("BOUNDED_ACTION_INTENT",packet); self.store.append("BOUNDED_ACTION_INTENT",packet)
        return {"status":"ACTION_INTENT_NOMINATED","intent":packet,"commitment":cmt.serializable(),"feasibility_basis":feasibility_basis,"execution_authority":"NONE","research_basis":"EPISTEMIC_PROGRAM_STEP_GROUNDED_FEASIBILITY"}

    def _evaluate_endogenous_epistemic_trial_candidate(
        self, candidate: OpaqueActionCompositionCandidate | GeneratedEpistemicProgramCandidate, *, deficit_id: str,
        decision_context: EpistemicDecisionBearingContext, obligation: QueryObligation,
        feasibility_options: tuple[RecruitmentOption, ...], feasibility_basis: dict[str, dict[str, object]],
    ) -> dict[str, Any]:
        """Research-only pure admission check for one already-represented candidate."""
        deficit=self.epistemic_deficits.records.get(str(deficit_id))
        current_state=self.action_closure.current_state
        if deficit is None:
            return {"status":"ABSTAIN","reason":"EPISTEMIC_DEFICIT_NOT_FOUND","execution_authority":"NONE"}
        if current_state is None:
            return {"status":"ABSTAIN","reason":"CURRENT_CONTROL_STATE_REQUIRED","execution_authority":"NONE"}
        try:
            begin = begin_generated_epistemic_program_trial if isinstance(candidate, GeneratedEpistemicProgramCandidate) else begin_epistemic_program_trial
            trial=begin(
                candidate, deficit_id=deficit.deficit_id,
                discrimination_signature_sha256=deficit.missing_discriminator_signature_sha256,
                capabilities=self.capabilities, obligation=obligation,
                current_frame_epochs=dict(self.frames.epochs),
                start_state_id=current_state.state_id, start_state_evidence_id=current_state.evidence_id,
            )
        except ValueError as exc:
            return {"status":"ABSTAIN","reason":str(exc),"execution_authority":"NONE"}
        first=trial.steps[0]
        option=next((x for x in feasibility_options if x.capability_id==first),None)
        if option is None:
            return {"status":"ABSTAIN","reason":"NO_CURRENT_FIRST_STEP_FEASIBILITY_ROUTE","execution_authority":"NONE"}
        # Preserve the already-earned first-step need/feasibility/route/state gate
        # *before* common opportunity priority.  A refused/unknown/missing route
        # must not be relabelled as a priority failure merely because arbitration
        # now shares one grounded feasibility surface.
        local=derive_epistemic_program_step_commitment(
            trial=trial, deficit=deficit, feasibility=option, capabilities=self.capabilities,
            obligation=obligation, current_frame_epochs=dict(self.frames.epochs), current_state=current_state,
        )
        if not local.licenses_yes():
            return {"status":"ABSTAIN","reason":local.reason,"commitment":local.serializable(),"feasibility_basis":feasibility_basis.get(first),"execution_authority":"NONE"}
        priority=derive_current_decision_bearing_commitment_from_grounded_surface(
            trial=trial, deficit=deficit, decision_context=decision_context,
            feasibility_options=feasibility_options, capabilities=self.capabilities, values=self.values,
            current_frame_epochs=dict(self.frames.epochs), current_episode_epochs=dict(self.episodes.epochs),
            current_topology_epochs=dict(self.topologies.epochs), current_coordination_epochs=dict(self.coordinations.epochs),
        )
        if not priority.licenses_yes():
            return {"status":"ABSTAIN","reason":priority.reason,"priority":priority.serializable(),"execution_authority":"NONE"}
        information=derive_current_program_discrimination_commitment(
            trial=trial, decision_context=decision_context, decision_bearing_commitment=priority,
        )
        if not information.licenses_yes():
            return {"status":"ABSTAIN","reason":information.reason,"priority":priority.serializable(),"information":information.serializable(),"execution_authority":"NONE"}
        commitment=derive_epistemic_program_step_commitment(
            trial=trial, deficit=deficit, feasibility=option, capabilities=self.capabilities,
            obligation=obligation, current_frame_epochs=dict(self.frames.epochs),
            current_state=current_state, priority_commitment=priority, information_commitment=information,
        )
        if not commitment.licenses_yes():
            return {"status":"ABSTAIN","reason":commitment.reason,"priority":priority.serializable(),"information":information.serializable(),"commitment":commitment.serializable(),"feasibility_basis":feasibility_basis.get(first),"execution_authority":"NONE"}
        return {
            "status":"EPISTEMIC_TRIAL_ADMISSIBLE", "reason":"CURRENT_INFORMATIVE_EXECUTABLE_OPPORTUNITY",
            "trial":trial, "trial_serializable":trial.serializable(),
            "priority":priority.serializable(), "information":information.serializable(),
            "commitment":commitment.serializable(), "feasibility_basis":feasibility_basis.get(first),
            "proposal_authority":"NONE", "truth_authority":"NONE", "execution_authority":"NONE",
        }

    def arbitrate_endogenous_epistemic_trial_candidates(
        self, candidates: Iterable[OpaqueActionCompositionCandidate | GeneratedEpistemicProgramCandidate], *, deficit_id: str,
        decision_context: EpistemicDecisionBearingContext, obligation: QueryObligation,
    ) -> dict[str, Any]:
        """Research-only bounded arbitration over current proposal candidates.

        Feasibility is grounded once for the whole cycle. Zero/one/multiple
        admissible candidates remain distinct. A unique winner is licensed only
        when its observable-trace partition strictly refines every other live
        admissible candidate; no scalar score or caller order is used.
        """
        before_intents=len(self.action_closure.intents); before_exec=len(self.action_closure.executions)
        options,basis=derive_current_grounded_feasibility_surface(
            capabilities=self.capabilities, operational_scope_id=obligation.operational_scope_id,
        )
        rows=[]
        for candidate in sorted(tuple(candidates),key=lambda c:(c.digest(),c.candidate_id)):
            result=self._evaluate_endogenous_epistemic_trial_candidate(
                candidate, deficit_id=deficit_id, decision_context=decision_context, obligation=obligation,
                feasibility_options=options, feasibility_basis=basis,
            )
            rows.append((candidate,result))
        admitted=[(c,r) for c,r in rows if r.get("status")=="EPISTEMIC_TRIAL_ADMISSIBLE"]
        assert len(self.action_closure.intents)==before_intents and len(self.action_closure.executions)==before_exec
        if not admitted:
            reasons=tuple(sorted({str(r.get("reason","ABSTAIN")) for _,r in rows}))
            return {"status":"ABSTAIN","reason":reasons[0] if len(reasons)==1 else "NO_CURRENT_EXECUTABLE_DISCRIMINATOR","candidate_reasons":reasons,"execution_authority":"NONE"}
        if len(admitted)==1:
            c,r=admitted[0]
            return {**r,"status":"EPISTEMIC_TRIAL_INSTANTIATED","relation_candidate_id":c.candidate_id}
        partitions=[]
        for c,r in admitted:
            part=derive_program_observable_partition(trial=r["trial"],decision_context=decision_context)
            partitions.append((c,r,part))
        dominators=[]
        for i,(c,r,p) in enumerate(partitions):
            if p is None: continue
            others=[op for j,(_,_,op) in enumerate(partitions) if j!=i]
            if others and all(op is not None and program_partition_strictly_refines(p,op) for op in others):
                dominators.append((c,r,p))
        if len(dominators)==1:
            c,r,p=dominators[0]
            return {**r,"status":"EPISTEMIC_TRIAL_INSTANTIATED","reason":"UNIQUE_STRICT_PARTITION_REFINEMENT","relation_candidate_id":c.candidate_id,"partition":p}
        return {
            "status":"MULTIPLE_CURRENT_EPISTEMIC_OPPORTUNITIES",
            "reason":"NO_UNIQUE_STRICT_PARTITION_REFINEMENT",
            "candidate_ids":tuple(c.candidate_id for c,_ in admitted),
            "partitions":tuple((c.candidate_id,p) for c,_,p in partitions),
            "selection_authority":"NONE","execution_authority":"NONE","truth_authority":"NONE",
        }

    def discover_and_arbitrate_endogenous_epistemic_trial(
        self, samples: Iterable[OpaqueTransitionSample], *, deficit_id: str,
        decision_context: EpistemicDecisionBearingContext, obligation: QueryObligation,
    ) -> dict[str, Any]:
        """Research-only composition from supplied current frame-bound transition values.

        The existing relational-algebra owner keeps its own support threshold.
        Supplied samples are not promoted to admitted observations or independent
        physical evidence by this wrapper.
        """
        candidates=discover_opaque_action_composition_candidates(tuple(samples))
        result=self.arbitrate_endogenous_epistemic_trial_candidates(
            candidates, deficit_id=deficit_id, decision_context=decision_context, obligation=obligation,
        )
        result=dict(result)
        result["candidate_surface_count"]=len(candidates)
        result["sample_provenance_authority"]="SUPPLIED_FRAME_BOUND_VALUES_ONLY"
        result["observation_admission_authority"]="NONE"
        result["evidence_independence_authority"]="NONE"
        return result

    def derive_bounded_action_outcome_epistemic_relation_sets(self) -> dict[str, Any]:
        """Derive one bounded ephemeral alternative-model surface from owned outcome history.

        Exactly one recurrent conflict locus is supported. Shared background edges
        must already be qualified/current learned relations on the same value
        coordinate. Multiple uncoupled conflicts abstain rather than acquiring
        Cartesian-product model coherence. Nothing is persisted or qualified here.
        """
        hypotheses=discover_action_outcome_alternative_hypotheses(self._action_outcome_experiences())
        base=assemble_single_conflict_epistemic_relation_sets(hypotheses)
        if not base:
            return {
                "status":"NO_SINGLE_CONFLICT_EPISODIC_MODEL_SURFACE",
                "hypothesis_count":len(hypotheses),"relation_sets":(),
                "model_set_authority":"NONE","truth_authority":"NONE","execution_authority":"NONE",
            }
        conflict=base[0][0]
        background=[]
        for learned in self.action_outcome_learning.relations.values():
            if not self._action_outcome_relation_current(learned):
                continue
            if learned.value_epoch != conflict.value_epoch:
                continue
            if (learned.start_state_id,learned.capability_id)==(conflict.state_id,conflict.capability_id):
                continue
            rr=learned.as_epistemic_alternative_relation()
            if rr is not None:
                background.append(rr)
        sets=assemble_single_conflict_epistemic_relation_sets(hypotheses,background_relations=tuple(background))
        if not sets:
            return {
                "status":"NO_COHERENT_SINGLE_CONFLICT_EPISODIC_MODEL_SURFACE",
                "hypothesis_count":len(hypotheses),"background_relation_count":len(background),"relation_sets":(),
                "model_set_authority":"NONE","truth_authority":"NONE","execution_authority":"NONE",
            }
        return {
            "status":"SINGLE_CONFLICT_EPISODIC_MODEL_SURFACE",
            "hypothesis_count":len(hypotheses),"background_relation_count":len(background),
            "relation_sets":sets,"conflict_slot":(conflict.state_id,conflict.capability_id),
            "value_epoch":conflict.value_epoch,"model_set_authority":"PROPOSAL_ONLY_EPHEMERAL",
            "truth_authority":"NONE","causal_explanation_authority":"NONE",
            "evidence_independence_authority":"NONE","execution_authority":"NONE",
        }

    def discover_and_arbitrate_endogenous_epistemic_trial_from_admitted_history_and_endogenous_alternatives(
        self, *, deficit_id: str, obligation: QueryObligation,
    ) -> dict[str, Any]:
        """Compose the MS1767 admitted-history surface with one endogenous conflict model surface."""
        surface=self.derive_bounded_action_outcome_epistemic_relation_sets()
        if surface.get("status")!="SINGLE_CONFLICT_EPISODIC_MODEL_SURFACE":
            return {
                "status":"ABSTAIN","reason":str(surface.get("status","NO_MODEL_SURFACE")),
                "alternative_surface":surface,"execution_authority":"NONE","truth_authority":"NONE",
            }
        decision_context=EpistemicDecisionBearingContext(tuple(surface["relation_sets"]),())
        result=self.discover_and_arbitrate_endogenous_epistemic_trial_from_admitted_history(
            deficit_id=deficit_id,decision_context=decision_context,obligation=obligation,
        )
        result=dict(result)
        result["alternative_surface_status"]=surface["status"]
        result["alternative_hypothesis_count"]=surface["hypothesis_count"]
        result["alternative_background_relation_count"]=surface["background_relation_count"]
        result["alternative_model_set_authority"]="PROPOSAL_ONLY_EPHEMERAL"
        result["world_model_authority"]="NONE"
        result["causal_explanation_authority"]="NONE"
        return result

    def discover_and_arbitrate_endogenous_epistemic_trial_from_admitted_history(
        self, *, deficit_id: str, decision_context: EpistemicDecisionBearingContext,
        obligation: QueryObligation,
    ) -> dict[str, Any]:
        """Research-only composition from authenticated admitted action history.

        This removes the caller-supplied transition-sample surface.  It does not
        construct the competing relational alternative-model set in
        `decision_context`, infer physical truth/independence, or execute an
        action during discovery/arbitration.
        """
        surface = self.discover_admitted_opaque_action_composition_candidates()
        result = self.arbitrate_endogenous_epistemic_trial_candidates(
            surface["candidates"], deficit_id=deficit_id,
            decision_context=decision_context, obligation=obligation,
        )
        result = dict(result)
        result["candidate_surface_count"] = len(surface["candidates"])
        result["admitted_sample_count"] = surface["admitted_sample_count"]
        result["rejected_execution_reasons"] = surface["rejected_execution_reasons"]
        result["sample_provenance_authority"] = "AUTHENTICATED_ORDINARY_EXECUTION_PLUS_BOUNDED_OBSERVATION_INGRESS"
        result["observation_admission_authority"] = "BOUNDED_ROUTE_PROVENANCE_ONLY"
        result["physical_truth_authority"] = "NONE"
        result["evidence_independence_authority"] = "NONE"
        return result

    def derive_action_outcome_successor_couplings(self):
        """Derive recurrent outcome-mode successor coupling from owned action history.

        The immediate-successor relation is recovered only from the exact content-bound
        control-state evidence link already carried by the next action intent. No episode
        object, caller-supplied successor pair, persistence, truth, causal, independence,
        or model-set authority is introduced here.
        """
        experiences = self._action_outcome_experiences()
        by_evidence: dict[str, list[ActionOutcomeExperience]] = {}
        for row in experiences:
            by_evidence.setdefault(row.evidence_id, []).append(row)
        successor_pairs = []
        for second in experiences:
            ex = self.action_closure.executions.get(second.execution_id)
            if ex is None:
                continue
            intent = self.action_closure.intents.get(ex.intent_id)
            if intent is None:
                continue
            first_rows = by_evidence.get(intent.control_state_evidence_id, ())
            if len(first_rows) != 1:
                continue
            first = first_rows[0]
            if first.execution_id == second.execution_id:
                continue
            if first.actual_next_state_id != second.start_state_id:
                continue
            successor_pairs.append((first.execution_id, second.execution_id))
        hypotheses = discover_action_outcome_alternative_hypotheses(experiences)
        return discover_action_outcome_successor_couplings(hypotheses, successor_pairs)

    def derive_successor_coupled_action_outcome_epistemic_relation_sets(self) -> dict[str, Any]:
        experiences = self._action_outcome_experiences()
        hypotheses = discover_action_outcome_alternative_hypotheses(experiences)
        couplings = self.derive_action_outcome_successor_couplings()
        base = assemble_successor_coupled_epistemic_relation_sets(hypotheses, couplings)
        if not base:
            relation_sets = ()
        else:
            conflict_slots = {(r.state_id, r.capability_id) for model in base for r in model}
            value_epochs = {r.value_epoch for model in base for r in model}
            background = []
            if len(value_epochs) == 1:
                value_epoch = next(iter(value_epochs))
                for learned in self.action_outcome_learning.relations.values():
                    if not self._action_outcome_relation_current(learned) or learned.value_epoch != value_epoch:
                        continue
                    if (learned.start_state_id, learned.capability_id) in conflict_slots:
                        continue
                    rr = learned.as_epistemic_alternative_relation()
                    if rr is not None:
                        background.append(rr)
            relation_sets = assemble_successor_coupled_epistemic_relation_sets(
                hypotheses, couplings, background_relations=tuple(background),
            )
        if not relation_sets:
            return {
                "status": "NO_COHERENT_SUCCESSOR_COUPLED_MODEL_SURFACE",
                "hypothesis_count": len(hypotheses), "coupling_count": len(couplings),
                "background_relation_count": 0, "relation_sets": (),
                "model_set_authority": "NONE", "truth_authority": "NONE", "execution_authority": "NONE",
            }
        return {
            "status": "SUCCESSOR_COUPLED_TWO_CONFLICT_MODEL_SURFACE",
            "hypothesis_count": len(hypotheses), "coupling_count": len(couplings),
            "background_relation_count": len(relation_sets[0]) - 2, "relation_sets": relation_sets,
            "model_set_authority": "PROPOSAL_ONLY_EPHEMERAL", "truth_authority": "NONE",
            "causal_explanation_authority": "NONE", "evidence_independence_authority": "NONE",
            "execution_authority": "NONE", "episode_manager_authority": "NONE",
        }

    def derive_three_locus_chain_action_outcome_epistemic_relation_sets(self) -> dict[str, Any]:
        experiences = self._action_outcome_experiences()
        hypotheses = discover_action_outcome_alternative_hypotheses(experiences)
        couplings = self.derive_action_outcome_successor_couplings()
        chains = discover_action_outcome_three_locus_chains(hypotheses, couplings)
        base = assemble_three_locus_chain_epistemic_relation_sets(hypotheses, chains)
        background = []
        if base:
            conflict_slots = {(r.state_id, r.capability_id) for model in base for r in model}
            value_epochs = {r.value_epoch for model in base for r in model}
            if len(value_epochs) == 1:
                value_epoch = next(iter(value_epochs))
                for learned in self.action_outcome_learning.relations.values():
                    if not self._action_outcome_relation_current(learned) or learned.value_epoch != value_epoch:
                        continue
                    if (learned.start_state_id, learned.capability_id) in conflict_slots:
                        continue
                    rr = learned.as_epistemic_alternative_relation()
                    if rr is not None:
                        background.append(rr)
        relation_sets = assemble_three_locus_chain_epistemic_relation_sets(
            hypotheses, chains, background_relations=tuple(background),
        ) if base else ()
        if not relation_sets:
            return {
                "status": "NO_COHERENT_THREE_LOCUS_CHAIN_MODEL_SURFACE",
                "hypothesis_count": len(hypotheses), "coupling_count": len(couplings),
                "chain_count": len(chains), "background_relation_count": len(background), "relation_sets": (),
                "model_set_authority": "NONE", "truth_authority": "NONE", "execution_authority": "NONE",
            }
        return {
            "status": "THREE_LOCUS_CHAIN_MODEL_SURFACE", "hypothesis_count": len(hypotheses),
            "coupling_count": len(couplings), "chain_count": len(chains), "background_relation_count": len(background), "relation_sets": relation_sets,
            "model_set_authority": "PROPOSAL_ONLY_EPHEMERAL", "truth_authority": "NONE",
            "causal_explanation_authority": "NONE", "evidence_independence_authority": "NONE",
            "execution_authority": "NONE", "history_depth_authority": "NONE",
        }

    def derive_current_generated_epistemic_program_candidates_from_three_locus_history(
        self, *, obligation: QueryObligation, max_nodes: int = 64,
    ) -> dict[str, Any]:
        """Compose owned three-locus alternatives directly into represented program search.

        The alternative surface remains proposal-only/ephemeral and the generated
        candidates retain zero truth, execution, qualification and closure authority.
        No external relation-set selection or model registry is introduced here.
        """
        surface = self.derive_three_locus_chain_action_outcome_epistemic_relation_sets()
        if surface.get("status") != "THREE_LOCUS_CHAIN_MODEL_SURFACE":
            return {
                "status": "ABSTAIN",
                "reason": str(surface.get("status", "NO_MODEL_SURFACE")),
                "alternative_surface": surface,
                "candidates": (),
                "truth_authority": "NONE",
                "execution_authority": "NONE",
                "closure_authority": "NONE",
            }
        decision_context = EpistemicDecisionBearingContext(tuple(surface["relation_sets"]), ())
        result = dict(derive_current_generated_epistemic_program_candidates(
            decision_context=decision_context,
            start_state_id=self.action_closure.current_state.state_id,
            capabilities=self.capabilities,
            obligation=obligation,
            max_nodes=max_nodes,
        ))
        result["alternative_surface_status"] = surface["status"]
        result["alternative_model_set_authority"] = "PROPOSAL_ONLY_EPHEMERAL"
        result["world_model_authority"] = "NONE"
        result["causal_explanation_authority"] = "NONE"
        result["evidence_independence_authority"] = "NONE"
        return result

    def discover_and_arbitrate_generated_epistemic_trial_from_three_locus_history(
        self, *, deficit_id: str, obligation: QueryObligation, max_nodes: int = 64,
    ) -> dict[str, Any]:
        """Compose the owned three-locus surface through the existing trial admission lane.

        Generated-program construction is proposal-only.  This wrapper introduces no
        generated-program executor, selector, persistence, truth or closure authority.
        """
        surface = self.derive_three_locus_chain_action_outcome_epistemic_relation_sets()
        if surface.get("status") != "THREE_LOCUS_CHAIN_MODEL_SURFACE":
            return {
                "status": "ABSTAIN", "reason": str(surface.get("status", "NO_MODEL_SURFACE")),
                "alternative_surface": surface, "execution_authority": "NONE", "truth_authority": "NONE",
            }
        decision_context = EpistemicDecisionBearingContext(tuple(surface["relation_sets"]), ())
        generated = derive_current_generated_epistemic_program_candidates(
            decision_context=decision_context, start_state_id=self.action_closure.current_state.state_id,
            capabilities=self.capabilities, obligation=obligation, max_nodes=max_nodes,
        )
        candidates = tuple(generated.get("candidates", ()))
        if not candidates:
            return {
                **generated, "status": "ABSTAIN", "reason": str(generated.get("reason", generated.get("status", "NO_GENERATED_PROGRAM"))),
                "alternative_surface_status": surface["status"], "execution_authority": "NONE",
            }
        result = dict(self.arbitrate_endogenous_epistemic_trial_candidates(
            candidates, deficit_id=deficit_id, decision_context=decision_context, obligation=obligation,
        ))
        result["generated_program_candidate_count"] = len(candidates)
        result["represented_program_search_status"] = generated.get("status")
        result["alternative_surface_status"] = surface["status"]
        result["alternative_model_set_authority"] = "PROPOSAL_ONLY_EPHEMERAL"
        result["generated_program_authority"] = "PROPOSAL_ONLY_EPHEMERAL"
        result["world_model_authority"] = "NONE"
        result["closure_authority"] = "NONE"
        return result

    def discover_and_arbitrate_endogenous_epistemic_trial_from_admitted_history_and_successor_coupled_alternatives(
        self, *, deficit_id: str, obligation: QueryObligation,
    ) -> dict[str, Any]:
        """Feed the owned bounded two-conflict surface through the existing trial lane.

        Model construction remains ephemeral/proposal-only; trial arbitration and any
        later execution retain their already-owned authority boundaries.
        """
        surface = self.derive_successor_coupled_action_outcome_epistemic_relation_sets()
        if surface.get("status") != "SUCCESSOR_COUPLED_TWO_CONFLICT_MODEL_SURFACE":
            return {
                "status": "ABSTAIN", "reason": str(surface.get("status", "NO_MODEL_SURFACE")),
                "alternative_surface": surface, "execution_authority": "NONE", "truth_authority": "NONE",
            }
        decision_context = EpistemicDecisionBearingContext(tuple(surface["relation_sets"]), ())
        result = self.discover_and_arbitrate_endogenous_epistemic_trial_from_admitted_history(
            deficit_id=deficit_id, decision_context=decision_context, obligation=obligation,
        )
        result = dict(result)
        result["alternative_surface_status"] = surface["status"]
        result["alternative_model_set_authority"] = "PROPOSAL_ONLY_EPHEMERAL"
        result["world_model_authority"] = "NONE"
        result["causal_explanation_authority"] = "NONE"
        result["evidence_independence_authority"] = "NONE"
        return result

    def nominate_endogenous_epistemic_program_step_intent_from_current_surface(
        self, trial, decision_context: EpistemicDecisionBearingContext, obligation: QueryObligation,
    ) -> dict[str, Any]:
        """Nominate the next epistemic primitive from the current grounded feasibility surface.

        No caller chooses a feasibility route.  Existing route derivation/grounding owns
        target binding, agreement/disagreement, currentness and scope.  The resulting
        RecruitmentOption remains a bounded premise only and grants no execution authority.
        """
        idx = len(trial.step_records)
        if trial.status != "OPEN" or idx >= len(trial.steps):
            return {"status":"ABSTAIN","reason":"EPISTEMIC_PROGRAM_NOT_OPEN","execution_authority":"NONE"}
        target = trial.steps[idx]
        options, basis = derive_current_grounded_feasibility_surface(
            capabilities=self.capabilities, operational_scope_id=obligation.operational_scope_id,
        )
        option = next((x for x in options if x.capability_id == target), None)
        if option is None:
            return {
                "status":"ABSTAIN","reason":"CURRENT_STEP_FEASIBILITY_ROUTE_NOT_REPRESENTED",
                "feasibility_basis":basis.get(target),"execution_authority":"NONE",
            }
        deficit=self.epistemic_deficits.records.get(trial.deficit_id)
        priority=derive_current_decision_bearing_commitment_from_grounded_surface(
            trial=trial, deficit=deficit, decision_context=decision_context, feasibility_options=options,
            capabilities=self.capabilities, values=self.values, current_frame_epochs=dict(self.frames.epochs),
            current_episode_epochs=dict(self.episodes.epochs), current_topology_epochs=dict(self.topologies.epochs),
            current_coordination_epochs=dict(self.coordinations.epochs),
        )
        if not priority.licenses_yes():
            return {"status":"ABSTAIN","reason":priority.reason,"priority":priority.serializable(),"feasibility_basis":basis.get(target),"execution_authority":"NONE"}
        information=derive_current_program_discrimination_commitment(trial=trial,decision_context=decision_context,decision_bearing_commitment=priority)
        if not information.licenses_yes():
            return {"status":"ABSTAIN","reason":information.reason,"priority":priority.serializable(),"information":information.serializable(),"feasibility_basis":basis.get(target),"execution_authority":"NONE"}
        intent,cmt=derive_epistemic_program_step_intent(
            trial=trial, deficit=deficit, feasibility=option, capabilities=self.capabilities, obligation=obligation,
            current_frame_epochs=dict(self.frames.epochs), current_state=self.action_closure.current_state,
            priority_commitment=priority, information_commitment=information,
        )
        if intent is None:
            return {"status":"ABSTAIN","reason":cmt.reason,"priority":priority.serializable(),"information":information.serializable(),"commitment":cmt.serializable(),"feasibility_basis":basis.get(target),"execution_authority":"NONE"}
        self.action_closure.add_intent(intent); packet=intent.serializable(); self.path.append("BOUNDED_ACTION_INTENT",packet); self.store.append("BOUNDED_ACTION_INTENT",packet)
        return {"status":"ACTION_INTENT_NOMINATED","intent":packet,"priority":priority.serializable(),"information":information.serializable(),"commitment":cmt.serializable(),"feasibility_basis":basis.get(target),"execution_authority":"NONE","research_basis":"ENDOGENOUS_EPISTEMIC_PROGRAM_STEP_CURRENT_SURFACE"}

    def nominate_endogenous_epistemic_program_step_intent(
        self, trial, decision_context: EpistemicDecisionBearingContext, feasibility_capability_id: str,
        feasibility_obligation: QueryObligation, obligation: QueryObligation
    ) -> dict[str, Any]:
        """Research-only: nominate one primitive only when the UNKNOWN is current-decision-bearing."""
        deficit=self.epistemic_deficits.records.get(trial.deficit_id)
        priority_options,_priority_basis=derive_current_grounded_feasibility_surface(
            capabilities=self.capabilities, operational_scope_id=obligation.operational_scope_id,
        )
        priority=derive_current_decision_bearing_commitment_from_grounded_surface(
            trial=trial, deficit=deficit, decision_context=decision_context, feasibility_options=priority_options,
            capabilities=self.capabilities, values=self.values, current_frame_epochs=dict(self.frames.epochs),
            current_episode_epochs=dict(self.episodes.epochs), current_topology_epochs=dict(self.topologies.epochs),
            current_coordination_epochs=dict(self.coordinations.epochs),
        )
        if not priority.licenses_yes():
            return {"status":"ABSTAIN","reason":priority.reason,"priority":priority.serializable(),"execution_authority":"NONE"}
        information=derive_current_program_discrimination_commitment(trial=trial,decision_context=decision_context,decision_bearing_commitment=priority)
        if not information.licenses_yes():
            return {"status":"ABSTAIN","reason":information.reason,"priority":priority.serializable(),"information":information.serializable(),"execution_authority":"NONE"}
        idx=len(trial.step_records)
        if trial.status!="OPEN" or idx>=len(trial.steps):
            return {"status":"ABSTAIN","reason":"EPISTEMIC_PROGRAM_NOT_OPEN","priority":priority.serializable(),"execution_authority":"NONE"}
        option,feasibility_basis=derive_grounded_feasibility_option(
            target_capability_id=trial.steps[idx], feasibility_capability_id=feasibility_capability_id,
            feasibility_obligation=feasibility_obligation, capabilities=self.capabilities,
        )
        intent,cmt=derive_epistemic_program_step_intent(
            trial=trial, deficit=deficit, feasibility=option, capabilities=self.capabilities, obligation=obligation,
            current_frame_epochs=dict(self.frames.epochs), current_state=self.action_closure.current_state, priority_commitment=priority, information_commitment=information,
        )
        if intent is None:
            return {"status":"ABSTAIN","reason":cmt.reason,"priority":priority.serializable(),"information":information.serializable(),"commitment":cmt.serializable(),"feasibility_basis":feasibility_basis,"execution_authority":"NONE"}
        self.action_closure.add_intent(intent); packet=intent.serializable(); self.path.append("BOUNDED_ACTION_INTENT",packet); self.store.append("BOUNDED_ACTION_INTENT",packet)
        return {"status":"ACTION_INTENT_NOMINATED","intent":packet,"priority":priority.serializable(),"information":information.serializable(),"commitment":cmt.serializable(),"feasibility_basis":feasibility_basis,"execution_authority":"NONE","research_basis":"ENDOGENOUS_EPISTEMIC_PROGRAM_STEP"}

    def assess_epistemic_program_step_outcome_bearing(
        self, prior_trial, advanced_trial, decision_context: EpistemicDecisionBearingContext,
    ) -> dict[str, Any]:
        """Bind one actual program-step outcome to its represented alternatives.

        This may request revisit when the actual outcome either discriminates the live
        represented set or lies outside every represented prediction.  It never answers
        the deficit, chooses a replacement model, or grants execution/truth authority.
        """
        status, witness = derive_epistemic_program_step_outcome_bearing(
            prior_trial=prior_trial, advanced_trial=advanced_trial, decision_context=decision_context,
        )
        if witness is None:
            return {
                "status": "PROGRAM_STEP_BEARING_UNRESOLVED", "reason": status,
                "truth_authority": "NONE", "answer_authority": "NONE",
                "model_replacement_authority": "NONE", "execution_authority": "NONE",
            }
        packet = witness.serializable()
        duplicate = any(
            e.get("kind") == "EPISTEMIC_PROGRAM_STEP_BEARING_WITNESS"
            and e.get("payload", {}).get("witness_id") == witness.witness_id
            for e in self.store.events()
        )
        result = {
            "status": status, "witness": packet, "duplicate": bool(duplicate), "truth_authority": "NONE",
            "answer_authority": "NONE", "model_replacement_authority": "NONE",
            "execution_authority": "NONE",
        }
        if duplicate:
            deficit = self.epistemic_deficits.records.get(prior_trial.deficit_id)
            result["revisit_status"] = None if deficit is None else deficit.state.value
            return result
        self.path.append("EPISTEMIC_PROGRAM_STEP_BEARING_WITNESS", packet)
        self.store.append("EPISTEMIC_PROGRAM_STEP_BEARING_WITNESS", packet)
        if witness.kind in {EpistemicBearingKind.MODEL_SPACE_CHALLENGE, EpistemicBearingKind.DISCRIMINATES_LIVE_SET}:
            deficit = self.epistemic_deficits.records.get(prior_trial.deficit_id)
            if deficit is None or deficit.state == EpistemicDeficitState.STALE:
                result["revisit_status"] = "CURRENT_EPISTEMIC_DEFICIT_REQUIRED"
                return result
            rec = self.epistemic_deficits.request_revisit(prior_trial.deficit_id, witness.outcome_evidence_id)
            rp = {
                "deficit_id": prior_trial.deficit_id, "evidence_id": witness.outcome_evidence_id,
                "program_step_bearing_witness_id": witness.witness_id, "bearing_kind": witness.kind.value,
                "state": rec.state.value, "relevance_authority": "BOUNDED_PROGRAM_STEP_BEARING_ONLY",
                "truth_authority": "NONE", "answer_authority": "NONE", "model_replacement_authority": "NONE",
            }
            self.path.append("EPISTEMIC_DEFICIT_REVISIT_REQUESTED", rp)
            self.store.append("EPISTEMIC_DEFICIT_REVISIT_REQUESTED", rp)
            result["revisit_status"] = rec.state.value
        else:
            result["revisit_status"] = self.epistemic_deficits.records[prior_trial.deficit_id].state.value
        return result

    def record_completed_epistemic_program_evidence(self, trial, *, evidence_id: str) -> dict[str, Any]:
        """Research-only: bind a COMPLETE actual program trial to its existing deficit and request revisit.

        This is bookkeeping/relevance only.  It does not answer the question,
        qualify a relation, infer hidden structure, or retain action authority.
        Every step must resolve back to the ordinary action-closure records that
        physically produced the trial.
        """
        if trial.status != "COMPLETE" or len(trial.step_records) != len(trial.steps):
            return {"status":"PROGRAM_EVIDENCE_REJECTED","reason":"COMPLETE_PROGRAM_TRIAL_REQUIRED"}
        deficit=self.epistemic_deficits.records.get(trial.deficit_id)
        if deficit is None or deficit.state==EpistemicDeficitState.STALE:
            return {"status":"PROGRAM_EVIDENCE_REJECTED","reason":"CURRENT_EPISTEMIC_DEFICIT_REQUIRED"}
        if deficit.missing_discriminator_signature_sha256 != trial.discrimination_signature_sha256:
            return {"status":"PROGRAM_EVIDENCE_REJECTED","reason":"PROGRAM_DISCRIMINATION_SIGNATURE_MISMATCH"}
        for rec in trial.step_records:
            intent=self.action_closure.intents.get(rec.intent_id); execution=self.action_closure.executions.get(rec.execution_id); outcome=self.action_closure.outcomes.get(rec.outcome_id)
            if intent is None or execution is None or outcome is None:
                return {"status":"PROGRAM_EVIDENCE_REJECTED","reason":"PROGRAM_STEP_RECORD_NOT_IN_ACTION_CLOSURE"}
            if intent.proposal_id!=trial.trial_id or execution.intent_id!=intent.intent_id or outcome.execution_id!=execution.execution_id:
                return {"status":"PROGRAM_EVIDENCE_REJECTED","reason":"PROGRAM_STEP_RECORD_BINDING_MISMATCH"}
            if execution.capability_id!=rec.capability_id or execution.capability_epoch!=rec.capability_epoch or outcome.evidence_id!=rec.outcome_evidence_id or outcome.actual_next_state_id!=rec.actual_next_state_id:
                return {"status":"PROGRAM_EVIDENCE_REJECTED","reason":"PROGRAM_STEP_RECORD_CONTENT_MISMATCH"}
        payload=completed_program_evidence_payload(trial)
        payload["relevance_authority"]="BOUNDED_PROGRAM_DISCRIMINATION_BINDING_ONLY"
        payload["answer_authority"]="NONE"
        ref=self.append_evidence(evidence_id,payload,EpistemicStatus.PRESSURE_SUPPORTED,source="EPISTEMIC_PROGRAM_TRIAL")
        rec=self.epistemic_deficits.request_revisit(trial.deficit_id,ref.evidence_id)
        packet={"status":"PROGRAM_EVIDENCE_RECORDED","trial_id":trial.trial_id,"evidence_id":ref.evidence_id,"state":rec.state.value,"truth_authority":"NONE","answer_authority":"NONE","execution_authority":"NONE"}
        self.path.append("EPISTEMIC_PROGRAM_EVIDENCE_RECORDED",packet); self.store.append("EPISTEMIC_PROGRAM_EVIDENCE_RECORDED",packet)
        return packet

    def _fresh_action_commitment_for_intent(self, intent: BoundedActionIntent, *, obligation: QueryObligation | None = None, epistemic_step_context: EpistemicStepExecutionContext | None = None) -> tuple[RelationalCommitment | None, str, dict[str, Any] | None]:
        if intent.basis_kind=="EPISTEMIC_PROGRAM_STEP":
            if obligation is None or epistemic_step_context is None:
                return None,"EPISTEMIC_STEP_EXECUTION_CONTEXT_REQUIRED",None
            trial=epistemic_step_context.trial
            if intent.proposal_id!=trial.trial_id or intent.proposal_digest!=trial.digest():
                return None,"EPISTEMIC_PROGRAM_TRIAL_DRIFT",None
            deficit=self.epistemic_deficits.records.get(trial.deficit_id)
            feasibility=epistemic_step_context.feasibility
            feasibility_detail=None
            priority_options=None
            if feasibility is None:
                idx=len(trial.step_records)
                if trial.status!="OPEN" or idx>=len(trial.steps):
                    return None,"EPISTEMIC_PROGRAM_NOT_OPEN",None
                target_capability_id=trial.steps[idx]
                if epistemic_step_context.feasibility_capability_id is None:
                    priority_options, surface_basis=derive_current_grounded_feasibility_surface(
                        capabilities=self.capabilities, operational_scope_id=obligation.operational_scope_id,
                    )
                    feasibility=next((x for x in priority_options if x.capability_id==target_capability_id),None)
                    feasibility_detail=surface_basis.get(target_capability_id)
                    if feasibility is None:
                        feasibility=RecruitmentOption(target_capability_id,FeasibilityState.UNKNOWN,model_evidence_ids=())
                        feasibility_detail={"status":"UNKNOWN_INCOMPLETE","reason":"CURRENT_STEP_FEASIBILITY_ROUTE_NOT_REPRESENTED"}
                else:
                    feasibility,feasibility_detail=derive_grounded_feasibility_option(
                        target_capability_id=target_capability_id,
                        feasibility_capability_id=str(epistemic_step_context.feasibility_capability_id),
                        feasibility_obligation=epistemic_step_context.feasibility_obligation,
                        capabilities=self.capabilities,
                    )
            priority=None; information=None
            if epistemic_step_context.decision_context is not None:
                if priority_options is None:
                    priority_options,_priority_basis=derive_current_grounded_feasibility_surface(
                        capabilities=self.capabilities, operational_scope_id=obligation.operational_scope_id,
                    )
                priority=derive_current_decision_bearing_commitment_from_grounded_surface(
                    trial=trial, deficit=deficit, decision_context=epistemic_step_context.decision_context,
                    feasibility_options=priority_options, capabilities=self.capabilities, values=self.values,
                    current_frame_epochs=dict(self.frames.epochs), current_episode_epochs=dict(self.episodes.epochs),
                    current_topology_epochs=dict(self.topologies.epochs), current_coordination_epochs=dict(self.coordinations.epochs),
                )
                information=derive_current_program_discrimination_commitment(trial=trial,decision_context=epistemic_step_context.decision_context,decision_bearing_commitment=priority)
            fresh=derive_epistemic_program_step_commitment(
                trial=trial, deficit=deficit, feasibility=feasibility, capabilities=self.capabilities, obligation=obligation,
                current_frame_epochs=dict(self.frames.epochs), current_state=self.action_closure.current_state, priority_commitment=priority, information_commitment=information,
            )
            if fresh.commitment_id!=intent.action_commitment.commitment_id:
                return fresh,"EPISTEMIC_PROGRAM_STEP_PREMISE_DRIFT",{"fresh_commitment":fresh.serializable()}
            return fresh,"EPISTEMIC_PROGRAM_STEP_COMMITMENT_NOT_CURRENT",None
        if intent.basis_kind=="SINGLE_VALUE_REHEARSAL":
            if intent.proposal_id is None or self.counterfactual_rehearsal_status(intent.proposal_id).get("status")!="CURRENT_REHEARSAL_PROPOSAL":
                return None,"REHEARSAL_PREMISE_DRIFT",None
            return self.derive_bounded_action_commitment(intent.proposal_id),"ACTION_COMMITMENT_NOT_CURRENT",None
        if intent.basis_kind!="MULTI_VALUE_LICENSE":
            return None,"UNKNOWN_ACTION_INTENT_BASIS",None
        if not intent.required_value_epochs:
            return None,"MULTI_VALUE_INTENT_ANCESTRY_MISSING",None
        if any(not self.values.is_current(value_id,epoch) for value_id,epoch in intent.required_value_epochs):
            return None,"MULTI_VALUE_PREMISE_EPOCH_DRIFT",None
        try: cfg=DiscoveryConfig(**dict(intent.derivation_parameters))
        except (TypeError,ValueError): return None,"MULTI_VALUE_DERIVATION_CONFIG_INVALID",None
        license_result=self.derive_multi_value_action_licenses(tuple(value_id for value_id,_ in intent.required_value_epochs),config=cfg)
        if license_result.get("status")!="UNIQUE_ACTION_LICENSE" or license_result.get("licensed_action_ids")!=[intent.capability_id]:
            return None,"MULTI_VALUE_ACTION_LICENSE_NOT_CURRENT",license_result
        cmt=RelationalCommitment.from_serializable(license_result["action_commitments"][intent.capability_id])
        return cmt,"MULTI_VALUE_ACTION_COMMITMENT_NOT_CURRENT",license_result

    def execute_bounded_action(self, intent_id: str, obligation: QueryObligation, **kwargs: Any) -> dict[str, Any]:
        """Execute through an already-qualified EFFECT capability; the intent itself has no effect authority."""
        intent=self.action_closure.intents.get(intent_id)
        if intent is None: return {"status":"NO_EXECUTION","reason":"ACTION_INTENT_NOT_FOUND","authority":Authority.NONE.value}
        if any(e.intent_id==intent_id for e in self.action_closure.executions.values()): return {"status":"NO_EXECUTION","reason":"ACTION_INTENT_ALREADY_EXECUTED","authority":Authority.NONE.value}
        cw=self.action_closure.current_state
        if cw is None or cw.state_id!=intent.start_state_id or cw.evidence_id!=intent.control_state_evidence_id: return {"status":"NO_EXECUTION","reason":"CONTROL_STATE_DRIFT","authority":Authority.NONE.value}
        cap=self.capabilities.contracts.get(intent.capability_id)
        if cap is None or cap.authority!=Authority.EFFECT or cap.qualification not in {QualificationState.QUALIFIED,QualificationState.SHADOW_QUALIFIED} or self.capabilities.epochs.get(intent.capability_id,-1)!=intent.capability_epoch: return {"status":"NO_EXECUTION","reason":"EFFECT_CAPABILITY_NOT_CURRENT","authority":Authority.NONE.value}
        if obligation.required_authority!=Authority.EFFECT or obligation.obligation_id!=intent.obligation_id or obligation.operational_scope_id!=intent.operational_scope_id: return {"status":"NO_EXECUTION","reason":"ACTION_OBLIGATION_DRIFT","authority":Authority.NONE.value}
        # MS1532/MS1534: nomination-time premise licensing is not execution-time
        # authority. Re-derive the actual intent basis immediately before EFFECT.
        epistemic_step_context=kwargs.pop("epistemic_step_context",None)
        fresh_commitment, stale_reason, fresh_detail = self._fresh_action_commitment_for_intent(
            intent, obligation=obligation, epistemic_step_context=epistemic_step_context
        )
        if fresh_commitment is None:
            out={"status":"NO_EXECUTION","reason":stale_reason,"authority":Authority.NONE.value}
            if fresh_detail is not None: out["license"]=fresh_detail
            return out
        if not fresh_commitment.licenses_yes():
            return {"status":"NO_EXECUTION","reason":stale_reason,"commitment":fresh_commitment.serializable(),"authority":Authority.NONE.value}
        result=self.capabilities.invoke(intent.capability_id,obligation,**kwargs)
        if result.get("status")!="CAPABILITY_RESULT": return {"status":"NO_EXECUTION","reason":result.get("reason",result.get("status")),"authority":Authority.NONE.value}
        rec=ActionExecutionRecord(execution_id=action_stable_id("ACTION-EXEC-",{"intent":intent_id,"result":action_result_digest(result.get('value'))}),intent_id=intent_id,capability_id=intent.capability_id,capability_epoch=intent.capability_epoch,start_state_id=intent.start_state_id,handler_result_sha256=action_result_digest(result.get("value")),execution_commitment_id=fresh_commitment.commitment_id,execution_premise_ids=fresh_commitment.premise_ids)
        self.action_closure.add_execution(rec); packet=rec.serializable(); self.path.append("BOUNDED_ACTION_EXECUTED",packet); self.store.append("BOUNDED_ACTION_EXECUTED",packet)
        return {"status":"ACTION_EXECUTED","execution":packet,"handler_value":result.get("value"),"observation_recorded":False}

    def record_bounded_action_outcome_via_observation_basis(
        self,
        execution_id: str,
        *,
        observation_capability_id: str,
        observation_obligation: QueryObligation,
        basis_capability_id: str,
        basis_obligation: QueryObligation,
        evidence_id: str,
        capture_id: str,
        admission_basis_capability_id: str | None = None,
        admission_basis_obligation: QueryObligation | None = None,
        **observation_kwargs: Any,
    ) -> dict[str, Any]:
        """Close one action outcome only through current bounded observation-use ancestry.

        The basis and observation capability remain ordinary qualified capabilities.
        This bridge adds no truth authority and does not decide whether their
        qualification evidence was non-circular or physically grounded.
        """
        execution = self.action_closure.executions.get(execution_id)
        if execution is None:
            return {"status":"OUTCOME_REJECTED","reason":"EXECUTION_NOT_FOUND"}
        intent = self.action_closure.intents.get(execution.intent_id)
        if intent is None:
            return {"status":"OUTCOME_REJECTED","reason":"ACTION_INTENT_NOT_FOUND"}
        required_scope = intent.operational_scope_id
        if observation_obligation.operational_scope_id != required_scope or basis_obligation.operational_scope_id != required_scope:
            return {"status":"OUTCOME_REJECTED","reason":"OBSERVATION_ACTION_SCOPE_MISMATCH"}
        if admission_basis_obligation is not None and admission_basis_obligation.operational_scope_id != required_scope:
            return {"status":"OUTCOME_REJECTED","reason":"HISTORICAL_ADMISSION_ACTION_SCOPE_MISMATCH"}
        basis_contract = self.capabilities.contracts.get(basis_capability_id)
        if basis_contract is None or observation_capability_id not in basis_contract.dependencies:
            return {
                "status": "OUTCOME_REJECTED",
                "reason": "OBSERVATION_BASIS_DOES_NOT_BIND_CHANNEL",
            }
        basis = self.capabilities.invoke(
            basis_capability_id, basis_obligation, execution_id=execution_id
        )
        if (
            basis.get("status") != "CAPABILITY_RESULT"
            or basis.get("authority") != Authority.DERIVED_READ_ONLY.value
        ):
            return {
                "status": "OUTCOME_REJECTED",
                "reason": "OBSERVATION_BASIS_NOT_CURRENT",
                "basis": basis,
            }
        observed = self.capabilities.invoke(
            observation_capability_id,
            observation_obligation,
            execution_id=execution_id,
            **observation_kwargs,
        )
        if (
            observed.get("status") != "CAPABILITY_RESULT"
            or observed.get("authority") != Authority.OBSERVATION_ONLY.value
            or not isinstance(observed.get("value"), dict)
        ):
            return {
                "status": "OUTCOME_REJECTED",
                "reason": "OBSERVATION_CAPABILITY_NOT_CURRENT",
                "observation": observed,
            }
        premise_epochs=((basis_capability_id, self.capabilities.epochs[basis_capability_id]),)
        premise_signatures: tuple[tuple[str,str], ...] = ()
        lineage=(
            f"OBSERVATION_CAPABILITY:{observation_capability_id}@{self.capabilities.epochs[observation_capability_id]}",
            f"OBSERVATION_USE_BASIS:{basis_capability_id}@{self.capabilities.epochs[basis_capability_id]}",
        )
        currentness_basis="QUALIFIED_OBSERVATION_CAPABILITY_AND_BOUNDED_USE_BASIS"
        if admission_basis_capability_id is not None:
            if admission_basis_obligation is None:
                return {"status":"OUTCOME_REJECTED","reason":"HISTORICAL_ADMISSION_BASIS_OBLIGATION_REQUIRED"}
            admission_contract=self.capabilities.contracts.get(admission_basis_capability_id)
            admission=self.capabilities.invoke(
                admission_basis_capability_id, admission_basis_obligation, execution_id=execution_id
            )
            if (
                admission_contract is None
                or admission.get("status") != "CAPABILITY_RESULT"
                or admission.get("authority") != Authority.DERIVED_READ_ONLY.value
            ):
                return {
                    "status":"OUTCOME_REJECTED",
                    "reason":"HISTORICAL_ADMISSION_BASIS_NOT_CURRENT",
                    "admission_basis":admission,
                }
            raw_snapshot=admission_contract.boundary.get("admission_premise_signatures", ())
            try:
                admission_snapshot=tuple((str(cid),str(sig).lower()) for cid,sig in raw_snapshot)
            except (TypeError,ValueError):
                return {"status":"OUTCOME_REJECTED","reason":"HISTORICAL_ADMISSION_PREMISE_SIGNATURES_INVALID"}
            if not admission_snapshot:
                return {"status":"OUTCOME_REJECTED","reason":"HISTORICAL_ADMISSION_PREMISE_SIGNATURES_REQUIRED"}
            for cid,sig in admission_snapshot:
                premise_contract=self.capabilities.contracts.get(cid)
                if premise_contract is None or premise_contract.computed_signature_sha256()!=sig:
                    return {"status":"OUTCOME_REJECTED","reason":"HISTORICAL_ADMISSION_BASIS_NOT_APPLICABLE_TO_CURRENT_PREMISES"}
            premise_epochs=((admission_basis_capability_id,self.capabilities.epochs[admission_basis_capability_id]),)
            premise_signatures=((admission_basis_capability_id,admission_contract.computed_signature_sha256()),)
            lineage=lineage+(f"HISTORICAL_ADMISSION_BASIS:{admission_basis_capability_id}@{self.capabilities.epochs[admission_basis_capability_id]}",)
            currentness_basis="QUALIFIED_OBSERVATION_CAPABILITY_AND_LIVE_USE_PLUS_HISTORICAL_ADMISSION_BASIS"
        obs = Observation(
            capture_id=capture_id,
            origin=f"CAPABILITY:{observation_capability_id}",
            referent=f"action-execution:{execution_id}",
            value=dict(observed["value"]),
            currentness_basis=currentness_basis,
            authority=Authority.OBSERVATION_ONLY,
            lineage=lineage,
        )
        result = self.record_bounded_action_outcome(
            execution_id, obs, evidence_id=evidence_id,
            evidence_premise_epochs=premise_epochs,
            evidence_premise_signatures=premise_signatures,
        )
        if result.get("status") == "ACTION_OUTCOME_OBSERVED":
            outcome = result.get("outcome", {})
            ev = self.evidence.get(evidence_id)
            obs_contract = self.capabilities.contracts[observation_capability_id]
            action_contract = self.capabilities.contracts[execution.capability_id]
            action_frames = {
                fid for fid, dependents in self.frames.capability_dependents.items()
                if execution.capability_id in dependents and self.frames.is_current(fid)
            }
            observation_frames = {
                fid for fid, dependents in self.frames.capability_dependents.items()
                if observation_capability_id in dependents and self.frames.is_current(fid)
            }
            common_frames = tuple(sorted(action_frames & observation_frames))
            receipt_basis = {
                "execution_id": execution_id,
                "outcome_id": outcome.get("outcome_id"),
                "outcome_evidence_id": evidence_id,
                "outcome_evidence_sha256": None if ev is None else ev.get("sha256"),
                "capture_id": capture_id,
                "action_capability_id": execution.capability_id,
                "action_capability_epoch": execution.capability_epoch,
                "action_capability_signature_sha256": action_contract.computed_signature_sha256(),
                "action_operational_scope_id": intent.operational_scope_id,
                "observation_capability_id": observation_capability_id,
                "observation_capability_epoch": self.capabilities.epochs[observation_capability_id],
                "observation_capability_signature_sha256": obs_contract.computed_signature_sha256(),
                "observation_basis_capability_id": basis_capability_id,
                "observation_basis_capability_epoch": self.capabilities.epochs[basis_capability_id],
                "observation_basis_capability_signature_sha256": basis_contract.computed_signature_sha256(),
                "historical_admission_basis_capability_id": admission_basis_capability_id,
                "historical_admission_basis_capability_epoch": None if admission_basis_capability_id is None else self.capabilities.epochs[admission_basis_capability_id],
                "historical_admission_basis_signature_sha256": None if admission_basis_capability_id is None else self.capabilities.contracts[admission_basis_capability_id].computed_signature_sha256(),
                "operational_scope_id": observation_obligation.operational_scope_id,
                "common_operational_frame_epochs": [[fid, self.frames.epochs[fid]] for fid in common_frames],
                "common_operational_frame_signatures": [[fid, self.frames.frames[fid].signature_sha256] for fid in common_frames],
                "route_kind": "BOUNDED_OBSERVATION_USE_BASIS",
                "truth_authority": "NONE",
                "evidence_independence_authority": "NONE",
                "execution_authority": "NONE",
            }
            packet = {
                **receipt_basis,
                "receipt_id": action_stable_id("OBS-ADMIT-", receipt_basis),
                "receipt_sha256": action_result_digest(receipt_basis),
            }
            self.path.append("OBSERVATION_ADMISSION_RECEIPT", packet)
            self.store.append("OBSERVATION_ADMISSION_RECEIPT", packet)
            result = {**result, "observation_admission_receipt": packet}
        return result

    def derive_admitted_opaque_transition_sample(self, execution_id: str) -> dict[str, Any]:
        """Research-only ephemeral projection from authenticated outcome history.

        This consumes only existing action/outcome/evidence/frame owners plus the
        internally stamped observation-admission receipt. It persists nothing and
        grants no semantic, truth, qualification, execution, or independence
        authority.
        """
        execution = self.action_closure.executions.get(str(execution_id))
        if execution is None:
            return {"status":"ABSTAIN","reason":"EXECUTION_NOT_FOUND","authority":"NONE"}
        execution_events = [
            row["payload"] for row in self.store.events()
            if row["kind"] == "BOUNDED_ACTION_EXECUTED"
            and row["payload"].get("execution_id") == execution.execution_id
        ]
        if len(execution_events) != 1 or execution_events[0] != execution.serializable():
            return {"status":"ABSTAIN","reason":"AUTHENTICATED_ORDINARY_EXECUTION_REQUIRED","authority":"NONE"}
        outcomes = [o for o in self.action_closure.outcomes.values() if o.execution_id == execution.execution_id]
        if len(outcomes) != 1:
            return {"status":"ABSTAIN","reason":"EXACT_EXECUTION_OUTCOME_BINDING_REQUIRED","authority":"NONE"}
        outcome = outcomes[0]
        ev = self.evidence.get(outcome.evidence_id)
        if ev is None:
            return {"status":"ABSTAIN","reason":"OUTCOME_EVIDENCE_NOT_FOUND","authority":"NONE"}
        receipts = [
            row["payload"] for row in self.store.events()
            if row["kind"] == "OBSERVATION_ADMISSION_RECEIPT"
            and row["payload"].get("execution_id") == execution.execution_id
            and row["payload"].get("outcome_id") == outcome.outcome_id
            and row["payload"].get("outcome_evidence_id") == outcome.evidence_id
        ]
        if len(receipts) != 1:
            return {"status":"ABSTAIN","reason":"AUTHENTICATED_OBSERVATION_INGRESS_REQUIRED","authority":"NONE"}
        receipt = receipts[0]
        if receipt.get("outcome_evidence_sha256") != ev.get("sha256"):
            return {"status":"ABSTAIN","reason":"OBSERVATION_ADMISSION_EVIDENCE_DRIFT","authority":"NONE"}
        if (
            receipt.get("action_capability_id") != execution.capability_id
            or int(receipt.get("action_capability_epoch", -1)) != execution.capability_epoch
        ):
            return {"status":"ABSTAIN","reason":"OBSERVATION_ADMISSION_ACTION_BINDING_MISMATCH","authority":"NONE"}
        intent = self.action_closure.intents.get(execution.intent_id)
        if intent is None or receipt.get("action_operational_scope_id") != intent.operational_scope_id:
            return {"status":"ABSTAIN","reason":"OBSERVATION_ADMISSION_SCOPE_BINDING_MISMATCH","authority":"NONE"}
        if receipt.get("operational_scope_id") != intent.operational_scope_id:
            return {"status":"ABSTAIN","reason":"OBSERVATION_AND_ACTION_SCOPE_MISMATCH","authority":"NONE"}

        action_contract = self.capabilities.contracts.get(execution.capability_id)
        if (
            action_contract is None
            or action_contract.qualification not in {QualificationState.QUALIFIED, QualificationState.SHADOW_QUALIFIED}
            or action_contract.currentness != "CURRENT"
            or self.capabilities.epochs.get(execution.capability_id, -1) != execution.capability_epoch
            or action_contract.computed_signature_sha256() != receipt.get("action_capability_signature_sha256")
        ):
            return {"status":"ABSTAIN","reason":"ACTION_CAPABILITY_NOT_CURRENT_FOR_RELATIONAL_SAMPLE","authority":"NONE"}

        historical_id = receipt.get("historical_admission_basis_capability_id")
        if historical_id is not None:
            historical = self.capabilities.contracts.get(str(historical_id))
            if (
                historical is None
                or historical.qualification not in {QualificationState.QUALIFIED, QualificationState.SHADOW_QUALIFIED}
                or historical.currentness != "CURRENT"
                or self.capabilities.epochs.get(str(historical_id), -1) != int(receipt.get("historical_admission_basis_capability_epoch", -2))
                or historical.computed_signature_sha256() != receipt.get("historical_admission_basis_signature_sha256")
            ):
                return {"status":"ABSTAIN","reason":"HISTORICAL_OBSERVATION_ADMISSION_NOT_CURRENT","authority":"NONE"}
        else:
            for prefix in ("observation_capability", "observation_basis_capability"):
                cid = str(receipt.get(f"{prefix}_id", ""))
                contract = self.capabilities.contracts.get(cid)
                if (
                    not cid
                    or contract is None
                    or contract.qualification not in {QualificationState.QUALIFIED, QualificationState.SHADOW_QUALIFIED}
                    or contract.currentness != "CURRENT"
                    or self.capabilities.epochs.get(cid, -1) != int(receipt.get(f"{prefix}_epoch", -2))
                    or contract.computed_signature_sha256() != receipt.get(f"{prefix}_signature_sha256")
                ):
                    return {"status":"ABSTAIN","reason":"LIVE_OBSERVATION_ADMISSION_NOT_CURRENT","authority":"NONE"}

        frames = tuple((str(fid), int(epoch)) for fid, epoch in receipt.get("common_operational_frame_epochs", ()))
        if len(frames) != 1:
            return {"status":"ABSTAIN","reason":"UNIQUE_COMMON_OPERATIONAL_FRAME_REQUIRED","authority":"NONE"}
        frame_id, frame_epoch = frames[0]
        if not self.frames.is_current(frame_id, frame_epoch):
            return {"status":"ABSTAIN","reason":"OPERATIONAL_FRAME_NOT_CURRENT","authority":"NONE"}
        frame_signatures = {
            str(fid): str(sig).lower()
            for fid, sig in receipt.get("common_operational_frame_signatures", ())
        }
        frame_contract = self.frames.frames.get(frame_id)
        if frame_contract is None or frame_signatures.get(frame_id) != str(frame_contract.signature_sha256).lower():
            return {"status":"ABSTAIN","reason":"OPERATIONAL_FRAME_CONTENT_DRIFT","authority":"NONE"}

        evidence_payload = ev.get("payload", {})
        if (
            evidence_payload.get("execution_id") != execution.execution_id
            or evidence_payload.get("start_state_id") != execution.start_state_id
            or evidence_payload.get("next_state_id") != outcome.actual_next_state_id
            or evidence_payload.get("capability_id") != execution.capability_id
            or int(evidence_payload.get("capability_epoch", -1)) != execution.capability_epoch
        ):
            return {"status":"ABSTAIN","reason":"OUTCOME_EVIDENCE_CONTENT_BINDING_MISMATCH","authority":"NONE"}

        sample_basis = {
            "execution_id": execution.execution_id,
            "outcome_id": outcome.outcome_id,
            "evidence_sha256": ev["sha256"],
            "frame_id": frame_id,
            "frame_epoch": frame_epoch,
            "action_capability_id": execution.capability_id,
            "action_capability_epoch": execution.capability_epoch,
        }
        sample = OpaqueTransitionSample(
            sample_id=action_stable_id("OPAQUE-TRANSITION-", sample_basis),
            origin_id=execution.execution_id,
            start_token=execution.start_state_id,
            action_token=execution.capability_id,
            end_token=outcome.actual_next_state_id,
            frame_id=frame_id,
            frame_epoch=frame_epoch,
        )
        return {
            "status":"ADMITTED_OPAQUE_TRANSITION_SAMPLE",
            "sample":sample,
            "sample_serializable":sample.serializable(),
            "admission_receipt_id":receipt.get("receipt_id"),
            "proposal_authority":"NONE",
            "truth_authority":"NONE",
            "qualification_authority":"NONE",
            "execution_authority":"NONE",
            "evidence_independence_authority":"NONE",
        }

    def derive_admitted_one_step_visible_history_refinements(self) -> dict[str, Any]:
        """Ephemerally derive previous-visible-state refinement from owned admitted history.

        Predecessor/current pairing is accepted only when the current intent's exact
        control-state evidence id points to one prior actual outcome and both executions
        independently project as admitted opaque transitions in the same current frame.
        Nothing is persisted and no hidden-state/deeper-history authority is created.
        """
        admitted: dict[str, OpaqueTransitionSample] = {}
        rejected: list[tuple[str,str]] = []
        for execution_id in sorted(self.action_closure.executions):
            row=self.derive_admitted_opaque_transition_sample(execution_id)
            if row.get("status")=="ADMITTED_OPAQUE_TRANSITION_SAMPLE":
                admitted[execution_id]=row["sample"]
            else:
                rejected.append((execution_id,str(row.get("reason","ABSTAIN"))))
        outcomes_by_evidence: dict[str,list[ActionOutcomeRecord]] = {}
        for outcome in self.action_closure.outcomes.values():
            outcomes_by_evidence.setdefault(outcome.evidence_id,[]).append(outcome)
        pairs=[]
        for execution_id,current_sample in sorted(admitted.items()):
            execution=self.action_closure.executions.get(execution_id)
            intent=None if execution is None else self.action_closure.intents.get(execution.intent_id)
            if intent is None:
                continue
            prior_outcomes=outcomes_by_evidence.get(intent.control_state_evidence_id,())
            if len(prior_outcomes)!=1:
                continue
            prior=prior_outcomes[0]
            previous_sample=admitted.get(prior.execution_id)
            if previous_sample is None:
                continue
            if previous_sample.end_token!=current_sample.start_token:
                continue
            pairs.append((previous_sample,current_sample))
        refinements=discover_one_step_visible_history_refinements(pairs)
        return {
            "status": "ONE_STEP_VISIBLE_HISTORY_REFINEMENTS_FOUND" if refinements else "NO_ONE_STEP_VISIBLE_HISTORY_REFINEMENT",
            "refinements": refinements,
            "admitted_sample_count": len(admitted),
            "successor_pair_count": len(pairs),
            "rejected_execution_reasons": tuple(rejected),
            "context_basis": "PREVIOUS_VISIBLE_STATE_ONLY",
            "truth_authority": "NONE",
            "hidden_state_authority": "NONE",
            "history_depth_extension_authority": "NONE",
            "execution_authority": "NONE",
        }

    def derive_current_revisit_hypothesis_revision_surface(self, deficit_id: str) -> dict[str, Any]:
        """Derive all distinct current qualified revised model surfaces bound to one revisit.

        Binding multiplicity is not model multiplicity: bindings with the same content
        digest collapse. Distinct content digests remain explicit ambiguity. This method
        grants no model selection, deficit transition, truth, or execution authority.
        """
        deficit=self.epistemic_deficits.records.get(str(deficit_id))
        if deficit is None:
            return {"status":"ABSTAIN","reason":"DEFICIT_NOT_FOUND","authority":"NONE"}
        if deficit.state!=EpistemicDeficitState.REVISIT_REQUIRED:
            return {"status":"ABSTAIN","reason":"REVISIT_REQUIRED","authority":"NONE"}
        groups: dict[str,list[str]]={}
        for binding_id,binding in sorted(self.action_outcome_learning.projection_conditioned_bindings.items()):
            if not self._projection_conditioned_binding_current(binding):
                continue
            projection=self.epistemic_projections.records.get(binding.projection_id)
            if projection is None or f"DEFICIT:{deficit_id}" not in projection.assistance_ancestry:
                continue
            digest=projection_conditioned_hypothesis_surface_digest(binding,self.action_outcome_learning.relations)
            if digest==deficit.hypothesis_digest_sha256:
                continue
            groups.setdefault(digest,[]).append(binding_id)
        if not groups:
            return {"status":"NO_CURRENT_REVISED_HYPOTHESIS_SURFACE","deficit_id":str(deficit_id),"authority":"NONE"}
        if len(groups)>1:
            return {
                "status":"REVISION_AMBIGUOUS","deficit_id":str(deficit_id),
                "revised_hypothesis_digests":tuple(sorted(groups)),
                "binding_groups":tuple((d,tuple(sorted(groups[d]))) for d in sorted(groups)),
                "authority":"NONE","model_switch_authority":"NONE","deficit_transition_authority":"NONE",
            }
        digest=next(iter(groups))
        return {
            "status":"CURRENT_UNIQUE_REVISED_HYPOTHESIS_SURFACE","deficit_id":str(deficit_id),
            "revised_hypothesis_digest_sha256":digest,"binding_ids":tuple(sorted(groups[digest])),
            "authority":"NONE","model_switch_authority":"NONE","deficit_transition_authority":"NONE",
        }

    def derive_revisit_hypothesis_revision_candidate(self, deficit_id: str, binding_id: str) -> dict[str, Any]:
        """Derive one zero-authority candidate that a qualified revised model changed a revisit hypothesis surface.

        This does not stale/reopen a deficit, decide whether uncertainty remains, or grant model-switch/truth authority.
        Exact deficit ancestry comes from the already-qualified revisit projection; revised content identity comes from
        the qualified projection-conditioned binding plus the candidate semantic identities of its routed relations.
        """
        deficit=self.epistemic_deficits.records.get(str(deficit_id))
        if deficit is None:
            return {"status":"ABSTAIN","reason":"DEFICIT_NOT_FOUND","authority":"NONE"}
        if deficit.state!=EpistemicDeficitState.REVISIT_REQUIRED:
            return {"status":"ABSTAIN","reason":"REVISIT_REQUIRED","authority":"NONE"}
        binding=self.action_outcome_learning.projection_conditioned_bindings.get(str(binding_id))
        if binding is None or not self._projection_conditioned_binding_current(binding):
            return {"status":"ABSTAIN","reason":"REVISED_MODEL_BINDING_NOT_CURRENT","authority":"NONE"}
        projection=self.epistemic_projections.records.get(binding.projection_id)
        if projection is None or f"DEFICIT:{deficit_id}" not in projection.assistance_ancestry:
            return {"status":"ABSTAIN","reason":"REVISED_MODEL_NOT_BOUND_TO_REVISIT_DEFICIT","authority":"NONE"}
        revised_digest=projection_conditioned_hypothesis_surface_digest(binding,self.action_outcome_learning.relations)
        if revised_digest==deficit.hypothesis_digest_sha256:
            return {"status":"NO_HYPOTHESIS_SURFACE_CHANGE","deficit_id":str(deficit_id),"revised_hypothesis_digest_sha256":revised_digest,"authority":"NONE"}
        payload={
            "deficit_id":str(deficit_id),"old_hypothesis_digest_sha256":deficit.hypothesis_digest_sha256,
            "revised_hypothesis_digest_sha256":revised_digest,"projection_id":binding.projection_id,
            "projection_epoch":binding.projection_epoch,"binding_id":binding.binding_id,
            "binding_candidate_sha256":binding.candidate_sha256,
        }
        return {
            "status":"REVISIT_HYPOTHESIS_REVISION_CANDIDATE",
            "revision_candidate_id":action_stable_id("REVISION-",payload),
            **payload,
            "authority":"NONE","truth_authority":"NONE","model_switch_authority":"NONE",
            "deficit_transition_authority":"NONE","new_unknown_authority":"NONE",
        }

    def accept_revisit_hypothesis_revision(self, deficit_id: str, binding_id: str) -> dict[str, Any]:
        """Retire one historical revisit deficit only after a unique current revised model surface exists.

        The caller-supplied binding id may identify a member of the unique equivalent
        binding group, but cannot choose between distinct revised model contents.
        """
        surface=self.derive_current_revisit_hypothesis_revision_surface(deficit_id)
        if surface.get("status")=="REVISION_AMBIGUOUS":
            return surface
        if surface.get("status")!="CURRENT_UNIQUE_REVISED_HYPOTHESIS_SURFACE":
            return {"status":"REVISION_NOT_ACCEPTED","reason":surface.get("reason",surface.get("status","ABSTAIN")),"authority":"NONE"}
        if str(binding_id) not in surface["binding_ids"]:
            return {"status":"REVISION_NOT_ACCEPTED","reason":"CALLER_BINDING_NOT_MEMBER_OF_UNIQUE_REVISION","authority":"NONE"}
        candidate=self.derive_revisit_hypothesis_revision_candidate(deficit_id,binding_id)
        if candidate.get("status")!="REVISIT_HYPOTHESIS_REVISION_CANDIDATE":
            return {"status":"REVISION_NOT_ACCEPTED","reason":candidate.get("reason",candidate.get("status","ABSTAIN")),"authority":"NONE"}
        old=self.epistemic_deficits.records[str(deficit_id)]
        old_digest=old.hypothesis_digest_sha256
        old_unknown=old.unknown_evidence_id
        old_relevant=tuple(old.relevant_evidence_ids)
        revised_digest=surface["revised_hypothesis_digest_sha256"]
        self.epistemic_deficits.mark_stale(
            str(deficit_id),reason=f"BOUNDED_HYPOTHESIS_SET_CHANGED:{revised_digest}"
        )
        packet={
            "status":"OLD_REVISIT_DEFICIT_STALED_FOR_HYPOTHESIS_REVISION",
            "revision_candidate_id":candidate["revision_candidate_id"],
            "deficit_id":str(deficit_id),"old_hypothesis_digest_sha256":old_digest,
            "revised_hypothesis_digest_sha256":revised_digest,
            "equivalent_binding_ids":list(surface["binding_ids"]),
            "old_unknown_evidence_id":old_unknown,"preserved_relevant_evidence_ids":list(old_relevant),
            "binding_id":str(binding_id),"state":old.state.value,
            "truth_authority":"NONE","answer_authority":"NONE","model_switch_authority":"NONE",
            "successor_deficit_authority":"NONE","execution_authority":"NONE",
        }
        self.path.append("EPISTEMIC_REVISIT_HYPOTHESIS_REVISION_ACCEPTED",packet)
        self.store.append("EPISTEMIC_REVISIT_HYPOTHESIS_REVISION_ACCEPTED",packet)
        stale_packet=old.serializable()
        self.path.append("EPISTEMIC_DEFICIT_STALE",stale_packet)
        self.store.append("EPISTEMIC_DEFICIT_STALE",stale_packet)
        return packet

    def accepted_revisit_hypothesis_revision_status(self, deficit_id: str) -> dict[str, Any]:
        """Recover one accepted hypothesis revision from owned history and recheck its live model content.

        The historical acceptance is durable, but live reuse requires at least one
        equivalent binding to remain current and content-identical to the accepted
        revised hypothesis digest.  This grants no new-UNKNOWN or execution authority.
        """
        deficit=self.epistemic_deficits.records.get(str(deficit_id))
        if deficit is None:
            return {"status":"ABSTAIN","reason":"DEFICIT_NOT_FOUND","authority":"NONE"}
        if deficit.state!=EpistemicDeficitState.STALE:
            return {"status":"ABSTAIN","reason":"OLD_DEFICIT_NOT_STALE","authority":"NONE"}
        accepted=None
        for event in reversed(tuple(self.store.events())):
            if event.get("kind")!="EPISTEMIC_REVISIT_HYPOTHESIS_REVISION_ACCEPTED":
                continue
            payload=event.get("payload",{})
            if str(payload.get("deficit_id"))==str(deficit_id):
                accepted=payload; break
        if accepted is None:
            return {"status":"NO_ACCEPTED_REVISIT_HYPOTHESIS_REVISION","deficit_id":str(deficit_id),"authority":"NONE"}
        revised=str(accepted.get("revised_hypothesis_digest_sha256",""))
        current=[]
        for binding_id in tuple(accepted.get("equivalent_binding_ids",())) or (accepted.get("binding_id"),):
            if not binding_id: continue
            binding=self.action_outcome_learning.projection_conditioned_bindings.get(str(binding_id))
            if binding is None or not self._projection_conditioned_binding_current(binding):
                continue
            digest=projection_conditioned_hypothesis_surface_digest(binding,self.action_outcome_learning.relations)
            if digest==revised:
                current.append(str(binding_id))
        if not current:
            return {
                "status":"ACCEPTED_REVISION_MODEL_NOT_CURRENT","deficit_id":str(deficit_id),
                "revised_hypothesis_digest_sha256":revised,"authority":"NONE",
            }
        return {
            "status":"CURRENT_ACCEPTED_REVISED_HYPOTHESIS_SURFACE","deficit_id":str(deficit_id),
            "revised_hypothesis_digest_sha256":revised,"current_binding_ids":tuple(sorted(set(current))),
            "authority":"NONE","new_unknown_authority":"NONE","execution_authority":"NONE",
        }

    def record_revised_surface_action_limited_unknown(
        self, *, old_deficit_id: str, new_deficit_id: str, unknown_evidence_id: str,
        missing_discriminator_signature_sha256: str,
    ) -> EpistemicDeficitRecord:
        """Create a new bounded deficit after accepted model revision, never rewrite the old one.

        The revised hypothesis digest is recovered from the accepted revision event and
        revalidated current model content.  A genuinely fresh UNKNOWN_INCOMPLETE evidence
        record is still required; revision itself does not manufacture a new question.
        Currentness is conservatively anchored to one deterministic current qualified
        projection representing the unique revised surface.
        """
        old=self.epistemic_deficits.records.get(str(old_deficit_id))
        if old is None or old.state!=EpistemicDeficitState.STALE:
            raise ValueError("REVISED_SURFACE_SUCCESSOR_REQUIRES_STALE_OLD_DEFICIT")
        if str(unknown_evidence_id)==old.unknown_evidence_id:
            raise ValueError("REVISED_SURFACE_SUCCESSOR_REQUIRES_FRESH_UNKNOWN_EVIDENCE")
        ev=self.evidence.get(str(unknown_evidence_id))
        if ev is None or ev.get("disposition")!=EpistemicStatus.UNKNOWN_INCOMPLETE.value:
            raise ValueError("REVISED_SURFACE_SUCCESSOR_REQUIRES_FRESH_UNKNOWN_INCOMPLETE")
        status=self.accepted_revisit_hypothesis_revision_status(str(old_deficit_id))
        if status.get("status")!="CURRENT_ACCEPTED_REVISED_HYPOTHESIS_SURFACE":
            raise ValueError(f"REVISED_SURFACE_NOT_CURRENT:{status.get('status','ABSTAIN')}")
        binding_id=status["current_binding_ids"][0]
        binding=self.action_outcome_learning.projection_conditioned_bindings[binding_id]
        projection=self.epistemic_projections.records[binding.projection_id]
        projection_anchor=EpistemicCurrentnessAnchor("PROJECTION",projection.projection_id,projection.epoch)
        anchors=list(old.premise_anchors)
        if projection_anchor not in anchors:
            anchors.append(projection_anchor)
        rec=self.record_action_limited_unknown(
            deficit_id=str(new_deficit_id),question_key=old.question_key,
            hypothesis_digest_sha256=status["revised_hypothesis_digest_sha256"],
            unknown_evidence_id=str(unknown_evidence_id),
            missing_discriminator_signature_sha256=str(missing_discriminator_signature_sha256),
            premise_anchors=tuple(anchors),
            assistance_ancestry=tuple(old.assistance_ancestry)+(
                f"SUCCESSOR_OF:{old_deficit_id}",
                f"ACCEPTED_REVISED_HYPOTHESIS_SURFACE:{status['revised_hypothesis_digest_sha256']}",
                f"CURRENTNESS_REPRESENTATIVE_PROJECTION:{projection.projection_id}@{projection.epoch}",
                "MISSING_DISCRIMINATOR_SIGNATURE_SUPPLIED_TO_BOUNDED_SUCCESSOR",
            ),
        )
        packet={
            "old_deficit_id":str(old_deficit_id),"new_deficit_id":rec.deficit_id,
            "revised_hypothesis_digest_sha256":rec.hypothesis_digest_sha256,
            "unknown_evidence_id":rec.unknown_evidence_id,
            "projection_anchor":projection_anchor.serializable(),
            "truth_authority":"NONE","answer_authority":"NONE","model_switch_authority":"NONE",
        }
        self.path.append("EPISTEMIC_REVISED_SURFACE_SUCCESSOR_DEFICIT_RECORDED",packet)
        self.store.append("EPISTEMIC_REVISED_SURFACE_SUCCESSOR_DEFICIT_RECORDED",packet)
        return rec

    def derive_revisit_one_step_visible_history_refinement(self, deficit_id: str) -> dict[str, Any]:
        """Bind one-step refinement to the exact admitted MODEL_SPACE_CHALLENGE for a revisit.

        This is an ephemeral relevance join only. It does not select among unrelated
        refinements, reopen the deficit, qualify a model, assert hidden state, or grant
        deeper-history authority.
        """
        deficit=self.epistemic_deficits.records.get(str(deficit_id))
        if deficit is None:
            return {"status":"ABSTAIN","reason":"EPISTEMIC_DEFICIT_NOT_FOUND","authority":"NONE"}
        if deficit.state!=EpistemicDeficitState.REVISIT_REQUIRED:
            return {"status":"ABSTAIN","reason":"REVISIT_REQUIRED","authority":"NONE"}
        challenge_ids=[]
        witness_by_id={}
        for event in self.store.events():
            payload=event.get("payload",{})
            if event.get("kind")=="EPISTEMIC_PROGRAM_STEP_BEARING_WITNESS":
                wid=payload.get("witness_id")
                if wid: witness_by_id[str(wid)]=payload
            elif event.get("kind")=="EPISTEMIC_DEFICIT_REVISIT_REQUESTED" and payload.get("deficit_id")==deficit.deficit_id and payload.get("bearing_kind")==EpistemicBearingKind.MODEL_SPACE_CHALLENGE.value:
                wid=payload.get("program_step_bearing_witness_id")
                if wid: challenge_ids.append(str(wid))
        if not challenge_ids:
            return {"status":"NO_MODEL_SPACE_CHALLENGE_FOR_REVISIT","refinements":(),"authority":"NONE"}
        surface=self.derive_admitted_one_step_visible_history_refinements()
        matches=[]
        challenge_sample_ids=[]
        for wid in dict.fromkeys(challenge_ids):
            witness=witness_by_id.get(wid)
            if witness is None:
                continue
            eid=str(witness.get("outcome_evidence_id",""))
            outcomes=[o for o in self.action_closure.outcomes.values() if o.evidence_id==eid]
            if len(outcomes)!=1:
                continue
            projected=self.derive_admitted_opaque_transition_sample(outcomes[0].execution_id)
            if projected.get("status")!="ADMITTED_OPAQUE_TRANSITION_SAMPLE":
                continue
            sample=projected["sample"]; challenge_sample_ids.append(sample.sample_id)
            for candidate in surface.get("refinements",()):
                if (candidate.start_token,candidate.action_token)!=(sample.start_token,sample.action_token):
                    continue
                if candidate.frame_epoch!=(sample.frame_id,sample.frame_epoch):
                    continue
                if sample.sample_id not in candidate.source_sample_ids:
                    continue
                if sample.end_token not in {end for _,end,_ in candidate.context_outcomes}:
                    continue
                matches.append(candidate)
        unique={c.refinement_id:c for c in matches}
        if not unique:
            return {"status":"NO_BOUNDED_REFINEMENT_FOR_REVISIT","refinements":(),"challenge_sample_ids":tuple(challenge_sample_ids),"authority":"NONE"}
        if len(unique)>1:
            return {"status":"REVISIT_REFINEMENT_AMBIGUOUS","refinements":tuple(unique[k] for k in sorted(unique)),"challenge_sample_ids":tuple(challenge_sample_ids),"authority":"NONE"}
        candidate=next(iter(unique.values()))
        return {
            "status":"REVISIT_ONE_STEP_VISIBLE_HISTORY_REFINEMENT_CANDIDATE",
            "refinement":candidate,
            "challenge_sample_ids":tuple(challenge_sample_ids),
            "truth_authority":"NONE","hidden_state_authority":"NONE",
            "model_replacement_authority":"NONE","history_depth_extension_authority":"NONE",
            "execution_authority":"NONE",
        }

    def admit_revisit_one_step_visible_history_refinement_projection(
        self, deficit_id: str, ticket: ProjectionQualificationTicket, *, projection_id: str | None = None,
    ) -> EpistemicProjectionRecord:
        """Admit one challenge-bound visible-history refinement through the existing projection owner.

        The refinement is re-derived from current admitted history at admission time, so a
        stale or substituted proposal cannot ride an old ticket. External qualification is
        mandatory. Admission grants only an opaque current projection handle; it does not
        reopen the deficit, route a consequential relation, assert hidden state, or qualify
        any replacement model.
        """
        derived=self.derive_revisit_one_step_visible_history_refinement(deficit_id)
        if derived.get("status")!="REVISIT_ONE_STEP_VISIBLE_HISTORY_REFINEMENT_CANDIDATE":
            raise ValueError("REVISIT_REFINEMENT_NOT_CURRENTLY_ADMISSIBLE")
        candidate=derived["refinement"]
        ok,reason=validate_external_projection_ticket(candidate,ticket,self.evidence)
        if not ok:
            raise ValueError(f"INVALID_EXTERNAL_REVISIT_REFINEMENT_QUALIFICATION:{reason}")
        frame_id,frame_epoch=candidate.frame_epoch
        if not self.frames.is_current(frame_id,frame_epoch):
            raise ValueError("REVISIT_REFINEMENT_FRAME_DRIFT_AFTER_NOMINATION")
        pid=projection_id or ("proj-revisit-refinement-"+candidate.digest()[:20])
        if pid in self.epistemic_projections.records:
            raise ValueError("DUPLICATE_EPISTEMIC_PROJECTION")
        qids=tuple(x.evidence_id for x in ticket.qualification_evidence)
        rec=EpistemicProjectionRecord(
            projection_id=pid,signature_sha256=candidate.digest(),epoch=0,
            assistance_ancestry=(
                "REVISIT_ONE_STEP_VISIBLE_HISTORY_REFINEMENT",
                f"DEFICIT:{deficit_id}",
                f"EXTERNAL_PROJECTION_QUALIFIER:{ticket.qualifier_id}",
                f"CANDIDATE_SHA256:{ticket.candidate_sha256}",
                "QUALIFICATION_EVIDENCE:"+",".join(qids),
            ),
            projection_origin="ENDOGENOUS_PROPOSAL_EXTERNALLY_QUALIFIED",
            proposal_candidate_sha256=candidate.digest(),qualification_evidence_ids=qids,
            frame_epochs=(candidate.frame_epoch,),
        )
        self.epistemic_projections.register(rec)
        packet=rec.serializable();self.path.append("EPISTEMIC_PROJECTION_REGISTERED",packet);self.store.append("EPISTEMIC_PROJECTION_REGISTERED",packet)
        admitted={
            "candidate_id":candidate.candidate_id,"candidate_sha256":candidate.digest(),
            "projection_id":pid,"deficit_id":str(deficit_id),"qualifier_id":ticket.qualifier_id,
            "qualification":ticket.state.value,"qualification_evidence_ids":list(qids),
            "revisit_state":self.epistemic_deficits.records[str(deficit_id)].state.value,
            "truth_authority":"NONE","hidden_state_authority":"NONE",
            "model_replacement_authority":"NONE","execution_authority":"NONE",
        }
        self.path.append("REVISIT_ONE_STEP_VISIBLE_HISTORY_REFINEMENT_PROJECTION_ADMITTED",admitted)
        self.store.append("REVISIT_ONE_STEP_VISIBLE_HISTORY_REFINEMENT_PROJECTION_ADMITTED",admitted)
        return rec

    def discover_admitted_opaque_action_composition_candidates(self) -> dict[str, Any]:
        """Research-only relational discovery over organism-owned admitted history.

        Transition samples are re-projected ephemerally from the existing action,
        evidence, admission-receipt, and operational-frame owners.  Frames are
        kept separate; no sample/candidate registry or persistence is added.
        """
        projected: list[OpaqueTransitionSample] = []
        rejected: list[tuple[str, str]] = []
        for execution_id in sorted(self.action_closure.executions):
            row = self.derive_admitted_opaque_transition_sample(execution_id)
            if row.get("status") == "ADMITTED_OPAQUE_TRANSITION_SAMPLE":
                projected.append(row["sample"])
            else:
                rejected.append((execution_id, str(row.get("reason", "ABSTAIN"))))
        by_frame: dict[tuple[str, int], list[OpaqueTransitionSample]] = {}
        for sample in projected:
            by_frame.setdefault((sample.frame_id, sample.frame_epoch), []).append(sample)
        candidates: list[OpaqueActionCompositionCandidate] = []
        for key in sorted(by_frame):
            candidates.extend(discover_opaque_action_composition_candidates(tuple(by_frame[key])))
        candidates.sort(key=lambda c: (c.digest(), c.candidate_id))
        return {
            "status":"ADMITTED_RELATIONAL_CANDIDATE_SURFACE" if candidates else "NO_ADMITTED_RELATIONAL_CANDIDATE",
            "samples":tuple(projected),
            "candidates":tuple(candidates),
            "admitted_sample_count":len(projected),
            "rejected_execution_reasons":tuple(rejected),
            "frame_groups":tuple((fid, epoch, len(rows)) for (fid, epoch), rows in sorted(by_frame.items())),
            "sample_persistence":"NONE",
            "candidate_persistence":"NONE",
            "truth_authority":"NONE",
            "execution_authority":"NONE",
            "evidence_independence_authority":"NONE",
        }

    def record_bounded_action_outcome(self, execution_id: str, obs: Observation, *, evidence_id: str, evidence_premise_epochs: Iterable[tuple[str,int]] = (), evidence_premise_signatures: Iterable[tuple[str,str]] = ()) -> dict[str, Any]:
        """Close one executed step with external observation; never treat model output as observation."""
        ex=self.action_closure.executions.get(execution_id)
        if ex is None: return {"status":"OUTCOME_REJECTED","reason":"EXECUTION_NOT_FOUND"}
        if any(o.execution_id==execution_id for o in self.action_closure.outcomes.values()): return {"status":"OUTCOME_REJECTED","reason":"EXECUTION_ALREADY_HAS_OUTCOME"}
        if obs.authority!=Authority.OBSERVATION_ONLY or obs.referent!=f"action-execution:{execution_id}" or not isinstance(obs.value,dict): return {"status":"OUTCOME_REJECTED","reason":"CONTENT_BOUND_EXTERNAL_OBSERVATION_REQUIRED"}
        payload=dict(obs.value); intent=self.action_closure.intents[ex.intent_id]
        evidence_premise_epochs=tuple((str(cid),int(epoch)) for cid,epoch in evidence_premise_epochs)
        evidence_premise_signatures=tuple((str(cid),str(sig).lower()) for cid,sig in evidence_premise_signatures)
        if intent.basis_kind=="MULTI_VALUE_LICENSE":
            return self._record_multi_value_action_outcome(ex,intent,obs,payload,evidence_id=evidence_id,evidence_premise_epochs=evidence_premise_epochs,evidence_premise_signatures=evidence_premise_signatures)
        if intent.basis_kind=="EPISTEMIC_PROGRAM_STEP":
            if "next_state_id" not in payload:
                return {"status":"OUTCOME_REJECTED","reason":"EPISTEMIC_STEP_OUTCOME_FIELDS_MISSING"}
            if any(k in payload for k in ("value_id","observed_value","observed_values","actual_value_effect")):
                return {"status":"OUTCOME_REJECTED","reason":"EPISTEMIC_STEP_VALUE_CLAIM_NOT_ALLOWED"}
            next_state=str(payload["next_state_id"])
            self.observe(obs)
            ref=self.append_evidence(evidence_id,{"execution_id":execution_id,"next_state_id":next_state,"start_state_id":intent.start_state_id,"capability_id":ex.capability_id,"capability_epoch":ex.capability_epoch,"capture_id":obs.capture_id,"observation_lineage":list(obs.lineage),"observation_currentness_basis":obs.currentness_basis,"evidence_premise_epochs":[list(x) for x in evidence_premise_epochs],"evidence_premise_signatures":[list(x) for x in evidence_premise_signatures],"epistemic_program_trial_id":intent.proposal_id,"value_authority":"NONE","truth_authority":"NONE"},EpistemicStatus.PRESSURE_SUPPORTED,source=obs.origin)
            self.action_closure.set_state(OpaqueControlStateWitness(next_state,ref.evidence_id))
            pc=RelationalCommitment(action_stable_id("ACTION-PREDICTION-",{"execution":execution_id,"evidence":ref.sha256}),f"action-execution:{execution_id}:prediction-match",TernaryCommitment.UNKNOWN,reason="EPISTEMIC_STEP_HAS_NO_STEP_LOCAL_PREDICTION_CLAIM",qualifiers=(("evidence_id",ref.evidence_id),("truth_authority","NONE")),premise_ids=(intent.proposal_id,execution_id))
            outcome=ActionOutcomeRecord(outcome_id=action_stable_id("ACTION-OUTCOME-",{"execution":execution_id,"evidence":ref.sha256}),execution_id=execution_id,evidence_id=ref.evidence_id,actual_next_state_id=next_state,observed_value=None,value_id=None,prediction_commitment=pc,actual_value_effect=None,state_only=True)
            self.action_closure.add_outcome(outcome); packet=outcome.serializable(); self.path.append("BOUNDED_ACTION_OUTCOME",packet); self.store.append("BOUNDED_ACTION_OUTCOME",packet)
            state_packet=self.action_closure.current_state.serializable(); self.path.append("OPAQUE_CONTROL_STATE_OBSERVED",state_packet); self.store.append("OPAQUE_CONTROL_STATE_OBSERVED",state_packet)
            return {"status":"ACTION_OUTCOME_OBSERVED","outcome":packet,"value_state":None,"requires_redeliberation":True}
        required={"next_state_id","value_id","observed_value"}
        if not required.issubset(payload): return {"status":"OUTCOME_REJECTED","reason":"ACTION_OUTCOME_FIELDS_MISSING"}
        if intent.basis_kind!="SINGLE_VALUE_REHEARSAL": return {"status":"OUTCOME_REJECTED","reason":"UNKNOWN_ACTION_INTENT_BASIS"}
        if intent.value_epoch is None: return {"status":"OUTCOME_REJECTED","reason":"ACTION_OUTCOME_VALUE_PREMISE_MISSING"}
        vid=str(payload["value_id"]); next_state=str(payload["next_state_id"]); observed=float(payload["observed_value"])
        if vid!=intent.value_epoch[0] or not self.values.is_current(vid,intent.value_epoch[1]) or not math.isfinite(observed): return {"status":"OUTCOME_REJECTED","reason":"ACTION_OUTCOME_VALUE_PREMISE_NOT_CURRENT"}
        latest=self.values.latest.get(vid)
        if latest is None or latest[0]!=intent.value_epoch[1]: return {"status":"OUTCOME_REJECTED","reason":"NO_PREACTION_VALUE_STATE"}
        pre=float(latest[1]); self.observe(obs)
        ref=self.append_evidence(evidence_id,{"execution_id":execution_id,"next_state_id":next_state,"value_id":vid,"observed_value":observed,"actual_value_effect":round(observed-pre,3),"start_state_id":intent.start_state_id,"capability_id":ex.capability_id,"capability_epoch":ex.capability_epoch,"capture_id":obs.capture_id,"observation_lineage":list(obs.lineage),"observation_currentness_basis":obs.currentness_basis,"evidence_premise_epochs":[list(x) for x in evidence_premise_epochs],"evidence_premise_signatures":[list(x) for x in evidence_premise_signatures],"intended_next_state_id":intent.expected_next_state_id,"intended_value_effect":intent.expected_value_effect},EpistemicStatus.PRESSURE_SUPPORTED,source=obs.origin)
        value_packet=self.observe_value_state(vid,observed)
        self.action_closure.set_state(OpaqueControlStateWitness(next_state,ref.evidence_id))
        state_match=(next_state==intent.expected_next_state_id); effect_match=(round(observed-pre,3)==round(intent.expected_value_effect,3))
        match=state_match and effect_match; stance=TernaryCommitment.YES if match else TernaryCommitment.NO
        pc=RelationalCommitment(action_stable_id("ACTION-PREDICTION-",{"execution":execution_id,"evidence":ref.sha256}),f"action-execution:{execution_id}:prediction-match",stance,reason="STEP_PREDICTION_MATCHED_OBSERVATION" if match else "STEP_PREDICTION_VIOLATED_BY_OBSERVATION",qualifiers=(("evidence_id",ref.evidence_id),("state_match",str(state_match)),("effect_match",str(effect_match)),("truth_authority","NONE")),premise_ids=(intent.proposal_id,execution_id))
        outcome=ActionOutcomeRecord(outcome_id=action_stable_id("ACTION-OUTCOME-",{"execution":execution_id,"evidence":ref.sha256}),execution_id=execution_id,evidence_id=ref.evidence_id,actual_next_state_id=next_state,observed_value=observed,value_id=vid,actual_value_effect=round(observed-pre,3),prediction_commitment=pc)
        self.action_closure.add_outcome(outcome); packet=outcome.serializable(); self.path.append("BOUNDED_ACTION_OUTCOME",packet); self.store.append("BOUNDED_ACTION_OUTCOME",packet)
        state_packet=self.action_closure.current_state.serializable(); self.path.append("OPAQUE_CONTROL_STATE_OBSERVED",state_packet); self.store.append("OPAQUE_CONTROL_STATE_OBSERVED",state_packet)
        return {"status":"ACTION_OUTCOME_OBSERVED","outcome":packet,"value_state":value_packet,"requires_redeliberation":True}

    def _record_multi_value_action_outcome(self, ex: ActionExecutionRecord, intent: BoundedActionIntent, obs: Observation, payload: dict[str, Any], *, evidence_id: str, evidence_premise_epochs: tuple[tuple[str,int], ...] = (), evidence_premise_signatures: tuple[tuple[str,str], ...] = ()) -> dict[str, Any]:
        """Record one execution outcome with independently observed value coordinates."""
        if "next_state_id" not in payload or not isinstance(payload.get("observed_values"),dict):
            return {"status":"OUTCOME_REJECTED","reason":"MULTI_VALUE_OUTCOME_FIELDS_MISSING"}
        observed_values={str(k):float(v) for k,v in payload["observed_values"].items()}
        if not observed_values or any(not math.isfinite(v) for v in observed_values.values()):
            return {"status":"OUTCOME_REJECTED","reason":"MULTI_VALUE_OUTCOME_OBSERVATION_INVALID"}
        required_epochs=dict(intent.required_value_epochs)
        if any(value_id not in required_epochs for value_id in observed_values):
            return {"status":"OUTCOME_REJECTED","reason":"MULTI_VALUE_OUTCOME_UNBOUND_VALUE"}

        pre_values: dict[str,float]={}
        for value_id in observed_values:
            epoch=required_epochs[value_id]
            if not self.values.is_current(value_id,epoch):
                return {"status":"OUTCOME_REJECTED","reason":"MULTI_VALUE_OUTCOME_VALUE_PREMISE_NOT_CURRENT","value_id":value_id}
            latest=self.values.latest.get(value_id)
            if latest is None or latest[0]!=epoch:
                return {"status":"OUTCOME_REJECTED","reason":"NO_PREACTION_VALUE_STATE","value_id":value_id}
            pre_values[value_id]=float(latest[1])

        next_state=str(payload["next_state_id"])
        try:
            cfg=DiscoveryConfig(**dict(intent.derivation_parameters))
        except (TypeError,ValueError):
            return {"status":"OUTCOME_REJECTED","reason":"MULTI_VALUE_DERIVATION_CONFIG_INVALID"}
        current_license=self.derive_multi_value_action_licenses(tuple(required_epochs),config=cfg)
        coordinates,actual_effects=build_multi_value_outcome_coordinates(
            intent.required_value_epochs,ex.capability_id,observed_values,pre_values,
            current_license.get("effect_witnesses",{}),self.operational_traces,
        )

        missing=tuple(value_id for value_id,_ in intent.required_value_epochs if value_id not in observed_values)
        self.observe(obs)
        ref=self.append_evidence(evidence_id,{
            "execution_id":ex.execution_id,"next_state_id":next_state,"observed_values":observed_values,"actual_value_effects":actual_effects,
            "missing_value_ids":missing,"required_value_epochs":list(intent.required_value_epochs),"start_state_id":intent.start_state_id,
            "capability_id":ex.capability_id,"capability_epoch":ex.capability_epoch,"capture_id":obs.capture_id,
            "observation_lineage":list(obs.lineage),"observation_currentness_basis":obs.currentness_basis,
            "evidence_premise_epochs":[list(x) for x in evidence_premise_epochs],
            "evidence_premise_signatures":[list(x) for x in evidence_premise_signatures],
            "intended_effect_authority":"NONE","semantic_goal_authority":"NONE",
        },EpistemicStatus.PRESSURE_SUPPORTED,source=obs.origin)
        value_packets={
            value_id:self.observe_value_state(value_id,observed_values[value_id])
            for value_id,_ in intent.required_value_epochs
            if value_id in observed_values
        }
        self.action_closure.set_state(OpaqueControlStateWitness(next_state,ref.evidence_id))
        premise_ids=tuple(x for x in ((ex.execution_commitment_id,) + ex.execution_premise_ids) if x)
        pc=RelationalCommitment(
            action_stable_id("ACTION-PREDICTION-",{"execution":ex.execution_id,"evidence":ref.sha256}),
            f"action-execution:{ex.execution_id}:prediction-match",TernaryCommitment.UNKNOWN,
            reason="MULTI_VALUE_PREDICTION_MATCH_NOT_CLAIMED",
            qualifiers=(("evidence_id",ref.evidence_id),("truth_authority","NONE"),("semantic_goal_authority","NONE")),premise_ids=premise_ids,
        )
        outcome=ActionOutcomeRecord(
            outcome_id=action_stable_id("ACTION-OUTCOME-",{"execution":ex.execution_id,"evidence":ref.sha256}),execution_id=ex.execution_id,
            evidence_id=ref.evidence_id,actual_next_state_id=next_state,observed_value=None,value_id=None,actual_value_effect=None,
            value_outcomes=tuple(coordinates),prediction_commitment=pc,
        )
        self.action_closure.add_outcome(outcome); packet=outcome.serializable(); self.path.append("BOUNDED_ACTION_OUTCOME",packet); self.store.append("BOUNDED_ACTION_OUTCOME",packet)
        state_packet=self.action_closure.current_state.serializable(); self.path.append("OPAQUE_CONTROL_STATE_OBSERVED",state_packet); self.store.append("OPAQUE_CONTROL_STATE_OBSERVED",state_packet)
        return {"status":"ACTION_OUTCOME_OBSERVED","outcome":packet,"value_states":value_packets,"missing_value_ids":list(missing),"requires_redeliberation":True}

    def _action_outcome_relation_structurally_current(self, r: QualifiedActionOutcomePredictiveRelation) -> bool:
        cap=self.capabilities.contracts.get(r.capability_id)
        if cap is None or cap.qualification not in {QualificationState.QUALIFIED,QualificationState.SHADOW_QUALIFIED}: return False
        if self.capabilities.epochs.get(r.capability_id,-1)!=r.capability_epoch: return False
        if not self.values.is_current(r.value_epoch[0],r.value_epoch[1]): return False
        if any(not self.frames.is_current(fid,ep) for fid,ep in r.frame_epochs): return False
        if any(not self.episodes.is_current(eid,ep) for eid,ep in r.episode_schema_epochs): return False
        if any(not self.topologies.is_current(tid,ep) for tid,ep in r.topology_epochs): return False
        if any(not self.coordinations.is_current(cid,ep) for cid,ep in r.coordination_epochs): return False
        for cid,ep in r.evidence_premise_epochs:
            c=self.capabilities.contracts.get(cid)
            if c is None or c.qualification not in {QualificationState.QUALIFIED,QualificationState.SHADOW_QUALIFIED}: return False
            if self.capabilities.epochs.get(cid,-1)!=ep: return False
        for cid,sig in r.evidence_premise_signatures:
            c=self.capabilities.contracts.get(cid)
            if c is None or c.computed_signature_sha256()!=sig: return False
        return True

    def _action_outcome_relation_current(self, r: QualifiedActionOutcomePredictiveRelation) -> bool:
        if not self._action_outcome_relation_structurally_current(r):
            return False
        witness=self.action_outcome_learning.currentness_witnesses.get(r.relation_id)
        return witness is None or witness.status != "DRIFT_WITNESS"

    def _action_outcome_experiences(self) -> tuple[ActionOutcomeExperience,...]:
        out=[]
        for outcome in self.action_closure.outcomes.values():
            evrow=self.evidence.get(outcome.evidence_id) or {}
            evpayload=evrow.get("payload",{}) if isinstance(evrow,dict) else {}
            evidence_premise_epochs=tuple((str(a),int(b)) for a,b in evpayload.get("evidence_premise_epochs",())) if isinstance(evpayload,dict) else ()
            evidence_premise_signatures=tuple((str(a),str(b)) for a,b in evpayload.get("evidence_premise_signatures",())) if isinstance(evpayload,dict) else ()
            ex=self.action_closure.executions.get(outcome.execution_id)
            if ex is None: continue
            intent=self.action_closure.intents.get(ex.intent_id)
            if intent is None: continue
            if outcome.value_outcomes:
                for coordinate in outcome.value_outcomes:
                    if coordinate.learning_ancestry_status!="CURRENT":
                        continue
                    out.append(ActionOutcomeExperience(
                        evidence_id=outcome.evidence_id,execution_id=outcome.execution_id,start_state_id=ex.start_state_id,
                        capability_id=ex.capability_id,actual_next_state_id=outcome.actual_next_state_id,actual_value_effect=float(coordinate.actual_value_effect),
                        capability_epoch=ex.capability_epoch,frame_epochs=tuple(coordinate.frame_epochs),episode_schema_epochs=tuple(coordinate.episode_schema_epochs),
                        value_epoch=(coordinate.value_id,coordinate.value_epoch),topology_epochs=tuple(coordinate.topology_epochs),coordination_epochs=tuple(coordinate.coordination_epochs),evidence_premise_epochs=evidence_premise_epochs,evidence_premise_signatures=evidence_premise_signatures,
                    ))
                continue
            if outcome.actual_value_effect is None: continue
            p=self.counterfactual_rehearsals.proposals.get(intent.proposal_id)
            if p is None: continue
            out.append(ActionOutcomeExperience(
                evidence_id=outcome.evidence_id, execution_id=outcome.execution_id, start_state_id=ex.start_state_id,
                capability_id=ex.capability_id, actual_next_state_id=outcome.actual_next_state_id, actual_value_effect=float(outcome.actual_value_effect),
                capability_epoch=ex.capability_epoch, frame_epochs=tuple(p.frame_epochs), episode_schema_epochs=tuple(p.episode_schema_epochs),
                value_epoch=tuple(p.value_epoch), topology_epochs=tuple(p.topology_epochs), coordination_epochs=tuple(p.coordination_epochs), evidence_premise_epochs=evidence_premise_epochs, evidence_premise_signatures=evidence_premise_signatures,
            ))
        return tuple(out)

    def nominate_action_outcome_predictive_candidates(self, *, min_support:int=8, min_consistency:float=.78) -> tuple[ActionOutcomePredictiveCandidate,...]:
        """Nominate consequence relations from executed actions and actual observed outcomes only. Intent is provenance, never the label."""
        candidates=nominate_action_outcome_candidates(self._action_outcome_experiences(),min_support=min_support,min_consistency=min_consistency)
        for c in candidates:
            if c.candidate_id not in self.action_outcome_learning.candidates:
                self.action_outcome_learning.add_candidate(c); packet=c.serializable(); self.path.append("ACTION_OUTCOME_PREDICTIVE_CANDIDATE",packet); self.store.append("ACTION_OUTCOME_PREDICTIVE_CANDIDATE",packet)
        return candidates

    def qualify_action_outcome_predictive_relation(self, ticket:ActionOutcomeRelationQualificationTicket) -> dict[str,Any]:
        c=self.action_outcome_learning.candidates.get(ticket.candidate_id)
        if c is None: return {"status":"RELATION_REJECTED","reason":"CANDIDATE_NOT_FOUND"}
        ok,reason=validate_external_action_outcome_ticket(c,ticket,self.evidence)
        if not ok: return {"status":"RELATION_REJECTED","reason":reason}
        # Currentness is checked at admission and whenever the relation is reused.
        proto=QualifiedActionOutcomePredictiveRelation(
            relation_id="PENDING",candidate_id=c.candidate_id,candidate_sha256=c.digest(),start_state_id=c.start_state_id,capability_id=c.capability_id,
            next_state_id=c.next_state_id,value_effect=c.value_effect,support=c.support,consistency=c.consistency,source_evidence_ids=c.source_evidence_ids,
            qualification_evidence_ids=tuple(r.evidence_id for r in ticket.qualification_evidence),holdout_support=ticket.holdout_support,holdout_accuracy=ticket.holdout_accuracy,
            capability_epoch=c.capability_epoch,frame_epochs=c.frame_epochs,episode_schema_epochs=c.episode_schema_epochs,value_epoch=c.value_epoch,topology_epochs=c.topology_epochs,coordination_epochs=c.coordination_epochs,evidence_premise_epochs=c.evidence_premise_epochs,evidence_premise_signatures=c.evidence_premise_signatures,
        )
        rid="ACTION-LAW-"+action_result_digest(proto.serializable())[:20]
        r=QualifiedActionOutcomePredictiveRelation(**{**proto.__dict__,"relation_id":rid})
        if not self._action_outcome_relation_current(r): return {"status":"RELATION_REJECTED","reason":"RELATION_PREMISE_NOT_CURRENT"}
        self.action_outcome_learning.add_relation(r); packet=r.serializable(); self.path.append("ACTION_OUTCOME_PREDICTIVE_RELATION_QUALIFIED",packet); self.store.append("ACTION_OUTCOME_PREDICTIVE_RELATION_QUALIFIED",packet)
        link=self.action_outcome_learning.replacement_links.get(c.candidate_id)
        if link is not None:
            lp={"relation_id":r.relation_id,"replacement_of_relation_id":link.replacement_of_relation_id,"drift_witness_id":link.drift_witness_id,"model_switch_authority":"NONE","semantic_regime_authority":"NONE"}
            self.action_outcome_learning.relation_replacement_lineage[r.relation_id]={"replacement_of_relation_id":link.replacement_of_relation_id,"drift_witness_id":link.drift_witness_id}
            self.path.append("ACTION_OUTCOME_REPLACEMENT_RELATION_LINK",lp); self.store.append("ACTION_OUTCOME_REPLACEMENT_RELATION_LINK",lp)
        return {"status":"CURRENT_PREDICTIVE_RELATION","relation":packet,"replacement_of":None if link is None else link.replacement_of_relation_id,"truth_authority":"NONE","causal_theorem_authority":"NONE"}

    def action_outcome_predictive_relation_status(self, relation_id:str) -> dict[str,Any]:
        r=self.action_outcome_learning.relations.get(relation_id)
        if r is None: return {"status":"UNKNOWN_INCOMPLETE","reason":"RELATION_NOT_FOUND"}
        witness=self.action_outcome_learning.currentness_witnesses.get(relation_id)
        lineage=self.action_outcome_learning.relation_replacement_lineage.get(relation_id)
        structural=self._action_outcome_relation_structurally_current(r)
        if not structural:
            status="STALE_PREDICTIVE_RELATION"
            stale_reason="STRUCTURAL_PREMISE_NOT_CURRENT"
        elif witness is not None and witness.status=="DRIFT_WITNESS":
            status="STALE_PREDICTIVE_RELATION"
            stale_reason="EMPIRICAL_DRIFT_WITNESS"
        else:
            status="CURRENT_PREDICTIVE_RELATION"
            stale_reason=None
        return {"status":status,"reason":stale_reason,"relation_id":relation_id,"authority":r.authority,"truth_authority":r.truth_authority,"causal_theorem_authority":r.causal_theorem_authority,"empirical_currentness_witness":None if witness is None else witness.serializable(),"replacement_lineage":lineage}

    def action_outcome_learning_status(self) -> dict[str,Any]:
        current=sum(self._action_outcome_relation_current(r) for r in self.action_outcome_learning.relations.values())
        return {"status":"ACTION_OUTCOME_LEARNING_STATE","candidate_count":len(self.action_outcome_learning.candidates),"relation_count":len(self.action_outcome_learning.relations),"current_relation_count":current,"empirical_currentness_witness_count":len(self.action_outcome_learning.currentness_witnesses),"replacement_link_count":len(self.action_outcome_learning.replacement_links),"general_causal_learner_authority":"NONE","self_qualification_authority":"NONE","semantic_goal_authority":"NONE","model_switch_authority":"NONE","drift_cause_authority":"NONE"}

    def _post_admission_action_outcome_experiences(self, relation_id:str) -> tuple[ActionOutcomeExperience,...]:
        events=self.store.events(); seen=False; ids=[]
        for event in events:
            kind=event.get("kind"); payload=event.get("payload",{})
            if kind=="ACTION_OUTCOME_PREDICTIVE_RELATION_QUALIFIED" and payload.get("relation_id")==relation_id:
                seen=True; continue
            if seen and kind=="BOUNDED_ACTION_OUTCOME":
                eid=payload.get("evidence_id")
                if eid: ids.append(str(eid))
        wanted=set(ids)
        return tuple(x for x in self._action_outcome_experiences() if x.evidence_id in wanted)

    def assess_action_outcome_predictive_currentness(
        self, relation_id:str, *, config:PredictiveCurrentnessConfig=PredictiveCurrentnessConfig(),
    ) -> dict[str,Any]:
        r=self.action_outcome_learning.relations.get(relation_id)
        if r is None:
            return {"status":"UNKNOWN_INCOMPLETE","reason":"RELATION_NOT_FOUND"}
        if not self._action_outcome_relation_structurally_current(r):
            return {"status":"STALE_STRUCTURAL_PREMISE","reason":"STRUCTURAL_PREMISE_NOT_CURRENT","drift_witness":None,"drift_cause_authority":"NONE"}
        rows=self._post_admission_action_outcome_experiences(relation_id)
        w=assess_action_outcome_relation_currentness(r,rows,config)
        previous=self.action_outcome_learning.currentness_witnesses.get(relation_id)
        # A drift witness is durable currentness-negative evidence. A later recovery window does not reactivate it.
        if previous is not None and previous.status=="DRIFT_WITNESS" and w.status!="DRIFT_WITNESS":
            w=previous
        self.action_outcome_learning.currentness_witnesses[relation_id]=w
        packet=w.serializable(); self.path.append("ACTION_OUTCOME_PREDICTIVE_CURRENTNESS_WITNESS",packet); self.store.append("ACTION_OUTCOME_PREDICTIVE_CURRENTNESS_WITNESS",packet)
        return {"status":w.status,"witness":packet,"model_switch_authority":"NONE","drift_cause_authority":"NONE","semantic_regime_authority":"NONE"}

    def nominate_action_outcome_replacement_candidates(
        self, relation_id:str, witness_id:str, *, min_support:int=8, min_consistency:float=.78,
    ) -> tuple[ActionOutcomePredictiveCandidate,...]:
        r=self.action_outcome_learning.relations.get(relation_id)
        w=self.action_outcome_learning.currentness_witnesses.get(relation_id)
        if r is None or w is None or w.witness_id!=witness_id or w.status!="DRIFT_WITNESS":
            return ()
        pairs=nominate_action_outcome_replacements(r,w,self._post_admission_action_outcome_experiences(relation_id),min_support=min_support,min_consistency=min_consistency)
        out=[]
        for c,link in pairs:
            if c.candidate_id not in self.action_outcome_learning.candidates:
                self.action_outcome_learning.add_candidate(c)
                packet=c.serializable(); self.path.append("ACTION_OUTCOME_PREDICTIVE_CANDIDATE",packet); self.store.append("ACTION_OUTCOME_PREDICTIVE_CANDIDATE",packet)
                lp=link.serializable(); self.action_outcome_learning.replacement_links[c.candidate_id]=link; self.path.append("ACTION_OUTCOME_REPLACEMENT_LINK",lp); self.store.append("ACTION_OUTCOME_REPLACEMENT_LINK",lp)
            out.append(c)
        return tuple(out)


    def nominate_projection_conditioned_relation_routing(
        self,
        *,
        projection_id: str,
        task_id: str,
        action_ids: Iterable[str],
        channel_ids: Iterable[str],
        horizon: int,
        default_action_relations: Iterable[tuple[str, str]],
        bucket_action_overrides: Iterable[tuple[str, str, str]],
        source_evidence_ids: Iterable[str],
    ) -> ProjectionConditionedRelationCandidate:
        """Propose relation routing through an existing qualified opaque projection.

        MS1453-1477 does not create a second state/partition subsystem. The
        selector is an already-admitted EpistemicProjectionRecord from the
        v1.7-v2.4 lineage. This candidate only proposes how its opaque buckets
        route existing action-outcome predictive relations in one bounded scope.
        """
        rec=self.epistemic_projections.records.get(str(projection_id))
        if rec is None or not rec.current:
            raise ValueError("PROJECTION_ROUTING_REQUIRES_CURRENT_EPISTEMIC_PROJECTION")
        actions=tuple(str(x) for x in action_ids)
        channels=tuple(str(x) for x in channel_ids)
        defaults=tuple((str(a),str(r)) for a,r in default_action_relations)
        overrides=tuple((str(b),str(a),str(r)) for b,a,r in bucket_action_overrides)
        evidence_ids=tuple(str(x) for x in source_evidence_ids)
        if not evidence_ids or any(self.evidence.get(eid) is None for eid in evidence_ids):
            raise ValueError("PROJECTION_ROUTING_REQUIRES_DURABLE_SOURCE_EVIDENCE")
        relation_ids=set(r for _,r in defaults) | {r for _,_,r in overrides}
        if any(rid not in self.action_outcome_learning.relations for rid in relation_ids):
            raise ValueError("PROJECTION_ROUTING_RELATION_NOT_FOUND")
        proto=ProjectionConditionedRelationCandidate(
            candidate_id="PENDING",
            projection_id=rec.projection_id,
            projection_epoch=rec.epoch,
            projection_signature_sha256=rec.signature_sha256,
            task_id=str(task_id),
            action_ids=actions,
            channel_ids=channels,
            horizon=int(horizon),
            default_action_relations=defaults,
            bucket_action_overrides=overrides,
            source_evidence_ids=evidence_ids,
        )
        cid="PROJ-REL-ROUTE-"+proto.digest()[:20]
        candidate=ProjectionConditionedRelationCandidate(**{**proto.__dict__,"candidate_id":cid})
        if cid not in self.action_outcome_learning.projection_routing_candidates:
            self.action_outcome_learning.add_projection_routing_candidate(candidate)
            packet=candidate.serializable()
            self.path.append("ACTION_OUTCOME_PROJECTION_ROUTING_CANDIDATE",packet)
            self.store.append("ACTION_OUTCOME_PROJECTION_ROUTING_CANDIDATE",packet)
        return candidate

    def _projection_conditioned_binding_current(self, binding: QualifiedProjectionConditionedRelationBinding) -> bool:
        rec=self.epistemic_projections.records.get(binding.projection_id)
        if rec is None or not rec.current or rec.epoch!=binding.projection_epoch or rec.signature_sha256!=binding.projection_signature_sha256:
            return False
        # Scoped qualification may lawfully reuse a globally empirical-stale relation,
        # but never one whose structural premises (capability/frame/episode/value/etc.)
        # have themselves ceased to be current.
        for relation_id in binding.relation_ids():
            relation=self.action_outcome_learning.relations.get(relation_id)
            if relation is None or not self._action_outcome_relation_structurally_current(relation):
                return False
        return True

    def qualify_projection_conditioned_relation_routing(
        self,
        ticket: ProjectionConditionedRelationQualificationTicket,
    ) -> dict[str,Any]:
        candidate=self.action_outcome_learning.projection_routing_candidates.get(ticket.candidate_id)
        if candidate is None:
            return {"status":"ROUTING_REJECTED","reason":"CANDIDATE_NOT_FOUND"}
        ok,reason=validate_external_projection_conditioned_relation_ticket(
            candidate,ticket,self.evidence,self.action_outcome_learning.relations,
        )
        if not ok:
            return {"status":"ROUTING_REJECTED","reason":reason}
        rec=self.epistemic_projections.records.get(candidate.projection_id)
        if rec is None or not rec.current or rec.epoch!=candidate.projection_epoch or rec.signature_sha256!=candidate.projection_signature_sha256:
            return {"status":"ROUTING_REJECTED","reason":"PROJECTION_CURRENTNESS_DRIFT_AFTER_NOMINATION"}
        for relation_id in candidate.relation_ids():
            relation=self.action_outcome_learning.relations.get(relation_id)
            if relation is None or not self._action_outcome_relation_structurally_current(relation):
                return {"status":"ROUTING_REJECTED","reason":f"ROUTING_RELATION_STRUCTURAL_PREMISE_NOT_CURRENT:{relation_id}"}
        proto=QualifiedProjectionConditionedRelationBinding(
            binding_id="PENDING",
            candidate_id=candidate.candidate_id,
            candidate_sha256=candidate.digest(),
            projection_id=candidate.projection_id,
            projection_epoch=candidate.projection_epoch,
            projection_signature_sha256=candidate.projection_signature_sha256,
            task_id=candidate.task_id,
            action_ids=candidate.action_ids,
            channel_ids=candidate.channel_ids,
            horizon=candidate.horizon,
            default_action_relations=candidate.default_action_relations,
            bucket_action_overrides=candidate.bucket_action_overrides,
            source_evidence_ids=candidate.source_evidence_ids,
            qualification_evidence_ids=tuple(r.evidence_id for r in ticket.qualification_evidence),
            holdout_support=ticket.holdout_support,
            holdout_accuracy=ticket.holdout_accuracy,
            holdout_coverage=ticket.holdout_coverage,
            qualified_bucket_ids=ticket.qualified_bucket_ids,
        )
        bid="PROJ-REL-BIND-"+action_result_digest(proto.serializable())[:20]
        binding=QualifiedProjectionConditionedRelationBinding(**{**proto.__dict__,"binding_id":bid})
        if not self._projection_conditioned_binding_current(binding):
            return {"status":"ROUTING_REJECTED","reason":"ROUTING_BINDING_NOT_CURRENT_AT_ADMISSION"}
        self.action_outcome_learning.add_projection_conditioned_binding(binding)
        packet=binding.serializable()
        self.path.append("ACTION_OUTCOME_PROJECTION_ROUTING_QUALIFIED",packet)
        self.store.append("ACTION_OUTCOME_PROJECTION_ROUTING_QUALIFIED",packet)
        return {
            "status":"CURRENT_PROJECTION_CONDITIONED_ROUTING",
            "binding":packet,
            "truth_authority":"NONE",
            "semantic_regime_authority":"NONE",
            "model_switch_authority":"NONE",
        }

    def projection_conditioned_relation_routing_status(self, binding_id:str) -> dict[str,Any]:
        binding=self.action_outcome_learning.projection_conditioned_bindings.get(binding_id)
        if binding is None:
            return {"status":"UNKNOWN_INCOMPLETE","reason":"ROUTING_BINDING_NOT_FOUND"}
        return {
            "status":"CURRENT_PROJECTION_CONDITIONED_ROUTING" if self._projection_conditioned_binding_current(binding) else "STALE_PROJECTION_CONDITIONED_ROUTING",
            "binding_id":binding_id,
            "projection_id":binding.projection_id,
            "projection_epoch":binding.projection_epoch,
            "task_id":binding.task_id,
            "action_ids":list(binding.action_ids),
            "channel_ids":list(binding.channel_ids),
            "horizon":binding.horizon,
            "qualified_bucket_ids":list(binding.qualified_bucket_ids),
            "semantic_regime_authority":"NONE",
            "model_switch_authority":"NONE",
        }

    def resolve_projection_conditioned_action_outcome_relation(
        self,
        binding_id:str,
        *,
        projection_bucket_id:str,
        action_id:str,
        task_id:str,
        channel_id:str,
        horizon:int,
    ) -> dict[str,Any]:
        binding=self.action_outcome_learning.projection_conditioned_bindings.get(binding_id)
        if binding is None:
            return {"status":"DEFER_UNKNOWN","reason":"ROUTING_BINDING_NOT_FOUND"}
        if not self._projection_conditioned_binding_current(binding):
            return {"status":"DEFER_UNKNOWN","reason":"ROUTING_BINDING_NOT_CURRENT"}
        if task_id!=binding.task_id or channel_id not in binding.channel_ids or int(horizon)!=binding.horizon or action_id not in binding.action_ids:
            return {"status":"DEFER_UNKNOWN","reason":"ROUTING_SCOPE_MISMATCH"}
        if str(projection_bucket_id) not in binding.qualified_bucket_ids:
            return {"status":"DEFER_UNKNOWN","reason":"PROJECTION_BUCKET_NOT_QUALIFIED"}
        relation_id=binding.relation_id_for(str(projection_bucket_id),str(action_id))
        if relation_id is None:
            return {"status":"DEFER_UNKNOWN","reason":"NO_RELATION_FOR_PROJECTION_BUCKET"}
        relation=self.action_outcome_learning.relations.get(relation_id)
        if relation is None or not self._action_outcome_relation_structurally_current(relation):
            return {"status":"DEFER_UNKNOWN","reason":"SCOPED_RELATION_STRUCTURAL_PREMISE_NOT_CURRENT"}
        global_status=self.action_outcome_predictive_relation_status(relation_id)["status"]
        return {
            "status":"CURRENT_PARTITION_SCOPED_RELATION",
            "relation_id":relation_id,
            "projection_id":binding.projection_id,
            "projection_epoch":binding.projection_epoch,
            "projection_bucket_id":str(projection_bucket_id),
            "global_relation_status":global_status,
            "truth_authority":"NONE",
            "semantic_regime_authority":"NONE",
            "model_switch_authority":"NONE",
        }

    def resolve_current_one_step_visible_history_projection_conditioned_relation(
        self, binding_id: str, *, action_id: str, task_id: str, channel_id: str, horizon: int,
    ) -> dict[str, Any]:
        """Resolve an admitted one-step refinement from owned current-state ancestry.

        The caller does not supply a projection bucket.  The bucket is the previous
        visible state from the exact admitted transition that produced the current
        control-state witness.  The existing projection-conditioned routing owner
        still owns relation qualification/currentness and grants no model-switch or
        execution authority.
        """
        binding=self.action_outcome_learning.projection_conditioned_bindings.get(binding_id)
        if binding is None:
            return {"status":"DEFER_UNKNOWN","reason":"ROUTING_BINDING_NOT_FOUND","execution_authority":"NONE"}
        rec=self.epistemic_projections.records.get(binding.projection_id)
        if rec is None or not rec.current:
            return {"status":"DEFER_UNKNOWN","reason":"REFINEMENT_PROJECTION_NOT_CURRENT","execution_authority":"NONE"}
        surface=self.derive_admitted_one_step_visible_history_refinements()
        candidates=[c for c in surface.get("refinements",()) if c.digest()==rec.signature_sha256]
        if len(candidates)!=1:
            return {"status":"DEFER_UNKNOWN","reason":"CURRENT_REFINEMENT_CONTENT_NOT_RECOVERABLE","execution_authority":"NONE"}
        candidate=candidates[0]
        cw=self.action_closure.current_state
        if cw is None or cw.state_id!=candidate.start_token or str(action_id)!=candidate.action_token:
            return {"status":"DEFER_UNKNOWN","reason":"CURRENT_STATE_OR_ACTION_OUTSIDE_REFINEMENT","execution_authority":"NONE"}
        outcomes=[o for o in self.action_closure.outcomes.values() if o.evidence_id==cw.evidence_id]
        if len(outcomes)!=1:
            return {"status":"DEFER_UNKNOWN","reason":"CURRENT_STATE_PREDECESSOR_OUTCOME_NOT_UNIQUE","execution_authority":"NONE"}
        projected=self.derive_admitted_opaque_transition_sample(outcomes[0].execution_id)
        if projected.get("status")!="ADMITTED_OPAQUE_TRANSITION_SAMPLE":
            return {"status":"DEFER_UNKNOWN","reason":"CURRENT_STATE_PREDECESSOR_NOT_ADMITTED","execution_authority":"NONE"}
        predecessor=projected["sample"]
        if predecessor.end_token!=cw.state_id or predecessor.frame_id!=candidate.frame_epoch[0] or predecessor.frame_epoch!=candidate.frame_epoch[1]:
            return {"status":"DEFER_UNKNOWN","reason":"CURRENT_STATE_PREDECESSOR_FRAME_OR_STATE_MISMATCH","execution_authority":"NONE"}
        bucket=predecessor.start_token
        if bucket not in {context for context,_,_ in candidate.context_outcomes}:
            return {"status":"DEFER_UNKNOWN","reason":"CURRENT_VISIBLE_HISTORY_CONTEXT_UNQUALIFIED","execution_authority":"NONE"}
        result=dict(self.resolve_projection_conditioned_action_outcome_relation(
            binding_id,projection_bucket_id=bucket,action_id=action_id,task_id=task_id,channel_id=channel_id,horizon=horizon,
        ))
        result["projection_bucket_id"]=bucket
        result["bucket_derivation_basis"]="CURRENT_ADMITTED_PREDECESSOR_VISIBLE_STATE"
        result["bucket_selection_authority"]="NONE"
        result["hidden_state_authority"]="NONE"
        result["history_depth_extension_authority"]="NONE"
        return result

    def historical_reentry_projection(self) -> HistoricalReentryProjection:
        """Project durable operational-registration history without restoring authority."""
        return derive_historical_reentry_projection(self.store.events())

    def _reentry_handle_current(self, handle: str) -> bool:
        kind, object_id = handle.split(":", 1)
        if kind == "CAP":
            c = self.capabilities.contracts.get(object_id)
            return bool(c is not None and c.qualification in {QualificationState.QUALIFIED, QualificationState.SHADOW_QUALIFIED})
        if kind == "TOPO":
            return self.topologies.is_current(object_id)
        if kind == "CP":
            return self.counterparties.is_current(object_id)
        if kind == "COORD":
            return self.coordinations.is_current(object_id)
        return False

    def assess_historical_reentry(
        self, warrant: ReentryWarrant, *, requested_scope: str
    ) -> ReentryDecision:
        """Assess transient external evidence against *actual* current registry premises.

        The caller cannot manufacture dependency currentness inside the warrant:
        Microseed re-reads its existing current-authority registries at this
        boundary. A READY decision still grants Authority.NONE and does not
        register anything.
        """
        projection = self.historical_reentry_projection()
        record = projection.record(warrant.handle)
        actual = () if record is None else tuple((d, self._reentry_handle_current(d)) for d in record.dependencies)
        effective = replace(warrant, dependency_currentness=actual)
        return assess_reentry(projection, effective, requested_scope=requested_scope)

    def bounded_control_loop_status(self) -> dict[str, Any]:
        w=self.action_closure.current_state
        return {"status":"BOUNDED_CONTROL_LOOP_STATE","current_state":None if w is None else w.serializable(),"intent_count":len(self.action_closure.intents),"execution_count":len(self.action_closure.executions),"outcome_count":len(self.action_closure.outcomes),"general_policy_authority":"NONE","semantic_intention_authority":"NONE"}

    _EPISTEMIC_PREMISE_KINDS = {
        "FRAME", "EPISODE", "VALUE", "TOPOLOGY", "COUNTERPARTY", "COORDINATION", "CAPABILITY_PREMISE", "PROJECTION",
    }

    def _epistemic_anchor_current(self, anchor: EpistemicCurrentnessAnchor) -> bool:
        if anchor.kind not in self._EPISTEMIC_PREMISE_KINDS:
            raise ValueError(f"UNSUPPORTED_EPISTEMIC_PREMISE_KIND:{anchor.kind}")
        if anchor.kind == "FRAME":
            return self.frames.is_current(anchor.object_id,anchor.epoch)
        if anchor.kind == "EPISODE":
            return self.episodes.is_current(anchor.object_id,anchor.epoch)
        if anchor.kind == "VALUE":
            return self.values.is_current(anchor.object_id,anchor.epoch)
        if anchor.kind == "TOPOLOGY":
            return self.topologies.is_current(anchor.object_id,anchor.epoch)
        if anchor.kind == "COUNTERPARTY":
            return self.counterparties.is_current(anchor.object_id,anchor.epoch)
        if anchor.kind == "COORDINATION":
            return self.coordinations.is_current(anchor.object_id,anchor.epoch)
        if anchor.kind == "PROJECTION":
            rec=self.epistemic_projections.records.get(anchor.object_id)
            return bool(rec is not None and rec.current and rec.epoch==anchor.epoch)
        c=self.capabilities.contracts.get(anchor.object_id)
        return bool(
            c is not None
            and c.qualification in {QualificationState.QUALIFIED,QualificationState.SHADOW_QUALIFIED}
            and self.capabilities.epochs.get(anchor.object_id,0) == anchor.epoch
        )

    def record_action_limited_unknown(
        self, *, deficit_id: str, question_key: str, hypothesis_digest_sha256: str,
        unknown_evidence_id: str, missing_discriminator_signature_sha256: str,
        premise_anchors: Iterable[EpistemicCurrentnessAnchor] = (),
        assistance_ancestry: Iterable[str] = (),
    ) -> EpistemicDeficitRecord:
        """Persist one class-C UNKNOWN as proposal/scheduling state only.

        Premise anchors are opaque operational currentness ancestry, not semantic
        question categories. Legacy records may have no anchors; new callers may
        bind only premises that are current at record creation.
        """
        ev=self.evidence.get(unknown_evidence_id)
        if ev is None:
            raise ValueError("UNKNOWN_EVIDENCE_NOT_FOUND")
        if ev["disposition"] != EpistemicStatus.UNKNOWN_INCOMPLETE.value:
            raise ValueError("EPISTEMIC_DEFICIT_REQUIRES_UNKNOWN_INCOMPLETE_EVIDENCE")
        anchors=tuple(premise_anchors)
        for anchor in anchors:
            if not isinstance(anchor,EpistemicCurrentnessAnchor):
                raise ValueError("EPISTEMIC_PREMISE_ANCHOR_TYPE_REQUIRED")
            if not self._epistemic_anchor_current(anchor):
                raise ValueError(f"EPISTEMIC_PREMISE_NOT_CURRENT:{anchor.kind}:{anchor.object_id}@{anchor.epoch}")
        rec=EpistemicDeficitRecord(
            deficit_id=deficit_id, question_key=question_key,
            hypothesis_digest_sha256=hypothesis_digest_sha256,
            unknown_evidence_id=unknown_evidence_id,
            missing_discriminator_signature_sha256=missing_discriminator_signature_sha256,
            premise_anchors=anchors,
            assistance_ancestry=tuple(assistance_ancestry),
        )
        self.epistemic_deficits.register(rec)
        packet=rec.serializable()
        self.path.append("EPISTEMIC_DEFICIT_RECORDED",packet); self.store.append("EPISTEMIC_DEFICIT_RECORDED",packet)
        return rec

    def link_candidate_to_epistemic_deficit(self, deficit_id: str, candidate_id: str) -> dict[str, Any]:
        """Record motivation ancestry only; this cannot qualify either object."""
        if candidate_id not in self.capability_candidates:
            raise ValueError("CANDIDATE_NOT_NOMINATED")
        rec=self.epistemic_deficits.link_candidate(deficit_id,candidate_id)
        packet={"deficit_id":deficit_id,"candidate_id":candidate_id,"authority":"NONE_MOTIVATION_LINK_ONLY"}
        self.path.append("EPISTEMIC_DEFICIT_CANDIDATE_LINKED",packet); self.store.append("EPISTEMIC_DEFICIT_CANDIDATE_LINKED",packet)
        return rec.serializable()

    def bind_probe_capability(self, deficit_id: str, capability_id: str) -> dict[str, Any]:
        """Mark a current qualified capability as available to probe, never as an answer."""
        c=self.capabilities.contracts.get(capability_id)
        if c is None or c.qualification not in {QualificationState.QUALIFIED,QualificationState.SHADOW_QUALIFIED}:
            raise ValueError("PROBE_CAPABILITY_NOT_CURRENT")
        epoch=self.capabilities.epochs.get(capability_id,0)
        rec=self.epistemic_deficits.bind_probe(deficit_id,capability_id,epoch)
        packet={"deficit_id":deficit_id,"capability_id":capability_id,"capability_epoch":epoch,"truth_authority":"NONE"}
        self.path.append("EPISTEMIC_DEFICIT_PROBE_BOUND",packet); self.store.append("EPISTEMIC_DEFICIT_PROBE_BOUND",packet)
        return rec.serializable()

    def record_epistemic_probe_evidence(self, deficit_id: str, evidence_id: str) -> dict[str, Any]:
        """Attach actual new probe evidence and request revisit; do not auto-resolve."""
        if self.evidence.get(evidence_id) is None:
            raise ValueError("PROBE_EVIDENCE_NOT_FOUND")
        rec=self.epistemic_deficits.record_probe_evidence(deficit_id,evidence_id)
        packet={"deficit_id":deficit_id,"evidence_id":evidence_id,"state":rec.state.value,"truth_authority":"NONE"}
        self.path.append("EPISTEMIC_DEFICIT_PROBE_EVIDENCE",packet); self.store.append("EPISTEMIC_DEFICIT_PROBE_EVIDENCE",packet)
        return rec.serializable()

    def request_epistemic_revisit(
        self, deficit_id: str, evidence_id: str, *, relevance_basis_sha256: str,
    ) -> dict[str, Any]:
        """Accept an explicit content-bound relevance assertion; infer no semantics.

        Main-Dev does not decide that evidence is relevant. The caller supplies a
        content-bound relevance basis; this method only records bounded scheduling
        state. It confers neither truth authority nor semantic-question authority.
        """
        if self.evidence.get(evidence_id) is None:
            raise ValueError("REVISIT_EVIDENCE_NOT_FOUND")
        basis=str(relevance_basis_sha256).lower()
        if len(basis) != 64 or any(c not in "0123456789abcdef" for c in basis):
            raise ValueError("RELEVANCE_BASIS_SHA256_REQUIRED")
        rec=self.epistemic_deficits.request_revisit(deficit_id,evidence_id)
        packet={
            "deficit_id":deficit_id,"evidence_id":evidence_id,"relevance_basis_sha256":basis,
            "state":rec.state.value,"relevance_authority":"EXPLICIT_BOUNDING_ONLY",
            "truth_authority":"NONE","semantic_question_authority":"NONE",
        }
        self.path.append("EPISTEMIC_DEFICIT_REVISIT_REQUESTED",packet); self.store.append("EPISTEMIC_DEFICIT_REVISIT_REQUESTED",packet)
        return rec.serializable()

    def discover_epistemic_projection_candidates(
        self,
        training_samples: Iterable[ProjectionSample],
        validation_samples: Iterable[ProjectionSample],
        cfg: ProjectionDiscoveryConfig | None = None,
    ) -> list[dict[str, Any]]:
        """Nominate bounded predictive-equivalence projections from interaction.

        This is proposal generation only. Raw positions and action/effect tokens
        are supplied by the current operational frame, and the fixed subset
        grammar remains explicit assistance ancestry. No candidate is admitted
        or qualified by this method.
        """
        train = tuple(training_samples)
        validation = tuple(validation_samples)
        for sample in train + validation:
            if not self.frames.is_current(sample.frame_id, sample.frame_epoch):
                raise ValueError("STALE_OR_UNKNOWN_PROJECTION_SAMPLE_FRAME")
        findings = discover_projection_candidates(train, validation, cfg)
        out: list[dict[str, Any]] = []
        for candidate in findings:
            if candidate.candidate_id not in self.epistemic_projection_candidates:
                self.epistemic_projection_candidates[candidate.candidate_id] = candidate
                packet = candidate.serializable()
                self.path.append("EPISTEMIC_PROJECTION_CANDIDATE_NOMINATED", packet)
                self.store.append("EPISTEMIC_PROJECTION_CANDIDATE_NOMINATED", packet)
            out.append({
                "candidate_id": candidate.candidate_id,
                "candidate_sha256": candidate.digest(),
                "input_positions": list(candidate.input_positions),
                "validation_accuracy": candidate.validation_accuracy,
                "lift": candidate.lift,
                "proposal_authority": candidate.proposal_authority,
                "qualification_authority": candidate.qualification_authority,
                "semantic_projection_authority": candidate.semantic_projection_authority,
            })
        return out

    def epistemic_projection_candidate_status(self, candidate_id: str) -> dict[str, Any]:
        return self.epistemic_projection_candidates[candidate_id].serializable()

    def admit_epistemic_projection_candidate(
        self,
        ticket: ProjectionQualificationTicket,
        *,
        projection_id: str | None = None,
    ) -> EpistemicProjectionRecord:
        """Consume external qualification for a nominated projection proposal."""
        candidate = self.epistemic_projection_candidates.get(ticket.candidate_id)
        if candidate is None:
            raise ValueError("PROJECTION_CANDIDATE_NOT_NOMINATED")
        ok, reason = validate_external_projection_ticket(candidate, ticket, self.evidence)
        if not ok:
            raise ValueError(f"INVALID_EXTERNAL_PROJECTION_QUALIFICATION:{reason}")
        for frame_id, epoch in candidate.frame_epochs:
            if not self.frames.is_current(frame_id, epoch):
                raise ValueError("PROJECTION_CANDIDATE_FRAME_DRIFT_AFTER_NOMINATION")
        pid = projection_id or ("proj-" + candidate.digest()[:20])
        if pid in self.epistemic_projections.records:
            raise ValueError("DUPLICATE_EPISTEMIC_PROJECTION")
        qids = tuple(x.evidence_id for x in ticket.qualification_evidence)
        rec = EpistemicProjectionRecord(
            projection_id=pid,
            signature_sha256=candidate.digest(),
            epoch=0,
            assistance_ancestry=tuple(candidate.assistance_ancestry) + (
                f"EXTERNAL_PROJECTION_QUALIFIER:{ticket.qualifier_id}",
                f"CANDIDATE_SHA256:{ticket.candidate_sha256}",
                "QUALIFICATION_EVIDENCE:" + ",".join(qids),
            ),
            projection_origin="ENDOGENOUS_PROPOSAL_EXTERNALLY_QUALIFIED",
            proposal_candidate_sha256=candidate.digest(),
            qualification_evidence_ids=qids,
            frame_epochs=tuple(candidate.frame_epochs),
        )
        self.epistemic_projections.register(rec)
        packet = rec.serializable()
        self.path.append("EPISTEMIC_PROJECTION_REGISTERED", packet)
        self.store.append("EPISTEMIC_PROJECTION_REGISTERED", packet)
        ap = {
            "candidate_id": candidate.candidate_id,
            "candidate_sha256": candidate.digest(),
            "projection_id": pid,
            "qualifier_id": ticket.qualifier_id,
            "qualification": ticket.state.value,
            "qualification_evidence_ids": list(qids),
            "truth_authority": "NONE",
            "semantic_projection_authority": "NONE",
        }
        self.path.append("EPISTEMIC_PROJECTION_CANDIDATE_ADMITTED", ap)
        self.store.append("EPISTEMIC_PROJECTION_CANDIDATE_ADMITTED", ap)
        return rec

    def discover_epistemic_constructor_candidates(
        self,
        training_samples: Iterable[ConstructorProjectionSample],
        pressure_samples: Iterable[ConstructorProjectionSample],
        validation_samples: Iterable[ConstructorProjectionSample],
        cfg: ConstructorGrowthConfig | None = None,
    ) -> list[dict[str, Any]]:
        """Nominate bounded conflict-directed higher-order/history projections.

        Proposal-only. Support order and lag depth are selected from opaque
        consequence conflicts inside supplied ceilings. Temporal samples must be
        backed by current EpisodeSchema ancestry; neither time boundaries nor
        qualification are authored here.
        """
        train=tuple(training_samples); pressure=tuple(pressure_samples); validation=tuple(validation_samples)
        for sample in train + pressure + validation:
            if not self.frames.is_current(sample.frame_id, sample.frame_epoch):
                raise ValueError("STALE_OR_UNKNOWN_CONSTRUCTOR_SAMPLE_FRAME")
            if len(sample.raw_history) > 1:
                if sample.episode_schema_id is None or sample.episode_schema_epoch is None:
                    raise ValueError("TEMPORAL_CONSTRUCTOR_SAMPLE_REQUIRES_EPISODE_SCHEMA_CURRENTNESS")
                if not self.episodes.is_current(sample.episode_schema_id, sample.episode_schema_epoch):
                    raise ValueError("STALE_OR_UNKNOWN_CONSTRUCTOR_SAMPLE_EPISODE_SCHEMA")
        findings=discover_constructor_candidates(train,pressure,validation,cfg)
        out=[]
        for candidate in findings:
            if candidate.candidate_id not in self.epistemic_constructor_candidates:
                self.epistemic_constructor_candidates[candidate.candidate_id]=candidate
                packet=candidate.serializable()
                self.path.append("EPISTEMIC_PROJECTION_CONSTRUCTOR_CANDIDATE_NOMINATED",packet)
                self.store.append("EPISTEMIC_PROJECTION_CONSTRUCTOR_CANDIDATE_NOMINATED",packet)
            out.append({
                "candidate_id":candidate.candidate_id,"candidate_sha256":candidate.digest(),
                "atoms":[a.token() for a in candidate.atoms],"lag_depth_used":candidate.lag_depth_used,
                "validation_accuracy":candidate.validation_accuracy,"lift":candidate.lift,
                "proposal_authority":"NONE","qualification_authority":"NONE",
                "semantic_projection_authority":"NONE","truth_authority":"NONE",
            })
        return out

    def epistemic_constructor_candidate_status(self, candidate_id: str) -> dict[str, Any]:
        return self.epistemic_constructor_candidates[candidate_id].serializable()

    def admit_epistemic_constructor_candidate(
        self, ticket: ConstructorQualificationTicket, *, projection_id: str | None = None,
    ) -> EpistemicProjectionRecord:
        candidate=self.epistemic_constructor_candidates.get(ticket.candidate_id)
        if candidate is None:
            raise ValueError("CONSTRUCTOR_CANDIDATE_NOT_NOMINATED")
        ok,reason=validate_external_constructor_ticket(candidate,ticket,self.evidence)
        if not ok:
            raise ValueError(f"INVALID_EXTERNAL_CONSTRUCTOR_QUALIFICATION:{reason}")
        for frame_id,epoch in candidate.frame_epochs:
            if not self.frames.is_current(frame_id,epoch):
                raise ValueError("CONSTRUCTOR_CANDIDATE_FRAME_DRIFT_AFTER_NOMINATION")
        for schema_id,epoch in candidate.episode_schema_epochs:
            if not self.episodes.is_current(schema_id,epoch):
                raise ValueError("CONSTRUCTOR_CANDIDATE_EPISODE_DRIFT_AFTER_NOMINATION")
        pid=projection_id or ("proj-constructor-"+candidate.digest()[:20])
        if pid in self.epistemic_projections.records:
            raise ValueError("DUPLICATE_EPISTEMIC_PROJECTION")
        qids=tuple(x.evidence_id for x in ticket.qualification_evidence)
        rec=EpistemicProjectionRecord(
            projection_id=pid,signature_sha256=candidate.digest(),epoch=0,
            assistance_ancestry=tuple(candidate.assistance_ancestry)+(
                f"EXTERNAL_CONSTRUCTOR_QUALIFIER:{ticket.qualifier_id}",
                f"CANDIDATE_SHA256:{ticket.candidate_sha256}",
                "QUALIFICATION_EVIDENCE:"+",".join(qids),
            ),
            projection_origin="ENDOGENOUS_CONSTRUCTOR_GROWTH_EXTERNALLY_QUALIFIED",
            proposal_candidate_sha256=candidate.digest(),qualification_evidence_ids=qids,
            frame_epochs=tuple(candidate.frame_epochs),episode_schema_epochs=tuple(candidate.episode_schema_epochs),
        )
        self.epistemic_projections.register(rec)
        packet=rec.serializable(); self.path.append("EPISTEMIC_PROJECTION_REGISTERED",packet); self.store.append("EPISTEMIC_PROJECTION_REGISTERED",packet)
        ap={"candidate_id":candidate.candidate_id,"candidate_sha256":candidate.digest(),"projection_id":pid,
            "qualifier_id":ticket.qualifier_id,"qualification":ticket.state.value,
            "qualification_evidence_ids":list(qids),"truth_authority":"NONE","semantic_projection_authority":"NONE"}
        self.path.append("EPISTEMIC_PROJECTION_CONSTRUCTOR_CANDIDATE_ADMITTED",ap); self.store.append("EPISTEMIC_PROJECTION_CONSTRUCTOR_CANDIDATE_ADMITTED",ap)
        return rec

    def discover_robust_epistemic_constructor_candidates(
        self,
        training_samples: Iterable[ConstructorProjectionSample],
        pressure_samples: Iterable[ConstructorProjectionSample],
        validation_samples: Iterable[ConstructorProjectionSample],
        cfg: RobustConstructorGrowthConfig | None = None,
    ) -> list[dict[str, Any]]:
        """Nominate noise-tolerant bounded supports without a noise-rate model.

        Exact observed discordance remains exact evidence. Robustness comes from
        ranking bounded supports by the fraction of exact conflicts they cover and
        requiring the smallest order that survives independent predictive splits.
        This is proposal-only and preserves all supplied ceilings as ancestry.
        """
        train=tuple(training_samples); pressure=tuple(pressure_samples); validation=tuple(validation_samples)
        for sample in train+pressure+validation:
            if not self.frames.is_current(sample.frame_id,sample.frame_epoch):
                raise ValueError("STALE_OR_UNKNOWN_ROBUST_CONSTRUCTOR_SAMPLE_FRAME")
            if len(sample.raw_history)>1:
                if sample.episode_schema_id is None or sample.episode_schema_epoch is None:
                    raise ValueError("TEMPORAL_ROBUST_CONSTRUCTOR_SAMPLE_REQUIRES_EPISODE_SCHEMA_CURRENTNESS")
                if not self.episodes.is_current(sample.episode_schema_id,sample.episode_schema_epoch):
                    raise ValueError("STALE_OR_UNKNOWN_ROBUST_CONSTRUCTOR_SAMPLE_EPISODE_SCHEMA")
        findings=discover_robust_constructor_candidates(train,pressure,validation,cfg)
        out=[]
        for candidate in findings:
            if candidate.candidate_id not in self.robust_epistemic_constructor_candidates:
                self.robust_epistemic_constructor_candidates[candidate.candidate_id]=candidate
                packet=candidate.serializable(); self.path.append("EPISTEMIC_ROBUST_CONSTRUCTOR_CANDIDATE_NOMINATED",packet); self.store.append("EPISTEMIC_ROBUST_CONSTRUCTOR_CANDIDATE_NOMINATED",packet)
            out.append({
                "candidate_id":candidate.candidate_id,"candidate_sha256":candidate.digest(),
                "atoms":[a.token() for a in candidate.atoms],"lag_depth_used":candidate.lag_depth_used,
                "validation_accuracy":candidate.validation_accuracy,"pressure_accuracy":candidate.pressure_accuracy,
                "observed_conflict_coverage":candidate.observed_conflict_coverage,
                "evaluated_support_count":candidate.evaluated_support_count,
                "proposal_authority":"NONE","qualification_authority":"NONE",
                "semantic_projection_authority":"NONE","truth_authority":"NONE",
            })
        return out

    def robust_epistemic_constructor_candidate_status(self,candidate_id:str)->dict[str,Any]:
        return self.robust_epistemic_constructor_candidates[candidate_id].serializable()

    def admit_robust_epistemic_constructor_candidate(
        self,ticket:RobustConstructorQualificationTicket,*,projection_id:str|None=None,
    )->EpistemicProjectionRecord:
        candidate=self.robust_epistemic_constructor_candidates.get(ticket.candidate_id)
        if candidate is None:raise ValueError("ROBUST_CONSTRUCTOR_CANDIDATE_NOT_NOMINATED")
        ok,reason=validate_external_robust_constructor_ticket(candidate,ticket,self.evidence)
        if not ok:raise ValueError(f"INVALID_EXTERNAL_ROBUST_CONSTRUCTOR_QUALIFICATION:{reason}")
        for frame_id,epoch in candidate.frame_epochs:
            if not self.frames.is_current(frame_id,epoch):raise ValueError("ROBUST_CONSTRUCTOR_CANDIDATE_FRAME_DRIFT_AFTER_NOMINATION")
        for schema_id,epoch in candidate.episode_schema_epochs:
            if not self.episodes.is_current(schema_id,epoch):raise ValueError("ROBUST_CONSTRUCTOR_CANDIDATE_EPISODE_DRIFT_AFTER_NOMINATION")
        pid=projection_id or ("proj-robust-constructor-"+candidate.digest()[:20])
        if pid in self.epistemic_projections.records:raise ValueError("DUPLICATE_EPISTEMIC_PROJECTION")
        qids=tuple(x.evidence_id for x in ticket.qualification_evidence)
        rec=EpistemicProjectionRecord(
            projection_id=pid,signature_sha256=candidate.digest(),epoch=0,
            assistance_ancestry=tuple(candidate.assistance_ancestry)+(
                f"EXTERNAL_ROBUST_CONSTRUCTOR_QUALIFIER:{ticket.qualifier_id}",
                f"CANDIDATE_SHA256:{ticket.candidate_sha256}",
                "QUALIFICATION_EVIDENCE:"+",".join(qids),
            ),
            projection_origin="ENDOGENOUS_ROBUST_CONSTRUCTOR_GROWTH_EXTERNALLY_QUALIFIED",
            proposal_candidate_sha256=candidate.digest(),qualification_evidence_ids=qids,
            frame_epochs=tuple(candidate.frame_epochs),episode_schema_epochs=tuple(candidate.episode_schema_epochs),
        )
        self.epistemic_projections.register(rec);packet=rec.serializable();self.path.append("EPISTEMIC_PROJECTION_REGISTERED",packet);self.store.append("EPISTEMIC_PROJECTION_REGISTERED",packet)
        ap={"candidate_id":candidate.candidate_id,"candidate_sha256":candidate.digest(),"projection_id":pid,"qualifier_id":ticket.qualifier_id,"qualification":ticket.state.value,"qualification_evidence_ids":list(qids),"truth_authority":"NONE","semantic_projection_authority":"NONE","drift_cause_authority":"NONE"}
        self.path.append("EPISTEMIC_ROBUST_CONSTRUCTOR_CANDIDATE_ADMITTED",ap);self.store.append("EPISTEMIC_ROBUST_CONSTRUCTOR_CANDIDATE_ADMITTED",ap)
        return rec

    def assess_epistemic_projection_predictive_currentness(
        self,projection_id:str,ordered_samples:Iterable[ConstructorProjectionSample],
        cfg:ProjectionPredictiveCurrentnessConfig|None=None,
    )->dict[str,Any]:
        """Bounded law-currentness witness; does not identify a regime or drift cause.

        The caller supplies operational sample order and fixed windows/thresholds.
        Persistent predictive failure may stale a robust discovered projection, but
        cannot distinguish law change from increased nuisance/noise.
        """
        rec=self.epistemic_projections.records.get(projection_id)
        if rec is None:raise ValueError("UNKNOWN_EPISTEMIC_PROJECTION")
        if not rec.current:raise ValueError("STALE_EPISTEMIC_PROJECTION_CANNOT_ASSESS_CURRENTNESS")
        candidate=None
        for c in self.robust_epistemic_constructor_candidates.values():
            if c.digest()==rec.proposal_candidate_sha256:candidate=c;break
        if candidate is None:raise ValueError("PREDICTIVE_CURRENTNESS_REQUIRES_ROBUST_CONSTRUCTOR_ANCESTRY")
        rows=tuple(ordered_samples)
        for sample in rows:
            if not self.frames.is_current(sample.frame_id,sample.frame_epoch):raise ValueError("STALE_OR_UNKNOWN_CURRENTNESS_SAMPLE_FRAME")
            if candidate.episode_schema_epochs:
                if sample.episode_schema_id is None or sample.episode_schema_epoch is None or not self.episodes.is_current(sample.episode_schema_id,sample.episode_schema_epoch):
                    raise ValueError("STALE_OR_UNKNOWN_CURRENTNESS_SAMPLE_EPISODE_SCHEMA")
        witness=assess_projection_predictive_currentness(projection_id,rec.epoch,candidate,rows,cfg)
        wp=witness.serializable();self.path.append("EPISTEMIC_PROJECTION_PREDICTIVE_CURRENTNESS_ASSESSED",wp);self.store.append("EPISTEMIC_PROJECTION_PREDICTIVE_CURRENTNESS_ASSESSED",wp)
        if witness.status=="DRIFT_WITNESS":
            stale=self.epistemic_projections.invalidate(projection_id);bindings=self.epistemic_contrasts.invalidate_projection(projection_id,stale.epoch)
            stale_deficits=self._stale_epistemic_deficits_for_premise("PROJECTION",projection_id,stale.epoch,"PREDICTIVE_CURRENTNESS_DRIFT")
            packet={"projection_id":projection_id,"old_epoch":rec.epoch,"new_epoch":stale.epoch,"window_accuracies":list(witness.window_accuracies),"drift_window":witness.drift_window,"stale_binding_ids":list(bindings),"stale_deficit_ids":sorted(stale_deficits),"drift_cause_authority":"NONE","regime_identity_authority":"NONE","truth_authority":"NONE"}
            self.path.append("EPISTEMIC_PROJECTION_PREDICTIVE_INVALIDATED",packet);self.store.append("EPISTEMIC_PROJECTION_PREDICTIVE_INVALIDATED",packet)
            wp["projection_current"]=False;wp["new_projection_epoch"]=stale.epoch
        else:
            wp["projection_current"]=True;wp["new_projection_epoch"]=rec.epoch
        return wp

    def assess_epistemic_projection_drift_structure(
        self, projection_id: str, alternative_ticket: RobustConstructorQualificationTicket,
        comparison_samples: Iterable[ConstructorProjectionSample],
        cfg: ProjectionDriftStructureConfig | None = None,
    ) -> dict[str, Any]:
        """Compare one stale robust projection with one externally qualified alternative.

        Positive result means a different opaque predictive structure is supported
        within supplied bounds. It does not identify law-change cause, noise, or a
        recurring regime and does not admit/switch to the alternative automatically.
        """
        rec=self.epistemic_projections.records.get(projection_id)
        if rec is None: raise ValueError("UNKNOWN_EPISTEMIC_PROJECTION")
        if rec.current: raise ValueError("DRIFT_STRUCTURE_ASSESSMENT_REQUIRES_STALE_PROJECTION")
        historical=None
        for c in self.robust_epistemic_constructor_candidates.values():
            if c.digest()==rec.proposal_candidate_sha256: historical=c; break
        if historical is None: raise ValueError("DRIFT_STRUCTURE_ASSESSMENT_REQUIRES_ROBUST_CONSTRUCTOR_ANCESTRY")
        alternative=self.robust_epistemic_constructor_candidates.get(alternative_ticket.candidate_id)
        if alternative is None: raise ValueError("ALTERNATIVE_ROBUST_CONSTRUCTOR_CANDIDATE_NOT_NOMINATED")
        ok,reason=validate_external_robust_constructor_ticket(alternative,alternative_ticket,self.evidence)
        if not ok: raise ValueError(f"INVALID_EXTERNAL_ALTERNATIVE_STRUCTURE_QUALIFICATION:{reason}")
        for frame_id,epoch in rec.frame_epochs:
            if not self.frames.is_current(frame_id,epoch): raise ValueError("STALE_HISTORICAL_PROJECTION_FRAME_BLOCKS_DRIFT_COMPARISON")
        for schema_id,epoch in rec.episode_schema_epochs:
            if not self.episodes.is_current(schema_id,epoch): raise ValueError("STALE_HISTORICAL_PROJECTION_EPISODE_BLOCKS_DRIFT_COMPARISON")
        for frame_id,epoch in alternative.frame_epochs:
            if not self.frames.is_current(frame_id,epoch): raise ValueError("STALE_ALTERNATIVE_STRUCTURE_FRAME")
        for schema_id,epoch in alternative.episode_schema_epochs:
            if not self.episodes.is_current(schema_id,epoch): raise ValueError("STALE_ALTERNATIVE_STRUCTURE_EPISODE")
        rows=tuple(comparison_samples)
        for sample in rows:
            if not self.frames.is_current(sample.frame_id,sample.frame_epoch): raise ValueError("STALE_OR_UNKNOWN_DRIFT_COMPARISON_FRAME")
            if historical.episode_schema_epochs or alternative.episode_schema_epochs:
                if sample.episode_schema_id is None or sample.episode_schema_epoch is None or not self.episodes.is_current(sample.episode_schema_id,sample.episode_schema_epoch):
                    raise ValueError("STALE_OR_UNKNOWN_DRIFT_COMPARISON_EPISODE_SCHEMA")
        witness=assess_projection_drift_structure(projection_id,rec.epoch,historical,alternative,rows,cfg)
        packet=witness.serializable(); packet["alternative_qualifier_id"]=alternative_ticket.qualifier_id
        packet["alternative_qualification_evidence_ids"]=[x.evidence_id for x in alternative_ticket.qualification_evidence]
        self.path.append("EPISTEMIC_PROJECTION_DRIFT_STRUCTURE_ASSESSED",packet); self.store.append("EPISTEMIC_PROJECTION_DRIFT_STRUCTURE_ASSESSED",packet)
        return packet

    def assess_epistemic_projection_recurrence(
        self, projection_id: str, ordered_samples: Iterable[ConstructorProjectionSample],
        cfg: ProjectionRecurrenceConfig | None = None,
    ) -> dict[str, Any]:
        """Test whether one named stale projection's opaque predictive law recurs.

        This is not a global regime search. The caller names the historical
        projection and supplies operational sample order/bounds. A positive witness
        has no reactivation or regime-identity authority and requires fresh external
        requalification before currentness can return.
        """
        rec=self.epistemic_projections.records.get(projection_id)
        if rec is None: raise ValueError("UNKNOWN_EPISTEMIC_PROJECTION")
        if rec.current: raise ValueError("RECURRENCE_ASSESSMENT_REQUIRES_STALE_PROJECTION")
        candidate=None
        for c in self.robust_epistemic_constructor_candidates.values():
            if c.digest()==rec.proposal_candidate_sha256: candidate=c; break
        if candidate is None: raise ValueError("RECURRENCE_ASSESSMENT_REQUIRES_ROBUST_CONSTRUCTOR_ANCESTRY")
        for frame_id,epoch in rec.frame_epochs:
            if not self.frames.is_current(frame_id,epoch): raise ValueError("RECURRENCE_REQUIRES_CURRENT_HISTORICAL_FRAME_ANCESTRY")
        for schema_id,epoch in rec.episode_schema_epochs:
            if not self.episodes.is_current(schema_id,epoch): raise ValueError("RECURRENCE_REQUIRES_CURRENT_HISTORICAL_EPISODE_ANCESTRY")
        rows=tuple(ordered_samples)
        for sample in rows:
            if not self.frames.is_current(sample.frame_id,sample.frame_epoch): raise ValueError("STALE_OR_UNKNOWN_RECURRENCE_SAMPLE_FRAME")
            if candidate.episode_schema_epochs:
                if sample.episode_schema_id is None or sample.episode_schema_epoch is None or not self.episodes.is_current(sample.episode_schema_id,sample.episode_schema_epoch):
                    raise ValueError("STALE_OR_UNKNOWN_RECURRENCE_SAMPLE_EPISODE_SCHEMA")
        witness=assess_projection_recurrence(projection_id,rec.epoch,candidate,rows,cfg)
        self.epistemic_projection_recurrence_witnesses[witness.digest()]=witness
        packet=witness.serializable(); self.path.append("EPISTEMIC_PROJECTION_RECURRENCE_ASSESSED",packet); self.store.append("EPISTEMIC_PROJECTION_RECURRENCE_ASSESSED",packet)
        return packet

    def reactivate_epistemic_projection_from_recurrence(
        self, ticket: ProjectionRecurrenceQualificationTicket,
    ) -> EpistemicProjectionRecord:
        """Consume fresh external recurrence requalification and create a new current epoch."""
        witness=self.epistemic_projection_recurrence_witnesses.get(ticket.recurrence_witness_sha256)
        if witness is None: raise ValueError("RECURRENCE_WITNESS_NOT_FOUND")
        ok,reason=validate_external_projection_recurrence_ticket(witness,ticket,self.evidence)
        if not ok: raise ValueError(f"INVALID_EXTERNAL_RECURRENCE_REQUALIFICATION:{reason}")
        rec=self.epistemic_projections.records.get(ticket.projection_id)
        if rec is None: raise ValueError("UNKNOWN_EPISTEMIC_PROJECTION")
        if rec.current: raise ValueError("CURRENT_EPISTEMIC_PROJECTION_CANNOT_REACTIVATE")
        if rec.epoch!=ticket.stale_projection_epoch: raise ValueError("RECURRENCE_REQUALIFICATION_STALE_EPOCH_DRIFT")
        if rec.proposal_candidate_sha256!=ticket.candidate_sha256: raise ValueError("RECURRENCE_REQUALIFICATION_CANDIDATE_DRIFT")
        for frame_id,epoch in rec.frame_epochs:
            if not self.frames.is_current(frame_id,epoch): raise ValueError("RECURRENCE_REQUALIFICATION_FRAME_DRIFT")
        for schema_id,epoch in rec.episode_schema_epochs:
            if not self.episodes.is_current(schema_id,epoch): raise ValueError("RECURRENCE_REQUALIFICATION_EPISODE_DRIFT")
        qids=tuple(x.evidence_id for x in ticket.qualification_evidence)
        fresh=self.epistemic_projections.reactivate(
            ticket.projection_id, qualification_evidence_ids=qids,
            assistance_ancestry=(
                f"EXTERNAL_RECURRENCE_QUALIFIER:{ticket.qualifier_id}",
                f"RECURRENCE_WITNESS_SHA256:{ticket.recurrence_witness_sha256}",
                "RECURRENCE_REQUALIFICATION_EVIDENCE:"+",".join(qids),
                "NO_RECURRING_REGIME_IDENTITY_AUTHORITY",
            ),
        )
        packet={"record":fresh.serializable(),"recurrence_witness_sha256":ticket.recurrence_witness_sha256,"qualifier_id":ticket.qualifier_id,"qualification_evidence_ids":list(qids),"regime_identity_authority":"NONE","truth_authority":"NONE","contrast_reactivation_authority":"NONE"}
        self.path.append("EPISTEMIC_PROJECTION_REACTIVATED",packet); self.store.append("EPISTEMIC_PROJECTION_REACTIVATED",packet)
        return fresh

    def plan_epistemic_projection_drift_intervention(
        self, projection_id: str, alternative_ticket: RobustConstructorQualificationTicket,
        probes: Iterable[DriftInterventionProbe], cfg: DriftInterventionConfig | None = None,
    ) -> dict[str, Any]:
        """Select one bounded currently executable probe where two qualified predictive structures disagree.

        This does not execute the probe, identify a semantic drift cause, schedule future work,
        or switch the active projection. Probe templates and finite-evidence gates remain supplied ancestry.
        """
        cfg=cfg or DriftInterventionConfig()
        rec=self.epistemic_projections.records.get(projection_id)
        if rec is None: raise ValueError("UNKNOWN_EPISTEMIC_PROJECTION")
        if rec.current: raise ValueError("DRIFT_INTERVENTION_REQUIRES_STALE_PROJECTION")
        historical=None
        for c in self.robust_epistemic_constructor_candidates.values():
            if c.digest()==rec.proposal_candidate_sha256: historical=c; break
        if historical is None: raise ValueError("DRIFT_INTERVENTION_REQUIRES_ROBUST_HISTORICAL_ANCESTRY")
        alternative=self.robust_epistemic_constructor_candidates.get(alternative_ticket.candidate_id)
        if alternative is None: raise ValueError("DRIFT_INTERVENTION_ALTERNATIVE_NOT_NOMINATED")
        ok,reason=validate_external_robust_constructor_ticket(alternative,alternative_ticket,self.evidence)
        if not ok: raise ValueError(f"INVALID_EXTERNAL_DRIFT_INTERVENTION_ALTERNATIVE:{reason}")
        for frame_id,epoch in rec.frame_epochs:
            if not self.frames.is_current(frame_id,epoch): raise ValueError("DRIFT_INTERVENTION_HISTORICAL_FRAME_DRIFT")
        for schema_id,epoch in rec.episode_schema_epochs:
            if not self.episodes.is_current(schema_id,epoch): raise ValueError("DRIFT_INTERVENTION_HISTORICAL_EPISODE_DRIFT")
        for frame_id,epoch in alternative.frame_epochs:
            if not self.frames.is_current(frame_id,epoch): raise ValueError("DRIFT_INTERVENTION_ALTERNATIVE_FRAME_DRIFT")
        for schema_id,epoch in alternative.episode_schema_epochs:
            if not self.episodes.is_current(schema_id,epoch): raise ValueError("DRIFT_INTERVENTION_ALTERNATIVE_EPISODE_DRIFT")
        checked=[]
        for probe in tuple(probes):
            cap=self.capabilities.contracts.get(probe.capability_id)
            cap_current=(
                cap is not None
                and cap.qualification in {QualificationState.QUALIFIED,QualificationState.SHADOW_QUALIFIED}
                and self.capabilities.epochs.get(probe.capability_id,-1)==probe.capability_epoch
            )
            frame_current=self.frames.is_current(probe.frame_id,probe.frame_epoch)
            episode_current=True
            if probe.episode_schema_id is not None:
                episode_current=self.episodes.is_current(probe.episode_schema_id,int(probe.episode_schema_epoch))
            checked.append(replace(probe,current_access=bool(cap_current and frame_current and episode_current)))
        selection=select_drift_discriminating_intervention(
            projection_id,rec.epoch,historical,alternative,checked,cfg
        )
        packet=selection.serializable()
        packet["alternative_qualifier_id"]=alternative_ticket.qualifier_id
        packet["alternative_qualification_evidence_ids"]=[x.evidence_id for x in alternative_ticket.qualification_evidence]
        self.path.append("EPISTEMIC_DRIFT_INTERVENTION_SELECTION",packet); self.store.append("EPISTEMIC_DRIFT_INTERVENTION_SELECTION",packet)
        if selection.status=="PROBE_SELECTED" and selection.plan_id is not None:
            self.epistemic_drift_intervention_plans[selection.plan_id]=selection
            self.path.append("EPISTEMIC_DRIFT_INTERVENTION_PLAN_SELECTED",selection.serializable())
            self.store.append("EPISTEMIC_DRIFT_INTERVENTION_PLAN_SELECTED",selection.serializable())
        return packet

    def record_epistemic_projection_drift_intervention_evidence(
        self, plan_id: str, evidence_id: str,
    ) -> dict[str, Any]:
        """Consume actual content-bound outcome evidence for one selected probe; never auto-answer or switch models."""
        selection=self.epistemic_drift_intervention_plans.get(plan_id)
        if selection is None or selection.probe is None: raise ValueError("UNKNOWN_DRIFT_INTERVENTION_PLAN")
        if any(w.evidence_id==evidence_id for w in self.epistemic_drift_intervention_witnesses.values()):
            raise ValueError("DRIFT_INTERVENTION_EVIDENCE_ALREADY_CONSUMED")
        rec=self.epistemic_projections.records.get(selection.projection_id)
        if rec is None or rec.current or rec.epoch!=selection.stale_projection_epoch:
            raise ValueError("STALE_DRIFT_INTERVENTION_PLAN_PROJECTION_STATE")
        probe=selection.probe
        alternative=None
        for c in self.robust_epistemic_constructor_candidates.values():
            if c.digest()==selection.alternative_candidate_sha256:
                alternative=c; break
        if alternative is None:
            raise ValueError("STALE_DRIFT_INTERVENTION_PLAN_ALTERNATIVE_MISSING")
        for frame_id,epoch in alternative.frame_epochs:
            if not self.frames.is_current(frame_id,epoch): raise ValueError("STALE_DRIFT_INTERVENTION_PLAN_ALTERNATIVE_FRAME")
        for schema_id,epoch in alternative.episode_schema_epochs:
            if not self.episodes.is_current(schema_id,epoch): raise ValueError("STALE_DRIFT_INTERVENTION_PLAN_ALTERNATIVE_EPISODE")
        cap=self.capabilities.contracts.get(probe.capability_id)
        if cap is None or cap.qualification not in {QualificationState.QUALIFIED,QualificationState.SHADOW_QUALIFIED} or self.capabilities.epochs.get(probe.capability_id,-1)!=probe.capability_epoch:
            raise ValueError("STALE_DRIFT_INTERVENTION_PLAN_CAPABILITY")
        if not self.frames.is_current(probe.frame_id,probe.frame_epoch):
            raise ValueError("STALE_DRIFT_INTERVENTION_PLAN_FRAME")
        if probe.episode_schema_id is not None and not self.episodes.is_current(probe.episode_schema_id,int(probe.episode_schema_epoch)):
            raise ValueError("STALE_DRIFT_INTERVENTION_PLAN_EPISODE")
        row=self.evidence.get(evidence_id)
        if row is None: raise ValueError("DRIFT_INTERVENTION_EVIDENCE_NOT_FOUND")
        payload=row.get("payload",{})
        if payload.get("kind")!="DRIFT_INTERVENTION_OUTCOME_BATCH" or payload.get("plan_id")!=plan_id or payload.get("probe_id")!=probe.probe_id:
            raise ValueError("DRIFT_INTERVENTION_EVIDENCE_CONTENT_MISMATCH")
        outcomes=tuple(str(x) for x in payload.get("outcomes",()))
        cfg=DriftInterventionConfig(
            repeats=selection.repeats,min_agreement=selection.min_agreement,min_margin=selection.min_margin,
            max_probe_pool=selection.max_probe_pool,
        )
        witness=assess_drift_intervention_outcomes(selection,outcomes,evidence_id,row["sha256"],cfg)
        self.epistemic_drift_intervention_witnesses[witness.witness_id]=witness
        packet=witness.serializable()
        self.path.append("EPISTEMIC_DRIFT_INTERVENTION_WITNESS_RECORDED",packet); self.store.append("EPISTEMIC_DRIFT_INTERVENTION_WITNESS_RECORDED",packet)
        return packet

    def register_epistemic_projection(
        self, projection_id: str, signature_sha256: str, *,
        assistance_ancestry: Iterable[str] = (),
    ) -> EpistemicProjectionRecord:
        """Register one supplied opaque evidence coordinate; never discover one."""
        rec=EpistemicProjectionRecord(
            projection_id=projection_id,signature_sha256=signature_sha256,epoch=0,
            assistance_ancestry=tuple(assistance_ancestry),
            projection_origin="SUPPLIED_AND_PROVENANCED",
        )
        self.epistemic_projections.register(rec)
        packet=rec.serializable()
        self.path.append("EPISTEMIC_PROJECTION_REGISTERED",packet)
        self.store.append("EPISTEMIC_PROJECTION_REGISTERED",packet)
        return rec

    def change_epistemic_projection(
        self, projection_id: str, *, new_signature_sha256: str, reason: str,
    ) -> dict[str, Any]:
        """Advance supplied projection currentness and stale bound old contrasts."""
        if not reason:
            raise ValueError("EPISTEMIC_PROJECTION_CHANGE_REQUIRES_REASON")
        rec=self.epistemic_projections.change(
            projection_id,new_signature_sha256=new_signature_sha256
        )
        stale=self.epistemic_contrasts.invalidate_projection(projection_id,rec.epoch)
        stale_deficits=self._stale_epistemic_deficits_for_premise("PROJECTION",projection_id,rec.epoch,reason)
        packet={
            "projection_id":projection_id,"signature_sha256":rec.signature_sha256,
            "epoch":rec.epoch,"reason":reason,"stale_binding_ids":list(stale),"stale_deficit_ids":sorted(stale_deficits),
            "semantic_projection_authority":"NONE","raw_projection_discovery_authority":"NONE",
        }
        self.path.append("EPISTEMIC_PROJECTION_CHANGED",packet)
        self.store.append("EPISTEMIC_PROJECTION_CHANGED",packet)
        return packet

    def register_epistemic_contrast(
        self, binding: EpistemicContrastBinding,
    ) -> EpistemicContrastBinding:
        """Admit a supplied content-bound contrast, not a semantic question model."""
        deficit=self.epistemic_deficits.records.get(binding.deficit_id)
        if deficit is None:
            raise ValueError("EPISTEMIC_CONTRAST_DEFICIT_NOT_FOUND")
        if deficit.state == EpistemicDeficitState.STALE:
            raise ValueError("STALE_EPISTEMIC_DEFICIT_CANNOT_ACCEPT_CONTRAST")
        if deficit.hypothesis_digest_sha256 != binding.hypothesis_digest_sha256:
            raise ValueError("EPISTEMIC_CONTRAST_HYPOTHESIS_DIGEST_MISMATCH")
        self.epistemic_contrasts.register(binding)
        packet=binding.serializable()
        self.path.append("EPISTEMIC_CONTRAST_REGISTERED",packet)
        self.store.append("EPISTEMIC_CONTRAST_REGISTERED",packet)
        return binding

    def assess_epistemic_evidence_bearing(
        self, deficit_id: str, binding_id: str, evidence_id: str,
    ) -> dict[str, Any]:
        """Verify bounded bearing from content already carrying an opaque projection.

        The evidence producer must supply `epistemic_projection` metadata inside
        the content-bound ledger payload. Main-Dev does not infer that projection
        from raw data; that missing formation/discovery mechanism is the MS1202
        frontier. This method only verifies the relation against a current supplied
        contrast and, when warranted, requests revisit with zero answer authority.
        """
        deficit=self.epistemic_deficits.records.get(deficit_id)
        if deficit is None:
            raise ValueError("EPISTEMIC_DEFICIT_NOT_FOUND")
        if deficit.state == EpistemicDeficitState.STALE:
            raise ValueError("STALE_EPISTEMIC_DEFICIT_CANNOT_ASSESS_BEARING")
        binding=self.epistemic_contrasts.bindings.get(binding_id)
        if binding is None or binding.deficit_id != deficit_id:
            raise ValueError("EPISTEMIC_CONTRAST_BINDING_MISMATCH")
        ev=self.evidence.get(evidence_id)
        if ev is None:
            raise ValueError("EPISTEMIC_BEARING_EVIDENCE_NOT_FOUND")
        meta=ev.get("payload",{}).get("epistemic_projection")
        if not isinstance(meta,dict):
            raise ValueError("OPAQUE_EPISTEMIC_PROJECTION_METADATA_REQUIRED")
        required=("projection_id","projection_epoch","outcome_digest_sha256")
        if any(k not in meta for k in required):
            raise ValueError("INCOMPLETE_OPAQUE_EPISTEMIC_PROJECTION_METADATA")
        kind,witness,duplicate=self.epistemic_contrasts.assess(
            binding_id=binding_id,
            current_hypothesis_digest_sha256=deficit.hypothesis_digest_sha256,
            evidence_id=evidence_id,evidence_sha256=ev["sha256"],
            projection_id=str(meta["projection_id"]),projection_epoch=int(meta["projection_epoch"]),
            outcome_digest_sha256=str(meta["outcome_digest_sha256"]),
            condition_signature_sha256=meta.get("condition_signature_sha256"),
        )
        packet={
            "deficit_id":deficit_id,"binding_id":binding_id,"evidence_id":evidence_id,
            "bearing_kind":kind.value,"bearing":witness is not None or duplicate,
            "duplicate":bool(duplicate),"truth_authority":"NONE","answer_authority":"NONE",
            "semantic_question_authority":"NONE","raw_projection_discovery_authority":"NONE",
        }
        if witness is not None:
            wp=witness.serializable()
            self.path.append("EPISTEMIC_BEARING_WITNESS_RECORDED",wp)
            self.store.append("EPISTEMIC_BEARING_WITNESS_RECORDED",wp)
            rec=self.epistemic_deficits.request_revisit(deficit_id,evidence_id)
            rp={
                "deficit_id":deficit_id,"evidence_id":evidence_id,
                "relevance_basis_sha256":witness.binding_signature_sha256,
                "bearing_witness_id":witness.witness_id,"bearing_kind":kind.value,
                "state":rec.state.value,"relevance_authority":"VERIFIED_BOUNDED_OPERATIONAL_BEARING_ONLY",
                "truth_authority":"NONE","semantic_question_authority":"NONE",
            }
            self.path.append("EPISTEMIC_DEFICIT_REVISIT_REQUESTED",rp)
            self.store.append("EPISTEMIC_DEFICIT_REVISIT_REQUESTED",rp)
            packet["witness_id"]=witness.witness_id
            packet["state"]=rec.state.value
        else:
            packet["witness_id"]=None
            packet["state"]=deficit.state.value
        return packet

    def epistemic_contrast_status(self, binding_id: str) -> dict[str, Any]:
        return self.epistemic_contrasts.binding_status(binding_id)

    def epistemic_bearing_witnesses(self, deficit_id: str) -> tuple[dict[str, Any], ...]:
        return tuple(w.serializable() for w in self.epistemic_contrasts.witnesses_for_deficit(deficit_id))

    def stale_epistemic_deficit(
        self, deficit_id: str, *, reason: str, evidence_id: str | None = None,
    ) -> dict[str, Any]:
        """Explicitly stale a superseded bounded hypothesis/question premise."""
        if evidence_id is not None and self.evidence.get(evidence_id) is None:
            raise ValueError("STALE_EVIDENCE_NOT_FOUND")
        rec=self.epistemic_deficits.mark_stale(deficit_id,reason=reason,evidence_id=evidence_id)
        self.epistemic_contrasts.invalidate_deficit(deficit_id,reason=reason)
        packet={"deficit_id":deficit_id,"reason":reason,"evidence_id":evidence_id,"state":rec.state.value}
        self.path.append("EPISTEMIC_DEFICIT_STALE",packet); self.store.append("EPISTEMIC_DEFICIT_STALE",packet)
        return rec.serializable()

    def epistemic_development_pressure_ids(self) -> tuple[str, ...]:
        """Return currently eligible ACTION_LIMITED deficits; no priority ordering."""
        return self.epistemic_deficits.development_pressure_ids()

    def epistemic_revisit_required_ids(self) -> tuple[str, ...]:
        """Return deficits requiring revisit; do not execute or adjudicate them."""
        return self.epistemic_deficits.revisit_required_ids()

    def epistemic_deficit_status(self, deficit_id: str) -> dict[str, Any]:
        return self.epistemic_deficits.records[deficit_id].serializable()

    def _stale_epistemic_deficits_for_premise(
        self, kind: str, object_id: str, epoch: int, reason: str, *, force: bool = False,
    ) -> set[str]:
        changed=self.epistemic_deficits.invalidate_premise(kind,object_id,epoch,reason=reason,force=force)
        for deficit_id in changed:
            self.epistemic_contrasts.invalidate_deficit(deficit_id,reason=f"PREMISE_DRIFT:{kind}:{object_id}@{epoch}:{reason}")
        if changed:
            packet={
                "premise_kind":kind,"object_id":object_id,"new_epoch":int(epoch),
                "reason":reason,"force":bool(force),"deficit_ids":sorted(changed),
            }
            self.path.append("EPISTEMIC_DEFICIT_PREMISE_INVALIDATED",packet)
            self.store.append("EPISTEMIC_DEFICIT_PREMISE_INVALIDATED",packet)
        return changed

    def record_operational_trace(self, trace: OperationalTrace) -> OperationalTrace:
        """Record one operational trace with entity-captured dependency epochs.

        Legacy traces may still use the explicitly supplied MS853-877 action/effect
        frame. A frame-bound trace must reference a currently qualified operational
        frame; the entity captures that frame epoch so later drift cannot silently
        keep the trace current. Higher-level grouping of action events into this
        OperationalTrace may now be bound to an externally qualified episode
        schema whose epoch is captured. The entity still does not generally
        construct or self-qualify that grouping relation.
        """
        if not trace.trace_id or trace.trace_id in self.operational_traces:
            raise ValueError("duplicate/empty trace_id")
        if not trace.steps or len(trace.steps) != len(trace.step_effects):
            raise ValueError("trace steps/effects must be nonempty and aligned")
        dims = {len(v) for v in trace.step_effects}
        if len(dims) != 1 or 0 in dims:
            raise ValueError("effect coordinates must have one nonzero dimensionality")
        if any(not math.isfinite(float(x)) for v in trace.step_effects for x in v):
            raise ValueError("effect coordinates must be finite")
        frame_epoch = None
        if trace.frame_id is not None:
            if not self.frames.is_current(trace.frame_id):
                raise ValueError(f"unknown/stale operational frame:{trace.frame_id}")
            frame_epoch = self.frames.epochs[trace.frame_id]
        elif trace.frame_epoch is not None:
            raise ValueError("frame_epoch cannot exist without frame_id")
        episode_schema_epoch = None
        if trace.episode_schema_id is not None:
            if not self.episodes.is_current(trace.episode_schema_id):
                raise ValueError(f"unknown/stale episode schema:{trace.episode_schema_id}")
            episode_schema_epoch = self.episodes.epochs[trace.episode_schema_id]
        elif trace.episode_schema_epoch is not None:
            raise ValueError("episode_schema_epoch cannot exist without episode_schema_id")

        topology_ids = tuple(sorted(dict.fromkeys(trace.topology_ids)))
        topology_epochs: list[tuple[str, int]] = []
        trace_step_set = set(trace.steps)
        for topology_id in topology_ids:
            if not self.topologies.is_current(topology_id):
                raise ValueError(f"unknown/stale recruitment topology:{topology_id}")
            topology_contract = self.topologies.topologies[topology_id]
            if not any(a in trace_step_set and b in trace_step_set for a, b in topology_contract.relations):
                raise ValueError(f"TRACE_TOPOLOGY_NOT_BOUND_TO_STEPS:{topology_id}")
            topology_epochs.append((topology_id, self.topologies.epochs[topology_id]))

        coordination_ids = tuple(sorted(dict.fromkeys(trace.coordination_ids)))
        coordination_epochs: list[tuple[str, int]] = []
        inherited_counterparty_ids: set[str] = set()
        for coordination_id in coordination_ids:
            if not self.coordinations.is_current(coordination_id):
                raise ValueError(f"unknown/stale operational coordination:{coordination_id}")
            coordination_epochs.append((coordination_id, self.coordinations.epochs[coordination_id]))
            contract = self.coordinations.contracts[coordination_id]
            inherited_counterparty_ids.update(cid for cid, _ in contract.participant_counterparty_epochs)

        counterparty_ids = tuple(sorted(set(trace.counterparty_ids) | inherited_counterparty_ids))
        counterparty_epochs: list[tuple[str, int]] = []
        for counterparty_id in counterparty_ids:
            if not self.counterparties.is_current(counterparty_id):
                raise ValueError(f"unknown/stale operational counterparty:{counterparty_id}")
            counterparty_epochs.append((counterparty_id, self.counterparties.epochs[counterparty_id]))

        epochs: list[tuple[str, int]] = []
        for cid in dict.fromkeys(trace.steps):
            contract = self.capabilities.contracts.get(cid)
            if contract is None:
                raise ValueError(f"unknown trace capability:{cid}")
            if contract.qualification not in {QualificationState.QUALIFIED, QualificationState.SHADOW_QUALIFIED}:
                raise ValueError(f"noncurrent trace capability:{cid}:{contract.qualification.value}")
            epochs.append((cid, self.capabilities.epochs.get(cid, 0)))
        bound = replace(
            trace,
            dependency_epochs=tuple(epochs),
            frame_epoch=frame_epoch,
            episode_schema_epoch=episode_schema_epoch,
            topology_ids=topology_ids,
            topology_epochs=tuple(topology_epochs),
            counterparty_ids=counterparty_ids,
            counterparty_epochs=tuple(counterparty_epochs),
            coordination_ids=coordination_ids,
            coordination_epochs=tuple(coordination_epochs),
        )
        self.operational_traces[bound.trace_id] = bound
        packet = bound.serializable()
        self.path.append("CAPABILITY_TRACE", packet)
        self.store.append("CAPABILITY_TRACE", packet)
        return bound

    def derive_multi_value_action_licenses(
        self,
        value_ids: Iterable[str],
        *,
        config: DiscoveryConfig | None = None,
    ) -> dict[str, Any]:
        """Expose a transient multi-pressure license from already-earned parts.

        The entity owns only the wiring boundary: current registries supply the
        ancestry-qualified effect evidence and current value snapshot. Stateless
        premise projection/composition lives in the developmental adapter.
        """
        requested = tuple(str(value_id) for value_id in value_ids)
        if not requested or len(set(requested)) != len(requested):
            return {
                "status": "UNKNOWN_INCOMPLETE",
                "reason": "INVALID_OR_DUPLICATE_VALUE_PREMISES",
                "authority": Authority.NONE.value,
                "execution_authority": Authority.NONE.value,
            }

        if any(not self.values.is_current(value_id) for value_id in requested):
            return {
                "status": "UNKNOWN_INCOMPLETE",
                "reason": "VALUE_PREMISE_NOT_CURRENT",
                "authority": Authority.NONE.value,
                "execution_authority": Authority.NONE.value,
            }

        episode_bindings: dict[tuple[str, int], tuple[str, int]] = {}
        for schema_id, schema in self.episodes.schemas.items():
            epoch = self.episodes.epochs.get(schema_id)
            if epoch is None or not self.episodes.is_current(schema_id, epoch):
                continue
            if len(schema.value_epochs) != 1:
                continue
            value_id, value_epoch = schema.value_epochs[0]
            if self.values.is_current(value_id, value_epoch):
                episode_bindings[(schema_id, epoch)] = (value_id, value_epoch)

        current_capability_ids = {
            capability_id
            for capability_id, contract in self.capabilities.contracts.items()
            if contract.qualification in {
                QualificationState.QUALIFIED,
                QualificationState.SHADOW_QUALIFIED,
            }
        }
        effects = derive_value_bound_singleton_effects(
            self.operational_traces.values(),
            dict(self.capabilities.epochs),
            episode_bindings,
            dict(self.values.epochs),
            config or DiscoveryConfig(),
            current_capability_ids=current_capability_ids,
            current_frame_epochs=dict(self.frames.epochs),
            current_episode_schema_epochs=dict(self.episodes.epochs),
            current_topology_epochs=dict(self.topologies.epochs),
            current_counterparty_epochs=dict(self.counterparties.epochs),
            current_coordination_epochs=dict(self.coordinations.epochs),
        )

        current_values: dict[str, dict[str, Any]] = {}
        for value_id in requested:
            pressure = self.values.pressure(value_id)
            latest = self.values.latest.get(value_id)
            if pressure.get("status") != "CURRENT" or latest is None:
                continue
            current_values[value_id] = {
                "value": float(latest[1]),
                "pressure_magnitude": float(pressure["pressure_magnitude"]),
                "epoch": int(self.values.epochs[value_id]),
                "contract": self.values.contracts[value_id],
            }

        result = compose_multi_value_action_licenses(
            requested,
            effects,
            current_values,
            current_capability_ids,
        )
        result["effect_witnesses"] = {
            f"{capability_id}::{value_id}": {
                **row,
                "source_trace_ids": list(row.get("source_trace_ids", ())),
                "assistance_ancestry": list(row.get("assistance_ancestry", ())),
            }
            for (capability_id, value_id), row in effects.items()
        }
        result["effect_coordinate_mapping_ancestry"] = (
            "CURRENT_SINGLE_VALUE_EPISODE_BINDING"
        )
        return result

    def discover_capability_candidates(
        self,
        config: DiscoveryConfig | None = None,
    ) -> list[dict[str, Any]]:
        """Nominate bounded candidate compositions from the entity's own traces.

        This method may create proposals only. It cannot issue qualification
        tickets and it writes its own inference as UNKNOWN_INCOMPLETE proposal
        evidence so the fixed qualifier cannot mistake self-generated nomination
        evidence for external support.
        """
        cfg = config or DiscoveryConfig()
        findings = discover_candidates(
            self.operational_traces.values(),
            dict(self.capabilities.epochs),
            cfg,
            current_frame_epochs=dict(self.frames.epochs),
            current_episode_schema_epochs=dict(self.episodes.epochs),
            current_topology_epochs=dict(self.topologies.epochs),
            current_counterparty_epochs=dict(self.counterparties.epochs),
            current_coordination_epochs=dict(self.coordinations.epochs),
        )
        out: list[dict[str, Any]] = []
        for finding in findings:
            cid = "cand-" + finding.candidate_key()[:20]
            if cid in self.capability_candidates or cid in self.capabilities.contracts:
                continue
            payload = finding.structural_payload() | {
                "source_trace_ids": list(finding.source_trace_ids),
                "proposal_only": True,
            }
            ev = self.append_evidence(
                f"DISCOVERY-{cid}",
                payload,
                EpistemicStatus.UNKNOWN_INCOMPLETE,
                source="MICROSEED_ENDOGENOUS_PROPOSAL_GENERATOR",
            )
            assistance = list(cfg.assistance_ancestry())
            if finding.frame_epochs:
                # The effect/action frame is a qualified developmental dependency
                # rather than anonymous supplied coordinates.
                assistance = [
                    x for x in assistance
                    if x not in {"SUPPLIED_EFFECT_COORDINATES", "STABLE_CAPABILITY_HANDLE_IDENTITY"}
                ]
                assistance.extend(
                    f"QUALIFIED_OPERATIONAL_FRAME:{fid}@{epoch}"
                    for fid, epoch in finding.frame_epochs
                )
            if finding.episode_schema_epochs:
                # MS903-927 warrants replacing anonymous supplied trace grouping
                # only when an externally qualified episode schema is explicitly
                # bound. It still does not make Microseed the truth authority for
                # how that schema was constructed.
                assistance = [
                    x for x in assistance
                    if x not in {"SUPPLIED_TRACE_BOUNDARIES", "SUPPLIED_HIGHER_LEVEL_OPERATIONAL_TRACE_GROUPING"}
                ]
                assistance.extend(
                    f"QUALIFIED_OPERATIONAL_EPISODE_SCHEMA:{sid}@{epoch}"
                    for sid, epoch in finding.episode_schema_epochs
                )
            elif finding.frame_epochs:
                assistance.append("SUPPLIED_HIGHER_LEVEL_OPERATIONAL_TRACE_GROUPING")
            assistance = tuple(dict.fromkeys(assistance))
            invariants = ["PROPOSAL_NOT_AUTHORITY", "DEPENDENCY_EPOCH_BOUND"]
            hazards = ["EFFECT_FRAME_ASSISTANCE", "FALSE_PROPOSAL_LOAD"]
            lineage = ["MS853-877-ENDOGENOUS-NOMINATION"]
            if finding.episode_schema_epochs:
                invariants.append("EPISODE_SCHEMA_EPOCH_BOUND")
                lineage.append("MS903-927-EPISODE-SCHEMA-LIFECYCLE")
            else:
                hazards.append("TRACE_BOUNDARY_ASSISTANCE")
            if finding.topology_epochs:
                invariants.append("RECRUITMENT_TOPOLOGY_EPOCH_BOUND")
                lineage.append("MS978-1027-RECRUITMENT-TOPOLOGY-CURRENTNESS")
            if finding.counterparty_epochs:
                invariants.append("COUNTERPARTY_EPOCH_BOUND")
                lineage.append("MS1053-1077-COUNTERPARTY-CURRENTNESS")
            if finding.coordination_epochs:
                invariants.append("COORDINATION_EPOCH_BOUND")
                lineage.append("MS1078-1102-COORDINATION-CURRENTNESS")
            if finding.topology_epochs or finding.counterparty_epochs or finding.coordination_epochs:
                lineage.append("MS1478-1502-COMPOSITION-ANCESTRY-PRESERVATION")
            contract = CapabilityContract(
                capability_id=cid,
                purpose="opaque-discovered-operational-composite",
                boundary={"kind": "OPERATIONAL_TRACE_MOTIF"},
                interface={
                    "ordered_dependency_sequence": list(finding.motif),
                    "effect_residual_signature": list(finding.residual),
                },
                invariants=tuple(invariants),
                hazards=tuple(hazards),
                authority=Authority.DERIVED_READ_ONLY,
                lineage=tuple(lineage),
                currentness="CANDIDATE",
                resources={"discovery_score": finding.score, "support": finding.support},
                dependencies=tuple(dict.fromkeys(finding.motif)),
                qualification=QualificationState.CANDIDATE,
                assistance_ancestry=assistance,
                operational_scope_id=finding.operational_scope_id,
            )
            candidate = CapabilityCandidate(
                candidate_id=cid,
                proposed_contract=contract,
                evidence=(ev,),
                assistance_ancestry=assistance,
                nomination_basis="ENDOGENOUS_OPERATIONAL_RESIDUAL_RECURRENCE_V0_1",
                source_trace_ids=finding.source_trace_ids,
                operational_signature={
                    "residual": list(finding.residual),
                    "support": finding.support,
                    "consistency": finding.consistency,
                    "dependency_epochs": [list(x) for x in finding.dependency_epochs],
                    "frame_epochs": [list(x) for x in finding.frame_epochs],
                    "episode_schema_epochs": [list(x) for x in finding.episode_schema_epochs],
                    "topology_epochs": [list(x) for x in finding.topology_epochs],
                    "counterparty_epochs": [list(x) for x in finding.counterparty_epochs],
                    "coordination_epochs": [list(x) for x in finding.coordination_epochs],
                    "operational_scope_id": finding.operational_scope_id,
                },
            )
            digest = self.nominate_capability_candidate(candidate)
            out.append({
                "candidate_id": cid,
                "candidate_sha256": digest,
                "score": finding.score,
                "support": finding.support,
                "operational_scope_id": finding.operational_scope_id,
                "authority": "NONE_PROPOSAL_ONLY",
            })
        return out

    def register_operational_frame(
        self,
        frame: OperationalFrameContract,
        *,
        evidence: Iterable = (),
        notes: Iterable[str] = (),
    ) -> None:
        """Register an already externally-qualified operational frame.

        This is not frame learning or self-qualification. It gives Main-Dev/HSP
        evidence a first-class currentness object that downstream traces and
        capabilities can depend on.
        """
        self.frames.register(frame)
        ev = tuple(evidence)
        self.development.nominate(DevelopmentRecord(
            artifact_id=frame.frame_id,
            kind="OPERATIONAL_FRAME_CONTRACT",
            lineage=tuple(frame.lineage),
            assistance_ancestry=tuple(frame.assistance_ancestry),
            dependencies=(),
            qualification=frame.qualification,
            authority=frame.authority,
            evidence=ev,
            notes=tuple(notes) + (
                f"FRAME_SIGNATURE_SHA256:{frame.signature_sha256}",
                "NO_SEMANTIC_IDENTITY_AUTHORITY",
            ),
        ))
        packet = {
            "frame_id": frame.frame_id,
            "frame_epoch": self.frames.epochs[frame.frame_id],
            "qualification": frame.qualification.value,
            "signature_sha256": frame.signature_sha256,
            "assistance_ancestry": list(frame.assistance_ancestry),
        }
        self.path.append("OPERATIONAL_FRAME_REGISTERED", packet)
        self.store.append("OPERATIONAL_FRAME_REGISTERED", packet)

    def register_value_variable(
        self,
        contract: ValueVariableContract,
        *,
        evidence: Iterable = (),
        notes: Iterable[str] = (),
    ) -> None:
        """Register an already externally-qualified constitutional value variable.

        The handle and viable interval remain explicit supplied constitutional
        ancestry. Registration does not let Microseed invent or rewrite what
        should matter; it makes bounded regulatory pressure/currentness explicit.
        """
        self.values.register(contract)
        ev = tuple(evidence)
        self.development.nominate(DevelopmentRecord(
            artifact_id=contract.value_id,
            kind="CONSTITUTIONAL_VALUE_VARIABLE_CONTRACT",
            lineage=tuple(contract.lineage),
            assistance_ancestry=tuple(contract.assistance_ancestry),
            dependencies=(),
            qualification=contract.qualification,
            authority=contract.authority,
            evidence=ev,
            notes=tuple(notes) + (
                f"VALUE_SIGNATURE_SHA256:{contract.signature_sha256}",
                f"VIABLE_INTERVAL:{contract.viable_low}:{contract.viable_high}",
                "CONSTITUTIONAL_PRIOR_NOT_LEARNED_WORLD_ONTOLOGY",
                "NO_SEMANTIC_GOAL_OR_REWARD_AUTHORITY",
            ),
        ))
        packet = {
            "value_id": contract.value_id,
            "value_epoch": self.values.epochs[contract.value_id],
            "qualification": contract.qualification.value,
            "signature_sha256": contract.signature_sha256,
            "viable_interval": [contract.viable_low, contract.viable_high],
            "assistance_ancestry": list(contract.assistance_ancestry),
        }
        self.path.append("VALUE_VARIABLE_REGISTERED", packet)
        self.store.append("VALUE_VARIABLE_REGISTERED", packet)

    def observe_value_state(self, value_id: str, value: float) -> dict[str, Any]:
        """Update one current opaque regulatory variable and derive no policy."""
        packet = self.values.observe(value_id, value)
        if packet.get("status") == "CURRENT":
            self.path.append("VALUE_STATE_OBSERVED", packet)
            self.store.append("VALUE_STATE_OBSERVED", packet)
        return packet

    def value_pressure(self, value_id: str) -> dict[str, Any]:
        """Derive signed regulatory pressure; never semantic goal authority."""
        return self.values.pressure(value_id)

    def change_value_variable(self, value_id: str, *, reason: str) -> set[str]:
        """Stale a changed constitutional value contract and dependent closure."""
        direct_caps = set(self.values.capability_dependents.get(value_id, ()))
        episode_schemas = set(self.values.episode_dependents.get(value_id, ()))
        self.values.change(value_id, reason=reason)
        if value_id in self.development.records:
            self.development.invalidate(value_id, reason)
        stale_caps: set[str] = set()
        for schema_id in sorted(episode_schemas):
            if self.episodes.is_current(schema_id):
                stale_caps |= self.change_episode_schema(
                    schema_id, reason=f"VALUE:{value_id}:{reason}"
                )
        for cid in sorted(direct_caps):
            if cid in self.capabilities.contracts:
                stale_caps |= self.capabilities.invalidate(
                    cid, reason=f"VALUE:{value_id}:{reason}"
                )
        return stale_caps

    def _on_value_invalidated(self, value_id: str, epoch: int, reason: str) -> None:
        packet = {
            "value_id": value_id,
            "new_epoch": epoch,
            "reason": reason,
            "direct_capability_dependents": sorted(
                self.values.capability_dependents.get(value_id, ())
            ),
            "episode_dependents": sorted(
                self.values.episode_dependents.get(value_id, ())
            ),
        }
        self.path.append("VALUE_VARIABLE_INVALIDATED", packet)
        self.store.append("VALUE_VARIABLE_INVALIDATED", packet)
        self._stale_epistemic_deficits_for_premise("VALUE",value_id,epoch,reason)

    def register_episode_schema(
        self,
        schema: EpisodeSchemaContract,
        *,
        evidence: Iterable = (),
        notes: Iterable[str] = (),
    ) -> None:
        """Register an externally qualified operational episode/grouping schema.

        Registration creates currentness/provenance plumbing only. It does not
        claim general endogenous episode construction or semantic episode identity.
        """
        for frame_id, epoch in schema.frame_epochs:
            if not self.frames.is_current(frame_id, epoch):
                raise ValueError(f"EPISODE_SCHEMA_FRAME_EPOCH_DRIFT:{frame_id}")
        for value_id, epoch in schema.value_epochs:
            if not self.values.is_current(value_id, epoch):
                raise ValueError(f"EPISODE_SCHEMA_VALUE_EPOCH_DRIFT:{value_id}")
        for counterparty_id, epoch in schema.counterparty_epochs:
            if not self.counterparties.is_current(counterparty_id, epoch):
                raise ValueError(f"EPISODE_SCHEMA_COUNTERPARTY_EPOCH_DRIFT:{counterparty_id}")
        for coordination_id, epoch in schema.coordination_epochs:
            if not self.coordinations.is_current(coordination_id, epoch):
                raise ValueError(f"EPISODE_SCHEMA_COORDINATION_EPOCH_DRIFT:{coordination_id}")
        self.episodes.register(schema)
        for value_id, _ in schema.value_epochs:
            self.values.bind_episode(value_id, schema.schema_id)
        ev = tuple(evidence)
        self.development.nominate(DevelopmentRecord(
            artifact_id=schema.schema_id,
            kind="OPERATIONAL_EPISODE_SCHEMA_CONTRACT",
            lineage=tuple(schema.lineage),
            assistance_ancestry=tuple(schema.assistance_ancestry),
            dependencies=(
                tuple(fid for fid, _ in schema.frame_epochs)
                + tuple(vid for vid, _ in schema.value_epochs)
                + tuple(cid for cid, _ in schema.counterparty_epochs)
                + tuple(rid for rid, _ in schema.coordination_epochs)
            ),
            qualification=schema.qualification,
            authority=schema.authority,
            evidence=ev,
            notes=tuple(notes) + (
                f"EPISODE_SCHEMA_SIGNATURE_SHA256:{schema.signature_sha256}",
                "NO_SEMANTIC_EPISODE_OR_IDENTITY_AUTHORITY",
                "FRAME_DEPENDENCIES:" + ",".join(f"{fid}@{epoch}" for fid, epoch in schema.frame_epochs),
                "VALUE_DEPENDENCIES:" + ",".join(f"{vid}@{epoch}" for vid, epoch in schema.value_epochs),
                "COUNTERPARTY_DEPENDENCIES:" + ",".join(f"{cid}@{epoch}" for cid, epoch in schema.counterparty_epochs),
                "COORDINATION_DEPENDENCIES:" + ",".join(f"{rid}@{epoch}" for rid, epoch in schema.coordination_epochs),
                "NO_SEMANTIC_JOINT_GOAL_AUTHORITY",
            ),
        ))
        packet = {
            "schema_id": schema.schema_id,
            "schema_epoch": self.episodes.epochs[schema.schema_id],
            "qualification": schema.qualification.value,
            "signature_sha256": schema.signature_sha256,
            "frame_dependencies": [list(x) for x in schema.frame_epochs],
            "value_dependencies": [list(x) for x in schema.value_epochs],
            "counterparty_dependencies": [list(x) for x in schema.counterparty_epochs],
            "coordination_dependencies": [list(x) for x in schema.coordination_epochs],
            "assistance_ancestry": list(schema.assistance_ancestry),
        }
        self.path.append("OPERATIONAL_EPISODE_SCHEMA_REGISTERED", packet)
        self.store.append("OPERATIONAL_EPISODE_SCHEMA_REGISTERED", packet)

    def change_episode_schema(self, schema_id: str, *, reason: str) -> set[str]:
        """Stale a materially changed episode schema and its capability closure."""
        direct = set(self.episodes.capability_dependents.get(schema_id, ()))
        self.episodes.change(schema_id, reason=reason)
        if schema_id in self.development.records:
            self.development.invalidate(schema_id, reason)
        stale_caps: set[str] = set()
        for cid in sorted(direct):
            if cid in self.capabilities.contracts:
                stale_caps |= self.capabilities.invalidate(
                    cid, reason=f"EPISODE_SCHEMA:{schema_id}:{reason}"
                )
        return stale_caps

    def _on_episode_schema_invalidated(self, schema_id: str, epoch: int, reason: str) -> None:
        packet = {
            "schema_id": schema_id,
            "new_epoch": epoch,
            "reason": reason,
            "direct_capability_dependents": sorted(
                self.episodes.capability_dependents.get(schema_id, ())
            ),
        }
        self.path.append("OPERATIONAL_EPISODE_SCHEMA_INVALIDATED", packet)
        self.store.append("OPERATIONAL_EPISODE_SCHEMA_INVALIDATED", packet)
        self._stale_epistemic_deficits_for_premise("EPISODE",schema_id,epoch,reason)
        self._invalidate_epistemic_projection_dependency("EPISODE",schema_id,reason)

    def _stale_episode_schema_dependents_after_external_premise_change(
        self, schema_ids: Iterable[str], *, reason: str
    ) -> set[str]:
        """Synchronize already-staled episode metadata into developmental/capability closure."""
        stale_caps: set[str] = set()
        for schema_id in sorted(set(schema_ids)):
            if schema_id in self.development.records and self.development.records[schema_id].qualification != QualificationState.STALE:
                self.development.invalidate(schema_id, reason)
            for cid in sorted(self.episodes.capability_dependents.get(schema_id, ())):
                if cid in self.capabilities.contracts:
                    stale_caps |= self.capabilities.invalidate(
                        cid, reason=f"EPISODE_SCHEMA:{schema_id}:{reason}"
                    )
        return stale_caps

    def _invalidate_epistemic_projection_dependency(self, kind: str, object_id: str, reason: str) -> tuple[str, ...]:
        changed=self.epistemic_projections.invalidate_dependency(kind,object_id)
        stale_bindings=[]
        stale_deficits=[]
        for pid in changed:
            rec=self.epistemic_projections.records[pid]
            stale_bindings.extend(self.epistemic_contrasts.invalidate_projection(pid,rec.epoch))
            stale_deficits.extend(self._stale_epistemic_deficits_for_premise("PROJECTION",pid,rec.epoch,f"DEPENDENCY:{kind}:{object_id}:{reason}"))
        if changed:
            packet={"premise_kind":str(kind).upper(),"object_id":str(object_id),"reason":str(reason),
                    "projection_ids":list(changed),"stale_binding_ids":sorted(set(stale_bindings)),"stale_deficit_ids":sorted(set(stale_deficits)),
                    "truth_authority":"NONE"}
            self.path.append("EPISTEMIC_PROJECTION_DEPENDENCY_INVALIDATED",packet)
            self.store.append("EPISTEMIC_PROJECTION_DEPENDENCY_INVALIDATED",packet)
        return changed

    def change_operational_frame(self, frame_id: str, *, reason: str) -> set[str]:
        """Stale a materially changed operational frame and its capability closure."""
        direct = set(self.frames.capability_dependents.get(frame_id, ()))
        self.frames.change(frame_id, reason=reason)
        episode_schemas = self.episodes.invalidate_by_frame(frame_id, reason=reason)
        # Invalidate the developmental frame node first. Its dependency closure may
        # already include admitted frame-bound capabilities. Capability invalidation
        # below then synchronizes executable metadata without duplicating the same
        # developmental stale transition through the callback path.
        if frame_id in self.development.records:
            self.development.invalidate(frame_id, reason)
        for schema_id in episode_schemas:
            if schema_id in self.development.records:
                self.development.invalidate(schema_id, f"FRAME:{frame_id}:{reason}")
        stale_caps: set[str] = set()
        for schema_id in sorted(episode_schemas):
            for cid in sorted(self.episodes.capability_dependents.get(schema_id, ())):
                if cid in self.capabilities.contracts:
                    stale_caps |= self.capabilities.invalidate(
                        cid, reason=f"EPISODE_SCHEMA:{schema_id}:FRAME:{frame_id}:{reason}"
                    )
        for cid in sorted(direct):
            if cid in self.capabilities.contracts:
                stale_caps |= self.capabilities.invalidate(
                    cid, reason=f"FRAME:{frame_id}:{reason}"
                )
        return stale_caps

    def _on_frame_invalidated(self, frame_id: str, epoch: int, reason: str) -> None:
        packet = {
            "frame_id": frame_id,
            "new_epoch": epoch,
            "reason": reason,
            "direct_capability_dependents": sorted(
                self.frames.capability_dependents.get(frame_id, ())
            ),
        }
        self.path.append("OPERATIONAL_FRAME_INVALIDATED", packet)
        self.store.append("OPERATIONAL_FRAME_INVALIDATED", packet)
        self._stale_epistemic_deficits_for_premise("FRAME",frame_id,epoch,reason)
        self._invalidate_epistemic_projection_dependency("FRAME",frame_id,reason)

    def register_recruitment_topology(
        self,
        contract: RecruitmentTopologyContract,
        *,
        evidence: Iterable = (),
        notes: Iterable[str] = (),
    ) -> None:
        """Register an already externally-qualified opaque recruitment topology.

        This is currentness/provenance plumbing only. The entity does not run the
        MS1003-1027 pairwise constructor and gains no semantic role or identity
        authority from the graph shape.
        """
        for cid, epoch in contract.capability_epochs:
            c=self.capabilities.contracts.get(cid)
            if c is None or c.qualification not in {QualificationState.QUALIFIED, QualificationState.SHADOW_QUALIFIED}:
                raise ValueError(f"TOPOLOGY_CAPABILITY_NOT_CURRENT:{cid}")
            if self.capabilities.epochs.get(cid,-1) != int(epoch):
                raise ValueError(f"TOPOLOGY_CAPABILITY_EPOCH_DRIFT:{cid}")
        self.topologies.register(contract)
        ev=tuple(evidence)
        self.development.nominate(DevelopmentRecord(
            artifact_id=contract.topology_id,
            kind="OPERATIONAL_RECRUITMENT_TOPOLOGY_CONTRACT",
            lineage=tuple(contract.lineage),
            assistance_ancestry=tuple(contract.assistance_ancestry),
            dependencies=tuple(cid for cid,_ in contract.capability_epochs),
            qualification=contract.qualification,
            authority=contract.authority,
            evidence=ev,
            notes=tuple(notes) + (
                f"TOPOLOGY_SIGNATURE_SHA256:{contract.signature_sha256}",
                "NO_SEMANTIC_ROLE_AUTHORITY",
                "NO_IDENTITY_AUTHORITY",
                "CAPABILITY_DEPENDENCIES:"+",".join(f"{cid}@{epoch}" for cid,epoch in contract.capability_epochs),
            ),
        ))
        packet={
            "topology_id":contract.topology_id,
            "topology_epoch":self.topologies.epochs[contract.topology_id],
            "qualification":contract.qualification.value,
            "signature_sha256":contract.signature_sha256,
            "relations":[list(x) for x in contract.relations],
            "capability_dependencies":[list(x) for x in contract.capability_epochs],
            "semantic_role_authority":contract.semantic_role_authority,
            "identity_authority":contract.identity_authority,
            "assistance_ancestry":list(contract.assistance_ancestry),
        }
        self.path.append("RECRUITMENT_TOPOLOGY_REGISTERED",packet)
        self.store.append("RECRUITMENT_TOPOLOGY_REGISTERED",packet)

    def change_recruitment_topology(self, topology_id: str, *, reason: str) -> set[str]:
        """Stale a changed topology and all explicitly bound capabilities."""
        direct=set(self.topologies.capability_dependents.get(topology_id,()))
        self.topologies.change(topology_id,reason=reason)
        if topology_id in self.development.records:
            self.development.invalidate(topology_id,reason)
        stale_caps:set[str]=set()
        for cid in sorted(direct):
            if cid in self.capabilities.contracts:
                stale_caps |= self.capabilities.invalidate(cid,reason=f"TOPOLOGY:{topology_id}:{reason}")
        return stale_caps

    def _on_topology_invalidated(self, topology_id: str, epoch: int, reason: str) -> None:
        packet={
            "topology_id":topology_id,
            "new_epoch":epoch,
            "reason":reason,
            "direct_capability_dependents":sorted(self.topologies.capability_dependents.get(topology_id,())),
        }
        self.path.append("RECRUITMENT_TOPOLOGY_INVALIDATED",packet)
        self.store.append("RECRUITMENT_TOPOLOGY_INVALIDATED",packet)
        self._stale_epistemic_deficits_for_premise("TOPOLOGY",topology_id,epoch,reason)

    def register_operational_counterparty(
        self,
        contract: OperationalCounterpartyContract,
        *,
        evidence: Iterable = (),
        notes: Iterable[str] = (),
    ) -> None:
        """Register an already externally-qualified opaque counterparty relation.

        Registration supplies currentness/provenance for distributed capabilities.
        It does not assert semantic actor identity, genealogy, numerical selfhood,
        hidden value state, or command authority.
        """
        if contract.counterparty_id in self.development.records:
            raise ValueError(f"development record already exists: {contract.counterparty_id}")
        self.counterparties.register(contract)
        ev=tuple(evidence)
        self.development.nominate(DevelopmentRecord(
            artifact_id=contract.counterparty_id,
            kind="OPERATIONAL_COUNTERPARTY_CONTRACT",
            lineage=tuple(contract.lineage),
            assistance_ancestry=tuple(contract.assistance_ancestry),
            dependencies=(),
            qualification=contract.qualification,
            authority=contract.authority,
            evidence=ev,
            notes=tuple(notes)+(
                f"COUNTERPARTY_SIGNATURE_SHA256:{contract.signature_sha256}",
                "OPERATIONAL_CAUSAL_RELATION_ONLY",
                "NO_SEMANTIC_IDENTITY_AUTHORITY",
                "NO_NUMERICAL_IDENTITY_AUTHORITY",
                "NO_GENEALOGY_AUTHORITY",
                "NO_OTHER_VALUE_STATE_AUTHORITY",
            ),
        ))
        packet={
            "counterparty_id":contract.counterparty_id,
            "counterparty_epoch":self.counterparties.epochs[contract.counterparty_id],
            "qualification":contract.qualification.value,
            "signature_sha256":contract.signature_sha256,
            "operational_role_authority":contract.operational_role_authority,
            "semantic_identity_authority":contract.semantic_identity_authority,
            "numerical_identity_authority":contract.numerical_identity_authority,
            "genealogy_authority":contract.genealogy_authority,
            "value_state_authority":contract.value_state_authority,
            "assistance_ancestry":list(contract.assistance_ancestry),
        }
        self.path.append("OPERATIONAL_COUNTERPARTY_REGISTERED",packet)
        self.store.append("OPERATIONAL_COUNTERPARTY_REGISTERED",packet)

    def change_operational_counterparty(self, counterparty_id: str, *, reason: str) -> set[str]:
        """Stale a changed counterparty relation and distributed-capability closure."""
        direct=set(self.counterparties.capability_dependents.get(counterparty_id,()))
        self.counterparties.change(counterparty_id,reason=reason)
        if counterparty_id in self.development.records:
            self.development.invalidate(counterparty_id,reason)
        stale_caps:set[str]=set()
        # Any relation qualified against this counterparty is now stale. This is
        # broad invalidation only when the counterparty relation itself changes;
        # a coordination-only change uses change_operational_coordination instead.
        direct_episode_schemas=self.episodes.invalidate_by_counterparty(counterparty_id,reason=reason)
        changed_relations=self.coordinations.invalidate_by_counterparty(counterparty_id,reason=reason)
        relation_episode_schemas:set[str]=set()
        for rid in sorted(changed_relations):
            relation_episode_schemas |= self.episodes.invalidate_by_coordination(rid,reason=f"COUNTERPARTY:{counterparty_id}:{reason}")
            if rid in self.development.records:
                self.development.invalidate(rid,f"COUNTERPARTY:{counterparty_id}:{reason}")
            for cid in sorted(self.coordinations.capability_dependents.get(rid,())):
                if cid in self.capabilities.contracts:
                    stale_caps |= self.capabilities.invalidate(cid,reason=f"COORDINATION:{rid}:COUNTERPARTY:{reason}")
        stale_caps |= self._stale_episode_schema_dependents_after_external_premise_change(
            direct_episode_schemas | relation_episode_schemas,
            reason=f"COUNTERPARTY:{counterparty_id}:{reason}",
        )
        for cid in sorted(direct):
            if cid in self.capabilities.contracts:
                stale_caps |= self.capabilities.invalidate(cid,reason=f"COUNTERPARTY:{counterparty_id}:{reason}")
        return stale_caps

    def _on_counterparty_invalidated(self, counterparty_id: str, epoch: int, reason: str) -> None:
        packet={
            "counterparty_id":counterparty_id,
            "new_epoch":epoch,
            "reason":reason,
            "direct_capability_dependents":sorted(self.counterparties.capability_dependents.get(counterparty_id,())),
        }
        self.path.append("OPERATIONAL_COUNTERPARTY_INVALIDATED",packet)
        self.store.append("OPERATIONAL_COUNTERPARTY_INVALIDATED",packet)
        self._stale_epistemic_deficits_for_premise("COUNTERPARTY",counterparty_id,epoch,reason)

    def register_operational_coordination(
        self,
        contract: OperationalCoordinationContract,
        *,
        evidence: Iterable = (),
        notes: Iterable[str] = (),
    ) -> None:
        """Register an already externally-qualified opaque coordination relation.

        The relation is narrower than counterparty identity/currentness and grants
        no semantic commitment, intention, promise, hidden-value, identity, or
        feasibility-override authority.
        """
        if contract.coordination_id in self.development.records:
            raise ValueError(f"development record already exists: {contract.coordination_id}")
        for counterparty_id, epoch in contract.participant_counterparty_epochs:
            if not self.counterparties.is_current(counterparty_id, epoch):
                raise ValueError(f"COORDINATION_COUNTERPARTY_EPOCH_DRIFT:{counterparty_id}")
        self.coordinations.register(contract)
        ev = tuple(evidence)
        self.development.nominate(DevelopmentRecord(
            artifact_id=contract.coordination_id,
            kind="OPERATIONAL_COORDINATION_CONTRACT",
            lineage=tuple(contract.lineage),
            assistance_ancestry=tuple(contract.assistance_ancestry),
            dependencies=tuple(cid for cid, _ in contract.participant_counterparty_epochs),
            qualification=contract.qualification,
            authority=contract.authority,
            evidence=ev,
            notes=tuple(notes)+(
                f"COORDINATION_SIGNATURE_SHA256:{contract.signature_sha256}",
                "BOUNDED_MUTUALLY_CONTINGENT_JOINT_ACTION_RELATION_ONLY",
                "NO_SEMANTIC_COMMITMENT_AUTHORITY",
                "NO_INTENTION_AUTHORITY",
                "NO_PROMISE_AUTHORITY",
                "NO_IDENTITY_AUTHORITY",
                "NO_OTHER_VALUE_STATE_AUTHORITY",
                "NO_FEASIBILITY_OVERRIDE_AUTHORITY",
                "COUNTERPARTY_DEPENDENCIES:"+",".join(f"{cid}@{epoch}" for cid,epoch in contract.participant_counterparty_epochs),
            ),
        ))
        packet={
            "coordination_id":contract.coordination_id,
            "coordination_epoch":self.coordinations.epochs[contract.coordination_id],
            "qualification":contract.qualification.value,
            "signature_sha256":contract.signature_sha256,
            "participant_counterparty_epochs":[list(x) for x in contract.participant_counterparty_epochs],
            "operational_relation_authority":contract.operational_relation_authority,
            "semantic_commitment_authority":contract.semantic_commitment_authority,
            "intention_authority":contract.intention_authority,
            "promise_authority":contract.promise_authority,
            "identity_authority":contract.identity_authority,
            "value_state_authority":contract.value_state_authority,
            "feasibility_override_authority":contract.feasibility_override_authority,
            "assistance_ancestry":list(contract.assistance_ancestry),
        }
        self.path.append("OPERATIONAL_COORDINATION_REGISTERED",packet)
        self.store.append("OPERATIONAL_COORDINATION_REGISTERED",packet)

    def change_operational_coordination(self, coordination_id: str, *, reason: str) -> set[str]:
        """Stale one changed coordination relation and only its capability closure."""
        direct=set(self.coordinations.capability_dependents.get(coordination_id,()))
        self.coordinations.change(coordination_id,reason=reason)
        episode_schemas=self.episodes.invalidate_by_coordination(coordination_id,reason=reason)
        if coordination_id in self.development.records:
            self.development.invalidate(coordination_id,reason)
        stale_caps:set[str]=set()
        stale_caps |= self._stale_episode_schema_dependents_after_external_premise_change(
            episode_schemas, reason=f"COORDINATION:{coordination_id}:{reason}"
        )
        for cid in sorted(direct):
            if cid in self.capabilities.contracts:
                stale_caps |= self.capabilities.invalidate(cid,reason=f"COORDINATION:{coordination_id}:{reason}")
        return stale_caps

    def _on_coordination_invalidated(self, coordination_id: str, epoch: int, reason: str) -> None:
        packet={
            "coordination_id":coordination_id,
            "new_epoch":epoch,
            "reason":reason,
            "direct_capability_dependents":sorted(self.coordinations.capability_dependents.get(coordination_id,())),
        }
        self.path.append("OPERATIONAL_COORDINATION_INVALIDATED",packet)
        self.store.append("OPERATIONAL_COORDINATION_INVALIDATED",packet)
        self._stale_epistemic_deficits_for_premise("COORDINATION",coordination_id,epoch,reason)

    def _bootstrap_research_registry(self) -> None:
        for cid, meta in RESEARCH_COMPONENTS.items():
            self.development.nominate(DevelopmentRecord(
                artifact_id=cid,
                kind="COGNITIVE_RESEARCH_COMPONENT",
                lineage=(cid.split("_")[0],),
                assistance_ancestry=(meta["ceiling"],),
                dependencies=(),
                qualification=QualificationState.RESEARCH_ONLY,
                authority=Authority.RESEARCH_ONLY,
                notes=(f"SOURCE_SHA256:{meta['source_sha256']}",),
            ))

    def _on_capability_invalidated(self, root: str, stale: set[str], reason: str) -> None:
        dev_stale: set[str] = set()
        if (
            root in self.development.records
            and self.development.records[root].qualification != QualificationState.STALE
        ):
            dev_stale = self.development.invalidate(root, reason)
        topology_stale: set[str] = set()
        # A topology qualified over a changed constituent is no longer current.
        # Invalidate the topology first; then stale capabilities explicitly bound
        # to that topology. Already-stale topologies are skipped, preventing loops.
        for cid in sorted(stale):
            changed = self.topologies.invalidate_by_capability(cid, reason=reason)
            topology_stale |= changed
        for topology_id in sorted(topology_stale):
            if topology_id in self.development.records:
                self.development.invalidate(topology_id, f"CAPABILITY_CONSTITUENT:{reason}")
            for dependent in sorted(self.topologies.capability_dependents.get(topology_id,())):
                if dependent in self.capabilities.contracts and dependent not in stale:
                    self.capabilities.invalidate(
                        dependent, reason=f"TOPOLOGY:{topology_id}:CONSTITUENT:{reason}"
                    )
        epistemic_premise_stale: set[str] = set()
        for cid in sorted(stale):
            epistemic_premise_stale |= self._stale_epistemic_deficits_for_premise(
                "CAPABILITY_PREMISE",cid,self.capabilities.epochs.get(cid,0),reason,force=True
            )
        epistemic_reopened: set[str] = set()
        for cid in sorted(stale):
            epistemic_reopened |= self.epistemic_deficits.invalidate_probe(cid)
        if epistemic_reopened:
            ep_packet={"capability_id":root,"stale_capabilities":sorted(stale),"deficit_ids":sorted(epistemic_reopened),"reason":reason}
            self.path.append("EPISTEMIC_DEFICIT_PROBE_INVALIDATED",ep_packet)
            self.store.append("EPISTEMIC_DEFICIT_PROBE_INVALIDATED",ep_packet)
        payload = {
            "root": root,
            "reason": reason,
            "capability_stale": sorted(stale),
            "epistemic_deficits_reopened": sorted(epistemic_reopened),
            "epistemic_deficits_staled_by_premise": sorted(epistemic_premise_stale),
            "topology_stale": sorted(topology_stale),
            "development_stale": sorted(dev_stale),
        }
        self.path.append("CAPABILITY_INVALIDATED", payload)
        self.store.append("CAPABILITY_INVALIDATED", payload)

    def append_evidence(
        self,
        evidence_id: str,
        payload: Any,
        disposition: EpistemicStatus,
        *,
        negative: bool = False,
        source: str = "LOCAL",
    ):
        ref = self.evidence.append(
            evidence_id, payload, disposition, negative=negative, source=source
        )
        self.path.append("EVIDENCE", {
            "evidence_id": ref.evidence_id,
            "sha256": ref.sha256,
            "disposition": ref.disposition.value,
            "negative": ref.negative,
        })
        self.store.append("EVIDENCE", {
            "evidence_id": ref.evidence_id,
            "sha256": ref.sha256,
        })
        return ref

    def register_capability(
        self,
        contract: CapabilityContract,
        *,
        evidence: Iterable = (),
        assistance_ancestry: Iterable[str] = (),
        notes: Iterable[str] = (),
        extra_development_dependencies: Iterable[str] = (),
        value_dependencies: Iterable[tuple[str, int]] = (),
        topology_dependencies: Iterable[tuple[str, int]] = (),
        counterparty_dependencies: Iterable[tuple[str, int]] = (),
        coordination_dependencies: Iterable[tuple[str, int]] = (),
    ) -> None:
        """Register an already-qualified capability contract.

        Registration is not a qualification operation. It synchronizes the
        executable capability graph and the developmental dependency graph so
        currentness cannot silently diverge between them again.
        """
        value_deps = tuple((str(vid), int(epoch)) for vid, epoch in value_dependencies)
        topology_deps = tuple((str(tid), int(epoch)) for tid, epoch in topology_dependencies)
        counterparty_deps = tuple((str(cid), int(epoch)) for cid, epoch in counterparty_dependencies)
        coordination_deps = tuple((str(rid), int(epoch)) for rid, epoch in coordination_dependencies)
        for value_id, epoch in value_deps:
            if not self.values.is_current(value_id, epoch):
                raise ValueError(f"CAPABILITY_VALUE_EPOCH_DRIFT:{value_id}")
        for topology_id, epoch in topology_deps:
            if not self.topologies.is_current(topology_id, epoch):
                raise ValueError(f"CAPABILITY_TOPOLOGY_EPOCH_DRIFT:{topology_id}")
        for counterparty_id, epoch in counterparty_deps:
            if not self.counterparties.is_current(counterparty_id, epoch):
                raise ValueError(f"CAPABILITY_COUNTERPARTY_EPOCH_DRIFT:{counterparty_id}")
        for coordination_id, epoch in coordination_deps:
            if not self.coordinations.is_current(coordination_id, epoch):
                raise ValueError(f"CAPABILITY_COORDINATION_EPOCH_DRIFT:{coordination_id}")
        self.capabilities.register(contract)
        for value_id, _ in value_deps:
            self.values.bind_capability(value_id, contract.capability_id)
        for topology_id, _ in topology_deps:
            self.topologies.bind_capability(topology_id, contract.capability_id)
        for counterparty_id, _ in counterparty_deps:
            self.counterparties.bind_capability(counterparty_id, contract.capability_id)
        for coordination_id, _ in coordination_deps:
            self.coordinations.bind_capability(coordination_id, contract.capability_id)
        ev = tuple(evidence)
        assistance = tuple(assistance_ancestry) or tuple(contract.assistance_ancestry)
        if contract.capability_id in self.development.records:
            raise ValueError(f"development record already exists: {contract.capability_id}")
        self.development.nominate(DevelopmentRecord(
            artifact_id=contract.capability_id,
            kind="CAPABILITY_CONTRACT",
            lineage=tuple(contract.lineage),
            assistance_ancestry=assistance,
            dependencies=tuple(contract.dependencies) + tuple(extra_development_dependencies) + tuple(vid for vid, _ in value_deps) + tuple(tid for tid, _ in topology_deps) + tuple(cid for cid, _ in counterparty_deps) + tuple(rid for rid, _ in coordination_deps),
            qualification=contract.qualification,
            authority=contract.authority,
            evidence=ev,
            notes=tuple(notes) + (
                f"OPERATIONAL_SCOPE:{contract.operational_scope_id or 'GLOBAL_OR_UNSCOPED'}",
                "VALUE_DEPENDENCIES:" + ",".join(f"{vid}@{epoch}" for vid, epoch in value_deps),
                "TOPOLOGY_DEPENDENCIES:" + ",".join(f"{tid}@{epoch}" for tid, epoch in topology_deps),
                "COUNTERPARTY_DEPENDENCIES:" + ",".join(f"{cid}@{epoch}" for cid, epoch in counterparty_deps),
                "COORDINATION_DEPENDENCIES:" + ",".join(f"{rid}@{epoch}" for rid, epoch in coordination_deps),
            ),
        ))
        packet = {
            "capability_id": contract.capability_id,
            "qualification": contract.qualification.value,
            "dependencies": list(contract.dependencies),
            "operational_scope_id": contract.operational_scope_id,
            "assistance_ancestry": list(assistance),
            "value_dependencies": [list(x) for x in value_deps],
            "topology_dependencies": [list(x) for x in topology_deps],
            "counterparty_dependencies": [list(x) for x in counterparty_deps],
            "coordination_dependencies": [list(x) for x in coordination_deps],
        }
        self.path.append("CAPABILITY_REGISTERED", packet)
        self.store.append("CAPABILITY_REGISTERED", packet)

    def nominate_capability_candidate(self, candidate: CapabilityCandidate) -> str:
        """Record a proposal without admitting it to the executable repertoire."""
        cid = candidate.candidate_id
        if cid in self.capability_candidates or cid in self.capabilities.contracts:
            raise ValueError(f"duplicate candidate/capability: {cid}")
        self.capability_candidates[cid] = candidate
        packet = {
            "candidate_id": cid,
            "candidate_sha256": candidate.digest(),
            "dependencies": list(candidate.proposed_contract.dependencies),
            "assistance_ancestry": list(candidate.assistance_ancestry),
            "nomination_basis": candidate.nomination_basis,
            "authority": "NONE_PROPOSAL_ONLY",
        }
        self.path.append("CAPABILITY_CANDIDATE_NOMINATED", packet)
        self.store.append("CAPABILITY_CANDIDATE_NOMINATED", packet)
        return candidate.digest()

    def admit_capability_candidate(
        self,
        ticket: CapabilityQualificationTicket,
        *,
        handler=None,
    ) -> CapabilityContract:
        """Consume external qualification; never manufacture it.

        The ticket is content-bound to the proposal and evidence set. This is a
        structural firewall, not a cryptographic remote-attestation claim.
        """
        candidate = self.capability_candidates.get(ticket.candidate_id)
        if candidate is None:
            raise ValueError("candidate not nominated")
        ok, reason = validate_external_ticket(candidate, ticket, self.evidence)
        if not ok:
            raise ValueError(reason)
        sig = candidate.operational_signature or {}
        bound_epochs = sig.get("dependency_epochs")
        if bound_epochs is not None:
            for dep, epoch in bound_epochs:
                contract_now = self.capabilities.contracts.get(dep)
                if contract_now is None or contract_now.qualification not in {
                    QualificationState.QUALIFIED, QualificationState.SHADOW_QUALIFIED
                }:
                    raise ValueError(f"CANDIDATE_DEPENDENCY_NOT_CURRENT:{dep}")
                if self.capabilities.epochs.get(dep, 0) != int(epoch):
                    raise ValueError(f"CANDIDATE_DEPENDENCY_EPOCH_DRIFT:{dep}")
        bound_frames = tuple((str(fid), int(epoch)) for fid, epoch in sig.get("frame_epochs", ()))
        for frame_id, epoch in bound_frames:
            if not self.frames.is_current(frame_id, epoch):
                raise ValueError(f"CANDIDATE_FRAME_EPOCH_DRIFT:{frame_id}")
        bound_episode_schemas = tuple((str(sid), int(epoch)) for sid, epoch in sig.get("episode_schema_epochs", ()))
        for schema_id, epoch in bound_episode_schemas:
            if not self.episodes.is_current(schema_id, epoch):
                raise ValueError(f"CANDIDATE_EPISODE_SCHEMA_EPOCH_DRIFT:{schema_id}")
        bound_values = tuple((str(vid), int(epoch)) for vid, epoch in sig.get("value_epochs", ()))
        for value_id, epoch in bound_values:
            if not self.values.is_current(value_id, epoch):
                raise ValueError(f"CANDIDATE_VALUE_EPOCH_DRIFT:{value_id}")
        bound_topologies = tuple((str(tid), int(epoch)) for tid, epoch in sig.get("topology_epochs", ()))
        for topology_id, epoch in bound_topologies:
            if not self.topologies.is_current(topology_id, epoch):
                raise ValueError(f"CANDIDATE_TOPOLOGY_EPOCH_DRIFT:{topology_id}")
        bound_counterparties = tuple((str(cid), int(epoch)) for cid, epoch in sig.get("counterparty_epochs", ()))
        for counterparty_id, epoch in bound_counterparties:
            if not self.counterparties.is_current(counterparty_id, epoch):
                raise ValueError(f"CANDIDATE_COUNTERPARTY_EPOCH_DRIFT:{counterparty_id}")
        bound_coordinations = tuple((str(rid), int(epoch)) for rid, epoch in sig.get("coordination_epochs", ()))
        for coordination_id, epoch in bound_coordinations:
            if not self.coordinations.is_current(coordination_id, epoch):
                raise ValueError(f"CANDIDATE_COORDINATION_EPOCH_DRIFT:{coordination_id}")
        contract = replace(
            candidate.proposed_contract,
            qualification=ticket.state,
            authority=ticket.authority,
            currentness="CURRENT",
            handler=handler,
            assistance_ancestry=tuple(candidate.assistance_ancestry),
        )
        self.register_capability(
            contract,
            evidence=tuple(candidate.evidence) + tuple(ticket.qualification_evidence),
            assistance_ancestry=candidate.assistance_ancestry,
            notes=(
                f"EXTERNAL_QUALIFIER:{ticket.qualifier_id}",
                f"CANDIDATE_SHA256:{ticket.candidate_sha256}",
                f"QUALIFICATION_REASON:{ticket.reason}",
                "QUALIFICATION_EVIDENCE:" + ",".join(x.evidence_id for x in ticket.qualification_evidence),
                "FRAME_DEPENDENCIES:" + ",".join(f"{fid}@{epoch}" for fid, epoch in bound_frames),
                "EPISODE_SCHEMA_DEPENDENCIES:" + ",".join(f"{sid}@{epoch}" for sid, epoch in bound_episode_schemas),
                "TOPOLOGY_DEPENDENCIES:" + ",".join(f"{tid}@{epoch}" for tid, epoch in bound_topologies),
                "COUNTERPARTY_DEPENDENCIES:" + ",".join(f"{cid}@{epoch}" for cid, epoch in bound_counterparties),
                "COORDINATION_DEPENDENCIES:" + ",".join(f"{rid}@{epoch}" for rid, epoch in bound_coordinations),
            ),
            extra_development_dependencies=tuple(fid for fid, _ in bound_frames) + tuple(sid for sid, _ in bound_episode_schemas),
            value_dependencies=bound_values,
            topology_dependencies=bound_topologies,
            counterparty_dependencies=bound_counterparties,
            coordination_dependencies=bound_coordinations,
        )
        for frame_id, _ in bound_frames:
            self.frames.bind_capability(frame_id, contract.capability_id)
        for schema_id, _ in bound_episode_schemas:
            self.episodes.bind_capability(schema_id, contract.capability_id)
        packet = {
            "candidate_id": candidate.candidate_id,
            "candidate_sha256": ticket.candidate_sha256,
            "qualifier_id": ticket.qualifier_id,
            "qualification": ticket.state.value,
            "authority": ticket.authority.value,
            "proposal_evidence_ids": list(ticket.evidence_ids),
            "qualification_evidence_ids": [x.evidence_id for x in ticket.qualification_evidence],
            "frame_dependencies": [list(x) for x in bound_frames],
            "episode_schema_dependencies": [list(x) for x in bound_episode_schemas],
            "value_dependencies": [list(x) for x in bound_values],
            "topology_dependencies": [list(x) for x in bound_topologies],
            "counterparty_dependencies": [list(x) for x in bound_counterparties],
            "coordination_dependencies": [list(x) for x in bound_coordinations],
        }
        self.path.append("CAPABILITY_CANDIDATE_ADMITTED", packet)
        self.store.append("CAPABILITY_CANDIDATE_ADMITTED", packet)
        return contract

    def invalidate_capability(self, capability_id: str, *, reason: str) -> set[str]:
        return self.capabilities.invalidate(capability_id, reason=reason)

    def change_capability_dependency(self, capability_id: str, *, reason: str) -> set[str]:
        return self.capabilities.change_dependency(capability_id, reason=reason)

    def observe(self, obs: Observation, *, now_iso: str | None = None,
                max_age_seconds: int = 300) -> dict[str, Any]:
        state = "UNKNOWN_INCOMPLETE"
        if now_iso is not None:
            state = currentness(obs, now_iso, max_age_seconds)
        packet = {
            "capture_id": obs.capture_id,
            "origin": obs.origin,
            "referent": obs.referent,
            "currentness": state,
            "resource_mode": obs.resource_mode.value,
            "authority": obs.authority.value,
        }
        self.path.append("OBSERVATION", packet)
        self.store.append("OBSERVATION", packet)
        return packet

    def active_discrimination(self, hypotheses: list[Hypothesis], candidates: list[Any],
                              observations: list[tuple[Any, Any]]) -> dict[str, Any]:
        hs = HypothesisSet(hypotheses)
        for x, y in observations:
            hs.observe(x, y)
        return {
            "disposition": hs.disposition(),
            "live": [h.hypothesis_id for h in hs.live],
            "next_probe": hs.best_probe(candidates),
        }

    def infer_event_frame(self, effects, *, rival_segmentations=None):
        return infer_event_frame(effects, rival_segmentations=rival_segmentations)

    def nominate_referents(self, boundary_signatures):
        return nominate_by_boundary_coherence(boundary_signatures)

    def compose(self, goals):
        return compose_capabilities(self.capabilities.contracts, goals)

    def biography_witness(self) -> dict[str, Any]:
        """Return bounded developmental-lineage evidence, never a selfhood claim."""
        data = self.biography.export()
        data["event_count"] = len(data.get("events", ()))
        data["persistent_selfhood"] = "NOT_QUALIFIED"
        data["numerical_identity_authority"] = "NONE"
        data["execution_uniqueness_authority"] = "NONE"
        data["same_biography_state_semantics"] = "GRAPH_STATE_EQUIVALENCE__COPY_AMBIGUOUS_NOT_NUMERICAL_IDENTITY"
        return data

    def compare_biography(self, other_export: dict[str, Any]) -> str:
        """Legacy graph-relation API; SAME_BIOGRAPHY_STATE is not selfhood."""
        return DevelopmentalBiography.relation(self.biography.export(), other_export)

    def developmental_continuity_witness(self, source_export: dict[str, Any]) -> dict[str, Any]:
        """Assess source → current branch-relative developmental continuity.

        The witness deliberately carries no numerical-identity, semantic-self, or
        exclusive-successor authority. Perfect copies may have identical biography
        graphs until asymmetric consequence makes their branches diverge.
        """
        target=self.biography.export()
        relation=DevelopmentalBiography.relation(source_export, target)
        return continuity_witness_from_exports(source_export, target, relation=relation).serializable()

    def continuity_assessment(self):
        ok, _ = self.biography.verify()
        events = bool(self.biography.events)
        return assess_continuity(state=True, history=bool(ok and events), unfinished=True, deps=True)

    def status(self) -> dict[str, Any]:
        ca = self.continuity_assessment()
        return {
            "embodiment": "PROTO_MICROSEED_MAINDEV_INTEGRATION_V2_9",
            "ancestral_entity_baseline_ms": self.ANCESTRAL_ENTITY_BASELINE_MS,
            "research_terminal_ms": self.RESEARCH_TERMINAL_MS,
            "integration_evidence_through_ms": self.INTEGRATION_EVIDENCE_THROUGH_MS,
            "frontier": self.FRONTIER,
            "deferred_frontiers": list(self.DEFERRED_FRONTIERS),
            "next_ms": self.NEXT_MS,
            "ms1403_started": True,
            "ms1428_started": True,
            "ms1453_started": True,
            "ms1478_started": True,
            "ms1503_started": True,
            "ms1528_started": self.NEXT_STARTED,
            "next_started": self.NEXT_STARTED,
            "language": "DEFERRED_PRELINGUAL_COGNITION_ACTIVE",
            "persistent_identity": "BOUNDED_BRANCH_RELATIVE_DEVELOPMENTAL_CONTINUITY_INTEGRATED__NUMERICAL_SELFHOOD_NOT_QUALIFIED",
            "persistence_infrastructure": ca.status,
            "bounded_qualified_reentry": "TRANSIENT_HISTORY_PROJECTION_PLUS_EXTERNAL_ORTHOGONAL_WARRANT__EXISTING_REGISTER_PATH_ONLY__NO_SNAPSHOT_AUTHORITY",
            "reentry_current_authority_owner": "EXISTING_OPERATIONAL_REGISTRIES_ONLY",
            "reentry_manager_authority": "NONE",
            "reentry_self_qualification_authority": "NONE",
            "reentry_indefinite_automatic_recovery_claim": "NOT_WARRANTED",
            "identity_claim": ca.identity_claim,
            "research_components": len(RESEARCH_COMPONENTS),
            "transitive_capability_currentness": "INTEGRATED_FROM_MS841_843",
            "candidate_lifecycle": "ENDOGENOUS_PROPOSAL__EXTERNAL_QUALIFICATION__ADMISSION",
            "endogenous_candidate_discovery": "BOUNDED_HIGH_RECALL_PROPOSAL_GENERATOR_INTEGRATED__NOT_TRUTH_AUTHORITY",
            "qualification_evidence_separation": "INTEGRATED_FROM_MS862_866",
            "supportive_disposition_gate": "INTEGRATED_FROM_MS862",
            "pending_candidate_epoch_recheck": "INTEGRATED_FROM_MS865_866",
            "operational_trace_frame": "BOUNDED_OPERATIONAL_FRAME_DEPENDENCY_INTEGRATED__FRAME_CONSTRUCTION_NOT_ENTITY_AUTHORITY",
            "operational_frame_currentness": "FIRST_CLASS_EPOCH_BOUND_DEPENDENCY_INTEGRATED_FROM_MS895_897",
            "operational_trace_count": len(self.operational_traces),
            "episode_schema_currentness": "FIRST_CLASS_EPOCH_BOUND_DEPENDENCY__DISTRIBUTED_COORDINATION_ANCESTRY_INTEGRATED_FROM_MS1117_1120",
            "episode_grouping": "BOUNDED_RESEARCH_MECHANISM_NOT_ENTITY_TRUTH_AUTHORITY__ENTITY_ACCEPTS_EXTERNALLY_QUALIFIED_EPISODE_SCHEMAS",
            "distributed_episode_semantic_joint_goal_authority": "NONE",
            "epistemic_deficit_lifecycle": "HISTORICAL_MEMORY_PLUS_OPAQUE_PREMISE_CURRENTNESS__ACTION_LIMITED_PRESSURE__STALE_SUPPRESSION__NO_TRUTH_AUTHORITY",
            "epistemic_deficit_counts": {state.value: sum(1 for r in self.epistemic_deficits.records.values() if r.state == state) for state in EpistemicDeficitState},
            "epistemic_development_pressure_ids": list(self.epistemic_development_pressure_ids()),
            "epistemic_revisit_required_ids": list(self.epistemic_revisit_required_ids()),
            "epistemic_relevance_classifier": "BOUNDED_OPERATIONAL_BEARING_VERIFIER_INTEGRATED__QUALIFIED_DISCOVERED_PROJECTIONS_ALLOWED",
            "epistemic_projection_candidate_count": len(self.epistemic_projection_candidates),
            "epistemic_constructor_candidate_count": len(self.epistemic_constructor_candidates),
            "robust_epistemic_constructor_candidate_count": len(self.robust_epistemic_constructor_candidates),
            "epistemic_projection_count": len(self.epistemic_projections.records),
            "epistemic_contrast_binding_count": len(self.epistemic_contrasts.bindings),
            "epistemic_bearing_witness_count": len(self.epistemic_contrasts.witnesses),
            "epistemic_projection_discovery": "BOUNDED_ACTION_CONDITIONED_PREDICTIVE_EQUIVALENCE_PLUS_CONFLICT_DIRECTED_SUPPORT_AND_LAG_GROWTH__SUPPLIED_CEILINGS__EXTERNAL_QUALIFICATION_REQUIRED",
            "projection_constructor_growth": "EXACT_HYPERGRAPH_PATH_PLUS_BOUNDED_CONFLICT_COVERAGE_ROBUST_PATH__NO_EFFECT_METRIC_OR_NOISE_RATE_MODEL",
            "projection_predictive_currentness": "BOUNDED_WINDOWED_FAILURE_WITNESS__CAN_STALE_PROJECTION__NO_DRIFT_CAUSE_OR_REGIME_IDENTITY_AUTHORITY",
            "projection_drift_structure": "EXTERNALLY_QUALIFIED_ALTERNATIVE_STRUCTURE_COMPARISON__POSITIVE_STRUCTURE_WITNESS_ONLY__NO_CAUSE_IDENTITY",
            "projection_recurrence": "NAMED_HISTORICAL_PREDICTIVE_LAW_MATCH__EXTERNAL_REQUALIFICATION_REQUIRED__NO_REGIME_IDENTITY_OR_AUTO_SWITCH",
            "epistemic_drift_intervention_plan_count": len(self.epistemic_drift_intervention_plans),
            "epistemic_drift_intervention_witness_count": len(self.epistemic_drift_intervention_witnesses),
            "projection_drift_intervention": "BOUNDED_CURRENT_DISAGREEMENT_PROBE_SELECTION_PLUS_REPEATED_EXACT_OUTCOME_WITNESS__NO_SEMANTIC_CAUSE_OR_AUTO_SWITCH",
            "epistemic_bearing_authority": "BOUNDED_OPERATIONAL_BEARING_ONLY__NO_TRUTH_OR_ANSWER_AUTHORITY",
            "question_revisit_scheduler": "NOT_INTEGRATED__ELIGIBILITY_SURFACE_ONLY",
            "episode_schema_count": len(self.episodes.schemas),
            "developmental_biography": "CONTENT_BOUND_CAUSAL_LEDGER_INTEGRATED__OPERATIONAL_LINEAGE_ONLY",
            "biography_integrity": self.biography_witness()["integrity"],
            "biography_event_count": self.biography_witness()["event_count"],
            "biography_identity_claim": "NOT_QUALIFIED",
            "developmental_continuity_witness": "TYPED_BRANCH_RELATIVE_LINEAGE__COPY_AMBIGUITY_EXPLICIT__NO_NUMERICAL_IDENTITY_AUTHORITY",
            "exclusive_successor_authority": "NOT_ESTABLISHED_BY_INTERNAL_BIOGRAPHY",
            "value_variable_count": len(self.values.contracts),
            "regulatory_value_pressure": "INTERNAL_SIGNED_PRESSURE_FROM_EXTERNALLY_QUALIFIED_CONSTITUTIONAL_VALUE_CONTRACT__NOT_VALUE_ORIGIN",
            "value_currentness": "FIRST_CLASS_EPOCH_BOUND_CONSTITUTIONAL_DEPENDENCY_INTEGRATED_FROM_MS966_968",
            "goal_formation": "NOT_QUALIFIED",
            "hierarchical_recruitment": "PROPOSAL_CURRENTNESS_SUBSTRATE_INTEGRATED__PLANNER_RESEARCH_ONLY__GENERAL_PLANNER_NOT_QUALIFIED",
            "counterfactual_rehearsal": "BOUNDED_EVIDENCE_BOUND_MULTI_STEP_PROPOSAL_INTEGRATED__NO_EXECUTION_TRUTH_OR_QUALIFICATION_AUTHORITY",
            "counterfactual_rehearsal_proposal_count": len(self.counterfactual_rehearsals.proposals),
            "bounded_action_outcome_closure": "ONE_ACTION_AT_A_TIME__TRCH_PREMISE_LICENSING_PLUS_QUALIFIED_EFFECT_AUTHORITY_PLUS_EXTERNAL_OUTCOME_OBSERVATION__REDELIBERATE_FROM_REALITY",
            "bounded_action_intent_count": len(self.action_closure.intents),
            "bounded_action_execution_count": len(self.action_closure.executions),
            "bounded_action_outcome_count": len(self.action_closure.outcomes),
            "action_outcome_predictive_learning": "EXECUTED_ACTION_PLUS_ACTUAL_OUTCOME_TO_PROPOSAL__INDEPENDENT_EXTERNAL_QUALIFICATION__CURRENT_REHEARSAL_REUSE__NO_INTENTION_LABEL_OR_CAUSAL_THEOREM",
            "action_outcome_predictive_adaptation": "POST_ADMISSION_EMPIRICAL_CURRENTNESS__DRIFT_WITNESS__HISTORICAL_PRESERVATION__DRIFT_SCOPED_REPLACEMENT_PROPOSAL__EXTERNAL_REQUALIFICATION__NO_AUTO_SWITCH_OR_DRIFT_CAUSE_IDENTITY",
            "projection_conditioned_relation_routing": "EXISTING_OPAQUE_PROJECTION__SCOPED_SHARED_PLUS_DELTA_RELATION_BINDING__DISJOINT_EXTERNAL_QUALIFICATION__NO_SECOND_STATE_SYSTEM_OR_SEMANTIC_REGIME_AUTHORITY",
            "projection_routing_candidate_count": len(self.action_outcome_learning.projection_routing_candidates),
            "projection_conditioned_binding_count": len(self.action_outcome_learning.projection_conditioned_bindings),
            "action_outcome_predictive_candidate_count": len(self.action_outcome_learning.candidates),
            "action_outcome_predictive_relation_count": len(self.action_outcome_learning.relations),
            "general_action_policy_authority": "NONE",
            "semantic_intention_authority": "NONE",
            "recruitment_proposal_count": len(self.recruitments.proposals),
            "hierarchy_topology": "EXTERNALLY_QUALIFIED_OPERATIONAL_TOPOLOGY_CURRENTNESS_INTEGRATED__ENDOGENOUS_PAIRWISE_CONSTRUCTOR_RESEARCH_ONLY",
            "recruitment_topology_count": len(self.topologies.topologies),
            "topology_constructor": "PAIRWISE_RESEARCH_MECHANISM_NOT_ENTITY_AUTHORITY__HIGHER_ORDER_GENERALIZATION_UNRESOLVED",
            "topology_identity_authority": "NONE",
            "operational_counterparty_count": len(self.counterparties.contracts),
            "operational_counterparty_currentness": "FIRST_CLASS_EPOCH_BOUND_DISTRIBUTED_CAPABILITY_DEPENDENCY_INTEGRATED_FROM_MS1066_1069",
            "counterparty_semantic_identity_authority": "NONE",
            "counterparty_numerical_identity_authority": "NONE",
            "other_value_state_authority": "NONE",
            "agent_discovery": "BOUNDED_RESEARCH_MECHANISM_NOT_ENTITY_TRUTH_AUTHORITY",
            "operational_coordination_count": len(self.coordinations.contracts),
            "operational_coordination_currentness": "FIRST_CLASS_RELATION_SPECIFIC_EPOCH_DEPENDENCY_INTEGRATED_FROM_MS1087_1092",
            "coordination_semantic_commitment_authority": "NONE",
            "coordination_intention_authority": "NONE",
            "coordination_promise_authority": "NONE",
            "coordination_identity_authority": "NONE",
            "joint_action_grounding": "BOUNDED_RESEARCH_MECHANISM_NOT_ENTITY_TRUTH_AUTHORITY__ENTITY_ACCEPTS_EXTERNALLY_QUALIFIED_COORDINATION_RELATIONS",
            "composition_ancestry_preservation": "OPERATIONAL_TRACE_TO_DISCOVERY_TO_CAPABILITY_CANDIDATE__EXISTING_TOPOLOGY_COUNTERPARTY_COORDINATION_EPOCHS",
            "multi_child_planner_authority": "NONE",
            "composition_self_qualification_authority": "NONE",
            "architecture_promotion": "MAINDEV_NARROW_INTEGRATION_MS1503_1527_BOUNDED_QUALIFIED_REENTRY",
        }

    def self_test(self) -> dict[str, Any]:
        checks: dict[str, bool] = {}
        e = self.append_evidence("SELFTEST-POS", {"ok": True}, EpistemicStatus.PROVED)
        checks["evidence_resolves"] = self.evidence.resolve([e])[0]
        n = self.append_evidence(
            "SELFTEST-NEG", {"bad": True}, EpistemicStatus.VIOLATED, negative=True
        )
        d = self.qualifier.decide([n], Authority.DERIVED_READ_ONLY)
        checks["negative_evidence_blocks_green"] = d.state == QualificationState.REJECTED
        d0 = self.qualifier.decide([], Authority.DERIVED_READ_ONLY)
        checks["no_evidence_cannot_qualify"] = d0.state == QualificationState.REJECTED
        u = self.append_evidence("SELFTEST-UNKNOWN", {"unknown": True}, EpistemicStatus.UNKNOWN_INCOMPLETE)
        du = self.qualifier.decide([u], Authority.DERIVED_READ_ONLY)
        checks["resolved_unknown_is_not_supportive"] = du.state == QualificationState.REJECTED
        d2 = self.qualifier.decide([e], Authority.EFFECT)
        checks["proposal_cannot_self_grant_effect_authority"] = d2.authority == Authority.NONE

        hs = [Hypothesis("ZERO", lambda x: 0), Hypothesis("PARITY", lambda x: x % 2)]
        ad = self.active_discrimination(hs, [0, 1, 2, 3], [(0, 0)])
        checks["active_discrimination_selects_probe"] = ad["next_probe"] in {1, 3}

        fr = self.infer_event_frame([0, 0, 1, 1], rival_segmentations=[[0, 2], [0, 1, 2]])
        checks["event_frame_ambiguity_unknown"] = fr.status == "UNKNOWN_INCOMPLETE"
        rr = self.nominate_referents([[0, 2], [0, 2]])
        checks["boundary_synchrony_not_object_identity"] = rr.identity_authority == "NONE"
        checks["persistence_not_selfhood"] = (
            self.continuity_assessment().identity_claim == "NOT_QUALIFIED"
        )

        a = CapabilityContract(
            "SELFTEST-A", "opaque", {}, {}, (), (), Authority.DERIVED_READ_ONLY,
            ("SELFTEST",), "CURRENT", {}, qualification=QualificationState.SHADOW_QUALIFIED,
        )
        b = CapabilityContract(
            "SELFTEST-B", "opaque", {}, {}, (), (), Authority.DERIVED_READ_ONLY,
            ("SELFTEST",), "CURRENT", {}, dependencies=("SELFTEST-A",),
            qualification=QualificationState.SHADOW_QUALIFIED,
        )
        c = CapabilityContract(
            "SELFTEST-C", "opaque", {}, {}, (), (), Authority.DERIVED_READ_ONLY,
            ("SELFTEST",), "CURRENT", {}, dependencies=("SELFTEST-B",),
            qualification=QualificationState.SHADOW_QUALIFIED,
        )
        for contract in (a, b, c):
            self.register_capability(contract)
        stale = self.change_capability_dependency("SELFTEST-A", reason="SELFTEST_DRIFT")
        checks["transitive_currentness"] = stale == {"SELFTEST-A", "SELFTEST-B", "SELFTEST-C"}
        checks["metadata_matches_execution_currentness"] = (
            self.compose(["SELFTEST-C"]).status == "NO_PATH"
            and all(
                self.capabilities.contracts[x].qualification == QualificationState.STALE
                for x in stale
            )
        )
        # MS853-877: entity-side proposal generation from supplied prelingual traces.
        da = CapabilityContract(
            "SELFTEST-DISC-A", "opaque", {}, {}, (), (), Authority.DERIVED_READ_ONLY,
            ("SELFTEST",), "CURRENT", {}, qualification=QualificationState.SHADOW_QUALIFIED,
        )
        db = CapabilityContract(
            "SELFTEST-DISC-B", "opaque", {}, {}, (), (), Authority.DERIVED_READ_ONLY,
            ("SELFTEST",), "CURRENT", {}, qualification=QualificationState.SHADOW_QUALIFIED,
        )
        self.register_capability(da); self.register_capability(db)
        for i in range(5):
            self.record_operational_trace(OperationalTrace(f"SA-{i}", ("SELFTEST-DISC-A",), ((1.0, 0.0),), "r0"))
            self.record_operational_trace(OperationalTrace(f"SB-{i}", ("SELFTEST-DISC-B",), ((0.0, 1.0),), "r0"))
        for scope in ("r0", "r1"):
            for i in range(8):
                self.record_operational_trace(OperationalTrace(
                    f"SM-{scope}-{i}", ("SELFTEST-DISC-A", "SELFTEST-DISC-B"),
                    ((1.0, 0.0), (0.0, 2.0)), scope
                ))
        proposals = self.discover_capability_candidates()
        checks["bounded_endogenous_candidate_nomination"] = bool(proposals)
        if proposals:
            pc = self.capability_candidates[proposals[0]["candidate_id"]]
            checks["endogenous_nomination_not_admission"] = pc.candidate_id not in self.capabilities.contracts
            checks["endogenous_proposal_evidence_not_self_supportive"] = (
                self.qualifier.decide(pc.evidence, Authority.DERIVED_READ_ONLY).state == QualificationState.REJECTED
            )
        else:
            checks["endogenous_nomination_not_admission"] = False
            checks["endogenous_proposal_evidence_not_self_supportive"] = False
        checks["hard_stop_ms1528"] = (
            self.NEXT_STARTED is False
            and self.RESEARCH_TERMINAL_MS == 1527
            and self.INTEGRATION_EVIDENCE_THROUGH_MS == 1527
            and self.NEXT_MS == 1528
        )
        checks["qualified_reentry_reuses_existing_registration_authority"] = (
            hasattr(self, "historical_reentry_projection")
            and hasattr(self, "assess_historical_reentry")
            and not hasattr(self, "reentry_registry")
            and not hasattr(self, "reentry_manager")
        )
        checks["qualified_reentry_has_no_auto_restore_or_self_qualification"] = (
            not hasattr(self, "auto_reenter")
            and not hasattr(self, "restore_operational_state")
            and not hasattr(self, "self_qualify_reentry")
        )
        checks["ms1502_composition_ancestry_extends_existing_discovery_lineage"] = (
            "topology_ids" in OperationalTrace.__dataclass_fields__
            and "counterparty_ids" in OperationalTrace.__dataclass_fields__
            and "coordination_ids" in OperationalTrace.__dataclass_fields__
            and not hasattr(self, "multi_child_registry")
            and not hasattr(self, "multi_child_planner")
        )
        checks["action_outcome_learning_bridge_present"] = (
            hasattr(self,"nominate_action_outcome_predictive_candidates")
            and hasattr(self,"qualify_action_outcome_predictive_relation")
            and hasattr(self,"action_outcome_predictive_relation_status")
        )
        checks["predictive_adaptation_bridge_present"] = (
            hasattr(self,"assess_action_outcome_predictive_currentness")
            and hasattr(self,"nominate_action_outcome_replacement_candidates")
            and not hasattr(self,"auto_switch_action_outcome_relation")
            and not hasattr(self,"classify_action_outcome_drift_cause")
        )
        checks["projection_conditioned_routing_reuses_existing_projection_lineage"] = (
            hasattr(self,"nominate_projection_conditioned_relation_routing")
            and hasattr(self,"qualify_projection_conditioned_relation_routing")
            and hasattr(self,"resolve_projection_conditioned_action_outcome_relation")
            and not hasattr(self,"predictive_state_registry")
            and not hasattr(self,"predictive_partitions")
        )
        checks["projection_conditioned_routing_has_no_semantic_regime_or_auto_switch_authority"] = (
            not hasattr(self,"discover_semantic_regime")
            and not hasattr(self,"auto_split_predictive_state")
            and not hasattr(self,"auto_switch_action_outcome_relation")
            and not hasattr(self,"self_qualify_projection_conditioned_routing")
        )
        checks["action_outcome_learning_requires_external_qualification"] = (
            not hasattr(self,"self_qualify_action_outcome_relation")
            and not hasattr(self,"auto_qualify_action_outcome_relation")
        )
        checks["action_outcome_learning_has_no_general_causal_rewrite_authority"] = (
            not hasattr(self,"rewrite_world_model_from_prediction_error")
            and not hasattr(self,"infer_general_causal_theorem_from_outcomes")
        )
        checks["action_outcome_history_carries_actual_effect_not_intent_label"] = (
            "actual_value_effect" in ActionOutcomeRecord.__dataclass_fields__
            and "intended_value_effect" not in ActionOutcomeRecord.__dataclass_fields__
        )
        checks["drift_recurrence_api_present_without_cause_or_regime_classifier"] = (
            hasattr(self,"discover_robust_epistemic_constructor_candidates")
            and hasattr(self,"assess_epistemic_projection_predictive_currentness")
            and hasattr(self,"assess_epistemic_projection_drift_structure")
            and hasattr(self,"assess_epistemic_projection_recurrence")
            and hasattr(self,"reactivate_epistemic_projection_from_recurrence")
            and not hasattr(self,"infer_noise_model")
            and not hasattr(self,"discover_regime_identity")
            and not hasattr(self,"classify_drift_cause")
        )
        checks["drift_intervention_api_present_without_synthesis_or_model_switch"] = (
            hasattr(self,"plan_epistemic_projection_drift_intervention")
            and hasattr(self,"record_epistemic_projection_drift_intervention_evidence")
            and not hasattr(self,"synthesize_intervention")
            and not hasattr(self,"classify_drift_cause")
            and not hasattr(self,"auto_switch_projection")
            and not hasattr(self,"general_active_learning_plan")
        )
        vv = ValueVariableContract(
            value_id="SELFTEST-V0", purpose="opaque-regulatory-variable",
            viable_low=0.4, viable_high=0.8,
            signature_sha256="selftest-value-signature",
            authority=Authority.DERIVED_READ_ONLY, lineage=("MS953-977",),
            currentness="CURRENT", qualification=QualificationState.SHADOW_QUALIFIED,
            assistance_ancestry=("SUPPLIED_CONSTITUTIONAL_VIABILITY_INTERVAL",),
            invariants=("NO_SEMANTIC_GOAL_AUTHORITY",),
        )
        self.register_value_variable(vv)
        self.observe_value_state("SELFTEST-V0", 0.2)
        vp_low = self.value_pressure("SELFTEST-V0")
        checks["internal_signed_regulatory_pressure"] = (
            vp_low["status"] == "CURRENT"
            and vp_low["signed_pressure"] > 0
            and vp_low["semantic_goal_authority"] == "NONE"
        )
        self.observe_value_state("SELFTEST-V0", 1.0)
        vp_high = self.value_pressure("SELFTEST-V0")
        checks["bipolar_value_pressure"] = vp_high["signed_pressure"] < 0
        self.change_value_variable("SELFTEST-V0", reason="SELFTEST_VALUE_DRIFT")
        checks["stale_value_pressure_unknown"] = (
            self.value_pressure("SELFTEST-V0")["status"] == "UNKNOWN_INCOMPLETE"
        )
        checks["constitutional_value_not_self_rewritable"] = not hasattr(self, "set_value_viable_interval")

        # MS978-1002: proposal-only hierarchical recruitment envelope.
        qa=QueryObligation("SELFTEST-RECRUIT","opaque")
        for cid in ("SELFTEST-R1","SELFTEST-R2"):
            if cid not in self.capabilities.contracts:
                self.register_capability(CapabilityContract(
                    capability_id=cid,purpose="opaque-child",boundary={},interface={},invariants=(),hazards=(),
                    authority=Authority.DERIVED_READ_ONLY,lineage=("SELFTEST",),currentness="CURRENT",resources={},
                    qualification=QualificationState.SHADOW_QUALIFIED,handler=lambda **_:1,
                ))
        rp=self.nominate_recruitment((
            RecruitmentOption("SELFTEST-R1",FeasibilityState.FEASIBLE,predicted_effect=(1.0,),resource_tags=("X",)),
            RecruitmentOption("SELFTEST-R2",FeasibilityState.FEASIBLE,predicted_effect=(0.5,),resource_tags=("Y",)),
        ),("SELFTEST-R1","SELFTEST-R2"),assistance_ancestry=("SUPPLIED_ROLE_TOPOLOGY",))
        rr=self.compose_recruitment(rp.proposal_id)
        checks["recruitment_proposal_composes_without_authority_gain"] = rr["status"] == "COMPOSED_EPHEMERAL" and rr["semantic_goal_authority"] == "NONE"
        checks["recruitment_topology_not_endogenous"] = rp.role_topology_origin == "SUPPLIED_AND_PROVENANCED"
        self.change_capability_dependency("SELFTEST-R1",reason="SELFTEST_CHILD_DRIFT")
        checks["recruitment_stales_on_child_drift"] = self.recruitment_status(rp.proposal_id)["status"] == "UNKNOWN_INCOMPLETE"
        checks["recruitment_has_no_self_qualification_api"] = not hasattr(self,"qualify_recruitment")

        # MS1003-1027: externally qualified operational topology/currentness only.
        ta=CapabilityContract(
            "SELFTEST-T1","opaque",{},{},(),(),Authority.DERIVED_READ_ONLY,("SELFTEST",),"CURRENT",{},
            qualification=QualificationState.SHADOW_QUALIFIED,
        )
        tb=CapabilityContract(
            "SELFTEST-T2","opaque",{},{},(),(),Authority.DERIVED_READ_ONLY,("SELFTEST",),"CURRENT",{},
            qualification=QualificationState.SHADOW_QUALIFIED,
        )
        self.register_capability(ta); self.register_capability(tb)
        topo=RecruitmentTopologyContract(
            topology_id="SELFTEST-TOPO", purpose="opaque-operational-recruitment-topology",
            relations=(("SELFTEST-T1","SELFTEST-T2"),),
            capability_epochs=(("SELFTEST-T1",0),("SELFTEST-T2",0)),
            signature_sha256="", authority=Authority.DERIVED_READ_ONLY, lineage=("MS1003-1027",),
            currentness="CURRENT", qualification=QualificationState.SHADOW_QUALIFIED,
            assistance_ancestry=("EXTERNAL_TOPOLOGY_QUALIFICATION",),
            invariants=("NO_SEMANTIC_ROLE_AUTHORITY","NO_IDENTITY_AUTHORITY"),
        )
        topo.signature_sha256=topo.computed_signature_sha256()
        self.register_recruitment_topology(topo)
        checks["qualified_operational_topology_registered"] = self.topologies.is_current("SELFTEST-TOPO",0)
        checks["topology_grants_no_role_or_identity_authority"] = topo.semantic_role_authority == "NONE" and topo.identity_authority == "NONE"
        trp=self.nominate_recruitment((
            RecruitmentOption("SELFTEST-T1",FeasibilityState.FEASIBLE,resource_tags=("t1",)),
            RecruitmentOption("SELFTEST-T2",FeasibilityState.FEASIBLE,resource_tags=("t2",)),
        ),("SELFTEST-T1","SELFTEST-T2"),topology_id="SELFTEST-TOPO")
        checks["qualified_topology_can_bind_recruitment_without_authority_gain"] = (
            self.recruitment_status(trp.proposal_id)["status"] == "CURRENT"
            and trp.role_topology_origin == "EXTERNALLY_QUALIFIED_OPERATIONAL_TOPOLOGY"
            and trp.semantic_goal_authority == "NONE"
        )
        self.change_recruitment_topology("SELFTEST-TOPO",reason="SELFTEST_TOPOLOGY_DRIFT")
        checks["topology_drift_stales_bound_recruitment"] = self.recruitment_status(trp.proposal_id)["status"] == "UNKNOWN_INCOMPLETE"
        checks["topology_constructor_not_silently_promoted"] = not hasattr(self,"discover_recruitment_topology")

        bw = self.biography_witness()
        checks["biography_integrity_verified"] = bw["integrity"] == "VERIFIED"
        checks["biography_not_selfhood_authority"] = bw["identity_claim"] == "NOT_QUALIFIED"
        cw = self.developmental_continuity_witness(bw)
        checks["same_biography_graph_is_copy_ambiguous"] = (
            cw["relation"] == "SAME_BIOGRAPHY_STATE" and cw["copy_ambiguity"] is True
        )
        checks["continuity_witness_grants_no_numerical_identity"] = (
            cw["numerical_identity_authority"] == "NONE" and cw["selfhood_claim"] == "NOT_QUALIFIED"
        )
        checks["exclusive_successor_authority_not_internal"] = (
            cw["exclusive_successor_authority"] == "NOT_ESTABLISHED_BY_INTERNAL_BIOGRAPHY"
        )
        checks["episode_grouping_not_silently_promoted"] = (
            not hasattr(self, "record_operational_event")
            and not hasattr(self, "propose_episode_grouping")
        )
        # MS1053-1077: opaque counterparty currentness for distributed capabilities.
        cp = OperationalCounterpartyContract(
            counterparty_id="SELFTEST-CP0", purpose="opaque-independent-causal-relation",
            signature_sha256="", authority=Authority.DERIVED_READ_ONLY, lineage=("MS1053-1077",),
            currentness="CURRENT", qualification=QualificationState.SHADOW_QUALIFIED,
            assistance_ancestry=("HSP_EXTERNAL_COUNTERPARTY_QUALIFICATION",),
            invariants=("NO_SEMANTIC_IDENTITY_AUTHORITY",),
        )
        cp.signature_sha256=cp.computed_signature_sha256()
        self.register_operational_counterparty(cp)
        joint=CapabilityContract(
            "SELFTEST-JOINT", "opaque-distributed", {}, {}, (), (), Authority.DERIVED_READ_ONLY,
            ("MS1053-1077",), "CURRENT", {}, qualification=QualificationState.SHADOW_QUALIFIED,
        )
        self.register_capability(joint,counterparty_dependencies=(("SELFTEST-CP0",0),))
        stale_joint=self.change_operational_counterparty("SELFTEST-CP0",reason="SELFTEST_PARTNER_DRIFT")
        checks["distributed_capability_stales_on_counterparty_drift"] = (
            "SELFTEST-JOINT" in stale_joint and self.compose(["SELFTEST-JOINT"]).status=="NO_PATH"
        )
        checks["counterparty_relation_not_identity"] = (
            cp.semantic_identity_authority=="NONE" and cp.numerical_identity_authority=="NONE"
            and cp.genealogy_authority=="NONE" and cp.value_state_authority=="NONE"
        )
        # MS1078-1102: relation-specific coordination currentness.
        cp2 = OperationalCounterpartyContract(
            counterparty_id="SELFTEST-CP1", purpose="opaque-independent-causal-relation",
            signature_sha256="", authority=Authority.DERIVED_READ_ONLY, lineage=("MS1053-1077",),
            currentness="CURRENT", qualification=QualificationState.SHADOW_QUALIFIED,
            assistance_ancestry=("HSP_EXTERNAL_COUNTERPARTY_QUALIFICATION",),
        )
        cp2.signature_sha256=cp2.computed_signature_sha256(); self.register_operational_counterparty(cp2)
        rel=OperationalCoordinationContract(
            coordination_id="SELFTEST-COORD", purpose="opaque-mutual-action-contingency",
            participant_counterparty_epochs=(("SELFTEST-CP1",0),), signature_sha256="",
            authority=Authority.DERIVED_READ_ONLY, lineage=("MS1078-1102",), currentness="CURRENT",
            qualification=QualificationState.SHADOW_QUALIFIED,
            assistance_ancestry=("HSP_EXTERNAL_COORDINATION_QUALIFICATION",),
        )
        rel.signature_sha256=rel.computed_signature_sha256(); self.register_operational_coordination(rel)
        j2=CapabilityContract(
            "SELFTEST-JOINT2","opaque-distributed",{},{},(),(),Authority.DERIVED_READ_ONLY,
            ("MS1078-1102",),"CURRENT",{},qualification=QualificationState.SHADOW_QUALIFIED,
        )
        self.register_capability(j2,coordination_dependencies=(("SELFTEST-COORD",0),))
        stale2=self.change_operational_coordination("SELFTEST-COORD",reason="SELFTEST_COORDINATION_DRIFT")
        checks["coordination_drift_selectively_stales_bound_capability"] = (
            "SELFTEST-JOINT2" in stale2 and self.compose(["SELFTEST-JOINT2"]).status=="NO_PATH"
        )
        checks["coordination_relation_has_no_semantic_commitment_authority"] = (
            rel.semantic_commitment_authority=="NONE" and rel.intention_authority=="NONE"
            and rel.promise_authority=="NONE" and rel.identity_authority=="NONE"
        )
        checks["coordination_learner_not_silently_promoted"] = not hasattr(self,"discover_operational_coordination")
        # MS1103-1127: episode schema currentness may bind relation-specific coordination ancestry.
        cp3 = OperationalCounterpartyContract(
            counterparty_id="SELFTEST-CP2", purpose="opaque-independent-causal-relation",
            signature_sha256="", authority=Authority.DERIVED_READ_ONLY, lineage=("MS1053-1077",),
            currentness="CURRENT", qualification=QualificationState.SHADOW_QUALIFIED,
        )
        cp3.signature_sha256=cp3.computed_signature_sha256(); self.register_operational_counterparty(cp3)
        rel3=OperationalCoordinationContract(
            coordination_id="SELFTEST-COORD-EP", purpose="opaque-mutual-action-contingency",
            participant_counterparty_epochs=(("SELFTEST-CP2",0),), signature_sha256="",
            authority=Authority.DERIVED_READ_ONLY, lineage=("MS1078-1102",), currentness="CURRENT",
            qualification=QualificationState.SHADOW_QUALIFIED,
        )
        rel3.signature_sha256=rel3.computed_signature_sha256(); self.register_operational_coordination(rel3)
        eps=EpisodeSchemaContract(
            schema_id="SELFTEST-DIST-EP", purpose="opaque-distributed-grouping", signature_sha256="d"*64,
            authority=Authority.DERIVED_READ_ONLY, lineage=("MS1103-1127",), currentness="CURRENT",
            qualification=QualificationState.SHADOW_QUALIFIED, coordination_epochs=(("SELFTEST-COORD-EP",0),),
        )
        self.register_episode_schema(eps)
        ec=CapabilityContract(
            "SELFTEST-DIST-EP-CAP","opaque-distributed-episode",{},{},(),(),Authority.DERIVED_READ_ONLY,
            ("MS1103-1127",),"CURRENT",{},qualification=QualificationState.SHADOW_QUALIFIED,
        )
        self.register_capability(ec,extra_development_dependencies=("SELFTEST-DIST-EP",)); self.episodes.bind_capability("SELFTEST-DIST-EP","SELFTEST-DIST-EP-CAP")
        stale_ep=self.change_operational_coordination("SELFTEST-COORD-EP",reason="SELFTEST_EPISODE_PREMISE_DRIFT")
        checks["distributed_episode_stales_on_coordination_drift"] = (
            not self.episodes.is_current("SELFTEST-DIST-EP",0)
            and "SELFTEST-DIST-EP-CAP" in stale_ep
            and self.compose(["SELFTEST-DIST-EP-CAP"]).status=="NO_PATH"
        )
        checks["distributed_episode_constructor_not_silently_promoted"] = not hasattr(self,"discover_distributed_episode")
        # MS1128-1152: zero-disagreement actions are not falsely advertised as probes.
        h0=Hypothesis("SELFTEST-H0",lambda x: 0 if x in ("a","b") else 0)
        h1=Hypothesis("SELFTEST-H1",lambda x: 0 if x in ("a","b") else (1 if x=="d" else 0))
        checks["zero_disagreement_probe_returns_none"] = self.active_discrimination([h0,h1],["a","b"],[])["next_probe"] is None
        checks["disagreement_probe_selected_when_available"] = self.active_discrimination([h0,h1],["a","b","d"],[])["next_probe"] == "d"
        ev=self.append_evidence("SELFTEST-ACTION-LIMITED-UNKNOWN",{"opaque":True},EpistemicStatus.UNKNOWN_INCOMPLETE,source="SELFTEST")
        rec=self.record_action_limited_unknown(deficit_id="SELFTEST-DEFICIT",question_key="Q-OPAQUE",hypothesis_digest_sha256="0"*64,unknown_evidence_id=ev.evidence_id,missing_discriminator_signature_sha256="1"*64)
        checks["action_limited_deficit_has_no_truth_authority"] = rec.truth_authority=="NONE" and rec.state==EpistemicDeficitState.ACTION_LIMITED
        checks["probe_availability_not_resolution"] = "RESOLVED" not in {x.value for x in EpistemicDeficitState}
        checks["stale_state_excluded_from_development_pressure"] = (
            self.stale_epistemic_deficit("SELFTEST-DEFICIT",reason="SELFTEST_HYPOTHESIS_REVISION")["state"] == "STALE"
            and "SELFTEST-DEFICIT" not in self.epistemic_development_pressure_ids()
        )
        checks["stale_deficit_preserves_historical_unknown"] = (
            self.epistemic_deficit_status("SELFTEST-DEFICIT")["unknown_evidence_id"] == ev.evidence_id
        )
        # MS1178-1202: bounded operational bearing inside supplied opaque projections.
        od0=__import__("hashlib").sha256(b"outcome-0").hexdigest()
        od1=__import__("hashlib").sha256(b"outcome-1").hexdigest()
        ps=__import__("hashlib").sha256(b"projection-v0").hexdigest()
        self.register_epistemic_projection("SELFTEST-PROJ",ps,assistance_ancestry=("SUPPLIED_PROJECTION",))
        u2=self.append_evidence("SELFTEST-REL-UNKNOWN",{"opaque":True},EpistemicStatus.UNKNOWN_INCOMPLETE,source="SELFTEST")
        d2=self.record_action_limited_unknown(
            deficit_id="SELFTEST-REL-DEFICIT",question_key="OPAQUE",
            hypothesis_digest_sha256="2"*64,unknown_evidence_id=u2.evidence_id,
            missing_discriminator_signature_sha256="3"*64,
        )
        cb=EpistemicContrastBinding(
            binding_id="SELFTEST-CONTRAST",deficit_id=d2.deficit_id,
            hypothesis_digest_sha256=d2.hypothesis_digest_sha256,
            rows=(EpistemicContrastRow("SELFTEST-PROJ",0,(("h0",od0),("h1",od1))),),
            assistance_ancestry=("SUPPLIED_CONTRAST",),
        )
        self.register_epistemic_contrast(cb)
        rel=self.append_evidence(
            "SELFTEST-REL-EVIDENCE",
            {"epistemic_projection":{"projection_id":"SELFTEST-PROJ","projection_epoch":0,"outcome_digest_sha256":od1}},
            EpistemicStatus.PRESSURE_SUPPORTED,source="SELFTEST",
        )
        br=self.assess_epistemic_evidence_bearing(d2.deficit_id,cb.binding_id,rel.evidence_id)
        checks["bounded_contrast_can_verify_discriminating_bearing"] = (
            br["bearing_kind"]=="DISCRIMINATES_LIVE_SET" and br["state"]=="REVISIT_REQUIRED"
        )
        checks["bearing_witness_has_no_truth_or_answer_authority"] = (
            self.epistemic_bearing_witnesses(d2.deficit_id)[0]["truth_authority"]=="NONE"
            and self.epistemic_bearing_witnesses(d2.deficit_id)[0]["answer_authority"]=="NONE"
        )
        checks["bounded_projection_proposal_generator_present"] = hasattr(self,"discover_epistemic_projection_candidates")
        checks["no_projection_self_qualification_api"] = not hasattr(self,"qualify_epistemic_projection_candidate")
        checks["no_general_raw_projection_discovery_api"] = not hasattr(self,"discover_general_epistemic_projection")
        checks["no_general_question_revisit_scheduler"] = not hasattr(self,"schedule_question_revisits")
        checks["bounded_constructor_growth_api_present"] = hasattr(self,"discover_epistemic_constructor_candidates")
        checks["constructor_self_qualification_api_absent"] = not hasattr(self,"qualify_epistemic_constructor_candidate")
        checks["noise_tolerant_constructor_not_silently_promoted"] = not hasattr(self,"discover_noise_tolerant_constructor")
        # MS1328-1352: bounded counterfactual rehearsal is proposal-only and finite.
        r_a=RehearsalTransitionRelation("S0","RA","SA",0.8,12,1.0,("EA",),0,("F",0),("E",0))
        r_b=RehearsalTransitionRelation("S0","RB","S1",-0.4,12,1.0,("EB",),0,("F",0),("E",0))
        r_c=RehearsalTransitionRelation("S1","RC","S2",2.6,12,1.0,("EC",),0,("F",0),("E",0))
        rp=propose_counterfactual_rehearsal(
            {("S0","RA"):r_a,("S0","RB"):r_b,("S1","RC"):r_c},
            start_state_id="S0",start_value=0.0,viable_low=2.0,viable_high=3.0,value_epoch=("V",0),
            options=(RecruitmentOption("RA",FeasibilityState.FEASIBLE),RecruitmentOption("RB",FeasibilityState.FEASIBLE),RecruitmentOption("RC",FeasibilityState.FEASIBLE)),
            cfg=CounterfactualRehearsalConfig(max_horizon=2),
        )
        checks["bounded_rehearsal_can_outperform_myopic_path"] = rp is not None and rp.sequence == ("RB","RC") and rp.residual_pressure == 0.0
        checks["rehearsal_grants_no_execution_truth_or_qualification_authority"] = rp is not None and rp.execution_authority=="NONE" and rp.truth_authority=="NONE" and rp.qualification_authority=="NONE"
        checks["general_planner_not_silently_promoted"] = not hasattr(self,"plan") and not hasattr(self,"execute_counterfactual_rehearsal")
        # MS1353-1377: TRCH survives only as a common commitment projection layer.
        trch_yes = project_feasibility(FeasibilityState.FEASIBLE, commitment_id="SELFTEST-TRCH-F", target_id="cap:F")
        trch_unknown = project_epistemic_status(EpistemicStatus.UNKNOWN_INCOMPLETE, commitment_id="SELFTEST-TRCH-U", target_id="query:U")
        trch_na = project_epistemic_status(EpistemicStatus.NOT_APPLICABLE, commitment_id="SELFTEST-TRCH-NA", target_id="query:NA")
        trch_stale = project_qualification_state(QualificationState.STALE, commitment_id="SELFTEST-TRCH-S", target_id="candidate:S")
        checks["trch_common_commitment_primitive_present"] = trch_yes.licenses_yes() and trch_yes.commitment == TernaryCommitment.YES
        checks["trch_unknown_is_explicit_abstention"] = trch_unknown.commitment == TernaryCommitment.UNKNOWN and trch_unknown.abstains()
        checks["trch_binding_applicability_not_single_null_axis"] = trch_na.applicability == TernaryCommitment.NO and trch_na.binding == TernaryCommitment.YES and trch_na.coarse_null
        checks["trch_stale_is_sidecar_not_fourth_commitment"] = trch_stale.commitment == TernaryCommitment.UNKNOWN and trch_stale.qualifier("currentness") == "STALE"
        checks["trch_native_lifecycle_enums_preserved"] = "STALE" in {x.value for x in QualificationState} and "ACTION_LIMITED" in {x.value for x in EpistemicDeficitState}
        import microseed.development.commitment_adapters as _trch_adapters
        checks["trch_authority_not_collapsed_into_truth"] = not hasattr(_trch_adapters, "project_authority")
        # MS1378-1402: bounded control-loop closure is one action at a time and reality-facing.
        checks["rehearsal_carries_stepwise_feedback_ancestry"] = (
            rp is not None and rp.predicted_state_path == ("S0","S1","S2") and rp.predicted_step_value_effects == (-0.4,2.6)
        )
        cs=self.bounded_control_loop_status()
        checks["bounded_control_loop_has_no_general_policy_or_intention_authority"] = (
            cs["general_policy_authority"]=="NONE" and cs["semantic_intention_authority"]=="NONE"
        )
        checks["control_loop_is_receding_horizon_not_open_loop_plan_execution"] = (
            hasattr(self,"derive_bounded_action_commitment") and hasattr(self,"execute_bounded_action")
            and hasattr(self,"record_bounded_action_outcome") and not hasattr(self,"execute_plan")
        )
        checks["handler_result_not_automatically_observation"] = not hasattr(self,"treat_effect_result_as_observation")
        return {
            "checks": checks,
            "passed": sum(checks.values()),
            "total": len(checks),
            "all_pass": all(checks.values()),
        }
