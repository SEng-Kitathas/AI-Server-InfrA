from __future__ import annotations
from typing import Callable
from ..runtime.types import OperationalCounterpartyContract, QualificationState

CounterpartyInvalidationCallback = Callable[[str, int, str], None]


class OperationalCounterpartyRegistry:
    """Currentness registry for externally qualified opaque counterparties.

    A counterparty is only an operationally distinguished independently changing
    causal relation. Registration does not establish semantic actor identity,
    genealogy, numerical individuality, hidden value state, or command authority.
    """

    def __init__(self, *, on_invalidate: CounterpartyInvalidationCallback | None = None):
        self.contracts: dict[str, OperationalCounterpartyContract] = {}
        self.epochs: dict[str, int] = {}
        self.capability_dependents: dict[str, set[str]] = {}
        self._on_invalidate = on_invalidate

    def register(self, contract: OperationalCounterpartyContract) -> None:
        cid=contract.counterparty_id
        if not cid:
            raise ValueError("COUNTERPARTY_EMPTY_HANDLE")
        if cid in self.contracts:
            raise ValueError(f"duplicate counterparty: {cid}")
        if contract.qualification not in {QualificationState.QUALIFIED, QualificationState.SHADOW_QUALIFIED}:
            raise ValueError("counterparty must be externally qualified before registration")
        if not contract.signature_sha256:
            raise ValueError("counterparty requires content-bound signature_sha256")
        if contract.signature_sha256 != contract.computed_signature_sha256():
            raise ValueError("COUNTERPARTY_SIGNATURE_CONTENT_MISMATCH")
        if contract.operational_role_authority != "BOUNDED_CAUSAL_COUNTERPARTY_RELATION_ONLY":
            raise ValueError("COUNTERPARTY_ROLE_AUTHORITY_EXCEEDS_CEILING")
        for name in ("semantic_identity_authority","numerical_identity_authority","genealogy_authority","value_state_authority"):
            if getattr(contract,name) != "NONE":
                raise ValueError("COUNTERPARTY_FORBIDDEN_AUTHORITY:"+name)
        self.contracts[cid]=contract
        self.epochs[cid]=0

    def bind_capability(self, counterparty_id: str, capability_id: str) -> None:
        if counterparty_id not in self.contracts:
            raise ValueError(f"unknown counterparty: {counterparty_id}")
        self.capability_dependents.setdefault(counterparty_id,set()).add(capability_id)

    def is_current(self, counterparty_id: str, epoch: int | None = None) -> bool:
        c=self.contracts.get(counterparty_id)
        if c is None or c.qualification not in {QualificationState.QUALIFIED,QualificationState.SHADOW_QUALIFIED}:
            return False
        if epoch is not None and self.epochs.get(counterparty_id,-1)!=int(epoch):
            return False
        return True

    def change(self, counterparty_id: str, *, reason: str="COUNTERPARTY_RELATION_CHANGED") -> int:
        if counterparty_id not in self.contracts:
            raise ValueError(f"unknown counterparty: {counterparty_id}")
        self.epochs[counterparty_id]=self.epochs.get(counterparty_id,0)+1
        c=self.contracts[counterparty_id]
        c.qualification=QualificationState.STALE
        c.currentness="STALE"
        if self._on_invalidate is not None:
            self._on_invalidate(counterparty_id,self.epochs[counterparty_id],reason)
        return self.epochs[counterparty_id]

    def snapshot(self) -> dict[str,dict]:
        return {cid:{"contract":c.serializable(),"epoch":self.epochs.get(cid,0),"capability_dependents":sorted(self.capability_dependents.get(cid,()))} for cid,c in sorted(self.contracts.items())}
