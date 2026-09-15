from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from ..runtime.types import Authority, EvidenceRef, EpistemicStatus, QualificationState
from .ledger import EvidenceLedger


@dataclass(frozen=True)
class QualificationDecision:
    state: QualificationState
    authority: Authority
    reason: str


class FixedQualifier:
    """Out-of-band qualifier firewall.

    Proposal machinery may change. Qualification policy does not accept policy
    mutation from the proposal under review. MS862 adds a second lock: evidence
    being content-resolved is not enough; it must carry a supportive epistemic
    disposition. EVIDENCE_RESOLVED != EVIDENCE_SUPPORTIVE.
    """

    SUPPORTIVE_DISPOSITIONS = {
        EpistemicStatus.PROVED,
        EpistemicStatus.PRESSURE_SUPPORTED,
    }

    def __init__(self, ledger: EvidenceLedger):
        self.ledger = ledger

    def decide(self, evidence: Iterable[EvidenceRef], requested_authority: Authority,
               *, allow_effect: bool = False) -> QualificationDecision:
        refs = tuple(evidence)
        if not refs:
            return QualificationDecision(QualificationState.REJECTED, Authority.NONE,
                                         "NO_EVIDENCE")
        ok, missing = self.ledger.resolve(refs)
        if not ok:
            return QualificationDecision(QualificationState.REJECTED, Authority.NONE,
                                         f"UNRESOLVED_EVIDENCE:{','.join(missing)}")
        if any(r.negative for r in refs):
            return QualificationDecision(QualificationState.REJECTED, Authority.NONE,
                                         "NEGATIVE_EVIDENCE_PRESENT")
        unsupported = [r.evidence_id for r in refs if r.disposition not in self.SUPPORTIVE_DISPOSITIONS]
        if unsupported:
            return QualificationDecision(
                QualificationState.REJECTED,
                Authority.NONE,
                f"NON_SUPPORTIVE_EVIDENCE:{','.join(unsupported)}",
            )
        if requested_authority == Authority.EFFECT and not allow_effect:
            return QualificationDecision(QualificationState.RESEARCH_ONLY, Authority.NONE,
                                         "EFFECT_AUTHORITY_NOT_GRANTED_BY_QUALIFICATION")
        if requested_authority in (Authority.NONE, Authority.RESEARCH_ONLY):
            return QualificationDecision(QualificationState.RESEARCH_ONLY,
                                         Authority.RESEARCH_ONLY, "RESEARCH_ONLY")
        if requested_authority in {
            Authority.MODEL_OUTPUT_ONLY, Authority.OBSERVATION_ONLY,
            Authority.REFERENCE_ONLY, Authority.DERIVED_READ_ONLY,
        }:
            return QualificationDecision(QualificationState.SHADOW_QUALIFIED,
                                         requested_authority, "EVIDENCE_BOUND_SHADOW")
        return QualificationDecision(QualificationState.REJECTED, Authority.NONE,
                                     "UNRECOGNIZED_AUTHORITY_REQUEST")
