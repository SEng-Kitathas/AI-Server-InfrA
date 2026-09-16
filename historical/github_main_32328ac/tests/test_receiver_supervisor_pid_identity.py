from __future__ import annotations
import importlib.util,os,tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('sup',ROOT/'supervisor/receiver_supervisor.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_same_pid_same_creation_fences_duplicate():
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'l';p.write_text('pid=42\ncreation_100ns=100\n');
  with patch.object(m,'_process_creation_100ns',side_effect=lambda pid:100 if pid==42 else 999):assert m.acquire_singleton(p) is None
def test_same_pid_different_creation_is_pid_reuse_and_stale_lock_recovers():
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'l';p.write_text('pid=42\ncreation_100ns=100\n');
  with patch.object(m,'_process_creation_100ns',side_effect=lambda pid:200 if pid==42 else 999):fd=m.acquire_singleton(p);assert fd is not None;os.close(fd)
def test_dead_pid_stale_lock_recovers():
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'l';p.write_text('pid=42\ncreation_100ns=100\n');
  with patch.object(m,'_process_creation_100ns',side_effect=lambda pid:None if pid==42 else 999):fd=m.acquire_singleton(p);assert fd is not None;os.close(fd)
def test_malformed_lock_fails_safe_without_deleting_unknown_evidence():
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'l';p.write_text('nonsense');assert m.acquire_singleton(p) is None and p.exists()
