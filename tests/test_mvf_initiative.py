from datetime import datetime,timedelta,timezone
from mvf_resident.initiative import AttentionSignal,InquiryEngine

def sig(eid):
    return AttentionSignal("sig:"+eid,"duty_currentness","q","subject","reason",(eid,))

def test_inquiry_is_bounded_and_read_only():
    state=InquiryEngine(max_open=1).reconcile(None,(sig("e1"),AttentionSignal("s2","x","other","o","r",())))
    assert state["mutation_authority"] is False
    assert state["standing_duty_authority"] is False
    assert len([x for x in state["inquiries"] if x["status"]!="EXPIRED"])==1

def test_distinct_evidence_creates_candidate_not_duty():
    engine=InquiryEngine(nomination_evidence_threshold=2)
    first=engine.reconcile(None,(sig("e1"),))
    second=engine.reconcile(first,(sig("e2"),))
    assert second["nominated_count"]==1
    candidate=second["inquiries"][0]["nomination_candidate"]
    assert candidate["authority"]=="OBSERVATION_ONLY"
    assert candidate["qualification_required"]=="EXTERNAL"
    assert candidate["self_qualification"] is False

def test_same_evidence_does_not_fake_recurrence():
    engine=InquiryEngine(nomination_evidence_threshold=2)
    first=engine.reconcile(None,(sig("e1"),))
    second=engine.reconcile(first,(sig("e1"),))
    assert second["nominated_count"]==0
