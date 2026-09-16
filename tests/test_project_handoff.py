from __future__ import annotations
import hashlib,json,tempfile,threading,time
from pathlib import Path
import pytest
from mvf_resident.project_handoff import ProjectHandoffError,publish,resolve
from mvf_resident.surfaces import REQUIRED_ACTIVE_SURFACES
from mvf_resident.lifecycle import ResidentLifecycle
from mvf_resident.resident import MVFResident,DutyContract

class Fake:
    def call(self,name,payload): return {'ok':True}

def _source(root:Path, marker='v1'):
    files={}
    for n in REQUIRED_ACTIVE_SURFACES:
        p=root/n;p.write_text(f'{n}:{marker}',encoding='utf-8');b=p.read_bytes();files[n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    cp=files['THREAD_CONTINUITY_CHECKPOINT_2026-09-15.md']['sha256']
    (root/'SNAPSHOT_MANIFEST_SHA256.json').write_text(json.dumps({'updated_at':marker,'continuity_checkpoint_sha256':cp,'files':files},indent=2),encoding='utf-8')

def test_publish_requires_current_source_and_resolve_verifies_generation():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);src=b/'src';src.mkdir();project=b/'project';project.mkdir();_source(src)
        pointer=publish(src,project);resolved=resolve(project/'handoff')
        assert resolved.name==pointer['generation'];assert (resolved/'COMMANDERS_INTENT_CURRENT.md').exists()
        (src/'LIVE_SHADOW.md').write_text('drift',encoding='utf-8')
        with pytest.raises(ProjectHandoffError,match='SOURCE_HANDOFF_NOT_CURRENT'):publish(src,project)
        assert resolve(project/'handoff')==resolved

def test_pointer_escape_corrupt_missing_and_manifest_mismatch_are_rejected():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);src=b/'src';src.mkdir();project=b/'project';project.mkdir();_source(src);publish(src,project);root=project/'handoff';pp=root/'current.json'
        original=pp.read_text()
        pp.write_text('{broken',encoding='utf-8');
        with pytest.raises(ProjectHandoffError,match='POINTER_CORRUPT'):resolve(root)
        pp.write_text(json.dumps({'schema':'pcmmad.project-handoff-pointer.v1','relative_path':'../escape','manifest_sha256':'x'}),encoding='utf-8')
        with pytest.raises(ProjectHandoffError,match='POINTER_ESCAPE'):resolve(root)
        pp.write_text(original,encoding='utf-8');obj=json.loads(original);obj['manifest_sha256']='bad';pp.write_text(json.dumps(obj),encoding='utf-8')
        with pytest.raises(ProjectHandoffError,match='MANIFEST_MISMATCH'):resolve(root)

def test_two_publishes_switch_atomically_and_keep_old_generation():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);src=b/'src';src.mkdir();project=b/'project';project.mkdir();_source(src,'v1');p1=publish(src,project);old=resolve(project/'handoff');_source(src,'v2');p2=publish(src,project);new=resolve(project/'handoff')
        assert p1['generation']!=p2['generation'];assert old.exists() and new.exists();assert old!=new
        assert 'v1' in (old/'LIVE_SHADOW.md').read_text();assert 'v2' in (new/'LIVE_SHADOW.md').read_text()

def test_concurrent_resolve_during_publish_observes_only_complete_old_or_new_generation():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);src=b/'src';src.mkdir();project=b/'project';project.mkdir();_source(src,'v1');publish(src,project);seen=[];errors=[];stop=threading.Event()
        def reader():
            while not stop.is_set():
                try: seen.append((resolve(project/'handoff')/'LIVE_SHADOW.md').read_text())
                except Exception as e: errors.append(repr(e))
        t=threading.Thread(target=reader);t.start();_source(src,'v2');publish(src,project);time.sleep(.1);stop.set();t.join(2)
        assert not errors;assert seen;assert all(('v1' in x) or ('v2' in x) for x in seen);assert any('v2' in x for x in seen)

def test_lifecycle_resolver_picks_new_project_handoff_generation_between_cycles():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);src=b/'src';src.mkdir();project=b/'project';project.mkdir();_source(src,'v1');publish(src,project);root=b/'daemon';life=ResidentLifecycle.from_daemon_plane(MVFResident(Fake(),now=lambda:'2026-09-15T00:00:00+00:00'),root,None,daemon_id='d1',project_id='P',handoff_resolver=lambda:resolve(project/'handoff'))
        try:
            a=life.run_cycle((DutyContract('a','s','c',(('x',{}),)),));assert a['surface_audit']['status']=='CURRENT'
            _source(src,'v2');publish(src,project);bb=life.run_cycle((DutyContract('a','s','c',(('x',{}),)),));assert bb['surface_audit']['status']=='CURRENT'
            assert 'v2' in (resolve(project/'handoff')/'LIVE_SHADOW.md').read_text()
        finally:life.close()
