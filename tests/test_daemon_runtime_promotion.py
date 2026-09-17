from __future__ import annotations
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"baseline"/"pcmmad_receiver"
if str(BASE) not in sys.path: sys.path.insert(0,str(BASE))
import lab_tools_daemon_runtime as dr


def write_tree(root:Path,rows:dict[str,str]):
    for rel,text in rows.items():
        p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')


def test_runtime_status_and_promotion_transaction(monkeypatch,tmp_path):
    source=tmp_path/'live'/'mvf_resident';target=tmp_path/'recovery'/'daemon_runtime'/'mvf_resident';promotions=tmp_path/'recovery'/'promotions'
    write_tree(source,{'__init__.py':'','daemon_service.py':'new','nested/x.py':'x'})
    write_tree(target,{'__init__.py':'','daemon_service.py':'old'})
    monkeypatch.setattr(dr,'_source_root',lambda:source)
    monkeypatch.setattr(dr,'_target_root',lambda:target)
    monkeypatch.setattr(dr,'_promotion_root',lambda:promotions)
    monkeypatch.setattr(dr,'_daemon_port',lambda:5015)
    monkeypatch.setattr(dr,'_project_id',lambda:'RECEIVER-LAB')
    monkeypatch.setattr(dr,'_quiesce_daemon',lambda port:{'old_listener_pids':[1],'reaped_listener_pids':[],'port_closed':True})
    monkeypatch.setattr(dr,'_start_and_verify_daemon',lambda port:{'new_listener_pids':[2],'health_schema':'mvf.daemon-health.v1','daemon_id':'pcmmad-daemon','project_id':'RECEIVER-LAB','workload_state':'Running','supervisor_state':'Running'})
    status=dr.runtime_status('RECEIVER-LAB')
    assert status['current'] is False
    receipt=dr.promote_runtime('RECEIVER-LAB',status['source_tree_sha256'])
    assert receipt['promoted'] is True and receipt['consequence_readback']['tree_current'] is True
    assert dr.runtime_status('RECEIVER-LAB')['current'] is True
    assert (target/'daemon_service.py').read_text(encoding='utf-8')=='new'
    assert Path(receipt['backup_root']).joinpath('daemon_service.py').read_text(encoding='utf-8')=='old'


def test_promotion_refuses_stale_source_digest(monkeypatch,tmp_path):
    source=tmp_path/'live'/'mvf_resident';target=tmp_path/'recovery'/'daemon_runtime'/'mvf_resident'
    write_tree(source,{'daemon_service.py':'new'});write_tree(target,{'daemon_service.py':'old'})
    monkeypatch.setattr(dr,'_source_root',lambda:source);monkeypatch.setattr(dr,'_target_root',lambda:target);monkeypatch.setattr(dr,'_promotion_root',lambda:tmp_path/'promotions');monkeypatch.setattr(dr,'_daemon_port',lambda:5015);monkeypatch.setattr(dr,'_project_id',lambda:'RECEIVER-LAB')
    try:dr.promote_runtime('RECEIVER-LAB','0'*64)
    except RuntimeError as exc: assert 'CURRENTNESS_MISMATCH' in str(exc)
    else: raise AssertionError('expected currentness refusal')
    assert (target/'daemon_service.py').read_text(encoding='utf-8')=='old'


def test_registers_status_and_promote():
    handlers={}
    class E(Exception):
        def __init__(self,*args,**kwargs): pass
    def register(name,*args,**kwargs):
        def deco(fn): handlers[name]=(fn,kwargs);return fn
        return deco
    dr.register_daemon_runtime_tools(register,error_cls=E)
    assert {'control.daemon.runtime.status','control.daemon.runtime.promote'} <= set(handlers)
    assert handlers['control.daemon.runtime.promote'][1]['mutating'] is True
    assert handlers['control.daemon.runtime.status'][1]['mutating'] is False
