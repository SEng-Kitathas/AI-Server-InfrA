from __future__ import annotations
import importlib.util,json
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('sup',ROOT/'supervisor/receiver_supervisor.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Resp:
 def __init__(self,status,body):self.status=status;self.body=body
 def __enter__(self):return self
 def __exit__(self,*a):return False
 def read(self,n):return self.body
def check(body,status=200):
 with patch.object(m.urllib.request,'urlopen',return_value=Resp(status,json.dumps(body).encode())):return m.probe('x',1)
def test_fake_http_200_is_not_receiver_ready():assert not check({'hello':'world'})[0]
def test_invalid_json_200_is_not_ready():
 with patch.object(m.urllib.request,'urlopen',return_value=Resp(200,b'<html>ok</html>')):assert not m.probe('x',1)[0]
def test_core_ok_healthy_is_ready():assert check({'ok':True,'status':'healthy'})[0]
def test_core_ok_degraded_is_ready_so_optional_failure_does_not_restart_core():assert check({'ok':True,'status':'degraded','optional_failed':['browser']})[0]
def test_explicit_core_not_ok_is_not_ready():assert not check({'ok':False,'status':'degraded'})[0]
def test_unknown_status_fails_closed():assert not check({'ok':True,'status':'mystery'})[0]
