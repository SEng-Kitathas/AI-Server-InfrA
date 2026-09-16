from __future__ import annotations

import json, sys, tempfile, threading, time, urllib.error, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import pytest

from mvf_resident.daemon_plane import DaemonPlaneBusy
from mvf_resident.daemon_service import DaemonService, _Handler
from mvf_resident.surfaces import REQUIRED_ACTIVE_SURFACES

ROOT = Path(__file__).resolve().parents[1]


def _handoff(root: Path):
    import hashlib
    files = {}
    for n in REQUIRED_ACTIVE_SURFACES:
        p = root / n
        p.write_text(n, encoding='utf-8')
        b = p.read_bytes()
        files[n] = {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
    cp = files['THREAD_CONTINUITY_CHECKPOINT_2026-09-15.md']['sha256']
    (root / 'SNAPSHOT_MANIFEST_SHA256.json').write_text(json.dumps({'updated_at': 'x', 'continuity_checkpoint_sha256': cp, 'files': files}), encoding='utf-8')


def _dispatch(name, payload):
    return {'ok': True, 'status': 'current'} if name == 'continuity.convergence.inspect' else {'ok': True}


def test_health_http_status_and_body_come_from_one_snapshot():
    class Flap:
        def __init__(self): self.calls = 0
        def health(self):
            self.calls += 1
            return {'schema': 'mvf.daemon-health.v1', 'ok': self.calls == 1, 'status': 'healthy' if self.calls == 1 else 'degraded', 'daemon_id': 'd1', 'project_id': 'P', 'mutation_authority': False}
        def status(self): return {}
        def event_rows(self, limit=None): return []
    svc = Flap()
    server = ThreadingHTTPServer(('127.0.0.1', 0), _Handler)
    server.daemon_service = svc
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{server.server_address[1]}/health', timeout=2) as resp:
            body = json.loads(resp.read().decode())
            assert resp.status == 200
            assert body['ok'] is True
        assert svc.calls == 1
    finally:
        server.shutdown(); server.server_close(); t.join(2)


def test_native_daemon_health_preserves_structured_degraded_body_on_http_503(monkeypatch):
    class Degraded(BaseHTTPRequestHandler):
        def log_message(self, *args): return
        def do_GET(self):
            body = {'schema': 'mvf.daemon-health.v1', 'ok': False, 'status': 'degraded', 'daemon_id': 'd1', 'project_id': 'P', 'mutation_authority': False, 'last_error': 'x'}
            raw = json.dumps(body).encode()
            self.send_response(503); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(raw))); self.end_headers(); self.wfile.write(raw)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Degraded)
    t = threading.Thread(target=server.serve_forever, daemon=True); t.start()
    try:
        sys.path.insert(0, str(ROOT / 'baseline' / 'pcmmad_receiver'))
        import lab_tools_daemon
        monkeypatch.setenv('PCMMAD_DAEMON_URL', f'http://127.0.0.1:{server.server_address[1]}')
        body = lab_tools_daemon._get('/health')
        assert body['ok'] is False and body['status'] == 'degraded'
        assert body['_http_status'] == 503
    finally:
        server.shutdown(); server.server_close(); t.join(2)


def test_hung_initiative_stop_does_not_release_singleton_until_thread_actually_exits():
    with tempfile.TemporaryDirectory() as td:
        b = Path(td); h = b / 'h'; h.mkdir(); _handoff(h); entered = threading.Event(); release = threading.Event()
        def blocking(name, payload):
            entered.set(); release.wait(8)
            return {'ok': True, 'status': 'current'} if name == 'continuity.convergence.inspect' else {'ok': True}
        a = DaemonService(daemon_root=b / 'daemon', handoff_dir=h, project_id='P', daemon_id='d1', dispatch=blocking, interval_seconds=1)
        c = DaemonService(daemon_root=b / 'daemon', handoff_dir=h, project_id='P', daemon_id='d1', dispatch=_dispatch, interval_seconds=1)
        a.start(); assert entered.wait(2)
        try:
            stopped = a.stop()
            assert stopped is False
            with pytest.raises(DaemonPlaneBusy): c.start()
            release.set()
            deadline = time.time() + 4
            while a._thread is not None and a._thread.is_alive() and time.time() < deadline: time.sleep(.05)
            assert a.stop() is True
            c.start()
        finally:
            release.set(); c.close(); a.close()
