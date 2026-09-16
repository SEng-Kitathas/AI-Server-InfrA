from __future__ import annotations
import tempfile,sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import global_doctrine as gd

def test_candidate_does_not_self_promote_and_explicit_promotion_is_versioned():
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);candidate={'laws':[{'id':'STRIP_FOR_PARTS','text':'x','status':'CANDIDATE_GLOBAL'}]}
  with patch.object(gd,'ROOT',root),patch.object(gd,'CURRENT',root/'current.json'),patch.object(gd,'HISTORY',root/'history'):
   assert gd.inspect()['authority']=='NONE';assert not (root/'current.json').exists()
   out=gd.promote({'candidate':candidate,'candidate_sha256':'abc','operator_id':'operator','provenance':'hostile qualified test'})
   assert out['status']=='PROMOTED' and out['version']==1
   state=gd.inspect();assert state['authority']=='GLOBAL_DOCTRINE' and state['digest_valid'] is True
   out2=gd.promote({'candidate':candidate,'operator_id':'operator','provenance':'second explicit promotion'});assert out2['version']==2

def test_promotion_requires_operator_and_provenance():
 with tempfile.TemporaryDirectory() as td:
  root=Path(td)
  with patch.object(gd,'ROOT',root),patch.object(gd,'CURRENT',root/'current.json'),patch.object(gd,'HISTORY',root/'history'):
   try:gd.promote({'candidate':{'laws':[{'id':'X'}]}})
   except ValueError:pass
   else:raise AssertionError('candidate self-promoted without operator/provenance')
