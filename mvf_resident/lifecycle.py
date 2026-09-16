from __future__ import annotations

import hashlib, json
from pathlib import Path
from typing import Any

from .resident import MVFResident, DutyContract
from .governance import ResidentGovernance
from .initiative import AttentionSignal, InquiryEngine
from .surfaces import audit_continuity_surfaces
from .continuity_enforcement import plan_surface_use, handoff_gate
from .scar_intelligence import refresh_index, route_scars
from .daemon_plane import initialize as initialize_daemon_plane, paths as daemon_paths, write_current as daemon_write_current, write_current_unlocked as daemon_write_current_unlocked, plane_lock
from .donor_microseed.persistence.biography import DevelopmentalBiography
from .donor_microseed.runtime.types import EpistemicStatus

def _canon(obj: Any) -> bytes:
    return json.dumps(obj,sort_keys=True,separators=(",",":"),default=str).encode("utf-8")

def _digest(obj: Any) -> str:
    return hashlib.sha256(_canon(obj)).hexdigest()

class ResidentLifecycle:
    def __init__(self,resident: MVFResident,state_dir: Path,handoff_dir: Path | None, *, evidence_path: Path | None = None, biography_path: Path | None = None, daemon_root: Path | None = None, handoff_resolver=None) -> None:
        state_dir.mkdir(parents=True,exist_ok=True)
        self.resident=resident
        self.state_dir=state_dir
        self.governance=ResidentGovernance(state_dir,evidence_path=evidence_path)
        self.biography=DevelopmentalBiography(biography_path or (state_dir/'biography.sqlite'),legacy_anchor={'authority':'OPERATIONAL_LINEAGE_ONLY'})
        self.handoff_dir=handoff_dir
        self.handoff_resolver=handoff_resolver
        self.current_state_path=state_dir/'current_state.json'
        self.daemon_root=daemon_root

    @classmethod
    def from_daemon_plane(cls,resident: MVFResident,daemon_root: Path,handoff_dir: Path | None, *, daemon_id: str, project_id: str, handoff_resolver=None) -> 'ResidentLifecycle':
        p=initialize_daemon_plane(daemon_root,daemon_id=daemon_id,project_id=project_id)
        return cls(resident,p.current_state.parent,handoff_dir,evidence_path=p.evidence_db,biography_path=p.biography_db,daemon_root=daemon_root,handoff_resolver=handoff_resolver)

    def close(self) -> None:
        self.biography.close(); self.governance.close()

    def __enter__(self): return self
    def __exit__(self,exc_type,exc,tb): self.close()

    def _ensure_biography_event(self,kind:str,payload:dict[str,Any]):
        for ev in self.biography.events.values():
            if ev.kind == kind and _canon(ev.payload) == _canon(payload):
                return ev
        return self.biography.append(kind,payload)

    def _ensure_evidence(self,evidence_id:str,payload:Any,status:EpistemicStatus):
        if self.governance.ledger.get(evidence_id) is None:
            self.governance.record_observation_evidence(evidence_id,payload,status=status)

    def _ensure_deficit(self,duty_id:str,evidence_id:str):
        did=f'deficit:{duty_id}'
        if did not in self.governance.deficits.snapshot():
            self.governance.record_deficit(duty_id,evidence_id=evidence_id)

    def _resolved_handoff_dir(self) -> Path:
        if self.handoff_resolver is not None:
            value=Path(self.handoff_resolver()).resolve()
            return value
        if self.handoff_dir is None: raise RuntimeError('HANDOFF_SOURCE_UNAVAILABLE')
        return Path(self.handoff_dir).resolve()

    def _load_previous_state(self) -> dict[str,Any]:
        try:
            if self.daemon_root is not None:
                raw=json.loads(daemon_paths(self.daemon_root).current_state.read_text(encoding='utf-8'));return dict(raw.get('state') or {})
            if self.current_state_path.exists(): return dict(json.loads(self.current_state_path.read_text(encoding='utf-8')))
        except Exception:
            pass
        return {}

    @staticmethod
    def _duty_signature(d: dict[str,Any]) -> dict[str,Any]:
        return {k:d.get(k) for k in ('duty_id','status','commitment','stale_reasons','reopen_reasons','escalation_required','mutation_authority')}

    @staticmethod
    def _surface_signature(s: dict[str,Any]) -> dict[str,Any]:
        return {k:s.get(k) for k in ('status','missing','unmanifested','hash_mismatch','checkpoint_hash_match')}

    def run_cycle(self,duties:tuple[DutyContract,...]) -> dict[str,Any]:
        if self.daemon_root is not None:
            with plane_lock(daemon_paths(self.daemon_root).lock):
                return self._run_cycle_locked(duties)
        return self._run_cycle_locked(duties)

    def _run_cycle_locked(self,duties:tuple[DutyContract,...]) -> dict[str,Any]:
        previous=self._load_previous_state()
        self.governance.restore_deficits(previous.get('deficits') if isinstance(previous,dict) else None)
        prev_duties={d.get('duty_id'):d for d in previous.get('portfolio',{}).get('duties',[]) if isinstance(d,dict)}
        prev_surface=previous.get('surface_audit') if isinstance(previous.get('surface_audit'),dict) else None
        brief=self.resident.run_portfolio(duties)
        for d in brief['duties']:
            sig=self._duty_signature(d);prev=self._duty_signature(prev_duties.get(d['duty_id'],{})) if d['duty_id'] in prev_duties else None
            changed=(prev != sig)
            if changed:
                eid=f"duty:{d['duty_id']}:{_digest(sig)}"
                status=EpistemicStatus.PROVED if d['status']=='CURRENT' else EpistemicStatus.UNKNOWN_INCOMPLETE
                self._ensure_evidence(eid,{'signature':sig,'result':d},status)
                if d['status']!='CURRENT': self._ensure_deficit(d['duty_id'],eid)
                self._ensure_biography_event('MVF_DUTY_TRANSITION',{'duty_id':d['duty_id'],'status':d['status'],'evidence_id':eid,'signature':sig})
        surface=audit_continuity_surfaces(self._resolved_handoff_dir()).to_dict();ssig=self._surface_signature(surface);psig=self._surface_signature(prev_surface) if prev_surface else None
        if psig != ssig:
            seid=f"surface:{_digest(ssig)}";sstatus=EpistemicStatus.PROVED if surface['status']=='CURRENT' else EpistemicStatus.UNKNOWN_INCOMPLETE
            self._ensure_evidence(seid,{'signature':ssig,'result':surface},sstatus)
            if surface['status']!='CURRENT': self._ensure_deficit('continuity-active-surfaces',seid)
            self._ensure_biography_event('MVF_SURFACE_TRANSITION',{'status':surface['status'],'evidence_id':seid,'signature':ssig})
        resolved_handoff=self._resolved_handoff_dir();noncurrent=[d['duty_id'] for d in brief['duties'] if d.get('status')!='CURRENT'];ctx='resident cycle';
        if noncurrent:ctx+=' attention: '+', '.join(noncurrent)
        continuity_plan=plan_surface_use(resolved_handoff,ctx,mode='recovery' if noncurrent else 'discussion',limit=6)
        continuity_gate=handoff_gate(resolved_handoff)
        scar_path=(daemon_paths(self.daemon_root).scar_index if self.daemon_root is not None else self.state_dir/'scars'/'index.json')
        scar_sources=[resolved_handoff];external_candidates=[]
        if self.daemon_root is not None:external_candidates.append(Path(self.daemon_root).resolve().parent/'scar_sources')
        if resolved_handoff.name=='current' and resolved_handoff.parent.name=='handoff':external_candidates.append(resolved_handoff.parent.parent/'scar_sources')
        elif resolved_handoff.parent.name=='generations' and resolved_handoff.parent.parent.name=='handoff':external_candidates.append(resolved_handoff.parent.parent.parent/'scar_sources')
        seen={x.resolve() for x in scar_sources}
        for candidate in external_candidates:
            c=candidate.resolve()
            if c not in seen and c.is_dir():scar_sources.append(c);seen.add(c)
        scar_index=refresh_index(scar_sources,scar_path)
        scar_context=' '.join([ctx,brief.get('overall_status',''),surface.get('status',''),*(' '.join(str(d.get(k,'')) for k in ('duty_id','subject','commitment','status')) for d in brief['duties']),*(d.get('reason','') for d in brief['duties'] if d.get('status')!='CURRENT')])
        scar_routing=route_scars(scar_index,scar_context,limit=7)
        initiative_signals=[]
        for d in brief['duties']:
            if d.get('status')=='CURRENT': continue
            sig=self._duty_signature(d);eid=f"duty:{d['duty_id']}:{_digest(sig)}"
            initiative_signals.append(AttentionSignal(
                signal_id=f"attention:duty:{d['duty_id']}:{_digest(sig)}",
                source_kind='duty_currentness',
                question_key=f"duty:{d['duty_id']}",
                subject=str(d.get('subject') or d['duty_id']),
                reason=str(d.get('reason') or d.get('status') or 'non-current duty'),
                evidence_ids=(eid,) if self.governance.ledger.get(eid) is not None else (),
                priority=80,
            ))
        if surface.get('status')!='CURRENT':
            seid=f"surface:{_digest(ssig)}"
            initiative_signals.append(AttentionSignal(
                signal_id=f"attention:surface:{_digest(ssig)}",
                source_kind='continuity_surface',
                question_key='continuity:active-surfaces',
                subject='continuity active surfaces',
                reason=str(surface.get('status') or 'non-current continuity surface'),
                evidence_ids=(seid,) if self.governance.ledger.get(seid) is not None else (),
                priority=90,
            ))
        for raw in scar_index.get('source_deficits',[]) or []:
            initiative_signals.append(AttentionSignal(
                signal_id=f"attention:scar:{_digest(raw)}",
                source_kind='scar_source_deficit',
                question_key=f"scar-source:{_digest(raw)[:16]}",
                subject='scar source currentness',
                reason=str(raw),
                evidence_ids=(),
                priority=55,
            ))
        initiative=InquiryEngine().reconcile(
            previous.get('initiative') if isinstance(previous,dict) else None,
            tuple(initiative_signals),
        )
        state={'schema':'mvf.resident-current-state.v1','portfolio':brief,'surface_audit':surface,'continuity_enforcement':{'surfacing_plan':continuity_plan,'handoff_ready':continuity_gate['ready'],'handoff_failures':continuity_gate['failures'],'handoff_warnings':continuity_gate['warnings'],'campaign_labels':continuity_gate['campaign_labels']},'scar_intelligence':{'index_changed':scar_index['changed'],'scar_count':scar_index['scar_count'],'occurrence_count':scar_index['occurrence_count'],'source_digest':scar_index['source_digest'],'source_dirs':scar_index.get('source_dirs',[]),'source_deficits':scar_index.get('source_deficits',[]),'applicable':scar_routing['selected'],'candidate_count':scar_routing['candidate_count'],'ritual_dump_avoided':scar_routing['ritual_dump_avoided'],'authority':'DERIVED_ROUTING_ONLY'},'initiative':initiative,'evidence_count':len(self.governance.ledger.list()),'deficits':self.governance.deficits.snapshot(),'biography_graph_digest':self.biography.graph_digest(),'mutation_authority':False}
        if self.daemon_root is not None:
            daemon_write_current_unlocked(self.daemon_root,state)
        else:
            self.current_state_path.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        return state
