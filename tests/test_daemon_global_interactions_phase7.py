from __future__ import annotations
import hashlib,json,tempfile,time
from pathlib import Path
from mvf_resident.daemon_service import DaemonService
from mvf_resident.surfaces import REQUIRED_ACTIVE_SURFACES


def _handoff(root):
    files={}
    for n in REQUIRED_ACTIVE_SURFACES:
        p=root/n;p.write_text(n,encoding='utf-8');b=p.read_bytes();files[n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    cp=files['THREAD_CONTINUITY_CHECKPOINT_2026-09-15.md']['sha256'];(root/'SNAPSHOT_MANIFEST_SHA256.json').write_text(json.dumps({'updated_at':'x','continuity_checkpoint_sha256':cp,'files':files}),encoding='utf-8')

def _dispatch(name,payload):
    return {'ok':True,'status':'current'} if name=='continuity.convergence.inspect' else {'ok':True}


def test_timeline_persistence_failure_degrades_observability_without_reboot_signal(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);h=b/'h';h.mkdir();_handoff(h);svc=DaemonService(daemon_root=b/'daemon',handoff_dir=h,project_id='P',daemon_id='d1',dispatch=_dispatch,interval_seconds=30)
        monkeypatch.setattr(svc,'_append_timeline',lambda row:(_ for _ in ()).throw(OSError('disk full')))
        try:
            svc.start();deadline=time.time()+4
            while svc.cycle_count<1 and time.time()<deadline:time.sleep(.05)
            health=svc.health();assert health['ok'] is True;assert health['status']=='degraded';assert 'timeline:OSError:disk full' in health['observability_error'];assert svc._thread.is_alive()
        finally:svc.close()


def test_status_file_persistence_failure_is_visible_but_does_not_mark_cognition_dead(monkeypatch):
    import mvf_resident.daemon_service as ds
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);h=b/'h';h.mkdir();_handoff(h);svc=DaemonService(daemon_root=b/'daemon',handoff_dir=h,project_id='P',daemon_id='d1',dispatch=_dispatch,interval_seconds=30)
        real=ds.atomic_json
        monkeypatch.setattr(ds,'atomic_json',lambda path,payload:(_ for _ in ()).throw(PermissionError('readonly volume')))
        try:
            svc.start();deadline=time.time()+4
            while svc.cycle_count<1 and time.time()<deadline:time.sleep(.05)
            health=svc.health();assert health['ok'] is True;assert health['status']=='degraded';assert 'status:PermissionError:readonly volume' in health['observability_error']
        finally:
            svc.close();monkeypatch.setattr(ds,'atomic_json',real)


def test_corrupt_timeline_lines_are_skipped_on_restart_not_promoted_to_events():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);h=b/'h';h.mkdir();_handoff(h);root=b/'daemon';a=DaemonService(daemon_root=root,handoff_dir=h,project_id='P',daemon_id='d1',dispatch=_dispatch,interval_seconds=30);a._event('good',value=1);a.close()
        from mvf_resident.daemon_plane import paths
        p=paths(root);with_bad=p.status_timeline.read_text(encoding='utf-8')+'{broken json\n'+json.dumps({'ts':1,'kind':'good2'})+'\n';p.status_timeline.write_text(with_bad,encoding='utf-8')
        bsvc=DaemonService(daemon_root=root,handoff_dir=h,project_id='P',daemon_id='d1',dispatch=_dispatch,interval_seconds=30)
        try:
            kinds=[e.get('kind') for e in bsvc.event_rows()];assert 'good' in kinds and 'good2' in kinds
        finally:bsvc.close()
