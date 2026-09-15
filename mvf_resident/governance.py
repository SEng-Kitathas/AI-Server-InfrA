from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .donor_microseed.runtime.types import Authority, CapabilityContract, EpistemicStatus, QualificationState
from .donor_microseed.evidence.ledger import EvidenceLedger
from .donor_microseed.development.capability_admission import CapabilityCandidate, CapabilityQualificationTicket, ExternalCapabilityQualifier, validate_external_ticket
from .donor_microseed.development.epistemic import EpistemicDeficitRegistry, EpistemicDeficitRecord, EpistemicCurrentnessAnchor
from .donor_microseed.development.reentry import HistoricalReentryProjection, HistoricalReentryRecord, ReentryWarrant, assess_reentry


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class DutyCandidate:
    candidate_id: str
    subject: str
    maintained_claim: str
    dependencies: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()


class ResidentGovernance:
    """Governance sidecar: records uncertainty and proposals; never self-authorizes."""
    def __init__(self, state_dir: Path, *, evidence_path: Path | None = None) -> None:
        state_dir.mkdir(parents=True, exist_ok=True)
        ledger_path = evidence_path or (state_dir / 'evidence.sqlite')
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger = EvidenceLedger(ledger_path)
        self.deficits = EpistemicDeficitRegistry()
        self.candidates: dict[str, CapabilityCandidate] = {}
        self.tickets: dict[str, CapabilityQualificationTicket] = {}

    def close(self) -> None:
        self.ledger.conn.close()

    def __enter__(self) -> 'ResidentGovernance':
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def record_observation_evidence(self, evidence_id: str, payload: Any, *, status: EpistemicStatus) -> Any:
        return self.ledger.append(evidence_id, payload, status, source='MVF_RESIDENT')

    def record_deficit(self, duty_id: str, *, evidence_id: str, premise_kind: str='DUTY', premise_epoch: int=0) -> EpistemicDeficitRecord:
        rec = EpistemicDeficitRecord(
            deficit_id=f'deficit:{duty_id}', question_key=duty_id,
            hypothesis_digest_sha256=_sha('duty-current:'+duty_id),
            unknown_evidence_id=evidence_id,
            missing_discriminator_signature_sha256=_sha('missing-discriminator:'+duty_id),
            premise_anchors=(EpistemicCurrentnessAnchor(premise_kind,duty_id,premise_epoch),),
            assistance_ancestry=('MVF_RESIDENT',),
        )
        self.deficits.register(rec)
        return rec

    def mark_duty_premise_changed(self, duty_id: str, new_epoch: int, *, reason: str) -> set[str]:
        return self.deficits.invalidate_premise('DUTY', duty_id, new_epoch, reason=reason, force=True)

    def nominate_duty(self, candidate: DutyCandidate) -> CapabilityCandidate:
        refs=[]
        for eid in candidate.evidence_ids:
            row=self.ledger.get(eid)
            if row is None: raise ValueError(f'EVIDENCE_NOT_FOUND:{eid}')
            refs.append(self.ledger.append(f'proposal-link:{candidate.candidate_id}:{eid}', {'source_evidence_id':eid}, EpistemicStatus.PRESSURE_SUPPORTED, source='MVF_RESIDENT_PROPOSAL'))
        contract=CapabilityContract(
            capability_id=candidate.candidate_id,purpose='mvf-resident-duty',
            boundary={'subject':candidate.subject},interface={'maintained_claim':candidate.maintained_claim},
            invariants=('OBSERVATION_ONLY','NO_SELF_QUALIFICATION'),hazards=('STALE_EVIDENCE','SCOPE_LEAK'),
            authority=Authority.OBSERVATION_ONLY,lineage=('MVF_RESIDENT_DUTY_CANDIDATE',),currentness='CANDIDATE',
            resources={},dependencies=candidate.dependencies,qualification=QualificationState.CANDIDATE,
            assistance_ancestry=('MVF_RESIDENT',),
        )
        obj=CapabilityCandidate(candidate.candidate_id,contract,tuple(refs),assistance_ancestry=('MVF_RESIDENT',),nomination_basis='MVF_RESIDENT_PROPOSAL_ONLY')
        self.candidates[obj.candidate_id]=obj
        return obj

    def self_admit(self, candidate_id: str) -> None:
        raise PermissionError('RESIDENT_SELF_QUALIFICATION_FORBIDDEN')

    def external_qualify(self, candidate_id: str, qualification_evidence_ids: tuple[str,...], *, qualifier_id: str='MVF-EXTERNAL-QUALIFIER') -> CapabilityQualificationTicket:
        candidate=self.candidates[candidate_id]
        refs=[]
        for eid in qualification_evidence_ids:
            row=self.ledger.get(eid)
            if row is None: raise ValueError(f'EVIDENCE_NOT_FOUND:{eid}')
            from .donor_microseed.runtime.types import EvidenceRef
            refs.append(EvidenceRef(eid,row['sha256'],EpistemicStatus(row['disposition']),bool(row['negative'])))
        ticket=ExternalCapabilityQualifier(self.ledger,qualifier_id=qualifier_id).qualify(candidate,qualification_evidence=tuple(refs))
        ok,reason=validate_external_ticket(candidate,ticket,self.ledger)
        if not ok: raise ValueError(reason)
        self.tickets[candidate_id]=ticket
        return ticket

    def assess_stale_reentry(self, duty_id: str, *, dependency_currentness: tuple[tuple[str,bool],...], requested_scope: str='OBSERVATION_ONLY') -> Any:
        rec=HistoricalReentryRecord(handle=duty_id,kind='MVF_DUTY',status='HISTORICAL_NOMINATION_ONLY',registration_seq=1,fingerprint_sha256=_sha(duty_id),dependencies=tuple(d for d,_ in dependency_currentness))
        projection=HistoricalReentryProjection(records=(rec,),eligible_handles=(duty_id,),blocked=(),layers=((duty_id,),),cycles=())
        warrant=ReentryWarrant(handle=duty_id,historical_fingerprint_sha256=rec.fingerprint_sha256,provider_compatible=True,provider_evidence_id='mvf-provider',executable_challenge_passed=True,executable_evidence_id='mvf-readonly-challenge',dependency_currentness=dependency_currentness,diagnostic_scope=(requested_scope,))
        return assess_reentry(projection,warrant,requested_scope=requested_scope)
