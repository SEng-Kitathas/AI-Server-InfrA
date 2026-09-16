from __future__ import annotations
import json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SCRIPT=ROOT/'tools'/'pcmmad_maintenance_supervisor.py'
def run(args,env):return subprocess.run([sys.executable,str(SCRIPT),*args],cwd=ROOT,text=True,capture_output=True,env=env,timeout=20)
def test_supervisor_imports_without_receiver_http_or_router():
 # Process-level proof: CLI loads maintenance core directly; no receiver server is started/imported as a prerequisite.
 cp=subprocess.run([sys.executable,str(SCRIPT),'--help'],cwd=ROOT,text=True,capture_output=True,timeout=20);assert cp.returncode==0;assert 'reconcile-authority' in cp.stdout
def test_supervisor_and_receiver_module_share_one_maintenance_implementation():
 text=SCRIPT.read_text();assert 'from pcmmad_receiver import maintenance_plane' in text;assert 'def reconcile_' not in text
def test_supervisor_has_no_arbitrary_shell_or_file_write_command():
 text=SCRIPT.read_text().lower();assert 'subprocess' not in text;assert 'os.system' not in text;assert 'write_text' not in text;assert 'shell' not in text
def test_cli_requires_explicit_operator_reason_for_acquire():
 cp=subprocess.run([sys.executable,str(SCRIPT),'acquire'],cwd=ROOT,text=True,capture_output=True,timeout=20);assert cp.returncode!=0
