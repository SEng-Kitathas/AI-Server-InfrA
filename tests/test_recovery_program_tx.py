from __future__ import annotations
import json,tempfile
from pathlib import Path
import pytest
import supervisor.recovery_program_tx as tx

def _sources(base:Path,version:str):
    bundle=base/'bundle';support=base/'support';daemon=base/'daemon';bundle.mkdir(parents=True);support.mkdir();daemon.mkdir()
    (bundle/'bundle_manifest.json').write_text(version,encoding='utf-8');(bundle/'payload.txt').write_text('payload-'+version,encoding='utf-8')
    for name in tx.SUPPORT_FILES:(support/name).write_text(name+'-'+version,encoding='utf-8')
    (daemon/'resident.py').write_text('resident-'+version,encoding='utf-8')
    return bundle,support,daemon

def test_stage_commit_cleanly_replaces_old_program_and_preserves_mutable_state():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);install=b/'install';bundle1,support1,daemon1=_sources(b/'s1','v1');bundle2,support2,daemon2=_sources(b/'s2','v2')
        t1=tx.stage(bundle1,support1,daemon1,install);tx.commit(t1);(install/'secret.dpapi').write_text('secret');(install/'failure.json').write_text('budget');m=json.loads((install/tx.MANIFEST_NAME).read_text());(install/'obsolete_program.txt').write_text('old');m['files']['obsolete_program.txt']={'sha256':'x','bytes':3};(install/tx.MANIFEST_NAME).write_text(json.dumps(m))
        t2=tx.stage(bundle2,support2,daemon2,install);assert not (install/'obsolete_program.txt').exists();assert (install/'payload.txt').read_text()=='payload-v2';assert (install/'secret.dpapi').read_text()=='secret';assert (install/'failure.json').read_text()=='budget';tx.commit(t2)

def test_rollback_restores_exact_old_program_and_preserves_mutable_state():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);install=b/'install';bundle1,support1,daemon1=_sources(b/'s1','v1');bundle2,support2,daemon2=_sources(b/'s2','v2');t1=tx.stage(bundle1,support1,daemon1,install);tx.commit(t1);old=(install/'payload.txt').read_bytes();(install/'secret.dpapi').write_text('secret');t2=tx.stage(bundle2,support2,daemon2,install);tx.rollback(t2,install_root=install);assert (install/'payload.txt').read_bytes()==old;assert (install/'secret.dpapi').read_text()=='secret'

def test_corrupt_or_escaping_manifest_fails_before_program_mutation():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);install=b/'install';install.mkdir();bundle,support,daemon=_sources(b/'s','v');(install/'keep').write_text('keep');(install/tx.MANIFEST_NAME).write_text('{bad')
        with pytest.raises(tx.ProgramTxError,match='CORRUPT'):tx.stage(bundle,support,daemon,install)
        assert (install/'keep').read_text()=='keep'
        (install/tx.MANIFEST_NAME).write_text(json.dumps({'schema':tx.SCHEMA,'files':{'../escape':{}}}))
        with pytest.raises(tx.ProgramTxError,match='ESCAPE'):tx.stage(bundle,support,daemon,install)

def test_mid_copy_failure_rolls_back_previous_program(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);install=b/'install';bundle1,support1,daemon1=_sources(b/'s1','v1');bundle2,support2,daemon2=_sources(b/'s2','v2');t1=tx.stage(bundle1,support1,daemon1,install);tx.commit(t1);before=(install/'payload.txt').read_bytes();real=tx.shutil.copy2;calls={'n':0}
        def boom(src,dst,*a,**k):
            calls['n']+=1
            if calls['n']==4:raise OSError('simulated copy failure')
            return real(src,dst,*a,**k)
        monkeypatch.setattr(tx.shutil,'copy2',boom)
        with pytest.raises(OSError):tx.stage(bundle2,support2,daemon2,install)
        assert (install/'payload.txt').read_bytes()==before

def test_committed_transaction_can_be_archived_and_later_rolled_back():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);install=b/'install';bundle1,support1,daemon1=_sources(b/'s1','v1');bundle2,support2,daemon2=_sources(b/'s2','v2');t1=tx.stage(bundle1,support1,daemon1,install);tx.commit(t1);old=(install/'payload.txt').read_bytes();(install/'secret.dpapi').write_text('keep');t2=tx.stage(bundle2,support2,daemon2,install);arch=tx.commit(t2,archive_root=install/'promotion_backups');assert arch and arch.exists();tx.rollback(arch,install_root=install);assert (install/'payload.txt').read_bytes()==old;assert (install/'secret.dpapi').read_text()=='keep'


def test_bundle_excludes_vcs_and_runtime_debris():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);install=b/'install';bundle,support,daemon=_sources(b/'s','v')
        for rel in ['.git/objects/x','.pytest_cache/v/cache/x','.heat_runtime/tmp.txt','build/out.bin','pkg.egg-info/PKG-INFO','nested/__pycache__/x.pyc']:
            p=bundle/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('junk',encoding='utf-8')
        txid=tx.stage(bundle,support,daemon,install)
        manifest=json.loads((install/tx.MANIFEST_NAME).read_text())
        files=set(manifest['files'])
        assert 'payload.txt' in files
        assert not any(name.startswith('.git/') for name in files)
        assert not any(name.startswith('.pytest_cache/') for name in files)
        assert not any(name.startswith('.heat_runtime/') for name in files)
        assert not any('/__pycache__/' in '/'+name or name.endswith('.pyc') for name in files)
        assert not any(name.startswith('build/') or '.egg-info/' in name for name in files)
        tx.rollback(txid,install_root=install)

def test_safe_unlink_retries_permission_error_after_chmod(monkeypatch,tmp_path):
    p=tmp_path/'locked.txt';p.write_text('x',encoding='utf-8');real=Path.unlink;calls={'n':0}
    def flaky(self,*a,**k):
        if self==p and calls['n']==0:
            calls['n']+=1;raise PermissionError(13,'denied')
        return real(self,*a,**k)
    chmod_calls=[]
    real_chmod=tx.os.chmod
    def chmod(path,mode):
        chmod_calls.append((Path(path),mode));return real_chmod(path,mode)
    monkeypatch.setattr(Path,'unlink',flaky);monkeypatch.setattr(tx.os,'chmod',chmod)
    tx._safe_unlink(p)
    assert calls['n']==1 and chmod_calls and not p.exists()
