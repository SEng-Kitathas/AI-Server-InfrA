from __future__ import annotations
import importlib.util,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('sup',ROOT/'supervisor/receiver_supervisor.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_repeated_failure_enters_crash_loop_hold_instead_of_restart_storm():
 with tempfile.TemporaryDirectory() as td:
  state={};calls=[]
  def dead(*a):return False,'dead'
  def trig(n):calls.append(n);return True,'started'
  for now in [0,10,20]:m.supervise_once(health_url='x',task_name='R',receipt_path=Path(td)/'r.json',health_probe=dead,trigger=trig,recovery_seconds=0,poll_seconds=.001,failure_state=state,max_restarts=3,restart_window_seconds=300,now_monotonic=lambda n=now:n)
  r=m.supervise_once(health_url='x',task_name='R',receipt_path=Path(td)/'r.json',health_probe=dead,trigger=trig,recovery_seconds=0,poll_seconds=.001,failure_state=state,max_restarts=3,restart_window_seconds=300,now_monotonic=lambda:30)
  assert r['action']=='CRASH_LOOP_HOLD' and len(calls)==3
def test_old_failures_age_out_of_restart_window():
 with tempfile.TemporaryDirectory() as td:
  state={'restart_events':[0,10,20]};calls=[]
  r=m.supervise_once(health_url='x',task_name='R',receipt_path=Path(td)/'r.json',health_probe=lambda *_:(False,'dead'),trigger=lambda n:(calls.append(n) or (True,'started')),recovery_seconds=0,poll_seconds=.001,failure_state=state,max_restarts=3,restart_window_seconds=300,now_monotonic=lambda:400)
  assert r['action']=='TRIGGER_CANONICAL_RECEIVER_TASK' and calls==['R']
