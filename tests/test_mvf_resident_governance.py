from __future__ import annotations
from pathlib import Path
import tempfile
import pytest
from mvf_resident.governance import ResidentGovernance, DutyCandidate
from mvf_resident.donor_microseed.runtime.types import EpistemicStatus, QualificationState, Authority

def _gov(td): return ResidentGovernance(Path(td))

def test_deficit_lifecycle_invalidates_only_changed_duty_premise():
    with tempfile.TemporaryDirectory() as td:
        g=_gov(td)
        try:
            g.record_observation_evidence('u1', {'status':'UNKNOWN'}, status=EpistemicStatus.UNKNOWN_INCOMPLETE)
            rec=g.record_deficit('duty-a', evidence_id='u1', premise_epoch=0)
            assert rec.truth_authority == 'NONE'
            stale=g.mark_duty_premise_changed('duty-a',1,reason='dependency changed')
            assert rec.deficit_id in stale
            assert rec.deficit_id not in g.deficits.development_pressure_ids()
        finally: g.close()

def test_candidate_cannot_self_admit():
    with tempfile.TemporaryDirectory() as td:
        g=_gov(td)
        try:
            g.record_observation_evidence('p1', {'support':1}, status=EpistemicStatus.PRESSURE_SUPPORTED)
            c=g.nominate_duty(DutyCandidate('duty:new','subject','claim',evidence_ids=('p1',)))
            assert c.proposed_contract.qualification == QualificationState.CANDIDATE
            assert c.proposed_contract.authority == Authority.OBSERVATION_ONLY
            with pytest.raises(PermissionError, match='SELF_QUALIFICATION'): g.self_admit(c.candidate_id)
        finally: g.close()

def test_external_qualification_requires_independent_evidence_and_never_effect_authority():
    with tempfile.TemporaryDirectory() as td:
        g=_gov(td)
        try:
            g.record_observation_evidence('p1', {'support':1}, status=EpistemicStatus.PRESSURE_SUPPORTED)
            g.record_observation_evidence('q1', {'hostile_test':'pass'}, status=EpistemicStatus.PROVED)
            c=g.nominate_duty(DutyCandidate('duty:new','subject','claim',evidence_ids=('p1',)))
            ticket=g.external_qualify(c.candidate_id,('q1',),qualifier_id='HEAT-EXTERNAL-QUALIFIER')
            assert ticket.state in {QualificationState.SHADOW_QUALIFIED,QualificationState.QUALIFIED}
            assert ticket.authority != Authority.EFFECT
        finally: g.close()

def test_negative_qualification_evidence_cannot_admit_candidate():
    with tempfile.TemporaryDirectory() as td:
        g=_gov(td)
        try:
            g.record_observation_evidence('p1', {'support':1}, status=EpistemicStatus.PRESSURE_SUPPORTED)
            g.ledger.append('qneg', {'hostile_test':'fail'}, EpistemicStatus.VIOLATED, negative=True, source='HEAT')
            c=g.nominate_duty(DutyCandidate('duty:new','subject','claim',evidence_ids=('p1',)))
            with pytest.raises(ValueError): g.external_qualify(c.candidate_id,('qneg',),qualifier_id='HEAT-EXTERNAL-QUALIFIER')
        finally: g.close()

def test_reentry_blocks_when_dependency_is_not_current_and_never_grants_authority():
    with tempfile.TemporaryDirectory() as td:
        g=_gov(td)
        try:
            blocked=g.assess_stale_reentry('duty-a',dependency_currentness=(('dep-a',False),))
            assert blocked.status == 'DEFER' and blocked.reason == 'DEPENDENCY_NOT_CURRENT'
            ready=g.assess_stale_reentry('duty-a',dependency_currentness=(('dep-a',True),))
            assert ready.status == 'READY_FOR_EXISTING_REGISTRATION_PATH'
            assert ready.authority == Authority.NONE
        finally: g.close()
