from __future__ import annotations

import json, sqlite3, tempfile, threading
from pathlib import Path
import pytest

from mvf_resident.daemon_plane import (
    DaemonPlaneBusy, DaemonPlaneCorrupt, DaemonPlaneError, DaemonPlaneMigrationError,
    audit, checkpoint, initialize, migrate, paths, plane_lock, qualify_root, recover, write_current,
)

def test_plane_initializes_separate_identity_state_evidence_biography():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/'daemon';p=initialize(root,daemon_id='d1',project_id='P')
        assert audit(root).status=='CURRENT'
        assert json.loads(p.identity.read_text())['authority']=='COGNITIVE_PLANE_ONLY'
        assert json.loads(p.current_state.read_text())['generation']==0
        assert p.evidence_db.exists() and p.biography_db.exists()

def test_plane_rejects_reserved_sibling_collision():
    with tempfile.TemporaryDirectory() as td:
        for name in ('state','continuity','data','handoff'):
            with pytest.raises(DaemonPlaneError,match='COLLIDES'):
                qualify_root(Path(td)/name)
        project=Path(td)/'project';project.mkdir()
        qualify_root(project/'daemon',project_root=project)
        with pytest.raises(DaemonPlaneError,match='FIRST_CLASS'):
            qualify_root(project/'nested'/'daemon',project_root=project)

def test_missing_and_corrupt_state_are_visible_not_repaired_silently():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/'daemon';p=initialize(root,daemon_id='d1',project_id='P');p.current_state.unlink()
        a=audit(root);assert a.status=='UNKNOWN_INCOMPLETE' and 'current_state' in a.missing
        initialize(root,daemon_id='d1',project_id='P');p.current_state.write_text('{broken',encoding='utf-8')
        a=audit(root);assert a.status=='CORRUPT' and 'current_state' in a.corrupt

def test_atomic_write_interruption_preserves_canonical_state():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/'daemon';p=initialize(root,daemon_id='d1',project_id='P');before=p.current_state.read_bytes()
        def boom(_): raise RuntimeError('simulated crash before replace')
        with pytest.raises(RuntimeError): write_current(root,{'x':1},before_replace=boom)
        assert p.current_state.read_bytes()==before
        assert audit(root).status=='CURRENT'

def test_nonblocking_concurrent_writer_is_denied_but_stale_lock_bytes_do_not_strand():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/'daemon';p=initialize(root,daemon_id='d1',project_id='P');p.lock.write_text('pid=999999\ncreation=1\n',encoding='utf-8')
        # text is not authority; no OS lock means acquisition succeeds
        with plane_lock(p.lock,blocking=False): pass
        entered=threading.Event();release=threading.Event()
        def holder():
            with plane_lock(p.lock): entered.set();release.wait(3)
        t=threading.Thread(target=holder);t.start();assert entered.wait(2)
        try:
            with pytest.raises(DaemonPlaneBusy):
                with plane_lock(p.lock,blocking=False): pass
        finally:
            release.set();t.join(3)

def test_checkpoint_and_recovery_restore_exact_current_state_and_databases():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/'daemon';p=initialize(root,daemon_id='d1',project_id='P')
        write_current(root,{'phase':'good'})
        for dbp in (p.evidence_db,p.biography_db):
            db=sqlite3.connect(dbp);db.execute('CREATE TABLE IF NOT EXISTS t(v TEXT)');db.execute('INSERT INTO t VALUES ("good")');db.commit();db.close()
        checkpoint(root,'good')
        write_current(root,{'phase':'bad'})
        for dbp in (p.evidence_db,p.biography_db):
            db=sqlite3.connect(dbp);db.execute('DELETE FROM t');db.execute('INSERT INTO t VALUES ("bad")');db.commit();db.close()
        recover(root,'good')
        assert json.loads(p.current_state.read_text())['state']=={'phase':'good'}
        for dbp in (p.evidence_db,p.biography_db):
            db=sqlite3.connect(dbp);assert db.execute('SELECT v FROM t').fetchone()[0]=='good';db.close()
        assert audit(root).status=='CURRENT'

def test_corrupt_checkpoint_hash_blocks_recovery():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/'daemon';p=initialize(root,daemon_id='d1',project_id='P');cp=checkpoint(root,'good');(cp/'current.json').write_text('tampered',encoding='utf-8')
        with pytest.raises(DaemonPlaneCorrupt,match='HASH_MISMATCH'): recover(root,'good')

def test_failed_migration_rolls_back_current_state():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/'daemon';p=initialize(root,daemon_id='d1',project_id='P');write_current(root,{'version':'before'})
        before=p.current_state.read_bytes()
        def bad(root):
            write_current(root,{'version':'during'})
            raise RuntimeError('migration crash')
        with pytest.raises(DaemonPlaneMigrationError,match='ROLLED_BACK'): migrate(root,2,bad)
        assert p.current_state.read_bytes()==before
        assert audit(root).status=='CURRENT'
