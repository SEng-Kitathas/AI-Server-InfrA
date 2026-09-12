from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import lab_tools
from pcmmad_receiver import schema_vnext_runtime as runtime

def test_filesystem_capabilities_publish_real_argument_grammar():
    cards={x['name']:x for x in lab_tools.list_tools()}
    expected={
      'fs.read':({'path','project_id','max_bytes'},'path'),
      'fs.glob':({'pattern','project_id','recursive','limit'},'pattern'),
      'fs.grep':({'path','project_id','query','limit','max_file_bytes'},'query'),
      'fs.tree':({'path','project_id','depth','include_hidden','exclude_dirs','extensions','min_size_bytes','limit'},'path'),
    }
    hashes=set()
    for name,(properties,required) in expected.items():
        schema=cards[name]['input_schema'];assert schema['type']=='object';assert set(schema['properties'])==properties
        if required: assert required in schema.get('required',[])
        if name=='fs.grep': assert {'query','path'}.issubset(set(schema.get('required',[])))
        hashes.add(cards[name]['schema_hash'])
    assert len(hashes)==4

def test_orient_full_exposes_same_schema_as_handler_registry():
    names=['fs.read','fs.glob','fs.grep','fs.tree'];cards={x['name']:x for x in lab_tools.list_tools()}
    out=runtime.orient({'goal':'agent contract audit','project_id':'RECEIVER-LAB','capabilities':names,'detail':'full','ttl_seconds':60})
    got={x['name']:x for x in out['capabilities']}
    for name in names:
        assert got[name]['input_schema']==cards[name]['input_schema'];assert got[name]['schema_hash']==cards[name]['schema_hash'];assert got[name]['contract_digest']==cards[name]['contract_digest']

def test_capability_lease_survives_json_roundtrip_exactly():
    out=runtime.orient({'goal':'lease roundtrip','project_id':'RECEIVER-LAB','capabilities':['fs.grep','fs.glob'],'detail':'full','ttl_seconds':60});lease=out['lease'];roundtrip=json.loads(json.dumps(lease,sort_keys=True));assert runtime.validate_lease(roundtrip)['current'] is True;assert roundtrip['lease_digest']==lease['lease_digest']

def test_lease_tamper_fails_closed():
    out=runtime.orient({'goal':'lease tamper','project_id':'RECEIVER-LAB','capabilities':['fs.grep'],'detail':'full','ttl_seconds':60});lease=json.loads(json.dumps(out['lease']));lease['ttl_seconds']+=1
    try:runtime.validate_lease(lease)
    except lab_tools.LabToolError as exc:assert exc.error_code=='CAPABILITY_LEASE_INVALID'
    else:raise AssertionError('tampered lease unexpectedly validated')


def test_invoke_with_orient_lease_roundtrip_reaches_handler_contract():
    cards={x['name']:x for x in lab_tools.list_tools()}
    out=runtime.orient({'goal':'invoke roundtrip','project_id':'RECEIVER-LAB','capabilities':['fs.grep'],'detail':'full','ttl_seconds':60})
    lease=json.loads(json.dumps(out['lease'],sort_keys=True))
    try:
        runtime.invoke({'capability':'fs.grep','arguments':{'project_id':'RECEIVER-LAB','path':'.','query':'definitely-not-present-token-xyz','limit':1},'lease':lease})
    except lab_tools.LabToolError as exc:
        assert exc.error_code != 'CAPABILITY_LEASE_INVALID'
        assert exc.error_code != 'EXPECTED_CONTRACT_REQUIRED'


def test_catalog_has_no_opaque_generic_object_contracts():
    opaque=[c['name'] for c in lab_tools.list_tools() if c.get('input_schema')=={'type':'object'}]
    assert opaque==[], f'opaque agent-visible contracts: {opaque}'

def test_known_empty_contracts_are_explicitly_empty_not_opaque():
    cards={x['name']:x for x in lab_tools.list_tools()}
    for name in ['lab.health','lab.tools.reload','control.hud.status','control.hud.restart','control.receiver.restart','control.receiver.restart.status']:
        schema=cards[name]['input_schema']
        assert schema.get('type')=='object';assert schema.get('additionalProperties') is False;assert schema.get('properties')=={}


def test_explicit_full_orient_does_not_silently_drop_requested_capabilities():
    names=['fs.glob','project.files.list','git.status','execution.status','transfer.meta','sop.ingest.status','research.hunt','migration.inspect','control.hud.status','protocol.status']
    out=runtime.orient({'goal':'explicit full contract set','project_id':'RECEIVER-LAB','capabilities':names,'detail':'full','max_capabilities':20,'ttl_seconds':60})
    assert [row['name'] for row in out['capabilities']]==names
    assert [row['name'] for row in out['lease']['selected']]==names
