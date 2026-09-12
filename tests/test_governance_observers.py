from __future__ import annotations
import copy,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import governance_observers as o

def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def test_real_contract_projection_corruption_detected_without_owner_change():
 authority={'fs.glob':{'contract_digest':'abc','schema_hash':'def','input_schema':{'type':'object','required':['pattern']}}};before=digest(authority);projection=copy.deepcopy(authority);projection['fs.glob']['input_schema']={'type':'object'}
 obs=o.observe_contract(authority,projection);r=o.govern_observation('capability.contract',obs)
 assert r['status']=='CONTRADICTION';assert 'PROJECTION_CONTRADICTION' in {x['code'] for x in r['issues']};assert digest(authority)==before;assert r['authority']=='NONE'
def test_matching_contract_projection_consistent():
 authority={'x':{'contract_digest':'a','schema_hash':'b','input_schema':{'type':'object','properties':{}}}};r=o.govern_observation('capability.contract',o.observe_contract(authority,copy.deepcopy(authority)));assert r['status']=='CONSISTENT'
def test_doctrine_projection_corruption_detected_and_owner_unchanged():
 owner={'authority':'GLOBAL_DOCTRINE','status':'CURRENT','digest_valid':True,'document':{'version':4,'digest':'abcd'}};before=digest(owner);obs=o.observe_doctrine(lambda:owner,{'version':3,'digest':'old'});r=o.govern_observation('global.doctrine',obs);assert r['status']=='CONTRADICTION';assert digest(owner)==before;assert r['authority']=='NONE'
def test_doctrine_owner_unavailable_yields_unknown_not_projection_truth():
 obs=o.observe_doctrine(lambda:(_ for _ in ()).throw(OSError('owner down')),{'version':999,'digest':'projection-claims-current'});r=o.govern_observation('global.doctrine',obs);assert r['status']=='UNKNOWN';assert r['authority']=='NONE';assert {x['code'] for x in r['issues']}=={'AUTHORITATIVE_EVIDENCE_UNAVAILABLE'}
def test_uninitialized_doctrine_owner_yields_unknown():
 obs=o.observe_doctrine(lambda:{'authority':'NONE','status':'UNINITIALIZED'},None);r=o.govern_observation('global.doctrine',obs);assert r['status']=='UNKNOWN'
