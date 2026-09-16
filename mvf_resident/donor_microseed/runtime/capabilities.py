from __future__ import annotations
from typing import Any, Callable
from .types import Authority, CapabilityContract, QualificationState, QueryObligation


InvalidationCallback = Callable[[str, set[str], str], None]


class CapabilityRegistry:
    """Qualified capability registry with transitive currentness.

    MS841-843 exposed an integration mismatch: direct capability metadata only
    staled one dependency edge while DevelopmentRegistry already propagated
    invalidation transitively. The registry now maintains the same transitive
    semantics. Recursive composition was already conservative; metadata now
    agrees with executable currentness instead of depending on that accidental
    safety net.
    """

    def __init__(self, *, on_invalidate: InvalidationCallback | None = None):
        self.contracts: dict[str, CapabilityContract] = {}
        self.epochs: dict[str, int] = {}
        self.reverse_deps: dict[str, set[str]] = {}
        self._on_invalidate = on_invalidate

    def register(self, contract: CapabilityContract) -> None:
        if contract.capability_id in self.contracts:
            raise ValueError(f"duplicate capability: {contract.capability_id}")
        self.contracts[contract.capability_id] = contract
        self.epochs[contract.capability_id] = 0
        for dep in contract.dependencies:
            self.reverse_deps.setdefault(dep, set()).add(contract.capability_id)

    def invalidate(self, capability_id: str, *, reason: str = "DEPENDENCY_CHANGED") -> set[str]:
        """Stale a changed capability and all transitive dependents.

        History is not deleted and rejection is not rewritten as staleness.
        CANDIDATE/RESEARCH/SHADOW/QUALIFIED structures all require requalification
        if a prerequisite in their declared dependency graph changes.
        """
        stale: set[str] = set()
        queue = [capability_id]
        while queue:
            cid = queue.pop()
            if cid in stale:
                continue
            stale.add(cid)
            c = self.contracts.get(cid)
            if c is not None and c.qualification != QualificationState.REJECTED:
                c.qualification = QualificationState.STALE
                c.currentness = "STALE"
            queue.extend(sorted(self.reverse_deps.get(cid, ())))
        if self._on_invalidate is not None:
            self._on_invalidate(capability_id, stale, reason)
        return stale

    def change_dependency(self, capability_id: str, *, reason: str = "DEPENDENCY_CHANGED") -> set[str]:
        self.epochs[capability_id] = self.epochs.get(capability_id, 0) + 1
        return self.invalidate(capability_id, reason=reason)

    def invoke(self, capability_id: str, obligation: QueryObligation, **kwargs: Any) -> dict[str, Any]:
        c = self.contracts.get(capability_id)
        if c is None:
            return {"status": "NO_PATH", "authority": Authority.NONE.value}
        if c.qualification not in {QualificationState.QUALIFIED, QualificationState.SHADOW_QUALIFIED}:
            return {"status": "UNKNOWN_INCOMPLETE", "reason": c.qualification.value,
                    "authority": Authority.NONE.value}
        if c.query_obligation_id and c.query_obligation_id != obligation.obligation_id:
            return {"status": "UNKNOWN_INCOMPLETE", "reason": "QUERY_OBLIGATION_MISMATCH",
                    "authority": Authority.NONE.value}
        if c.operational_scope_id and c.operational_scope_id != obligation.operational_scope_id:
            return {"status": "UNKNOWN_INCOMPLETE", "reason": "OPERATIONAL_SCOPE_MISMATCH",
                    "authority": Authority.NONE.value}
        if c.handler is None:
            return {"status": "UNKNOWN_INCOMPLETE", "reason": "NO_HANDLER",
                    "authority": Authority.NONE.value}
        value = c.handler(**kwargs)
        return {"status": "CAPABILITY_RESULT", "capability_id": capability_id,
                "authority": c.authority.value, "value": value}

    def snapshot(self) -> dict[str, Any]:
        return {k: v.serializable() for k, v in sorted(self.contracts.items())}
