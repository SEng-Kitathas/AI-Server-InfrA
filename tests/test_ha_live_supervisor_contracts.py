from __future__ import annotations
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "receiver_supervisor_ha",
    ROOT/"supervisor"/"receiver_supervisor.py",
)
mod=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

class FakeResponse:
    def __init__(self,payload):
        self.status=200
        self.payload=payload
    def __enter__(self):
        return self
    def __exit__(self,*_):
        return False
    def read(self,*_):
        return json.dumps(self.payload).encode("utf-8")

def test_receiver_lab_health_accepts_degraded_router_without_schema():
    payload={"ok":True,"status":"degraded","router":True}
    with patch.object(mod.urllib.request,"urlopen",return_value=FakeResponse(payload)):
        ok,err=mod.probe(
            "http://x",1.0,
            expected_schema_family=None,
            expected_identity={"router":"True"},
        )
    assert ok is True
    assert err is None

def test_receiver_lab_health_accepts_online_router_without_schema():
    payload={"ok":True,"status":"online","router":True}
    with patch.object(mod.urllib.request,"urlopen",return_value=FakeResponse(payload)):
        ok,err=mod.probe(
            "http://x",1.0,
            expected_schema_family=None,
            expected_identity={"router":"True"},
        )
    assert ok is True
    assert err is None

def test_browser_service_identity_accepts_missing_status():
    payload={"ok":True,"service":"pcmmad_browser_bridge"}
    with patch.object(mod.urllib.request,"urlopen",return_value=FakeResponse(payload)):
        ok,err=mod.probe(
            "http://x",1.0,
            expected_schema_family=None,
            expected_identity={"service":"pcmmad_browser_bridge"},
        )
    assert ok is True
    assert err is None

def test_daemon_explicit_schema_still_enforced():
    payload={
        "ok":True,
        "status":"healthy",
        "schema":"wrong.v1",
        "daemon_id":"d",
        "project_id":"p",
        "mutation_authority":False,
    }
    with patch.object(mod.urllib.request,"urlopen",return_value=FakeResponse(payload)):
        ok,err=mod.probe(
            "http://x",1.0,
            expected_schema_family="mvf.daemon-health.",
            expected_identity={"daemon_id":"d","project_id":"p"},
        )
    assert ok is False
    assert str(err).startswith("SCHEMA_IDENTITY_MISMATCH")

def test_installer_generates_correct_supervisor_contracts():
    source=(ROOT/"supervisor"/"install_unattended_recovery.ps1").read_text(
        encoding="utf-8"
    )
    assert "'--expected-router'" in source
    assert "--receipt-action TRIGGER_CANONICAL_NGROK_TASK" not in source
    assert "BROWSER_SUPERVISOR_PYTHON_MISSING" in source
    assert "Get-Command python.exe -ErrorAction Stop" not in source
