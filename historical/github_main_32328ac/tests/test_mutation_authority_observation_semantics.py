from __future__ import annotations
import sys,tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'));from pcmmad_receiver import project_mutation_authority as m

from contextlib import ExitStack
def env(td):
 r=Path(td);st=ExitStack();st.enter_context(patch.object(m,'get_project_root',side_effect=lambda project_id:r/project_id));st.enter_context(patch.object(m,'init_project_layout',side_effect=lambda project_id:(r/project_id).mkdir(parents=True,exist_ok=True) or (r/project_id)));return st
def test_observe_redacts_bearer_even_when_active():
 with tempfile.TemporaryDirectory() as td,env(td):
  a=m.acquire_lease('P',expected_generation=0,owner_id='o',session_id='s',ttl_seconds=60);assert a['lease_id'];o=m.observe_lease('P');assert o['status']=='ACTIVE' and o['lease_id'] is None and o['lease_token_disclosed'] is False and o['authority_identity_present'] is True
def test_inspect_reconciles_expired_active_record():
 with tempfile.TemporaryDirectory() as td,env(td):
  a=m.acquire_lease('P',expected_generation=0,owner_id='o',session_id='s',ttl_seconds=10)
  with patch.object(m,'_now',return_value=m._parse_time(a['expires_at'])+m.timedelta(seconds=1)):
   i=m.inspect_lease('P');assert i['status']=='EXPIRED' and i['lease_id'] is None
def test_acquire_is_only_surface_that_discloses_new_bearer():
 with tempfile.TemporaryDirectory() as td,env(td):
  a=m.acquire_lease('P',expected_generation=0,owner_id='o',session_id='s',ttl_seconds=60);token=a['lease_id'];assert token and a['lease_token_disclosed'] is True and m.observe_lease('P')['lease_id'] is None and m.inspect_lease('P')['lease_id'] is None
  r=m.renew_lease('P',lease_id=token,generation=1,owner_id='o',session_id='s',ttl_seconds=60);assert r['lease_id'] is None
