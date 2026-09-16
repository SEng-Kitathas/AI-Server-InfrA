from __future__ import annotations
import importlib.util,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('sup',ROOT/'supervisor/receiver_supervisor.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_dead_receiver_triggers_canonical_task_and_recovers():
 with tempfile.TemporaryDirectory() as td:
  calls=[];seq=iter([(False,'dead'),(False,'dead'),(True,None)]);r=m.supervise_once(health_url='x',task_name='R',receipt_path=Path(td)/'r.json',health_probe=lambda *_:next(seq),trigger=lambda n:(calls.append(n) or (True,'started')),recovery_seconds=.1,poll_seconds=.001);assert r['healthy_after'] and calls==['R']
def test_healthy_receiver_is_not_restarted():
 with tempfile.TemporaryDirectory() as td:
  calls=[];r=m.supervise_once(health_url='x',task_name='R',receipt_path=Path(td)/'r.json',health_probe=lambda *_:(True,None),trigger=lambda n:(calls.append(n) or (True,'bad')));assert r['action']=='NONE' and not calls
def test_maintenance_hold_changes_desired_state_instead_of_fighting_operator():
 text=(ROOT/'supervisor/receiver_supervisor.py').read_text();assert 'desired_state":"STOPPED' in text and 'MAINTENANCE_HOLD' in text
def test_installer_is_boot_system_not_logon_polling_task():
 text=(ROOT/'supervisor/install_receiver_supervisor_task.ps1').read_text();assert '-AtStartup' in text and "-UserId 'SYSTEM'" in text and '-RunLevel Highest' in text and '--daemon' in text;assert 'RepetitionInterval' not in text
def test_installer_self_restarts_supervisor_and_start_when_available():
 text=(ROOT/'supervisor/install_receiver_supervisor_task.ps1').read_text();assert '-RestartCount 999' in text and '-StartWhenAvailable' in text and 'Start-ScheduledTask' in text
