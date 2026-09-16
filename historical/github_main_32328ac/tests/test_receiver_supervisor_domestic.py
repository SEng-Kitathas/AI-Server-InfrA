from __future__ import annotations
import importlib.util,os,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('sup',ROOT/'supervisor/receiver_supervisor.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_duplicate_supervisor_is_fenced_by_singleton_lock():
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'x.lock';a=m.acquire_singleton(p);assert a is not None;assert m.acquire_singleton(p) is None;os.close(a)
def test_dead_owner_stale_lock_is_recovered():
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'x.lock';p.write_text('pid=999999\ncreation_100ns=123\n');fd=m.acquire_singleton(p);assert fd is not None;os.close(fd)


def test_supervisor_default_targets_receiver_not_hud():
 text=(ROOT/'supervisor/receiver_supervisor.py').read_text();installer=(ROOT/'supervisor/install_receiver_supervisor_task.ps1').read_text();assert 'http://127.0.0.1:5000/health' in text and 'http://127.0.0.1:5000/health' in installer;assert '5090/api/health' not in text+installer
