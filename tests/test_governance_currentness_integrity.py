from __future__ import annotations
import copy,json,sys,tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import global_doctrine as gd
from pcmmad_receiver import governance_observers as o

def isolated():
 td=tempfile.TemporaryDirectory();root=Path(td.name);return td,root

def test_valid_persisted_owner_and_matching_projection_is_consistent():
 td,root=isolated()
 with td,patch.object(gd,'ROOT',root),patch.object(gd,'CURRENT',root/'current.json'),patch.object(gd,'HISTORY',root/'history'):
  gd.promote({'candidate':{'laws':[{'id':'X','text':'law'}]},'operator_id':'op','provenance':'test'})
  owner=gd.inspect();projection={'version':owner['document']['version'],'digest':owner['document']['digest']}
  r=o.govern_observation('global.doctrine',o.observe_doctrine(gd.inspect,projection));assert r['status']=='CONSISTENT'

def test_tampered_persisted_owner_agreed_by_projection_is_not_current_authority():
 td,root=isolated()
 with td,patch.object(gd,'ROOT',root),patch.object(gd,'CURRENT',root/'current.json'),patch.object(gd,'HISTORY',root/'history'):
  gd.promote({'candidate':{'laws':[{'id':'X','text':'law'}]},'operator_id':'op','provenance':'test'})
  doc=json.loads((root/'current.json').read_text());doc['laws'][0]['text']='tampered';(root/'current.json').write_text(json.dumps(doc),encoding='utf-8')
  owner=gd.inspect();assert owner['status']=='DIGEST_MISMATCH' and owner['authority']=='NONE'
  projection={'version':doc['version'],'digest':doc['digest']}
  r=o.govern_observation('global.doctrine',o.observe_doctrine(gd.inspect,projection));assert r['status']=='UNKNOWN' and r['authority']=='NONE'

def test_owner_name_without_integrity_witness_cannot_pass():
 fake=lambda:{'authority':'GLOBAL_DOCTRINE','status':'CURRENT','document':{'version':1,'digest':'claimed'},'digest_valid':False}
 r=o.govern_observation('global.doctrine',o.observe_doctrine(fake,{'version':1,'digest':'claimed'}));assert r['status']!='CONSISTENT'
