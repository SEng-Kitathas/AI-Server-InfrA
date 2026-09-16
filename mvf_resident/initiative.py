
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

@dataclass(frozen=True)
class AttentionSignal:
    signal_id: str
    source_kind: str
    question_key: str
    subject: str
    reason: str
    evidence_ids: tuple[str,...] = ()
    priority: int = 50

@dataclass
class Inquiry:
    inquiry_id: str
    question_key: str
    subject: str
    reason: str
    source_kinds: list[str]
    evidence_ids: list[str]
    status: str
    created_at: str
    updated_at: str
    expires_at: str
    nomination_candidate: dict[str,Any] | None = None

    def to_dict(self) -> dict[str,Any]:
        row=asdict(self)
        row["mutation_authority"]=False
        row["authority_ceiling"]="OBSERVATION_ONLY"
        return row

def _parse(value: str) -> datetime:
    text=str(value or "")
    if text.endswith("Z"): text=text[:-1]+"+00:00"
    dt=datetime.fromisoformat(text)
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

def _id(prefix: str, value: str) -> str:
    return prefix+":"+hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]

class InquiryEngine:
    def __init__(self, *, max_open: int=16, ttl_seconds: int=3600, nomination_evidence_threshold: int=2) -> None:
        self.max_open=max(1,int(max_open))
        self.ttl_seconds=max(60,int(ttl_seconds))
        self.threshold=max(2,int(nomination_evidence_threshold))

    def reconcile(self, previous: dict[str,Any] | None, signals: tuple[AttentionSignal,...], *, now_iso: str | None=None) -> dict[str,Any]:
        now=now_iso or datetime.now(timezone.utc).isoformat()
        now_dt=_parse(now)
        records: dict[str,Inquiry]={}
        if isinstance(previous,dict):
            for raw in previous.get("inquiries",[]) or []:
                if not isinstance(raw,dict) or not raw.get("question_key"): continue
                try:
                    rec=Inquiry(
                        inquiry_id=str(raw["inquiry_id"]),
                        question_key=str(raw["question_key"]),
                        subject=str(raw.get("subject") or raw["question_key"]),
                        reason=str(raw.get("reason") or ""),
                        source_kinds=[str(x) for x in raw.get("source_kinds",[])],
                        evidence_ids=[str(x) for x in raw.get("evidence_ids",[])],
                        status=str(raw.get("status") or "OPEN"),
                        created_at=str(raw.get("created_at") or now),
                        updated_at=str(raw.get("updated_at") or now),
                        expires_at=str(raw.get("expires_at") or now),
                        nomination_candidate=dict(raw["nomination_candidate"]) if isinstance(raw.get("nomination_candidate"),dict) else None,
                    )
                    records[rec.question_key]=rec
                except Exception:
                    continue
        for rec in records.values():
            if rec.status=="OPEN":
                try:
                    if _parse(rec.expires_at)<=now_dt: rec.status="EXPIRED"
                except Exception:
                    rec.status="EXPIRED"

        for sig in sorted(signals,key=lambda x:(-x.priority,x.question_key,x.signal_id)):
            rec=records.get(sig.question_key)
            if rec is None or rec.status=="EXPIRED":
                active=sum(1 for x in records.values() if x.status in {"OPEN","NOMINATED"})
                if active>=self.max_open: continue
                rec=Inquiry(
                    inquiry_id=_id("inquiry",sig.question_key),
                    question_key=sig.question_key,
                    subject=sig.subject,
                    reason=sig.reason,
                    source_kinds=[],
                    evidence_ids=[],
                    status="OPEN",
                    created_at=now,
                    updated_at=now,
                    expires_at=(now_dt+timedelta(seconds=self.ttl_seconds)).isoformat(),
                )
                records[sig.question_key]=rec
            rec.updated_at=now
            rec.expires_at=(now_dt+timedelta(seconds=self.ttl_seconds)).isoformat()
            rec.reason=sig.reason or rec.reason
            if sig.source_kind not in rec.source_kinds: rec.source_kinds.append(sig.source_kind)
            for eid in sig.evidence_ids:
                if eid and eid not in rec.evidence_ids: rec.evidence_ids.append(eid)
            if rec.status=="OPEN" and len(rec.evidence_ids)>=self.threshold and rec.nomination_candidate is None:
                candidate_id=_id("mvf-inquiry-duty",rec.question_key+"|"+"|".join(sorted(rec.evidence_ids)))
                rec.nomination_candidate={
                    "candidate_id":candidate_id,
                    "question_key":rec.question_key,
                    "subject":rec.subject,
                    "maintained_claim":f"Maintain current evidence for inquiry: {rec.question_key}",
                    "evidence_ids":sorted(rec.evidence_ids),
                    "authority":"OBSERVATION_ONLY",
                    "qualification_required":"EXTERNAL",
                    "self_qualification":False,
                }
                rec.status="NOMINATED"

        rows=sorted((x.to_dict() for x in records.values()),key=lambda r:(r["status"],r["question_key"]))
        return {
            "schema":"mvf.initiative-state.v1",
            "mutation_authority":False,
            "standing_duty_authority":False,
            "authority_ceiling":"OBSERVATION_ONLY",
            "open_count":sum(1 for x in rows if x["status"]=="OPEN"),
            "nominated_count":sum(1 for x in rows if x["status"]=="NOMINATED"),
            "inquiries":rows,
        }
