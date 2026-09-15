from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("receiver_supervisor_auth", ROOT / "supervisor" / "receiver_supervisor.py")
SUP = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(SUP)


class _Resp:
    status = 200
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, _n): return json.dumps({"ok": True, "status": "healthy", "schema_version": "11.0.0", "capability_count": 1, "catalog_digest": "abc"}).encode()


def test_probe_injects_existing_receiver_key_without_leaking_it():
    seen = {}
    secret = "super-secret-probe-key"
    def fake(req, timeout):
        seen["req"] = req; seen["timeout"] = timeout; return _Resp()
    with patch.dict(os.environ, {"GITHOME_API_KEY": secret}, clear=False), patch.object(SUP.urllib.request, "urlopen", side_effect=fake):
        ok, err = SUP.probe("http://127.0.0.1:5510/health", 1.0, "11.")
    assert ok is True and err is None
    assert isinstance(seen["req"], SUP.urllib.request.Request)
    assert seen["req"].get_header("X-githome-key") == secret
    assert secret not in repr((ok, err))


def test_probe_preserves_legacy_no_key_urlopen_shape():
    seen = {}
    def fake(req, timeout): seen["req"] = req; return _Resp()
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("GITHOME_API_KEY", None)
        with patch.object(SUP.urllib.request, "urlopen", side_effect=fake):
            ok, err = SUP.probe("http://127.0.0.1:5510/health", 1.0, "11.")
    assert ok is True and err is None
    assert seen["req"] == "http://127.0.0.1:5510/health"
