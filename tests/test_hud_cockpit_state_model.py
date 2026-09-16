from __future__ import annotations
import json,shutil,subprocess
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'operator_hud'/'static'/'app.js'

def _run(cases):
    node=shutil.which('node') or shutil.which('node.exe')
    if not node: pytest.skip('node unavailable')
    script=r"""
const fs=require('fs');
const src=fs.readFileSync(process.argv[1],'utf8');
const a=src.indexOf('function deriveCockpitPicture');
const b=src.indexOf('\nfunction setSynopticNode',a);
if(a<0||b<0)throw new Error('deriveCockpitPicture extraction failed');
eval(src.slice(a,b));
const cases=JSON.parse(process.argv[2]);
const out=cases.map(c=>deriveCockpitPicture(c.data,c.now));
process.stdout.write(JSON.stringify(out));
"""
    proc=subprocess.run([node,'-e',script,str(APP),json.dumps(cases)],capture_output=True,text=True,check=True,timeout=10)
    return json.loads(proc.stdout)

def base(now=1000):
    return {'ok':True,'checked_at':now-1,'hud':{'ok':True},'receiver':{'ok':True,'http_status':200},'journal':{'ok':True},'browser_bridge':{'ok':True},'ngrok':{'configured':True,'ok':True,'tunnel_count':1},'daemon':{'configured':False,'ok':False},'readiness':{'core_ready':True,'optional_degraded':[]}}

def test_nominal_and_daemon_absence_are_normal_not_warning():
    d=base();p=_run([{'data':d,'now':1000}])[0]
    assert p['label']=='NORMAL';assert p['level']=='normal';assert p['stale'] is False;assert p['d']['configured'] is False

def test_optional_browser_only_degradation_is_caution_not_core_failure():
    d=base();d['browser_bridge']['ok']=False;d['readiness']['optional_degraded']=['browser_bridge'];p=_run([{'data':d,'now':1000}])[0]
    assert p['label']=='CAUTION';assert p['coreReady'] is True;assert 'optional browser_bridge degraded' in p['chain']

def test_receiver_down_with_transport_up_is_warning_and_preserves_causal_chain():
    d=base();d['receiver']={'ok':False,'http_status':502};d['readiness']['core_ready']=False;p=_run([{'data':d,'now':1000}])[0]
    assert p['label']=='WARNING';assert p['faultTitle']=='Receiver unavailable';assert 'transport ONLINE' in p['chain'];assert 'Receiver DOWN (HTTP 502)' in p['chain'];assert 'Windows / Defender evidence' in p['cue']

def test_security_signal_is_explicitly_noncausal_without_causal_proof():
    d=base();d['receiver']={'ok':False,'http_status':502};d['readiness']['core_ready']=False;d['failure_evidence']={'security_signal_present':True,'causation_established':False};p=_run([{'data':d,'now':1000}])[0]
    assert 'Security signal present; causation is NOT established.' in p['cue']

def test_stale_status_overrides_embedded_green_state():
    d=base();d['checked_at']=900;p=_run([{'data':d,'now':1000}])[0]
    assert p['label']=='WARNING';assert p['stale'] is True;assert p['faultTitle']=='Status evidence stale or unavailable';assert 'not sufficient for readiness' in p['chain']

def test_fetch_failure_without_timestamp_is_warning():
    p=_run([{'data':{'ok':False,'error_code':'HUD_FETCH_FAILED'},'now':1000}])[0]
    assert p['label']=='WARNING';assert p['stale'] is True;assert p['coreReady'] is False


def _run_annunciation(sequence):
    node=shutil.which('node') or shutil.which('node.exe')
    if not node: pytest.skip('node unavailable')
    script=r"""
const fs=require('fs');
const src=fs.readFileSync(process.argv[1],'utf8');
const a=src.indexOf('function deriveCockpitPicture');
const b=src.indexOf('\nfunction setSynopticNode',a);
eval(src.slice(a,b));
const seq=JSON.parse(process.argv[2]);
let prev=null;const out=[];
for(const x of seq){prev=advanceAnnunciation(prev,x.picture,x.now);out.push(prev);}
process.stdout.write(JSON.stringify({out,up:trendDirection([10,20,30],true),down:trendDirection([30,20,10],true),flat:trendDirection([10,10.1,10.2],true)}));
"""
    proc=subprocess.run([node,'-e',script,str(APP),json.dumps(sequence)],capture_output=True,text=True,check=True,timeout=10)
    return json.loads(proc.stdout)

def test_annunciation_deduplicates_persistent_warning_and_marks_clear_transition():
    warning={'level':'warning','faultTitle':'Receiver unavailable'};normal={'level':'normal','faultTitle':'Required planes nominal'}
    result=_run_annunciation([{'picture':warning,'now':100},{'picture':warning,'now':105},{'picture':normal,'now':110}])['out']
    assert result[0]['changed'] is True and result[0]['since']==100
    assert result[1]['changed'] is False and result[1]['since']==100
    assert result[2]['changed'] is True and result[2]['cleared']['level']=='warning' and result[2]['cleared']['at']==110

def test_trend_direction_marks_worsening_improving_and_flat_for_lower_is_better_metrics():
    result=_run_annunciation([])
    assert result['up']=='↑'
    assert result['down']=='↓'
    assert result['flat']=='→'


