from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Callable, Hashable, Iterable, Any


@dataclass(frozen=True)
class Hypothesis:
    hypothesis_id: str
    predict: Callable[[Hashable], Any]
    complexity: int = 1


class HypothesisSet:
    """Bounded candidate maintenance + active disagreement probing (MS477 lineage)."""
    def __init__(self, hypotheses: Iterable[Hypothesis]):
        self.live = list(hypotheses)
        self.observations: dict[Hashable, Any] = {}

    def observe(self, x: Hashable, y: Any) -> None:
        self.observations[x] = y
        self.live = [h for h in self.live if h.predict(x) == y]

    def best_probe(self, candidates: Iterable[Hashable]) -> Hashable | None:
        if len(self.live) <= 1:
            return None
        best = None; best_entropy = -1.0
        for x in candidates:
            if x in self.observations:
                continue
            counts: dict[Any,int] = {}
            for h in self.live:
                counts[h.predict(x)] = counts.get(h.predict(x),0) + 1
            n = len(self.live)
            ent = -sum((c/n)*math.log2(c/n) for c in counts.values())
            if ent > best_entropy:
                best_entropy = ent; best = x
        # A zero-entropy candidate does not discriminate the live hypotheses.
        # Returning it as a probe creates a false impression that current action
        # access can reduce the ambiguity (MS1148).
        return best if best_entropy > 0.0 else None

    def disposition(self) -> str:
        if len(self.live) == 1: return "IDENTIFIED_WITHIN_CANDIDATE_SET"
        if len(self.live) == 0: return "MODEL_SPACE_MISSPECIFIED_OR_CONTRADICTED"
        return "UNRESOLVED"
