from __future__ import annotations

import hashlib,json,tempfile,threading,time
from pathlib import Path
import pytest

from mvf_resident.daemon_plane import checkpoint, paths, recover, DaemonPlaneBusy
from mvf_resident.daemon_service import DaemonService
from mvf_resident.lifecycle import ResidentLifecycle
from mvf_resident.resident import MVFResident,DutyContract
from mvf_resident.surfaces import REQUIRED_ACTIVE_SURFACES

def _handoff(root:Path):
    files={}
    for n in REQUIRED_ACTIVE_SURFACES:
        p=root/n;p.write_text(n,encoding='utf-8');b=p.read_bytes();files[n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    cp=files['THREAD_CONTINUITY_CHECKPOINT_2026-09-15.md']['sha256'];(root/'SNAPSHOT_MANIFEST_SHA256.json').write_text(json.dumps({'updated_at':'x','continuity_checkpoint_sha256':cp,'files':files}),encoding='utf-8')

def _dispatch(name,payload):
    return {'ok':True,'status':'current'} if name=='continuity.convergence.inspect' else {'ok':True}

def _tree_hash(root:Path):
    out={}
    for p in root.rglob('*'):
        if not p.is_file(): continue
        rel=p.relative_to(root).as_posix()
        if rel.endswith('/service.lock') or rel=='runtime/locks/service.lock':
            out[rel]='LOCKED_PRESENT';continue
        out[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
    return out

def test_status_read_does_not_mutate_daemon_plane():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);h=b/'h';h.mkdir();_handoff(h);svc=DaemonService(daemon_root=b/'daemon',handoff_dir=h,project_id='P',daemon_id='d1',dispatch=_dispatch,interval_seconds=30)
        try:
            svc.start();deadline=time.time()+4
            while svc.cycle_count<1 and time.time()<deadline: time.sleep(.05)
            before=_tree_hash(b/'daemon');svc.status();svc.status();after=_tree_hash(b/'daemon');assert before==after
        finally:svc.close()

def test_unchanged_polling_does_not_grow_evidence_biography_or_timeline_every_cycle():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);h=b/'h';h.mkdir();_handoff(h);svc=DaemonService(daemon_root=b/'daemon',handoff_dir=h,project_id='P',daemon_id='d1',dispatch=_dispatch,interval_seconds=1)
        try:
            svc.start();deadline=time.time()+6
            while svc.cycle_count<4 and time.time()<deadline: time.sleep(.05)
            p=paths(b/'daemon');state=json.loads(p.current_state.read_text())['state'];assert svc.cycle_count>=4
            # unchanged healthy polling should not produce linear immutable-history growth
            assert state['evidence_count'] <= 4
            assert len(state['deficits']) <= 1
            lines=p.status_timeline.read_text(encoding='utf-8').splitlines();cycle_events=[x for x in lines if 'cycle_completed' in x];assert len(cycle_events) <= 2
        finally:svc.close()

def test_second_service_same_plane_is_fenced():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);h=b/'h';h.mkdir();_handoff(h);root=b/'daemon';a=DaemonService(daemon_root=root,handoff_dir=h,project_id='P',daemon_id='d1',dispatch=_dispatch,interval_seconds=30);c=DaemonService(daemon_root=root,handoff_dir=h,project_id='P',daemon_id='d1',dispatch=_dispatch,interval_seconds=30)
        try:
            a.start();deadline=time.time()+3
            while a.cycle_count<1 and time.time()<deadline: time.sleep(.05)
            with pytest.raises(DaemonPlaneBusy): c.start()
        finally:
            c.close();a.close()

def test_recovery_is_refused_while_daemon_service_owns_plane():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);h=b/'h';h.mkdir();_handoff(h);root=b/'daemon';svc=DaemonService(daemon_root=root,handoff_dir=h,project_id='P',daemon_id='d1',dispatch=_dispatch,interval_seconds=30)
        try:
            svc.start();deadline=time.time()+3
            while svc.cycle_count<1 and time.time()<deadline: time.sleep(.05)
            checkpoint(root,'c1')
            with pytest.raises(DaemonPlaneBusy): recover(root,'c1')
        finally:svc.close()

def test_first_cycle_hang_does_not_report_healthy_forever():
    # model the service contract without actually hanging a test thread forever
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);h=b/'h';h.mkdir();_handoff(h);svc=DaemonService(daemon_root=b/'daemon',handoff_dir=h,project_id='P',daemon_id='d1',dispatch=_dispatch,interval_seconds=1)
        try:
            svc.start();svc.started_at=time.time()-120;svc.last_cycle_at=None
            health=svc.health();assert health['ok'] is False;assert health['status'] in {'degraded','stalled'}
        finally:svc.close()