def _run_diagnostic(cases):
    node=shutil.which('node') or shutil.which('node.exe')
    if not node: pytest.skip('node unavailable')
    script=r"""
const fs=require('fs');
const src=fs.readFileSync(process.argv[1],'utf8');
const a=src.indexOf('function deriveCockpitPicture');
const b=src.indexOf('\nfunction advanceAnnunciation',a);
if(a<0||b<0)throw new Error('diagnostic model extraction failed');
eval(src.slice(a,b));
const cases=JSON.parse(process.argv[2]);
const out=cases.map(c=>{const p=deriveCockpitPicture(c.data,c.now);return deriveDiagnosticPacket(c.data,p);});
process.stdout.write(JSON.stringify(out));
"""
    proc=subprocess.run([node,'-e',script,str(APP),json.dumps(cases)],capture_output=True,text=True,check=True,timeout=10)
    return json.loads(proc.stdout)

def test_diagnostic_receiver_down_transport_up_triangulates_without_root_cause_claim():
    d=base();d['receiver']={'ok':False,'http_status':502};d['readiness']['core_ready']=False
    packet=_run_diagnostic([{'data':d,'now':1000}])[0]
    assert packet['severity']=='WARNING'
    assert any(x['truth']=='INFERRED' and 'downstream of tunnel establishment' in x['text'] for x in packet['inferences'])
    assert any('Receiver failure mechanism' in x['text'] and 'supervisor' in x['discriminator'] for x in packet['unknowns'])
    assert any('windows.failure_evidence.inspect' in x for x in packet['nextEvidence'])
    assert not any('root cause' in (x.get('text') or '').lower() for x in packet['inferences'])

def test_diagnostic_stale_state_blocks_causal_inference_and_marks_topology_unknown():
    d=base();d['checked_at']=900
    packet=_run_diagnostic([{'data':d,'now':1000}])[0]
    assert packet['currentness']['stale'] is True
    assert any(x['truth']=='INFERENCE BLOCKED' for x in packet['inferences'])
    assert not any(x['truth']=='INFERRED' for x in packet['inferences'])
    assert all(x['state']=='unknown' for x in packet['topology']['nodes'])
    assert any('Refresh HUD /api/status' in x for x in packet['nextEvidence'])

def test_diagnostic_security_signal_remains_noncausal_without_evidence_flag():
    d=base();d['receiver']={'ok':False,'http_status':502};d['readiness']['core_ready']=False;d['failure_evidence']={'security_signal_present':True,'causation_established':False}
    packet=_run_diagnostic([{'data':d,'now':1000}])[0]
    assert any(x['label']=='Security telemetry' and x['truth']=='FACT' for x in packet['facts'])
    assert any(x['truth']=='INFERENCE BLOCKED' and 'not established' in x['text'] for x in packet['inferences'])
    assert any(x['text']=='Security causal role' for x in packet['unknowns'])

def test_diagnostic_informed_by_includes_continuity_surface_and_scar_occurrence_lineage():
    d=base();d['daemon']={'configured':True,'ok':True,'status':{'continuity_enforcement':{'surfacing_plan':{'selected':[{'surface':'COMMANDERS_INTENT_CURRENT.md','reason':'mandatory mutation'}]}}}}
    d['scar_intelligence']={'applicable':[{'expression':'PRETTY DASHBOARD != COCKPIT','reason':'expression:cockpit','best_occurrence':{'source':'active_handoff:DOCTRINE_SNAPSHOT.md'}}]}
    packet=_run_diagnostic([{'data':d,'now':1000}])[0];names={x['name'] for x in packet['informedBy']}
    assert 'continuity:COMMANDERS_INTENT_CURRENT.md' in names
    assert 'scar:active_handoff:DOCTRINE_SNAPSHOT.md' in names
    assert packet['scars'][0]['expression']=='PRETTY DASHBOARD != COCKPIT'
    assert packet['mutation_authority'] is False


def test_diagnostic_surfaces_registered_scar_source_coverage_deficit():
    d=base();d['scar_intelligence']={'applicable':[],'source_deficits':[{'source_id':'rahl-global-ledger','status':'REGISTERED_ATTACHMENT_IDENTITY_PENDING_MATERIALIZATION'}]}
    packet=_run_diagnostic([{'data':d,'now':1000}])[0]
    assert any(x['text']=='Scar-source coverage incomplete' and 'rahl-global-ledger' in x['discriminator'] for x in packet['unknowns'])
    assert any(x['name']=='scar-source:rahl-global-ledger' for x in packet['informedBy'])
    assert any('Materialize/verify registered scar sources' in x for x in packet['nextEvidence'])


def test_browser_blocked_healthy_is_secured_standby_not_degradation():
    d=base();d['browser_bridge']={'ok':True,'armed':False,'gate_state':'BLOCKED','playwright':True,'ready_for_browser_automation':False};d['readiness']['optional_degraded']=[]
    p=_run([{'data':d,'now':1000}])[0]
    assert p['label']=='NORMAL';assert p['coreReady'] is True;assert p['optionalDegraded']==[];assert p['b']['armed'] is False

def test_browser_armed_but_not_ready_is_caution_without_core_failure():
    d=base();d['browser_bridge']={'ok':True,'armed':True,'gate_state':'ARMED','playwright':False,'ready_for_browser_automation':False};d['readiness']['optional_degraded']=[]
    p=_run([{'data':d,'now':1000}])[0]
    assert p['label']=='CAUTION';assert p['coreReady'] is True;assert 'browser_armed_not_ready' in p['optionalDegraded']
    packet=_run_diagnostic([{'data':d,'now':1000}])[0]
    assert any(x['text']=='Browser armed but automation not ready' for x in packet['unknowns'])
    assert any('Playwright readiness' in x for x in packet['nextEvidence'])

def test_browser_armed_and_ready_is_normal_when_other_planes_nominal():
    d=base();d['browser_bridge']={'ok':True,'armed':True,'gate_state':'ARMED','playwright':True,'ready_for_browser_automation':True};d['readiness']['optional_degraded']=[]
    p=_run([{'data':d,'now':1000}])[0]
    assert p['label']=='NORMAL';assert p['optionalDegraded']==[]
