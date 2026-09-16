from __future__ import annotations

import json
from pathlib import Path

import pytest

from mvf_resident.resident import DutyContract, LabToolsAdapter, MVFResident, default_receiver_lab_duties

ROOT = Path(__file__).resolve().parents[1]


class FakeAdapter:
    def __init__(self, rows): self.rows = rows; self.calls = []
    def call(self, name, payload):
        self.calls.append((name, dict(payload)))
        value = self.rows[name]
        if isinstance(value, Exception): raise value
        return value


def test_donor_snapshot_is_explicitly_non_authoritative_and_complete_package_is_present():
    manifest = json.loads((ROOT / 'mvf_resident' / 'DONOR_MANIFEST.json').read_text(encoding='utf-8'))
    assert manifest['status'] == 'DONOR_ONLY_NOT_AUTHORITY'
    assert manifest['law'] == 'CROSS_BOUNDARY_DONOR != AUTHORITY'
    assert manifest['source_full_ingestion_corpus_digest'] == '160ffe8594964ca61570e18f668cb87f29346b8dfb247328b24be6791ff0c00b'
    microseed_files = [row for row in manifest['files'] if row['donor'] == 'microseed']
    assert any(row['path'].endswith('runtime/entity.py') for row in microseed_files)
    assert any(row['path'].endswith('development/epistemic.py') for row in microseed_files)
    assert any(row['path'].endswith('persistence/identity.py') for row in microseed_files)
    assert any(row['path'].endswith('evidence/authority.py') for row in microseed_files)


def test_duty_contract_rejects_mutation_effects():
    with pytest.raises(ValueError):
        DutyContract('bad','x','x',(),allowed_effects=('read','mutation'))


def test_current_duty_uses_microseed_currentness_and_returns_yes_commitment():
    adapter = FakeAdapter({'x.read': {'ok': True, 'value': 1}})
    resident = MVFResident(adapter, now=lambda: '2026-09-15T12:00:00+00:00')
    duty = DutyContract('d1','subject','claim',(('x.read',{}),),max_age_seconds=300)
    result = resident.run_duty(duty)
    assert result.status == 'CURRENT'
    assert result.commitment == 'YES'
    assert result.mutation_authority is False


def test_failure_becomes_unknown_and_requires_escalation():
    adapter = FakeAdapter({'x.read': RuntimeError('boom')})
    resident = MVFResident(adapter, now=lambda: '2026-09-15T12:00:00+00:00')
    duty = DutyContract('d1','subject','claim',(('x.read',{}),))
    result = resident.run_duty(duty)
    assert result.status == 'UNKNOWN_INCOMPLETE'
    assert result.commitment == 'UNKNOWN'
    assert result.escalation_required is True
    assert result.mutation_authority is False


def test_reopen_condition_marks_duty_stale_without_inventing_truth():
    adapter = FakeAdapter({'x.read': {'ok': True, 'status': 'RES_UPDATE_REQUIRED'}})
    resident = MVFResident(adapter, now=lambda: '2026-09-15T12:00:00+00:00')
    duty = DutyContract('d1','subject','claim',(('x.read',{}),),reopen_conditions=('status=RES_UPDATE_REQUIRED',))
    result = resident.run_duty(duty)
    assert result.status == 'STALE'
    assert result.commitment == 'UNKNOWN'
    assert result.reopen_reasons == ('status=RES_UPDATE_REQUIRED',)


def test_portfolio_composes_multiple_duties_and_compacts_attention():
    adapter = FakeAdapter({'a': {'ok': True}, 'b': {'ok': True, 'status': 'INCOMPLETE'}})
    resident = MVFResident(adapter, now=lambda: '2026-09-15T12:00:00+00:00')
    duties=(DutyContract('a-duty','a','a',(('a',{}),)), DutyContract('b-duty','b','b',(('b',{}),),reopen_conditions=('status=INCOMPLETE',)))
    brief = resident.run_portfolio(duties)
    assert brief['overall_status'] == 'STALE'
    assert brief['mutation_authority'] is False
    assert brief['compact']['current'] == ['a-duty']
    assert brief['compact']['attention'] == ['b-duty']
    assert brief['decisions_required'] == ['b-duty']


