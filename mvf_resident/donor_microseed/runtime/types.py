from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable


class EpistemicStatus(str, Enum):
    PROVED = "PROVED"
    PRESSURE_SUPPORTED = "PRESSURE_SUPPORTED"
    NARROWED = "NARROWED"
    VIOLATED = "VIOLATED"
    NOT_OBSERVED_WITHIN_BOUNDS = "NOT_OBSERVED_WITHIN_BOUNDS"
    UNKNOWN_INCOMPLETE = "UNKNOWN_INCOMPLETE"
    UNSUPPORTED = "UNSUPPORTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class QualificationState(str, Enum):
    CANDIDATE = "CANDIDATE"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    SHADOW_QUALIFIED = "SHADOW_QUALIFIED"
    QUALIFIED = "QUALIFIED"
    STALE = "STALE"
    REJECTED = "REJECTED"


class Authority(str, Enum):
    NONE = "NONE"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    MODEL_OUTPUT_ONLY = "MODEL_OUTPUT_ONLY"
    OBSERVATION_ONLY = "OBSERVATION_ONLY"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    DERIVED_READ_ONLY = "DERIVED_READ_ONLY"
    EFFECT = "EFFECT"


class ResourceMode(str, Enum):
    NAKED = "NAKED"
    EQUIPPED = "EQUIPPED"
    FEDERATED = "FEDERATED"


class FeasibilityState(str, Enum):
    FEASIBLE = "FEASIBLE"
    REFUSED = "REFUSED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class EvidenceRef:
    evidence_id: str
    sha256: str
    disposition: EpistemicStatus
    negative: bool = False


@dataclass(frozen=True)
class Observation:
    capture_id: str
    origin: str
    referent: str
    value: Any
    observed_at: str | None = None
    acquired_at: str | None = None
    currentness_basis: str = "UNDECLARED"
    resource_mode: ResourceMode = ResourceMode.NAKED
    authority: Authority = Authority.OBSERVATION_ONLY
    lineage: tuple[str, ...] = ()


@dataclass(frozen=True)
class QueryObligation:
    obligation_id: str
    purpose: str
    required_authority: Authority = Authority.NONE
    witness_predicate: str | None = None
    # Opaque operational regime handle. It is deliberately not a semantic
    # context label: MS844-845 showed that qualification can be local without
    # granting a named context ontology.
    operational_scope_id: str | None = None


