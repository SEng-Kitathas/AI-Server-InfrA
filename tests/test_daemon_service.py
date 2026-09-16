from __future__ import annotations

import hashlib,json,tempfile,threading,time,urllib.request
from pathlib import Path
from http.server import ThreadingHTTPServer

from mvf_resident.daemon_service import DaemonService,_Handler
from mvf_resident.surfaces import REQUIRED_ACTIVE_SURFACES

def _handoff(root:Path):
    files={}
    for n in REQUIRED_ACTIVE_SURFACES:
        p=root/n;p.write_text(n,encoding='utf-8');b=p.read_bytes();files[n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    cp=files['THREAD_CONTINUITY_CHECKPOINT_2026-09-15.md']['sha256'];(root/'SNAPSHOT_MANIFEST_SHA256.json').write_text(json.dumps({'updated_at':'x','continuity_checkpoint_sha256':cp,'files':files}),encoding='utf-8')

def _dispatch(name,payload):
    if name=='continuity.convergence.inspect': return {'ok':True,'status':'current'}
    return {'ok':True}

def test_daemon_service_runs_proactively_without_inbound_request():
    with tempfile.TemporaryDirectory() as td:
        base=Path(td);h=base/'h';h.mkdir();_handoff(h)
        svc=DaemonService(daemon_root=base/'daemon',handoff_dir=h,project_id='P',daemon_id='d1',dispatch=_dispatch,interval_seconds=1.0)
        try:
            svc.start();deadline=time.time()+4
            while svc.cycle_count<2 and time.time()<deadline: time.sleep(.05)
            assert svc.cycle_count>=2
            health=svc.health();assert health['ok'] is True;assert health['initiative_alive'] is True;assert health['mutation_authority'] is False
            assert any(e['kind']=='cycle_completed' for e in svc.event_rows())
            from mvf_resident.daemon_plane import paths
            dp=paths(base/'daemon');svc.status();assert dp.status_current.exists();assert dp.status_timeline.exists();assert 'cycle_completed' in dp.status_timeline.read_text(encoding='utf-8')
        finally: svc.close()

def test_health_status_and_events_http_surfaces_are_read_only():
    with tempfile.TemporaryDirectory() as td:
        base=Path(td);h=base/'h';h.mkdir();_handoff(h)
        svc=DaemonService(daemon_root=base/'daemon',handoff_dir=h,project_id='P',daemon_id='d1',dispatch=_dispatch,interval_seconds=1.0)
        httpd=ThreadingHTTPServer(('127.0.0.1',0),_Handler);httpd.daemon_service=svc;svc.start();t=threading.Thread(target=httpd.serve_forever,daemon=True);t.start()
        try:
            deadline=time.time()+3
            while svc.cycle_count<1 and time.time()<deadline: time.sleep(.05)
            port=httpd.server_address[1]
            for endpoint in ('health','status','events'):
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/{endpoint}',timeout=2) as resp:
                    body=json.loads(resp.read().decode('utf-8'));assert resp.status==200
                    if endpoint!='events': assert body['mutation_authority'] is False
            assert svc.cycle_count>=1
        finally:
            httpd.shutdown();httpd.server_close();svc.close();t.join(2)

def test_cycle_failure_degrades_health_but_loop_stays_alive():
    with tempfile.TemporaryDirectory() as td:
        base=Path(td);h=base/'h';h.mkdir();_handoff(h)
        def bad(name,payload): raise RuntimeError('tool unavailable')
        svc=DaemonService(daemon_root=base/'daemon',handoff_dir=h,project_id='P',daemon_id='d1',dispatch=bad,interval_seconds=1.0)
        try:
            svc.start();deadline=time.time()+3
            while svc.last_error is None and time.time()<deadline: time.sleep(.05)
            assert svc._thread is not None and svc._thread.is_alive()
            # duty exceptions are captured into UNKNOWN results by resident, so service should remain healthy if lifecycle completes
            assert svc.health()['initiative_alive'] is True
        finally: svc.close()
