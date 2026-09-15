from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class ContinuityAssessment:
    state_persisted: bool
    developmental_history_persisted: bool
    unfinished_discriminator_persisted: bool
    learned_dependencies_persisted: bool
    identity_claim: str = "NOT_QUALIFIED"

    @property
    def status(self) -> str:
        if all((self.state_persisted, self.developmental_history_persisted,
                self.unfinished_discriminator_persisted, self.learned_dependencies_persisted)):
            return "STATE_AND_DEVELOPMENTAL_CONTINUITY_INFRASTRUCTURE_PRESENT"
        return "PARTIAL_PERSISTENCE_ONLY"


def assess_continuity(*, state: bool, history: bool, unfinished: bool, deps: bool) -> ContinuityAssessment:
    # Deliberately never returns SELF_PERSISTENCE_PROVED.
    return ContinuityAssessment(state, history, unfinished, deps)


@dataclass(frozen=True)
class DevelopmentalContinuityWitness:
    """Typed, bounded interpretation of two developmental-biography graphs.

    MS1028-1052 established that causal graph lineage can support an operational
    branch-relative continuation relation through structural rewrite, but cannot
    establish numerical selfhood or execution uniqueness under perfect copying.
    This witness therefore makes the authority ceiling executable instead of
    leaving callers to over-read strings such as SAME_BIOGRAPHY_STATE.
    """

    relation: str
    branch_semantics: str
    source_graph_digest: str | None
    target_graph_digest: str | None
    shared_event_count: int
    source_head_count: int
    target_head_count: int
    copy_ambiguity: bool
    lineage_authority: str = "OPERATIONAL_DEVELOPMENTAL_LINEAGE_ONLY"
    numerical_identity_authority: str = "NONE"
    semantic_self_authority: str = "NONE"
    exclusive_successor_authority: str = "NOT_ESTABLISHED_BY_INTERNAL_BIOGRAPHY"
    selfhood_claim: str = "NOT_QUALIFIED"

    def serializable(self) -> dict[str, Any]:
        return asdict(self)


def continuity_witness_from_exports(
    source: dict[str, Any],
    target: dict[str, Any],
    *,
    relation: str,
) -> DevelopmentalContinuityWitness:
    """Build a non-selfhood witness from already-validated biography relation.

    The source/target orientation is explicit: source is the earlier/comparator
    biography and target is the biography being assessed as a possible
    continuation.  Graph equality is classified as copy-ambiguous rather than
    as numerical identity.
    """

    source_ids={str(e.get("event_id")) for e in source.get("events", ()) if e.get("event_id")}
    target_ids={str(e.get("event_id")) for e in target.get("events", ()) if e.get("event_id")}
    mapping={
        "SAME_BIOGRAPHY_STATE": "GRAPH_STATE_EQUIVALENT__COPY_AMBIGUOUS",
        "DESCENDANT_CONTINUATION": "BRANCH_RELATIVE_DESCENDANT_CONTINUATION",
        "ANCESTOR_STATE": "BRANCH_RELATIVE_ANCESTOR_STATE",
        "COMMON_ANCESTRY_DIVERGED": "SIBLING_OR_DIVERGED_BRANCHES",
        "UNRELATED_OR_UNKNOWN": "UNRELATED_OR_UNKNOWN",
        "UNKNOWN_INCOMPLETE": "UNKNOWN_INCOMPLETE",
    }
    return DevelopmentalContinuityWitness(
        relation=relation,
        branch_semantics=mapping.get(relation, "UNKNOWN_INCOMPLETE"),
        source_graph_digest=source.get("graph_digest"),
        target_graph_digest=target.get("graph_digest"),
        shared_event_count=len(source_ids & target_ids),
        source_head_count=len(source.get("heads", ())),
        target_head_count=len(target.get("heads", ())),
        copy_ambiguity=relation == "SAME_BIOGRAPHY_STATE",
    )
