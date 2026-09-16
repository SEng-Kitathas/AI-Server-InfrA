"""Proto-Microseed Main-Dev embodiment.

This package preserves research/authority separation while integrating the
narrow architectural changes warranted by evidence through MS1502.
"""
from .runtime.entity import Microseed
from .runtime.commitment import TernaryCommitment, RelationalCommitment
from .runtime.types import (
    Authority, EpistemicStatus, QualificationState, ResourceMode,
    Observation, QueryObligation, CapabilityContract, OperationalFrameContract, EpisodeSchemaContract,
    ValueVariableContract, FeasibilityState, RecruitmentTopologyContract, OperationalCounterpartyContract, OperationalCoordinationContract,
)
from .development.commitment_adapters import (
    project_feasibility, project_epistemic_status, project_qualification_state, project_epistemic_deficit_state,
)
from .development.capability_admission import (
    CapabilityCandidate,
    CapabilityQualificationTicket,
    ExternalCapabilityQualifier,
)
from .development.discovery import OperationalTrace, DiscoveryConfig, CandidateFinding
from .development.recruitment import RecruitmentOption, RecruitmentProposal, RecruitmentRegistry
from .development.constructor_growth import (
    ConstructorAtom, ConstructorProjectionSample, ConstructorGrowthConfig, ConstructorSearchDiagnostic,
    ProjectionConstructorCandidate, ConstructorQualificationTicket, ExternalConstructorQualifier,
    discover_projection_constructor_candidates, validate_external_constructor_ticket,
)
from .development.robust_constructor_growth import (
    RobustConstructorGrowthConfig, RobustConstructorSearchDiagnostic, RobustProjectionConstructorCandidate,
    RobustConstructorQualificationTicket, ExternalRobustConstructorQualifier,
    ProjectionPredictiveCurrentnessConfig, ProjectionPredictiveCurrentnessWitness,
    discover_robust_projection_constructor_candidates, validate_external_robust_constructor_ticket,
)
from .development.drift_recurrence import (
    ProjectionDriftStructureConfig, ProjectionDriftStructureWitness,
    ProjectionRecurrenceConfig, ProjectionRecurrenceWitness, ProjectionRecurrenceQualificationTicket,
    ExternalProjectionRecurrenceQualifier, assess_projection_drift_structure, assess_projection_recurrence,
    validate_external_projection_recurrence_ticket,
)
from .development.drift_intervention import (
    DriftInterventionConfig, DriftInterventionProbe, DriftInterventionSelection, DriftInterventionWitness,
    select_drift_discriminating_intervention, assess_drift_intervention_outcomes,
)
from .development.projection_discovery import (
    ProjectionSample, ProjectionDiscoveryConfig, EpistemicProjectionCandidate,
    ProjectionQualificationTicket, ExternalProjectionQualifier,
    discover_epistemic_projection_candidates, validate_external_projection_ticket,
)
from .development.rehearsal import (
    RehearsalTransitionObservation, RehearsalTransitionRelation, CounterfactualRehearsalConfig,
    CounterfactualRehearsalProposal, CounterfactualRehearsalRegistry,
    derive_rehearsal_transition_relations, propose_counterfactual_rehearsal,
)
from .development.action_closure import (
    OpaqueControlStateWitness, BoundedActionIntent, ActionExecutionRecord, ActionOutcomeRecord, ActionClosureRegistry,
)
from .development.epistemic import (
    EpistemicCurrentnessAnchor, EpistemicDeficitRecord, EpistemicDeficitRegistry, EpistemicDeficitState,
    EpistemicProjectionRecord, EpistemicProjectionRegistry, EpistemicContrastRow,
    EpistemicContrastBinding, EpistemicContrastRegistry, EpistemicBearingKind, EpistemicBearingWitness,
)

