from __future__ import annotations
import os,sys,tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"baseline"/"pcmmad_receiver"))
import lab_tools_ops

def test_configured_git_executable_wins():
    with tempfile.TemporaryDirectory() as d:
        fake=Path(d)/"git.exe";fake.write_bytes(b"x")
        with patch.dict(os.environ,{"PCMMAD_GIT_EXE":str(fake)},clear=False): exe,error=lab_tools_ops._resolve_git_executable()
        assert error is None and Path(exe)==fake.resolve()

def test_configured_missing_git_fails_closed():
    with tempfile.TemporaryDirectory() as d:
        missing=Path(d)/"missing-git.exe"
        with patch.dict(os.environ,{"PCMMAD_GIT_EXE":str(missing)},clear=False): exe,error=lab_tools_ops._resolve_git_executable()
        assert exe is None and error.startswith("PCMMAD_GIT_EXE_MISSING:")

def test_git_envelope_uses_configured_executable(monkeypatch,tmp_path):
    fake=tmp_path/"git.exe";fake.write_bytes(b"x");captured={}
    def runner(command,**kwargs): captured["command"]=command;return {"ok":True,"stdout":"","stderr":"","return_code":0}
    monkeypatch.setattr(lab_tools_ops,"run_subprocess_envelope",runner);monkeypatch.setenv("PCMMAD_GIT_EXE",str(fake))
    assert lab_tools_ops._git_envelope(tmp_path,["git","status"])["ok"] is True
    assert Path(captured["command"][0])==fake.resolve() and captured["command"][1:]==["status"]

def test_recovery_installer_persists_git_executable():
    source=(ROOT/"supervisor"/"install_unattended_recovery.ps1").read_text(encoding="utf-8")
    assert "PCMMAD_GIT_EXE" in source and "GIT_EXECUTABLE_NOT_FOUND_AT_INSTALL" in source and "Programs\\Git\\cmd\\git.exe" in source
