from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence, Hashable


@dataclass(frozen=True)
class FrameInference:
    status: str
    boundaries: tuple[int,...]
    reason: str
    authority: str = "RESEARCH_ONLY"


def effect_stationarity_boundaries(effects: Sequence[Hashable]) -> tuple[int,...]:
    if not effects: return ()
    b=[0]
    for i in range(1,len(effects)):
        if effects[i] != effects[i-1]: b.append(i)
    return tuple(b)


def infer_event_frame(effects: Sequence[Hashable], *, rival_segmentations: Sequence[Sequence[int]] | None=None) -> FrameInference:
    """Bounded operational segmentation; explicit UNKNOWN under observational equivalence.

    This deliberately does not claim that recovered boundaries are true events.
    """
    proposed=effect_stationarity_boundaries(effects)
    if rival_segmentations:
        distinct={tuple(x) for x in rival_segmentations}
        if len(distinct)>1:
            return FrameInference("UNKNOWN_INCOMPLETE",(),"MULTIPLE_LAWFUL_EVENT_FRAMES")
    return FrameInference("NOMINATED_OPERATIONAL_FRAME",proposed,
                          "ACTION_EFFECT_STATIONARITY_WITH_SUPPLIED_EFFECT_CHANNEL")
