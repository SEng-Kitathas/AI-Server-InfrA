from __future__ import annotations
from typing import Callable
from ..runtime.types import OperationalCoordinationContract, QualificationState

CoordinationInvalidationCallback = Callable[[str, int, str], None]


class OperationalCoordinationRegistry:
    """Currentness registry for externally qualified opaque joint-action relations.

    A relation is narrower than a counterparty: one independently changing
    counterparty can participate in several separately current coordination
    relations. The registry does not learn those relations or grant semantic
    commitment/intention/promise authority.
    """

    def __init__(self, *, on_invalidate: CoordinationInvalidationCallback | None = None):
        self.contracts: dict[str, OperationalCoordinationContract] = {}
        self.epochs: dict[str, int] = {}
        self.counterparty_dependents: dict[str, set[str]] = {}
        self.capability_dependents: dict[str, set[str]] = {}
        self._on_invalidate = on_invalidate

    def register(self, contract: OperationalCoordinationContract) -> None:
        rid = contract.coordination_id
        if not rid:
            raise ValueError("COORDINATION_EMPTY_HANDLE")
        if rid in self.contracts:
            raise ValueError(f"duplicate coordination relation: {rid}")
        if contract.qualification not in {QualificationState.QUALIFIED, QualificationState.SHADOW_QUALIFIED}:
            raise ValueError("coordination relation must be externally qualified before registration")
        if not contract.signature_sha256:
            raise ValueError("coordination relation requires content-bound signature_sha256")
        if contract.signature_sha256 != contract.computed_signature_sha256():
            raise ValueError("COORDINATION_SIGNATURE_CONTENT_MISMATCH")
        if contract.operational_relation_authority != "BOUNDED_MUTUALLY_CONTINGENT_JOINT_ACTION_RELATION_ONLY":
            raise ValueError("COORDINATION_RELATION_AUTHORITY_EXCEEDS_CEILING")
        for name in (
            "semantic_commitment_authority", "intention_authority", "promise_authority",
            "identity_authority", "value_state_authority", "feasibility_override_authority",
        ):
            if getattr(contract, name) != "NONE":
                raise ValueError("COORDINATION_FORBIDDEN_AUTHORITY:" + name)
        deps = tuple((str(cid), int(epoch)) for cid, epoch in contract.participant_counterparty_epochs)
        if not deps:
            raise ValueError("COORDINATION_REQUIRES_COUNTERPARTY_DEPENDENCY")
        ids = [cid for cid, _ in deps]
        if any(not cid or epoch < 0 for cid, epoch in deps):
            raise ValueError("COORDINATION_INVALID_COUNTERPARTY_EPOCH")
        if len(ids) != len(set(ids)):
            raise ValueError("COORDINATION_DUPLICATE_COUNTERPARTY_DEPENDENCY")
        if deps != contract.participant_counterparty_epochs:
            raise ValueError("COORDINATION_COUNTERPARTY_EPOCHS_NOT_CANONICAL")
        self.contracts[rid] = contract
        self.epochs[rid] = 0
        for cid, _ in deps:
            self.counterparty_dependents.setdefault(cid, set()).add(rid)

    def bind_capability(self, coordination_id: str, capability_id: str) -> None:
        if coordination_id not in self.contracts:
            raise ValueError(f"unknown coordination relation: {coordination_id}")
        self.capability_dependents.setdefault(coordination_id, set()).add(capability_id)

    def is_current(self, coordination_id: str, epoch: int | None = None) -> bool:
        c = self.contracts.get(coordination_id)
        if c is None or c.qualification not in {QualificationState.QUALIFIED, QualificationState.SHADOW_QUALIFIED}:
            return False
        if epoch is not None and self.epochs.get(coordination_id, -1) != int(epoch):
            return False
        return True

    def change(self, coordination_id: str, *, reason: str = "COORDINATION_RELATION_CHANGED") -> int:
        if coordination_id not in self.contracts:
            raise ValueError(f"unknown coordination relation: {coordination_id}")
        self.epochs[coordination_id] = self.epochs.get(coordination_id, 0) + 1
        c = self.contracts[coordination_id]
        c.qualification = QualificationState.STALE
        c.currentness = "STALE"
        if self._on_invalidate is not None:
            self._on_invalidate(coordination_id, self.epochs[coordination_id], reason)
        return self.epochs[coordination_id]

    def invalidate_by_counterparty(self, counterparty_id: str, *, reason: str) -> set[str]:
        changed: set[str] = set()
        for rid in sorted(self.counterparty_dependents.get(counterparty_id, ())):
            if self.is_current(rid):
                self.change(rid, reason=f"COUNTERPARTY:{counterparty_id}:{reason}")
                changed.add(rid)
        return changed

    def snapshot(self) -> dict[str, dict]:
        return {
            rid: {
                "contract": c.serializable(),
                "epoch": self.epochs.get(rid, 0),
                "capability_dependents": sorted(self.capability_dependents.get(rid, ())),
            }
            for rid, c in sorted(self.contracts.items())
        }
