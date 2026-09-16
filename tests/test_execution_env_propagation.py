from __future__ import annotations

import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"baseline"/"pcmmad_receiver"))

import lab_tools_execution


class FakeError(Exception):
    def __init__(self,error_code,message,status=400,**extra):
        super().__init__(message)
        self.error_code=error_code
        self.status=status
        self.extra=extra


def _deps(tmp_path, monkeypatch):
    captured={}
    def runner(command,**kwargs):
        captured["command"]=command
        captured["kwargs"]=kwargs
        return {"ok":True,"status":"COMPLETED","return_code":0,"stdout":"","stderr":"","stdout_truncated":False,"stderr_truncated":False}
    monkeypatch.setattr(lab_tools_execution,"run_subprocess_envelope",runner)
    dep=lab_tools_execution.ExecutionToolDeps(
        error_cls=FakeError,
        request_optional_positive_int=lambda *a,**k: None,
        resolve_cwd=lambda project_id,cwd: tmp_path,
        exec_env=lambda payload: {"PCMMAD_GIT_EXE":"X:/qualified/git.exe","SENTINEL":"present"},
        finalize_job=lambda *a,**k: {},
        read_job=lambda *a,**k: {},
        tail_text=lambda *a,**k:("",False),
        execution_modes=set(),
        max_output_bytes=50000,
        default_timeout_seconds=30,
        default_stdout_max_bytes=50000,
        default_stderr_max_bytes=50000,
        max_timeout_seconds=600,
        submit_job=lambda *a,**k:{},
        terminate_job=lambda *a,**k:None,
        utc_now=lambda:"now",
    )
    return dep,captured

def test_sync_execution_propagates_resolved_env(tmp_path,monkeypatch):
    dep,captured=_deps(tmp_path,monkeypatch)
    result=lab_tools_execution._sync_execution_payload({"project_id":"P","command":["python"],"args":["-V"],"env":{"PCMMAD_GIT_EXE":"X:/qualified/git.exe"}},dep)
    assert result["ok"] is True
    assert captured["kwargs"]["env"]["PCMMAD_GIT_EXE"]=="X:/qualified/git.exe"
    assert captured["kwargs"]["env"]["SENTINEL"]=="present"

def test_python_execution_propagates_resolved_env(tmp_path,monkeypatch):
    dep,captured=_deps(tmp_path,monkeypatch)
    result=lab_tools_execution._python_execution_payload({"project_id":"P","command":["python"],"code":"print(1)","env":{"PCMMAD_GIT_EXE":"X:/qualified/git.exe"}},dep)
    assert result["ok"] is True
    assert captured["kwargs"]["env"]["PCMMAD_GIT_EXE"]=="X:/qualified/git.exe"
