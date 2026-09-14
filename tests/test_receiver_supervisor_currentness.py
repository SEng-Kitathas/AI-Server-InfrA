from __future__ import annotations
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('sup',ROOT/'supervisor/receiver_supervisor.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_compatible_old_receiver_remains_service_ready_not_current():
 r=m.classify_readiness(service_ok=True,service_detail=None,observed_catalog_digest='old',expected_catalog_digest='new');assert r['service_ready'] and not r['deployment_current'] and r['status']=='SERVICE_READY_DEPLOYMENT_NOT_CURRENT'
def test_exact_expected_catalog_is_ready_and_current():
 r=m.classify_readiness(service_ok=True,service_detail=None,observed_catalog_digest='new',expected_catalog_digest='new');assert r['service_ready'] and r['deployment_current']
def test_failed_service_never_becomes_current_by_matching_digest():
 r=m.classify_readiness(service_ok=False,service_detail='dead',observed_catalog_digest='new',expected_catalog_digest='new');assert not r['service_ready'] and not r['deployment_current']
def test_missing_expected_identity_does_not_invent_currentness():
 r=m.classify_readiness(service_ok=True,service_detail=None,observed_catalog_digest='x',expected_catalog_digest=None);assert r['service_ready'] and not r['deployment_current']
