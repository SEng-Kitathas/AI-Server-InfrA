from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence, Hashable


@dataclass(frozen=True)
class ReferentNomination:
    status: str
    groups: tuple[tuple[int,...],...]
    reason: str
    identity_authority: str = "NONE"


def nominate_by_boundary_coherence(channel_boundaries: Sequence[Sequence[Hashable]]) -> ReferentNomination:
    """Nominate channel partitions by boundary coherence, never object identity.

    Equal/coherent signatures may suggest grouping. Symmetric equally lawful groupings
    remain UNKNOWN rather than receiving an invented object label.
    """
    sig_to_channels: dict[tuple[Hashable,...], list[int]]={}
    for i,b in enumerate(channel_boundaries):
        sig_to_channels.setdefault(tuple(b),[]).append(i)
    groups=tuple(tuple(v) for _,v in sorted(sig_to_channels.items(),key=lambda kv:kv[1][0]))
    if len(groups)==1 and len(channel_boundaries)>1:
        return ReferentNomination("UNKNOWN_INCOMPLETE",groups,
                                  "BOUNDARY_SYNCHRONY_DOES_NOT_IDENTIFY_DISTINCT_REFERENTS")
    return ReferentNomination("REFERENT_PARTITION_NOMINATED",groups,
                              "BOUNDARY_COHERENCE_ONLY")