@dataclass
class CapabilityContract:
    capability_id: str
    purpose: str
    boundary: dict[str, Any]
    interface: dict[str, Any]
    invariants: tuple[str, ...]
    hazards: tuple[str, ...]
    authority: Authority
    lineage: tuple[str, ...]
    currentness: str
    resources: dict[str, Any]
    dependencies: tuple[str, ...] = ()
    query_obligation_id: str | None = None
    witness_predicate: str | None = None
    qualification: QualificationState = QualificationState.CANDIDATE
    handler: Callable[..., Any] | None = field(default=None, repr=False, compare=False)
    # Assistance is first-class ancestry, not hidden in prose.
    assistance_ancestry: tuple[str, ...] = ()
    # Operational locality without semantic-context authority.
    operational_scope_id: str | None = None

    def serializable(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("handler", None)
        return d

    def signature_payload(self) -> dict[str, Any]:
        """Immutable capability content for ancestry/currentness identity.

        Mutable qualification/currentness and the runtime handler are excluded.
        This is content identity only; it grants no qualification or truth.
        """
        return {
            "capability_id": self.capability_id,
            "purpose": self.purpose,
            "boundary": self.boundary,
            "interface": self.interface,
            "invariants": list(self.invariants),
            "hazards": list(self.hazards),
            "authority": self.authority.value,
            "lineage": list(self.lineage),
            "resources": self.resources,
            "dependencies": list(self.dependencies),
            "query_obligation_id": self.query_obligation_id,
            "witness_predicate": self.witness_predicate,
            "assistance_ancestry": list(self.assistance_ancestry),
            "operational_scope_id": self.operational_scope_id,
        }

    def computed_signature_sha256(self) -> str:
        import hashlib, json
        blob = json.dumps(self.signature_payload(), sort_keys=True, separators=(",", ":"), default=str).encode()
        return hashlib.sha256(blob).hexdigest()

@dataclass
class OperationalFrameContract:
    """Externally qualified operational sensorimotor-frame artifact.

    The contract carries opaque operational structure/currentness only. It does
    not grant semantic sensor, action, object, or affordance identity.
    """

    frame_id: str
    purpose: str
    signature_sha256: str
    authority: Authority
    lineage: tuple[str, ...]
    currentness: str
    qualification: QualificationState = QualificationState.CANDIDATE
    assistance_ancestry: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    hazards: tuple[str, ...] = ()

    def serializable(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValueVariableContract:
    """Externally qualified constitutional regulatory-variable contract.

    The variable handle and viable interval are explicit constitutional priors.
    This contract lets the entity derive bounded signed regulatory pressure from
    current state without treating that pressure as semantic goal, reward, or
    self-authored value authority.
    """

    value_id: str
    purpose: str
    viable_low: float
    viable_high: float
    signature_sha256: str
    authority: Authority
    lineage: tuple[str, ...]
    currentness: str
    qualification: QualificationState = QualificationState.CANDIDATE
    assistance_ancestry: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    hazards: tuple[str, ...] = ()

    def serializable(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EpisodeSchemaContract:
    """Externally qualified operational episode/grouping-schema artifact.

    This is a content/currentness handle for the operational grouping relation
    used to produce higher-level traces. It does not grant semantic episode,
    goal, process, or persistent-identity authority.
    """

    schema_id: str
    purpose: str
    signature_sha256: str
    authority: Authority
    lineage: tuple[str, ...]
    currentness: str
    qualification: QualificationState = QualificationState.CANDIDATE
    assistance_ancestry: tuple[str, ...] = ()
    frame_epochs: tuple[tuple[str, int], ...] = ()
    value_epochs: tuple[tuple[str, int], ...] = ()
    invariants: tuple[str, ...] = ()
    hazards: tuple[str, ...] = ()
    # MS1103-1127: distributed episode/grouping relations may depend on
    # independently current counterparty and relation-specific coordination
    # premises. Appended after legacy fields to preserve positional ancestry.
    counterparty_epochs: tuple[tuple[str, int], ...] = ()
    coordination_epochs: tuple[tuple[str, int], ...] = ()

    def serializable(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OperationalCounterpartyContract:
    """Externally qualified opaque counterparty-currentness contract.

    This is an operational relation to an independently changing causal source,
    not a semantic person/self/other identity. It carries no genealogy, value,
    numerical-identity, or command authority. MS1053-1077 earned currentness
    plumbing for distributed capabilities, not a general agent ontology.
    """

    counterparty_id: str
    purpose: str
    signature_sha256: str
    authority: Authority
    lineage: tuple[str, ...]
    currentness: str
    qualification: QualificationState = QualificationState.CANDIDATE
    assistance_ancestry: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    hazards: tuple[str, ...] = ()
    operational_role_authority: str = "BOUNDED_CAUSAL_COUNTERPARTY_RELATION_ONLY"
    semantic_identity_authority: str = "NONE"
    numerical_identity_authority: str = "NONE"
    genealogy_authority: str = "NONE"
    value_state_authority: str = "NONE"

    def serializable(self) -> dict[str, Any]:
        return asdict(self)

    def signature_payload(self) -> dict[str, Any]:
        return {
            "counterparty_id": self.counterparty_id,
            "purpose": self.purpose,
            "authority": self.authority.value,
            "lineage": list(self.lineage),
            "assistance_ancestry": list(self.assistance_ancestry),
            "invariants": list(self.invariants),
            "hazards": list(self.hazards),
            "operational_role_authority": self.operational_role_authority,
            "semantic_identity_authority": self.semantic_identity_authority,
            "numerical_identity_authority": self.numerical_identity_authority,
            "genealogy_authority": self.genealogy_authority,
            "value_state_authority": self.value_state_authority,
        }

    def computed_signature_sha256(self) -> str:
        import hashlib, json
        blob = json.dumps(self.signature_payload(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(blob).hexdigest()


@dataclass
class OperationalCoordinationContract:
    """Externally qualified opaque coordination/currentness contract.

    This contract represents only a bounded mutually contingent joint-action
    relation among the local entity and one or more already-qualified opaque
    counterparties. It grants no semantic commitment, intention, promise,
    identity, hidden-value, feasibility-override, or command authority.
    """

    coordination_id: str
    purpose: str
    participant_counterparty_epochs: tuple[tuple[str, int], ...]
    signature_sha256: str
    authority: Authority
    lineage: tuple[str, ...]
    currentness: str
    qualification: QualificationState = QualificationState.CANDIDATE
    assistance_ancestry: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    hazards: tuple[str, ...] = ()
    operational_relation_authority: str = "BOUNDED_MUTUALLY_CONTINGENT_JOINT_ACTION_RELATION_ONLY"
    semantic_commitment_authority: str = "NONE"
    intention_authority: str = "NONE"
    promise_authority: str = "NONE"
    identity_authority: str = "NONE"
    value_state_authority: str = "NONE"
    feasibility_override_authority: str = "NONE"

    def serializable(self) -> dict[str, Any]:
        return asdict(self)

    def signature_payload(self) -> dict[str, Any]:
        return {
            "coordination_id": self.coordination_id,
            "purpose": self.purpose,
            "participant_counterparty_epochs": [list(x) for x in self.participant_counterparty_epochs],
            "authority": self.authority.value,
            "lineage": list(self.lineage),
            "assistance_ancestry": list(self.assistance_ancestry),
            "invariants": list(self.invariants),
            "hazards": list(self.hazards),
            "operational_relation_authority": self.operational_relation_authority,
            "semantic_commitment_authority": self.semantic_commitment_authority,
            "intention_authority": self.intention_authority,
            "promise_authority": self.promise_authority,
            "identity_authority": self.identity_authority,
            "value_state_authority": self.value_state_authority,
            "feasibility_override_authority": self.feasibility_override_authority,
        }

    def computed_signature_sha256(self) -> str:
        import hashlib, json
        blob = json.dumps(self.signature_payload(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(blob).hexdigest()


@dataclass
class RecruitmentTopologyContract:
    """Externally qualified opaque recruitment-topology contract.

    The contract represents a bounded operational relation among already-known
    capability handles. It grants no semantic parent/child role, object identity,
    feasibility, resource, value, or truth authority. MS1003-1027 earned a
    currentness-bearing structural relation, not a general topology constructor.
    """

    topology_id: str
    purpose: str
    relations: tuple[tuple[str, str], ...]
    capability_epochs: tuple[tuple[str, int], ...]
    signature_sha256: str
    authority: Authority
    lineage: tuple[str, ...]
    currentness: str
    qualification: QualificationState = QualificationState.CANDIDATE
    assistance_ancestry: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    hazards: tuple[str, ...] = ()
    semantic_role_authority: str = "NONE"
    identity_authority: str = "NONE"

    def serializable(self) -> dict[str, Any]:
        return asdict(self)

    def signature_payload(self) -> dict[str, Any]:
        """Canonical immutable content covered by signature_sha256.

        Mutable qualification/currentness are excluded so the same historical
        structural claim can become STALE without rewriting its identity.
        """
        return {
            "topology_id": self.topology_id,
            "purpose": self.purpose,
            "relations": [list(x) for x in self.relations],
            "capability_epochs": [list(x) for x in self.capability_epochs],
            "authority": self.authority.value,
            "lineage": list(self.lineage),
            "assistance_ancestry": list(self.assistance_ancestry),
            "invariants": list(self.invariants),
            "hazards": list(self.hazards),
            "semantic_role_authority": self.semantic_role_authority,
            "identity_authority": self.identity_authority,
        }

    def computed_signature_sha256(self) -> str:
        import hashlib, json
        blob = json.dumps(self.signature_payload(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(blob).hexdigest()