__all__ = [
    "Microseed", "TernaryCommitment", "RelationalCommitment", "Authority", "EpistemicStatus", "QualificationState",
    "ResourceMode", "Observation", "QueryObligation", "CapabilityContract", "OperationalFrameContract", "EpisodeSchemaContract", "ValueVariableContract", "FeasibilityState", "RecruitmentTopologyContract", "OperationalCounterpartyContract", "OperationalCoordinationContract",
    "project_feasibility", "project_epistemic_status", "project_qualification_state", "project_epistemic_deficit_state",
    "CapabilityCandidate", "CapabilityQualificationTicket", "ExternalCapabilityQualifier",
    "OperationalTrace", "DiscoveryConfig", "CandidateFinding",
    "RecruitmentOption", "RecruitmentProposal", "RecruitmentRegistry",
    "ProjectionSample", "ProjectionDiscoveryConfig", "EpistemicProjectionCandidate",
    "ProjectionQualificationTicket", "ExternalProjectionQualifier",
    "discover_epistemic_projection_candidates", "validate_external_projection_ticket",
    "ConstructorAtom", "ConstructorProjectionSample", "ConstructorGrowthConfig", "ConstructorSearchDiagnostic",
    "ProjectionConstructorCandidate", "ConstructorQualificationTicket", "ExternalConstructorQualifier",
    "discover_projection_constructor_candidates", "validate_external_constructor_ticket",
    "RobustConstructorGrowthConfig", "RobustConstructorSearchDiagnostic", "RobustProjectionConstructorCandidate",
    "RobustConstructorQualificationTicket", "ExternalRobustConstructorQualifier",
    "ProjectionPredictiveCurrentnessConfig", "ProjectionPredictiveCurrentnessWitness",
    "discover_robust_projection_constructor_candidates", "validate_external_robust_constructor_ticket",
    "ProjectionDriftStructureConfig", "ProjectionDriftStructureWitness",
    "ProjectionRecurrenceConfig", "ProjectionRecurrenceWitness", "ProjectionRecurrenceQualificationTicket",
    "ExternalProjectionRecurrenceQualifier", "assess_projection_drift_structure", "assess_projection_recurrence",
    "validate_external_projection_recurrence_ticket",
    "DriftInterventionConfig", "DriftInterventionProbe", "DriftInterventionSelection", "DriftInterventionWitness",
    "select_drift_discriminating_intervention", "assess_drift_intervention_outcomes",
    "RehearsalTransitionObservation", "RehearsalTransitionRelation", "CounterfactualRehearsalConfig",
    "CounterfactualRehearsalProposal", "CounterfactualRehearsalRegistry",
    "derive_rehearsal_transition_relations", "propose_counterfactual_rehearsal",
    "OpaqueControlStateWitness", "BoundedActionIntent", "ActionExecutionRecord", "ActionOutcomeRecord", "ActionClosureRegistry",
    "EpistemicCurrentnessAnchor", "EpistemicDeficitRecord", "EpistemicDeficitRegistry", "EpistemicDeficitState",
    "EpistemicProjectionRecord", "EpistemicProjectionRegistry", "EpistemicContrastRow",
    "EpistemicContrastBinding", "EpistemicContrastRegistry", "EpistemicBearingKind", "EpistemicBearingWitness",
]
__version__ = "2.9.0-maindev-ms1527"

from .development.action_learning import (
    ActionOutcomeExperience, ActionOutcomePredictiveCandidate, ActionOutcomeRelationQualificationTicket,
    QualifiedActionOutcomePredictiveRelation, ActionOutcomeLearningRegistry, ExternalActionOutcomeRelationQualifier,
    ProjectionConditionedRelationCandidate, ProjectionConditionedRelationQualificationTicket,
    QualifiedProjectionConditionedRelationBinding, ExternalProjectionConditionedRelationQualifier,
    validate_external_projection_conditioned_relation_ticket,
)

__all__.extend([
    "ActionOutcomeExperience", "ActionOutcomePredictiveCandidate", "ActionOutcomeRelationQualificationTicket",
    "QualifiedActionOutcomePredictiveRelation", "ActionOutcomeLearningRegistry", "ExternalActionOutcomeRelationQualifier",
    "ProjectionConditionedRelationCandidate", "ProjectionConditionedRelationQualificationTicket",
    "QualifiedProjectionConditionedRelationBinding", "ExternalProjectionConditionedRelationQualifier",
    "validate_external_projection_conditioned_relation_ticket",
])

from .development.reentry import (
    HistoricalReentryRecord, HistoricalReentryProjection, ReentryWarrant, ReentryDecision,
    historical_registration_fingerprint, derive_historical_reentry_projection, assess_reentry,
)

__all__.extend([
    "HistoricalReentryRecord", "HistoricalReentryProjection", "ReentryWarrant", "ReentryDecision",
    "historical_registration_fingerprint", "derive_historical_reentry_projection", "assess_reentry",
])

from .development.relational_algebra import (
    OpaqueTransitionSample, OpaqueActionCompositionCandidate,
    discover_opaque_action_composition_candidates, predict_opaque_action_composition,
)
__all__.extend([
    "OpaqueTransitionSample", "OpaqueActionCompositionCandidate",
    "discover_opaque_action_composition_candidates", "predict_opaque_action_composition",
])
