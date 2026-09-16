from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

BASE_OPS = ("ID","ZERO","INC","DEC","SAT_INC","SAT_DEC")


def op_apply(name: str, s: int, K: int) -> int:
    if name=="ID": return s
    if name=="ZERO": return 0
    if name=="INC": return (s+1)%K
    if name=="DEC": return (s-1)%K
    if name=="SAT_INC": return min(K-1,s+1)
    if name=="SAT_DEC": return max(0,s-1)
    raise KeyError(name)


def compose(f: tuple[int,...], g: tuple[int,...]) -> tuple[int,...]:
    return tuple(f[g[s]] for s in range(len(g)))


def base_closure(K: int) -> set[tuple[int,...]]:
    gens={name:tuple(op_apply(name,s,K) for s in range(K)) for name in BASE_OPS}
    seen=set(gens.values()); q=list(seen)
    while q:
        f=q.pop()
        for g in gens.values():
            for h in (compose(f,g),compose(g,f)):
                if h not in seen: seen.add(h); q.append(h)
    return seen


def swap_pair(K: int,a: int,b: int) -> tuple[int,...]:
    return tuple(b if s==a else a if s==b else s for s in range(K))


def cycle3(K: int,a: int,b: int,c: int) -> tuple[int,...]:
    return tuple(b if s==a else c if s==b else a if s==c else s for s in range(K))


@dataclass(frozen=True)
class ResearchOperator:
    name: str
    arity: int
    status: str = "RESEARCH_ONLY"
    assistance_ancestry: tuple[str,...] = (
        "STATE_IDENTITY_SUPPLIED", "TRANSITION_BOUNDARIES_SUPPLIED",
        "GENERIC_BRANCH_METALANGUAGE_SUPPLIED", "EVALUATOR_SUPPLIED",
    )


RESEARCH_OPERATORS = {
    "SWAP_PAIR": ResearchOperator("SWAP_PAIR",2),
    "CYCLE3": ResearchOperator("CYCLE3",3),
}
