from __future__ import annotations

import hashlib, json, tempfile, time
from pathlib import Path

from mvf_resident.daemon_plane import paths
from mvf_resident.daemon_service import DaemonService
from mvf_resident.lifecycle import ResidentLifecycle
from mvf_resident.resident import MVFResident, DutyContract
from mvf_resident.surfaces import REQUIRED_ACTIVE_SURFACES


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


class Fake:
    def call(self, name, payload):
        return {'ok': True}


def test_unresolved_surface_deficit_survives_lifecycle_restart_without_new_transition():
    with tempfile.TemporaryDirectory() as td:
        b = Path(td); h = b / 'h'; h.mkdir(); _handoff(h, drift=True); root = b / 'daemon'
        duty = (DutyContract('a', 's', 'c', (('x', {}),)),)
        life = ResidentLifecycle.from_daemon_plane(MVFResident(Fake(), now=lambda: '2026-09-15T00:00:00+00:00'), root, h, daemon_id='d1', project_id='P')
        try:
            first = life.run_cycle(duty)
            assert 'deficit:continuity-active-surfaces' in first['deficits']
            first_evidence = first['evidence_count']
        finally:
            life.close()
        life2 = ResidentLifecycle.from_daemon_plane(MVFResident(Fake(), now=lambda: '2026-09-15T00:01:00+00:00'), root, h, daemon_id='d1', project_id='P')
        try:
            second = life2.run_cycle(duty)
            assert 'deficit:continuity-active-surfaces' in second['deficits']
            assert second['evidence_count'] == first_evidence
        finally:
            life2.close()


def test_wall_clock_jump_does_not_change_daemon_health_freshness(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        b = Path(td); h = b / 'h'; h.mkdir(); _handoff(h); svc = DaemonService(daemon_root=b/'daemon', handoff_dir=h, project_id='P', daemon_id='d1', dispatch=lambda n,p: {'ok': True, 'status': 'current'} if n=='continuity.convergence.inspect' else {'ok': True}, interval_seconds=30)
        try:
            svc.start(); deadline=time.time()+4
            while svc.cycle_count<1 and time.time()<deadline: time.sleep(.05)
            assert svc.health()['ok'] is True
            import mvf_resident.daemon_service as ds
            real = ds.time.time
            monkeypatch.setattr(ds.time, 'time', lambda: real() + 10_000_000)
            assert svc.health()['ok'] is True
            monkeypatch.setattr(ds.time, 'time', lambda: real() - 10_000_000)
            assert svc.health()['ok'] is True
        finally:
            svc.close()


def test_timeline_rotation_bounds_single_generation_size():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td); h=b/'h'; h.mkdir(); _handoff(h); root=b/'daemon'; svc=DaemonService(daemon_root=root,handoff_dir=h,project_id='P',daemon_id='d1',dispatch=lambda n,p:{'ok':True},interval_seconds=30)
        p=paths(root); p.status_timeline.parent.mkdir(parents=True,exist_ok=True); p.status_timeline.write_bytes(b'X'*(4*1024*1024+1))
        svc._event('rotation_test', value=1)
        assert p.status_timeline.stat().st_size < 65536
        assert p.status_timeline.with_name('timeline.1.jsonl').exists()
        svc.close()
