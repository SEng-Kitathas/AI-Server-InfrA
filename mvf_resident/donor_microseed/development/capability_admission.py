from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any, Iterable
from ..runtime.types import Authority, CapabilityContract, EvidenceRef, QualificationState
from ..evidence.authority import FixedQualifier
from ..evidence.ledger import EvidenceLedger, canonical_json, sha256_bytes


@dataclass(frozen=True)
class CapabilityCandidate:
    """Proposal-only description of a potentially reusable composition.

    The proposal may now be nominated from bounded entity-side operational
    traces, but it still carries no admission authority. Proposal evidence is
    ancestry about why the entity nominated the candidate; it is not silently
    treated as independent qualification evidence.
    """

    candidate_id: str
    proposed_contract: CapabilityContract
    evidence: tuple[EvidenceRef, ...]
    assistance_ancestry: tuple[str, ...] = ()
    nomination_basis: str = "UNDECLARED"
    source_trace_ids: tuple[str, ...] = ()
    operational_signature: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.proposed_contract.qualification != QualificationState.CANDIDATE:
            raise ValueError("proposed contract must remain CANDIDATE before external qualification")
        if self.proposed_contract.capability_id != self.candidate_id:
            raise ValueError("candidate_id must equal proposed capability_id")

    def serializable(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "proposed_contract": self.proposed_contract.serializable(),
            "evidence": [asdict(x) for x in self.evidence],
            "assistance_ancestry": list(self.assistance_ancestry),
            "nomination_basis": self.nomination_basis,
            "source_trace_ids": list(self.source_trace_ids),
            "operational_signature": self.operational_signature,
        }

    def digest(self) -> str:
        return sha256_bytes(canonical_json(self.serializable()))


@dataclass(frozen=True)
class CapabilityQualificationTicket:
    """Externally issued, content-bound qualification decision.

    `evidence_ids` remains bound to the proposal's own evidence ancestry for
    compatibility and audit. `qualification_evidence` is a separate set that may
    be produced after nomination by HSP/another external qualification boundary.
    This allows later evidence to qualify a proposal without rewriting what the
    entity knew when it nominated it.
    """

    candidate_id: str
    candidate_sha256: str
    state: QualificationState
    authority: Authority
    qualifier_id: str
    reason: str
    evidence_ids: tuple[str, ...]
    qualification_evidence: tuple[EvidenceRef, ...] = ()


class ExternalCapabilityQualifier:
    """Harness-side qualifier for experiments/Main-Dev, not Microseed cognition."""

    def __init__(self, ledger: EvidenceLedger, *, qualifier_id: str = "HSP-EXTERNAL-QUALIFIER"):
        if not qualifier_id or qualifier_id.upper().startswith("MICROSEED"):
            raise ValueError("qualifier_id must identify an external qualification boundary")
        self.qualifier_id = qualifier_id
        self.fixed = FixedQualifier(ledger)

    def qualify(
        self,
        candidate: CapabilityCandidate,
        *,
        qualification_evidence: Iterable[EvidenceRef] | None = None,
    ) -> CapabilityQualificationTicket:
        refs = tuple(candidate.evidence if qualification_evidence is None else qualification_evidence)
        decision = self.fixed.decide(refs, candidate.proposed_contract.authority)
        return CapabilityQualificationTicket(
            candidate_id=candidate.candidate_id,
            candidate_sha256=candidate.digest(),
            state=decision.state,
            authority=decision.authority,
            qualifier_id=self.qualifier_id,
            reason=decision.reason,
            evidence_ids=tuple(x.evidence_id for x in candidate.evidence),
            qualification_evidence=refs,
        )


def validate_external_ticket(
    candidate: CapabilityCandidate,
    ticket: CapabilityQualificationTicket,
    ledger: EvidenceLedger,
) -> tuple[bool, str]:
    if not ticket.qualifier_id or ticket.qualifier_id.upper().startswith("MICROSEED"):
        return False, "QUALIFIER_NOT_EXTERNAL"
    if ticket.candidate_id != candidate.candidate_id:
        return False, "CANDIDATE_ID_MISMATCH"
    if ticket.candidate_sha256 != candidate.digest():
        return False, "CANDIDATE_DIGEST_MISMATCH"
    if ticket.evidence_ids != tuple(x.evidence_id for x in candidate.evidence):
        return False, "PROPOSAL_EVIDENCE_SET_MISMATCH"
    ok, missing = ledger.resolve(candidate.evidence)
    if not ok:
        return False, f"UNRESOLVED_PROPOSAL_EVIDENCE:{','.join(missing)}"
    if any(x.negative for x in candidate.evidence):
        return False, "NEGATIVE_PROPOSAL_EVIDENCE_PRESENT"
    if not ticket.qualification_evidence:
        return False, "NO_QUALIFICATION_EVIDENCE"
    # Recompute the fixed decision so a forged transport object cannot claim a
    # stronger state/authority than the actual external evidence warrants.
    decision = FixedQualifier(ledger).decide(
        ticket.qualification_evidence,
        candidate.proposed_contract.authority,
    )
    if ticket.state != decision.state or ticket.authority != decision.authority:
        return False, "QUALIFICATION_DECISION_MISMATCH"
    if ticket.reason != decision.reason:
        return False, "QUALIFICATION_REASON_MISMATCH"
    if ticket.state not in {QualificationState.SHADOW_QUALIFIED, QualificationState.QUALIFIED}:
        return False, f"NOT_ADMISSIBLE:{ticket.state.value}"
    if ticket.authority == Authority.EFFECT:
        return False, "EFFECT_AUTHORITY_NOT_ADMISSIBLE_BY_THIS_BRIDGE"
    return True, "VALID_EXTERNAL_QUALIFICATION"
