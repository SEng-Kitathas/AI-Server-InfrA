from __future__ import annotations
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('sup',ROOT/'supervisor/receiver_supervisor.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_clean_boot_is_recoverable():assert m.boot_recovery_classification(None)['continuity_recoverable']
def test_active_null_lease_boots_service_but_not_control_ready():
 r=m.boot_recovery_classification({'status':'ACTIVE','lease_id':None});assert r['service_can_start'] and not r['continuity_recoverable'] and r['control_state']=='RECONCILIATION_REQUIRED'
def test_interrupted_consequence_is_not_laundered_by_restart():
 r=m.boot_recovery_classification({'status':'ACTIVE','lease_id':'x','consequence_active':True});assert r['control_state']=='INTERRUPTED_CONSEQUENCE_REVIEW' and not r['continuity_recoverable']
def test_unknown_interrupted_state_fails_unknown_not_green():
 r=m.boot_recovery_classification({'status':'WEIRD'});assert r['control_state']=='UNKNOWN_INTERRUPTED_STATE' and not r['continuity_recoverable']
