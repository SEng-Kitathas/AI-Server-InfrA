from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class PredicateResult:
    values: tuple[bool,...]
    qualification: str
    frame_scope: str


def change(samples: Sequence[int], *, frame_scope: str="SAMPLE_ADJACENT") -> PredicateResult:
    vals=tuple(samples[i] != samples[i-1] for i in range(1,len(samples)))
    return PredicateResult(vals,"RESEARCH_ONLY",frame_scope)


def rise(samples: Sequence[int], *, frame_scope: str="SAMPLE_ADJACENT") -> PredicateResult:
    vals=tuple(bool(samples[i]) and not bool(samples[i-1]) for i in range(1,len(samples)))
    return PredicateResult(vals,"RESEARCH_ONLY",frame_scope)


ASSISTANCE_DENOMINATOR = (
    "ONE_STEP_REGISTER_MEMORY_SUPPLIED",
    "UPDATE_BOUNDARIES_SUPPLIED",
    "BOOLEAN_STATEFUL_SUBSTRATE_SUPPLIED",
    "ANTI_UNIFICATION_SUPPLIED",
    "QUALIFICATION_EVALUATOR_SUPPLIED",
)
