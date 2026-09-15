from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from .types import Authority, CapabilityContract, QualificationState


@dataclass(frozen=True)
class CompositionResult:
    status: str
    plan: tuple[str,...]
    missing: tuple[str,...]
    authority: Authority


def compose_capabilities(contracts: dict[str, CapabilityContract], goals: Iterable[str]) -> CompositionResult:
    """Exact dependency-directed composer descended from the MS251-300 spine.

    Capability may emerge by composition; authority is never strengthened by
    composition. Ephemeral composition is the default; reification requires a
    separately qualified composite contract.
    """
    goalset=tuple(goals); plan: list[str]=[]; visiting:set[str]=set(); resolved:set[str]=set(); missing:list[str]=[]

    def ensure(cid: str) -> bool:
        if cid in resolved: return True
        if cid in visiting: return False
        c=contracts.get(cid)
        if c is None or c.qualification not in {QualificationState.QUALIFIED,QualificationState.SHADOW_QUALIFIED}:
            missing.append(cid); return False
        visiting.add(cid)
        for dep in c.dependencies:
            if not ensure(dep):
                visiting.remove(cid); return False
        visiting.remove(cid); resolved.add(cid); plan.append(cid); return True

    ok=all(ensure(g) for g in goalset)
    if not ok:
        return CompositionResult("NO_PATH",tuple(plan),tuple(dict.fromkeys(missing)),Authority.NONE)
    # Conservative lattice: effect authority is never inferred by composition;
    # otherwise the least permissive authority among leaves wins for reporting.
    auths=[contracts[x].authority for x in plan]
    if any(a==Authority.EFFECT for a in auths):
        authority=Authority.NONE
    elif all(a==Authority.DERIVED_READ_ONLY for a in auths):
        authority=Authority.DERIVED_READ_ONLY
    elif any(a==Authority.RESEARCH_ONLY for a in auths):
        authority=Authority.RESEARCH_ONLY
    else:
        authority=Authority.NONE
    return CompositionResult("COMPOSED_EPHEMERAL",tuple(plan),(),authority)
