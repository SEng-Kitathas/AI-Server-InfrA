from __future__ import annotations
import hashlib,json,tempfile,threading,time
from pathlib import Path
from http.server import ThreadingHTTPServer
from mvf_resident.daemon_service import DaemonService,_Handler
from mvf_resident.surfaces import REQUIRED_ACTIVE_SURFACES
from supervisor.receiver_supervisor import probe

def _handoff(root:Path):
    files={}
    for n in REQUIRED_ACTIVE_SURFACES:
        p=root/n;p.write_text(n,encoding='utf-8');b=p.read_bytes();files[n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    cp=files['THREAD_CONTINUITY_CHECKPOINT_2026-09-15.md']['sha256'];(root/'SNAPSHOT_MANIFEST_SHA256.json').write_text(json.dumps({'updated_at':'x','continuity_checkpoint_sha256':cp,'files':files}),encoding='utf-8')

def _dispatch(name,payload):
    return {'ok':True,'status':'current'} if name=='continuity.convergence.inspect' else {'ok':True}

def test_existing_supervisor_probe_accepts_daemon_health_schema_family():
    with tempfile.TemporaryDirectory() as td:
        base=Path(td);h=base/'h';h.mkdir();_handoff(h);svc=DaemonService(daemon_root=base/'daemon',handoff_dir=h,project_id='P',daemon_id='d1',dispatch=_dispatch,interval_seconds=1.0)
        httpd=ThreadingHTTPServer(('127.0.0.1',0),_Handler);httpd.daemon_service=svc;svc.start();thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
        try:
            deadline=time.time()+3
            while svc.cycle_count<1 and time.time()<deadline: time.sleep(.05)
            ok,detail=probe(f'http://127.0.0.1:{httpd.server_address[1]}/health',2.0,'mvf.daemon-health.')
            assert ok is True, detail
        finally:
            httpd.shutdown();httpd.server_close();svc.close();thread.join(2)
