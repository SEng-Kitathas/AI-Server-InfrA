from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any

class TernaryCommitment(str, Enum):
    """Coarse premise-licensing stance, not truth or confidence."""
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"

@dataclass(frozen=True)
class RelationalCommitment:
    """Lossless adapter surface over existing decision-bearing state."""
    commitment_id: str
    target_id: str
    commitment: TernaryCommitment
    binding: TernaryCommitment = TernaryCommitment.YES
    applicability: TernaryCommitment = TernaryCommitment.YES
    reason: str = "UNDECLARED"
    qualifiers: tuple[tuple[str, str], ...] = ()
    premise_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.commitment_id or not self.target_id:
            raise ValueError("EMPTY_RELATIONAL_COMMITMENT_ID_OR_TARGET")
        object.__setattr__(self, "commitment", TernaryCommitment(self.commitment))
        object.__setattr__(self, "binding", TernaryCommitment(self.binding))
        object.__setattr__(self, "applicability", TernaryCommitment(self.applicability))
        object.__setattr__(self, "reason", str(self.reason or "UNDECLARED"))
        object.__setattr__(self, "qualifiers", tuple((str(k), str(v)) for k, v in self.qualifiers))
        object.__setattr__(self, "premise_ids", tuple(str(x) for x in self.premise_ids))

    @property
    def evaluable(self) -> bool:
        return self.binding == TernaryCommitment.YES and self.applicability == TernaryCommitment.YES

    @property
    def coarse_null(self) -> bool:
        return self.binding == TernaryCommitment.NO or self.applicability == TernaryCommitment.NO

    @property
    def gate_unknown(self) -> bool:
        return (not self.coarse_null) and (
            self.binding == TernaryCommitment.UNKNOWN or self.applicability == TernaryCommitment.UNKNOWN
        )

    def licenses_yes(self) -> bool:
        return self.evaluable and self.commitment == TernaryCommitment.YES

    def licenses_no(self) -> bool:
        return self.evaluable and self.commitment == TernaryCommitment.NO

    def abstains(self) -> bool:
        return (not self.evaluable) or self.commitment == TernaryCommitment.UNKNOWN

    def qualifier(self, key: str, default: str | None = None) -> str | None:
        for k, v in self.qualifiers:
            if k == key:
                return v
        return default

    def serializable(self) -> dict[str, Any]:
        return {
            "commitment_id": self.commitment_id,
            "target_id": self.target_id,
            "commitment": self.commitment.value,
            "binding": self.binding.value,
            "applicability": self.applicability.value,
            "reason": self.reason,
            "qualifiers": [[k, v] for k, v in self.qualifiers],
            "premise_ids": list(self.premise_ids),
        }

    @classmethod
    def from_serializable(cls, d: dict[str, Any]) -> "RelationalCommitment":
        return cls(
            commitment_id=d["commitment_id"], target_id=d["target_id"],
            commitment=TernaryCommitment(d["commitment"]),
            binding=TernaryCommitment(d.get("binding", "YES")),
            applicability=TernaryCommitment(d.get("applicability", "YES")),
            reason=d.get("reason", "UNDECLARED"),
            qualifiers=tuple((str(k), str(v)) for k, v in d.get("qualifiers", ())),
            premise_ids=tuple(str(x) for x in d.get("premise_ids", ())),
        )


def conjoin_required_commitments(
    commitments,
    *,
    commitment_id: str,
    target_id: str,
    reason_prefix: str = "REQUIRED_PREMISE",
) -> RelationalCommitment:
    """Conjoin required premise licenses without creating new authority.

    A current evaluable NO vetoes the conjunction. YES is licensed only when
    every required premise licenses YES. Any unresolved premise preserves
    UNKNOWN. The helper ranks nothing and grants no execution or truth authority.
    """
    rows = tuple(commitments)
    if not rows:
        return RelationalCommitment(
            commitment_id=commitment_id,
            target_id=target_id,
            commitment=TernaryCommitment.UNKNOWN,
            binding=TernaryCommitment.UNKNOWN,
            reason=f"{reason_prefix}_SET_EMPTY",
            qualifiers=(("authority_gain", "NONE"),),
        )

    if any(row.licenses_no() for row in rows):
        stance = TernaryCommitment.NO
        reason = f"{reason_prefix}_REFUSED"
    elif all(row.licenses_yes() for row in rows):
        stance = TernaryCommitment.YES
        reason = f"{reason_prefix}_ALL_LICENSED"
    else:
        stance = TernaryCommitment.UNKNOWN
        reason = f"{reason_prefix}_UNRESOLVED"

    return RelationalCommitment(
        commitment_id=commitment_id,
        target_id=target_id,
        commitment=stance,
        reason=reason,
        qualifiers=(
            ("authority_gain", "NONE"),
            ("composition", "CONJUNCTIVE_PREMISE_LICENSE_ONLY"),
        ),
        premise_ids=tuple(row.commitment_id for row in rows),
    )
