from __future__ import annotations
import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'baseline'/'pcmmad_receiver'))
import lab_tools_windows_telemetry as wt

class E(Exception):
 def __init__(self,code,msg,status=500,**kwargs): super().__init__(msg);self.code=code

def test_windows_event_query_rejects_unapproved_log_and_bounds_inputs():
 with pytest.raises(E): wt.events_query({'logs':['Security']},E)
 with pytest.raises(E): wt.events_query({'lookback_hours':999},E)
 with pytest.raises(E): wt.events_query({'limit':251},E)

def test_failure_correlator_never_promotes_security_signal_to_cause(monkeypatch):
 monkeypatch.setattr(wt,'events_query',lambda payload,error_cls:{'events':[{'event_id':1}]})
 monkeypatch.setattr(wt,'defender_detections',lambda payload,error_cls:{'detections':[{'threat_id':7,'initial_detection_time':'t','resources':['file:_C:/x/project/a.py'],'process_name':'powershell.exe','action_success':True}]})
 out=wt.failure_evidence({'path_filter':'C:/x/project','limit':10},E)
 assert out['security_signal_present'] is True
 assert out['causation_established'] is False
 assert out['defender_signals'][0]['path_match'] is True
 assert 'not promoted to cause' in out['interpretation']

def test_event_messages_and_defender_resources_are_bounded(monkeypatch):
 monkeypatch.setattr(wt,'_ps',lambda *a,**k:[{'TimeCreated':'t','ProviderName':'p','Id':1,'LevelDisplayName':'Error','RecordId':2,'Message':'X'*10000}])
 out=wt.events_query({'logs':['Application'],'limit':1},E);assert len(out['events'][0]['message'])<5000;assert 'truncated' in out['events'][0]['message']
 monkeypatch.setattr(wt,'_ps',lambda *a,**k:[{'ThreatID':1,'Resources':['Y'*10000]*40}])
 out2=wt.defender_detections({'limit':1},E);assert len(out2['detections'][0]['resources'])==32;assert len(out2['detections'][0]['resources'][0])<2200

def test_registered_windows_tools_are_low_read_only_and_no_mutation_authority():
 import lab_tools
 for name in ('windows.events.query','windows.defender.detections','windows.failure_evidence.inspect'):
  spec=lab_tools._TOOL_REGISTRY[name]
  assert spec.category=='windows';assert spec.danger_tier=='low';assert spec.mutating is False;assert spec.side_effect_class=='read';assert 'does_not_grant_mutation_authority' in spec.effect_traits
