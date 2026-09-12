from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import governance_witness as w

def doc():
 d={'schema':'x','version':1,'laws':[{'id':'A'}]};d['digest']=w.canonical_digest(d);return d
def test_valid_independent_recomputation_agrees():
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'x.json';d=doc();p.write_text(json.dumps(d));r=w.verify_json_document(p,d['digest']);assert r['valid'];assert w.combine_owner_and_witness({'digest_valid':True},r)['usable']
def test_owner_self_assertion_cannot_override_recomputed_tamper():
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'x.json';d=doc();p.write_text(json.dumps(d));d2=json.loads(p.read_text());d2['laws'][0]['id']='TAMPER';p.write_text(json.dumps(d2));r=w.verify_json_document(p,d['digest']);assert not r['valid'];c=w.combine_owner_and_witness({'digest_valid':True},r);assert c['status']=='CONTRADICTION' and not c['usable']
def test_external_claim_mismatch_fails_even_when_document_self_consistent():
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'x.json';d=doc();p.write_text(json.dumps(d));r=w.verify_json_document(p,'0'*64);assert not r['valid']
def test_missing_witness_is_unknown_not_valid():
 c=w.combine_owner_and_witness({'digest_valid':True},{'available':False,'valid':False});assert c['status']=='UNKNOWN' and not c['usable']
def test_owner_and_independent_witness_disagreement_fails_closed():
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'x.json';d=doc();p.write_text(json.dumps(d));r=w.verify_json_document(p,d['digest']);c=w.combine_owner_and_witness({'digest_valid':False},r);assert c['status']=='CONTRADICTION'
