from __future__ import annotations

import hashlib, json, sqlite3, subprocess, sys, tempfile, threading, time, urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
import pytest

from mvf_resident.daemon_plane import DaemonPlaneBusy, DaemonPlaneCorrupt, checkpoint, initialize, migrate, service_lease
from mvf_resident.daemon_service import DaemonService, _Handler
from mvf_resident.surfaces import REQUIRED_ACTIVE_SURFACES

ROOT = Path(__file__).resolve().parents[1]


def _handoff(root: Path, *, drift: bool = False):
    files = {}
    for n in REQUIRED_ACTIVE_SURFACES:
        p = root / n
        p.write_text(n, encoding='utf-8')
        b = p.read_bytes()
        files[n] = {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
    cp = files['THREAD_CONTINUITY_CHECKPOINT_2026-09-15.md']['sha256']
    (root / 'SNAPSHOT_MANIFEST_SHA256.json').write_text(json.dumps({'updated_at': 'x', 'continuity_checkpoint_sha256': cp, 'files': files}), encoding='utf-8')
    if drift:
        (root / 'LIVE_SHADOW.md').write_text('drift', encoding='utf-8')


def _dispatch(name, payload):
    return {'ok': True, 'status': 'current'} if name == 'continuity.convergence.inspect' else {'ok': True}


def _bio_digest(dbp: Path):
    db = sqlite3.connect(dbp)
    ids = sorted(str(x[0]) for x in db.execute('select event_id from biography_events').fetchall())
    db.close()
    return hashlib.sha256(json.dumps(ids, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def test_existing_plane_identity_mismatch_is_rejected_by_initialize():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / 'daemon'
        initialize(root, daemon_id='d1', project_id='P')
        with pytest.raises(DaemonPlaneCorrupt):
            initialize(root, daemon_id='d2', project_id='P')
        with pytest.raises(DaemonPlaneCorrupt):
            initialize(root, daemon_id='d1', project_id='Q')


def test_checkpoint_waits_for_active_cycle_and_captures_coherent_state_evidence_biography():
    with tempfile.TemporaryDirectory() as td:
        b = Path(td)
        h = b / 'h'
        h.mkdir()
        _handoff(h)
        entered = threading.Event()
        release = threading.Event()
        once = {'v': False}

        def blocking(name, payload):
            if not once['v']:
                once['v'] = True
                entered.set()
                release.wait(3)
            return {'ok': True, 'status': 'current'} if name == 'continuity.convergence.inspect' else {'ok': True}

        svc = DaemonService(daemon_root=b / 'daemon', handoff_dir=h, project_id='P', daemon_id='d1', dispatch=blocking, interval_seconds=30)
        svc.start()
        assert entered.wait(2)
        result = {}
        done = threading.Event()

        def cp():
            result['path'] = checkpoint(b / 'daemon', 'during')
            done.set()

        t = threading.Thread(target=cp)
        t.start()
        time.sleep(.2)
        assert not done.is_set()
        release.set()
        assert done.wait(4)
        t.join(2)
        try:
            cpdir = result['path']
            state = json.loads((cpdir / 'current.json').read_text())['state']
            edb = sqlite3.connect(cpdir / 'evidence.sqlite')
            ec = edb.execute('select count(*) from evidence').fetchone()[0]
            edb.close()
            assert state['evidence_count'] == ec
            assert state['biography_graph_digest'] == _bio_digest(cpdir / 'biography.sqlite')
        finally:
            svc.close()


def test_migration_is_refused_while_service_active():
    with tempfile.TemporaryDirectory() as td:
        b = Path(td)
        h = b / 'h'
        h.mkdir()
        _handoff(h)
        root = b / 'daemon'
        svc = DaemonService(daemon_root=root, handoff_dir=h, project_id='P', daemon_id='d1', dispatch=_dispatch, interval_seconds=30)
        svc.start()
        try:
            deadline = time.time() + 3
            while svc.cycle_count < 1 and time.time() < deadline:
                time.sleep(.05)
            with pytest.raises(DaemonPlaneBusy):
                migrate(root, 2, lambda _r: None)
        finally:
            svc.close()


def test_cross_process_service_lock_fences_duplicate_and_releases_after_crash():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / 'daemon'
        marker = Path(td) / 'ready'
        code = "from pathlib import Path\nimport sys,time\nfrom mvf_resident.daemon_plane import service_lease\nroot=Path(sys.argv[1]);marker=Path(sys.argv[2])\nwith service_lease(root,blocking=False):\n marker.write_text('ready')\n time.sleep(30)"
        proc = subprocess.Popen([sys.executable, '-c', code, str(root), str(marker)], cwd=str(ROOT))
        try:
            deadline = time.time() + 5
            while not marker.exists() and time.time() < deadline:
                time.sleep(.05)
            assert marker.exists()
            with pytest.raises(DaemonPlaneBusy):
                with service_lease(root, blocking=False):
                    pass
            proc.kill()
            proc.wait(timeout=5)
            deadline=time.time()+3
            while True:
                try:
                    with service_lease(root, blocking=False):
                        break
                except DaemonPlaneBusy:
                    if time.time()>=deadline: raise
                    time.sleep(.05)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)


def test_continuity_drift_is_cognitive_attention_not_process_restart_condition():
    with tempfile.TemporaryDirectory() as td:
        b = Path(td)
        h = b / 'h'
        h.mkdir()
        _handoff(h, drift=True)
        svc = DaemonService(daemon_root=b / 'daemon', handoff_dir=h, project_id='P', daemon_id='d1', dispatch=_dispatch, interval_seconds=30)
        try:
            svc.start()
            deadline = time.time() + 4
            while svc.cycle_count < 1 and time.time() < deadline:
                time.sleep(.05)
            assert svc.status()['surface_status'] == 'STALE'
            assert svc.health()['ok'] is True
        finally:
            svc.close()


def test_large_error_event_is_bounded_for_native_http_consumers():
    with tempfile.TemporaryDirectory() as td:
        b = Path(td)
        h = b / 'h'
        h.mkdir()
        _handoff(h)
        svc = DaemonService(daemon_root=b / 'daemon', handoff_dir=h, project_id='P', daemon_id='d1', dispatch=_dispatch, interval_seconds=30)
        svc._event('cycle_failed', error='X' * 400000)
        server = ThreadingHTTPServer(('127.0.0.1', 0), _Handler)
        server.daemon_service = svc
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            raw = urllib.request.urlopen(f'http://127.0.0.1:{server.server_address[1]}/events', timeout=2).read()
            assert len(raw) < 262144
            json.loads(raw.decode())
        finally:
            server.shutdown()
            server.server_close()
            t.join(2)
            svc.close()


def test_recent_event_timeline_survives_clean_service_restart():
    with tempfile.TemporaryDirectory() as td:
        b = Path(td)
        h = b / 'h'
        h.mkdir()
        _handoff(h)
        root = b / 'daemon'
        a = DaemonService(daemon_root=root, handoff_dir=h, project_id='P', daemon_id='d1', dispatch=_dispatch, interval_seconds=30)
        a._event('custom_test_event', value=1)
        a.close()
        bsvc = DaemonService(daemon_root=root, handoff_dir=h, project_id='P', daemon_id='d1', dispatch=_dispatch, interval_seconds=30)
        try:
            assert any(e.get('kind') == 'custom_test_event' for e in bsvc.event_rows())
        finally:
            bsvc.close()
