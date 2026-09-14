from __future__ import annotations
import importlib.util,json,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('sup',ROOT/'supervisor/receiver_supervisor.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def write(p,d):p.write_text(json.dumps(d))
def test_stale_hold_does_not_strand_server():
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'h';write(p,{'desired_state':'STOPPED','expires_at_epoch':99,'operator_id':'op','reason':'x'});r=m.hold_state(p,now_epoch=100);assert not r['hold'] and r['status']=='EXPIRED_HOLD_IGNORED'
def test_unparseable_hold_fails_toward_running_not_indefinite_stop():
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'h';p.write_text('junk');assert not m.hold_state(p,now_epoch=100)['hold']
def test_hold_requires_operator_reason():
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'h';write(p,{'desired_state':'STOPPED','expires_at_epoch':200});assert not m.hold_state(p,now_epoch=100)['hold']
def test_hold_cannot_exceed_maximum():
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'h';write(p,{'desired_state':'STOPPED','expires_at_epoch':100000,'operator_id':'op','reason':'x'});assert not m.hold_state(p,now_epoch=100,max_hold_seconds=1000)['hold']
def test_valid_bounded_hold_is_honored():
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'h';write(p,{'desired_state':'STOPPED','expires_at_epoch':200,'operator_id':'op','reason':'maintenance'});assert m.hold_state(p,now_epoch=100,max_hold_seconds=1000)['hold']