def test_default_portfolio_is_three_read_only_duties():
    duties = default_receiver_lab_duties()
    assert [d.duty_id for d in duties] == ['receiver-currentness-ha','repository-topology-currentness','continuity-evidence-staleness']
    assert all(d.authority_ceiling == 'OBSERVATION_ONLY' for d in duties)
    assert all(d.allowed_effects == ('read',) for d in duties)


def test_semantic_note_text_does_not_trigger_structured_stale_or_reopen_predicates():
    adapter = FakeAdapter({'x.read': {'ok': True, 'status': 'current', 'semantic_note': 'stale_known_ancestor divergent unknown'}})
    resident = MVFResident(adapter, now=lambda: '2026-09-15T12:00:00+00:00')
    duty = DutyContract('d1','subject','claim',(('x.read',{}),),stale_conditions=('status=stale_known_ancestor',),reopen_conditions=('status=divergent','status=unknown'))
    result = resident.run_duty(duty)
    assert result.status == 'CURRENT'
    assert result.stale_reasons == ()
    assert result.reopen_reasons == ()


def test_real_lab_adapter_blocks_mutation_and_execution_tools_even_if_named_by_a_duty():
    import sys
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(root/'baseline'/'pcmmad_receiver'))
    import lab_tools
    adapter=LabToolsAdapter(lab_tools.dispatch_tool)
    for tool,payload in [('fs.write',{'path':'x','content':'x'}),('execution.run',{'command':['cmd','/c','echo','x']})]:
        with pytest.raises(RuntimeError,match='RESIDENT_EFFECT_FORBIDDEN'):
            adapter.call(tool,payload)

def test_default_resident_duties_resolve_only_to_native_read_capabilities():
    import sys
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(root/'baseline'/'pcmmad_receiver'))
    import lab_tools
    for duty in default_receiver_lab_duties():
        for tool,_payload in duty.observation_plan:
            spec=lab_tools._TOOL_REGISTRY[tool]
            assert spec.mutating is False
            assert spec.side_effect_class=='read'


def test_body_health_duty_rejects_filter_self_contamination_without_exact_ngrok_identity():
    rows={
        'machine.processes.list': {'ok':True,'processes':[{'name':'python.exe','command_line':'observer querying ngrok'}]},
        'machine.scheduled_tasks.list': {'ok':True,'scheduled_tasks':[{'task_name':'PCMMAD_TEST'}]},
    }
    class A:
        def call(self,name,payload):
            if name=='machine.processes.list' and payload.get('name_filter')=='python':
                return {'ok':True,'processes':[{'name':'python.exe','command_line':r'C:\x\baseline\pcmmad_receiver\server.py'}]}
            return rows[name]
    result=MVFResident(A(),now=lambda:'2026-09-15T00:00:00+00:00').run_duty(default_receiver_lab_duties()[0])
    assert result.status=='VIOLATED'
    assert 'REQUIRED_OBSERVATION_MISSING' in result.reason

def test_body_health_duty_accepts_exact_receiver_ngrok_and_task_evidence():
    class A:
        def call(self,name,payload):
            if name=='machine.processes.list' and payload.get('name_filter')=='python': return {'ok':True,'processes':[{'name':'python.exe','command_line':r'C:\x\baseline\pcmmad_receiver\server.py'}]}
            if name=='machine.processes.list': return {'ok':True,'processes':[{'name':'ngrok.exe','command_line':'ngrok http 5000'}]}
            return {'ok':True,'scheduled_tasks':[{'task_name':'PCMMAD_V30_Receiver_SYSTEM'}]}
    result=MVFResident(A(),now=lambda:'2026-09-15T00:00:00+00:00').run_duty(default_receiver_lab_duties()[0])
    assert result.status=='CURRENT'
