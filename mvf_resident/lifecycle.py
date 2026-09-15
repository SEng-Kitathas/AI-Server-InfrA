from __future__ import annotations

import hashlib, json
from pathlib import Path
from typing import Any

from .resident import MVFResident, DutyContract
from .governance import ResidentGovernance
from .surfaces import audit_continuity_surfaces
from .donor_microseed.persistence.biography import DevelopmentalBiography
from .donor_microseed.runtime.types import EpistemicStatus

def _canon(obj: Any) -> bytes:
    return json.dumps(obj,sort_keys=True,separators=(",",":"),default=str).encode("utf-8")

def _digest(obj: Any) -> str:
    return hashlib.sha256(_canon(obj)).hexdigest()

class ResidentLifecycle:
    def __init__(self,resident: MVFResident,state_dir: Path,handoff_dir: Path) -> None:
        state_dir.mkdir(parents=True,exist_ok=True)
        self.resident=resident
        self.governance=ResidentGovernance(state_dir)
        self.biography=DevelopmentalBiography(state_dir/'biography.sqlite',legacy_anchor={'authority':'OPERATIONAL_LINEAGE_ONLY'})
        self.handoff_dir=handoff_dir
        self.current_state_path=state_dir/'current_state.json'

    def close(self) -> None:
        self.biography.close(); self.governance.close()

    def __enter__(self): return self
    def __exit__(self,exc_type,exc,tb): self.close()

    def _ensure_biography_event(self,kind:str,payload:dict[str,Any]):
        for ev in self.biography.events.values():
            if ev.kind == kind and ev.payload == payload:
                return ev
        return self.biography.append(kind,payload)

    def _ensure_evidence(self,evidence_id:str,payload:Any,status:EpistemicStatus):
        if self.governance.ledger.get(evidence_id) is None:
            self.governance.record_observation_evidence(evidence_id,payload,status=status)

    def _ensure_deficit(self,duty_id:str,evidence_id:str):
        did=f'deficit:{duty_id}'
        if did not in self.governance.deficits.snapshot():
            self.governance.record_deficit(duty_id,evidence_id=evidence_id)

    def run_cycle(self,duties:tuple[DutyContract,...]) -> dict[str,Any]:
        brief=self.resident.run_portfolio(duties)
        for d in brief['duties']:
            eid=f"duty:{d['duty_id']}:{_digest(d)}"
            status=EpistemicStatus.PROVED if d['status']=='CURRENT' else EpistemicStatus.UNKNOWN_INCOMPLETE
            self._ensure_evidence(eid,d,status)
            if d['status']!='CURRENT': self._ensure_deficit(d['duty_id'],eid)
            self._ensure_biography_event('MVF_DUTY_OBSERVATION',{'duty_id':d['duty_id'],'status':d['status'],'evidence_id':eid,'digest':_digest(d)})
        surface=audit_continuity_surfaces(self.handoff_dir).to_dict()
        seid=f"surface:{_digest(surface)}"
        sstatus=EpistemicStatus.PROVED if surface['status']=='CURRENT' else EpistemicStatus.UNKNOWN_INCOMPLETE
        self._ensure_evidence(seid,surface,sstatus)
        if surface['status']!='CURRENT': self._ensure_deficit('continuity-active-surfaces',seid)
        self._ensure_biography_event('MVF_SURFACE_AUDIT',{'status':surface['status'],'evidence_id':seid,'digest':_digest(surface)})
        state={'schema':'mvf.resident-current-state.v1','portfolio':brief,'surface_audit':surface,'evidence_count':len(self.governance.ledger.list()),'deficits':self.governance.deficits.snapshot(),'biography_graph_digest':self.biography.graph_digest(),'mutation_authority':False}
        self.current_state_path.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        return state
