from __future__ import annotations
import os,subprocess,sys,tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'baseline'/'pcmmad_receiver'))
import server_hardening as sh

def test_windows_child_creationflags_use_new_process_group():
    flags=sh._child_creationflags()
    if os.name=='nt': assert flags & subprocess.CREATE_NEW_PROCESS_GROUP
    else: assert flags==0

def test_sync_subprocess_envelope_passes_isolated_creationflags(monkeypatch,tmp_path):
    real=subprocess.Popen;seen=[]
    class Proxy:
        def __init__(self,*a,**k): seen.append(k.get('creationflags',0));self._p=real(*a,**k)
        def __getattr__(self,n): return getattr(self._p,n)
    monkeypatch.setattr(sh.subprocess,'Popen',Proxy)
    out=sh.run_subprocess_envelope([sys.executable,'-c','print("ok")'],cwd=tmp_path,timeout_seconds=5,stdout_max_bytes=1000,stderr_max_bytes=1000)
    assert out['ok'] is True
    if os.name=='nt': assert seen and seen[0] & subprocess.CREATE_NEW_PROCESS_GROUP

def test_background_process_uses_same_isolation(tmp_path):
    with open(tmp_path/'o','wb') as o, open(tmp_path/'e','wb') as e:
        p=sh.start_background_process([sys.executable,'-c','print(1)'],cwd=tmp_path,stdout=o,stderr=e)
        assert p.wait(timeout=5)==0
