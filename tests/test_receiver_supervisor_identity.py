from __future__ import annotations
import importlib.util,json
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('sup',ROOT/'supervisor/receiver_supervisor.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class R:
 def __init__(self,body,status=200):self.body=json.dumps(body).encode();self.status=status
 def __enter__(self):return self
 def __exit__(self,*a):return False
 def read(self,n):return self.body
def probe(health,identity):
 seq=iter([R(health),R(identity)])
 with patch.object(m.urllib.request,'urlopen',side_effect=lambda *a,**k:next(seq)):return m.probe('health',1,expected_schema_family='11.',identity_url='identity',minimum_capabilities=100)
def test_impostor_health_without_valid_identity_fails():
 ok,d=probe({'ok':True,'status':'healthy'},{'ok':True});assert not ok and ('SCHEMA' in d or 'CAPABILITY' in d)
def test_incompatible_schema_fails_even_with_many_capabilities():
 ok,d=probe({'ok':True,'status':'healthy'},{'ok':True,'schema_version':'12.0.0','capability_count':999,'catalog_digest':'x'});assert not ok and 'SCHEMA_INCOMPATIBLE' in d
def test_compatible_stale_receiver_can_be_service_ready():
 ok,d=probe({'ok':True,'status':'degraded'},{'ok':True,'schema_version':'11.0.0-candidate','capability_count':160,'catalog_digest':'old'});assert ok
def test_capability_floor_rejects_minimal_impostor():
 ok,d=probe({'ok':True,'status':'healthy'},{'ok':True,'schema_version':'11.0.0-candidate','capability_count':5,'catalog_digest':'x'});assert not ok and 'CAPABILITY_FLOOR' in d
def test_compatible_current_candidate_ready():
 assert probe({'ok':True,'status':'healthy'},{'ok':True,'schema_version':'11.0.0-candidate','capability_count':175,'catalog_digest':'new'})[0]
