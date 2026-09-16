from __future__ import annotations
import os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'baseline'/'pcmmad_receiver'))
import execution_routes as er

def test_worker_capsule_uses_base_interpreter_on_windows():
    value=er._worker_python_executable()
    if os.name=='nt':
        assert value == str(getattr(sys,'_base_executable',None) or sys.executable)
    else:
        assert value == sys.executable
