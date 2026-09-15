from __future__ import annotations
from typing import Callable, Iterable
from ..runtime.types import RecruitmentTopologyContract, QualificationState

TopologyInvalidationCallback = Callable[[str, int, str], None]


class RecruitmentTopologyRegistry:
    """Currentness registry for externally qualified opaque recruitment topology.

    MS1003-1027 earned a narrow structural relation: bounded intervention-based
    evidence can nominate sparse operational relations whose held-out predictive
    utility exceeds an additive/no-relation baseline. The research learner remains
    outside the entity because its pairwise candidate language, search and
    thresholds are supplied and fail higher-order-only structure.

    This registry therefore stores *already externally qualified* operational
    topology contracts and tracks their developmental currentness. It grants no
    semantic parent/child role, object identity, feasibility, resource, or truth
    authority.
    """

    def __init__(self, *, on_invalidate: TopologyInvalidationCallback | None = None):
        self.topologies: dict[str, RecruitmentTopologyContract] = {}
        self.epochs: dict[str, int] = {}
        # capability -> topology contracts that were qualified against it
        self.constituent_dependents: dict[str, set[str]] = {}
        # topology -> admitted capabilities that explicitly depend on it
        self.capability_dependents: dict[str, set[str]] = {}
        self._on_invalidate = on_invalidate

    @staticmethod
    def _normalized_relations(
        relations: Iterable[tuple[str, str]],
    ) -> tuple[tuple[str, str], ...]:
        out: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for raw in relations:
            if len(raw) != 2:
                raise ValueError("TOPOLOGY_RELATION_ARITY_MUST_BE_TWO")
            a, b = str(raw[0]), str(raw[1])
            if not a or not b:
                raise ValueError("TOPOLOGY_RELATION_EMPTY_HANDLE")
            if a == b:
                raise ValueError("TOPOLOGY_SELF_RELATION_FORBIDDEN")
            edge = tuple(sorted((a, b)))
            if edge in seen:
                raise ValueError("TOPOLOGY_DUPLICATE_RELATION")
            seen.add(edge)
            out.append(edge)
        if not out:
            raise ValueError("TOPOLOGY_REQUIRES_NONEMPTY_RELATIONS")
        return tuple(sorted(out))

    def register(self, contract: RecruitmentTopologyContract) -> None:
        if contract.topology_id in self.topologies:
            raise ValueError(f"duplicate recruitment topology: {contract.topology_id}")
        if contract.qualification not in {
            QualificationState.QUALIFIED,
            QualificationState.SHADOW_QUALIFIED,
        }:
            raise ValueError("recruitment topology must be externally qualified before registration")
        if not contract.signature_sha256:
            raise ValueError("recruitment topology requires content-bound signature_sha256")
        if contract.signature_sha256 != contract.computed_signature_sha256():
            raise ValueError("TOPOLOGY_SIGNATURE_CONTENT_MISMATCH")
        if contract.semantic_role_authority != "NONE":
            raise ValueError("TOPOLOGY_SEMANTIC_ROLE_AUTHORITY_FORBIDDEN")
        if contract.identity_authority != "NONE":
            raise ValueError("TOPOLOGY_IDENTITY_AUTHORITY_FORBIDDEN")
        normalized = self._normalized_relations(contract.relations)
        if normalized != tuple(contract.relations):
            raise ValueError("TOPOLOGY_RELATIONS_MUST_BE_CANONICALLY_NORMALIZED")
        if any(int(epoch) < 0 for _, epoch in contract.capability_epochs):
            raise ValueError("TOPOLOGY_NEGATIVE_CAPABILITY_EPOCH")
        epoch_ids = [cid for cid, _ in contract.capability_epochs]
        if len(epoch_ids) != len(set(epoch_ids)):
            raise ValueError("TOPOLOGY_DUPLICATE_CAPABILITY_EPOCH")
        nodes = {x for edge in normalized for x in edge}
        if not nodes.issubset(set(epoch_ids)):
            missing = sorted(nodes - set(epoch_ids))
            raise ValueError("TOPOLOGY_RELATION_WITHOUT_CAPABILITY_EPOCH:" + ",".join(missing))
        self.topologies[contract.topology_id] = contract
        self.epochs[contract.topology_id] = 0
        for cid, _ in contract.capability_epochs:
            self.constituent_dependents.setdefault(cid, set()).add(contract.topology_id)

    def bind_capability(self, topology_id: str, capability_id: str) -> None:
        if topology_id not in self.topologies:
            raise ValueError(f"unknown recruitment topology: {topology_id}")
        self.capability_dependents.setdefault(topology_id, set()).add(capability_id)

    def is_current(self, topology_id: str, epoch: int | None = None) -> bool:
        contract = self.topologies.get(topology_id)
        if contract is None or contract.qualification not in {
            QualificationState.QUALIFIED,
            QualificationState.SHADOW_QUALIFIED,
        }:
            return False
        if epoch is not None and self.epochs.get(topology_id, -1) != int(epoch):
            return False
        return True

    def change(self, topology_id: str, *, reason: str = "RECRUITMENT_TOPOLOGY_CHANGED") -> int:
        if topology_id not in self.topologies:
            raise ValueError(f"unknown recruitment topology: {topology_id}")
        self.epochs[topology_id] = self.epochs.get(topology_id, 0) + 1
        contract = self.topologies[topology_id]
        contract.qualification = QualificationState.STALE
        contract.currentness = "STALE"
        if self._on_invalidate is not None:
            self._on_invalidate(topology_id, self.epochs[topology_id], reason)
        return self.epochs[topology_id]

    def invalidate_by_capability(self, capability_id: str, *, reason: str) -> set[str]:
        """Stale current topology contracts qualified against a changed constituent."""
        changed: set[str] = set()
        for topology_id in sorted(self.constituent_dependents.get(capability_id, ())):
            if self.is_current(topology_id):
                self.change(topology_id, reason=f"CAPABILITY:{capability_id}:{reason}")
                changed.add(topology_id)
        return changed

    def nodes(self, topology_id: str) -> set[str]:
        contract = self.topologies.get(topology_id)
        if contract is None:
            return set()
        return {x for edge in contract.relations for x in edge}

    def snapshot(self) -> dict[str, dict]:
        return {
            tid: {
                "contract": contract.serializable(),
                "epoch": self.epochs.get(tid, 0),
                "capability_dependents": sorted(self.capability_dependents.get(tid, ())),
            }
            for tid, contract in sorted(self.topologies.items())
        }
