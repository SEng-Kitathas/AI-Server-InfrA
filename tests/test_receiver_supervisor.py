from __future__ import annotations
import importlib.util,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('receiver_supervisor',ROOT/'supervisor/receiver_supervisor.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class SupervisorTests(unittest.TestCase):
 def test_healthy_is_noop(self):
  with tempfile.TemporaryDirectory() as td:
   calls=[];r=mod.supervise_once(health_url='x',task_name='t',receipt_path=Path(td)/'r.json',health_probe=lambda *_:(True,None),trigger=lambda n:(calls.append(n) or (True,'ok')),recovery_seconds=.01,poll_seconds=.001);self.assertTrue(r['healthy_after']);self.assertEqual(r['action'],'NONE');self.assertEqual(calls,[])
 def test_unhealthy_triggers_once_and_waits_for_recovery(self):
  with tempfile.TemporaryDirectory() as td:
   states=iter([(False,'down'),(False,'down'),(True,None)]);calls=[]
   def probe(*_): return next(states,(True,None))
   r=mod.supervise_once(health_url='x',task_name='receiver',receipt_path=Path(td)/'r.json',health_probe=probe,trigger=lambda n:(calls.append(n) or (True,'started')),recovery_seconds=.05,poll_seconds=.001);self.assertTrue(r['healthy_after']);self.assertEqual(calls,['receiver']);self.assertTrue((Path(td)/'r.json').is_file())
if __name__=='__main__':unittest.main()
