"""Bounded read-only Windows EventLog and Defender telemetry."""
from __future__ import annotations
import json, os
from collections.abc import Callable, MutableMapping
from pathlib import Path
from typing import Any
from server_hardening import run_subprocess_envelope

JsonObject=MutableMapping[str,Any];Registrar=Callable[...,Any]
_ALLOWED_LOGS={"Application","System","Microsoft-Windows-TaskScheduler/Operational","Microsoft-Windows-Windows Defender/Operational"}

def _ps(script:str,error_cls:type[Exception],*,timeout:int=20,max_bytes:int=524288)->Any:
    if os.name!='nt':raise error_cls('PLATFORM_UNSUPPORTED','Windows telemetry requires Windows',501,platform=os.name)
    cwd=Path(os.environ.get('SystemRoot') or os.getcwd()).resolve()
    r=run_subprocess_envelope(['powershell.exe','-NoProfile','-Command',script],cwd=cwd,timeout_seconds=timeout,stdout_max_bytes=max_bytes,stderr_max_bytes=65536)
    if not r.get('ok'):raise error_cls('WINDOWS_TELEMETRY_FAILED',str(r.get('stderr') or r.get('stdout') or r.get('error') or 'telemetry query failed'),503,result=r)
    raw=str(r.get('stdout') or '').strip()
    if not raw:return []
    try:return json.loads(raw)
    except json.JSONDecodeError as exc:raise error_cls('WINDOWS_TELEMETRY_DECODE_FAILED','telemetry returned invalid JSON',502) from exc

def _lit(v:Any)->str:return "'"+str(v).replace("'","''")+"'"
def _limit(payload:JsonObject,max_limit:int=250)->int:
    n=int(payload.get('limit',100))
    if n<1 or n>max_limit:raise ValueError(f'limit must be between 1 and {max_limit}')
    return n

def _hours(payload:JsonObject)->float:
    h=float(payload.get('lookback_hours',1.0))
    if h<=0 or h>168:raise ValueError('lookback_hours must be >0 and <=168')
    return h

def _truncate(v:Any,n:int=4000)->str:
    s=str(v or '').replace('\x00','')
    return s if len(s)<=n else s[:n]+'...[truncated]'

def events_query(payload:JsonObject,error_cls:type[Exception])->JsonObject:
    try:limit=_limit(payload);hours=_hours(payload)
    except ValueError as exc:raise error_cls('BAD_REQUEST',str(exc),400) from exc
    logs=payload.get('logs') or ['Application','System','Microsoft-Windows-TaskScheduler/Operational','Microsoft-Windows-Windows Defender/Operational']
    if not isinstance(logs,list) or not logs or any(str(x) not in _ALLOWED_LOGS for x in logs):raise error_cls('BAD_REQUEST','logs contains unsupported channel',400,allowed=sorted(_ALLOWED_LOGS))
    provider=str(payload.get('provider') or '').strip();text=str(payload.get('text_filter') or '').strip();ids=payload.get('event_ids') or []
    if not isinstance(ids,list) or len(ids)>64:raise error_cls('BAD_REQUEST','event_ids must be a list of <=64 IDs',400)
    idvals=[]
    for x in ids:
        try:idvals.append(int(x))
        except Exception:raise error_cls('BAD_REQUEST','event_ids must be integers',400)
    rows=[];channel_errors=[]
    per=max(limit,25)
    for log in logs:
        filt=f"@{{LogName={_lit(log)};StartTime=(Get-Date).AddHours(-{hours})}}"
        clauses=[]
        if provider:clauses.append(f"$_.ProviderName -eq {_lit(provider)}")
        if idvals:clauses.append("$_.Id -in @("+','.join(map(str,idvals))+')')
        if text:clauses.append(f"([string]$_.Message -match [regex]::Escape({_lit(text)}))")
        where=(' | Where-Object { '+ ' -and '.join(clauses)+' }') if clauses else ''
        script=f"Get-WinEvent -FilterHashtable {filt} -ErrorAction SilentlyContinue{where} | Select-Object -First {per} TimeCreated,ProviderName,Id,LevelDisplayName,RecordId,Message | ForEach-Object {{[pscustomobject]@{{TimeCreated=$_.TimeCreated.ToString('o');ProviderName=$_.ProviderName;Id=$_.Id;LevelDisplayName=$_.LevelDisplayName;RecordId=$_.RecordId;Message=[string]$_.Message}}}} | ConvertTo-Json -Compress -Depth 4"
        try:
            raw=_ps(script,error_cls);items=raw if isinstance(raw,list) else ([raw] if isinstance(raw,dict) else [])
        except Exception as exc:
            channel_errors.append({'log':log,'error':_truncate(f'{type(exc).__name__}: {exc}',1024)});continue
        for row in items:
            rows.append({'time':str(row.get('TimeCreated') or ''),'log':log,'provider':str(row.get('ProviderName') or ''),'event_id':int(row.get('Id') or 0),'level':str(row.get('LevelDisplayName') or ''),'record_id':int(row.get('RecordId') or 0),'message':_truncate(row.get('Message'))})
    rows.sort(key=lambda x:x['time'],reverse=True);matched=len(rows);rows=rows[:limit]
    return {'ok':True,'scope':'operator_machine_read','platform':'windows','events':rows,'count':len(rows),'matched_count':matched,'limit':limit,'truncated':matched>limit,'logs':logs,'channel_errors':channel_errors,'partial':bool(channel_errors),'mutation_authority':False}

def defender_detections(payload:JsonObject,error_cls:type[Exception])->JsonObject:
    try:limit=_limit(payload,100);hours=_hours(payload)
    except ValueError as exc:raise error_cls('BAD_REQUEST',str(exc),400) from exc
    script=f"Get-MpThreatDetection -ErrorAction SilentlyContinue | Where-Object {{$_.InitialDetectionTime -ge (Get-Date).AddHours(-{hours})}} | Sort-Object InitialDetectionTime -Descending | Select-Object -First {limit} ThreatID,InitialDetectionTime,LastThreatStatusChangeTime,ActionSuccess,CurrentThreatExecutionStatusID,ThreatStatusID,Resources,ProcessName,RemediationTime,DomainUser | ForEach-Object {{[pscustomobject]@{{ThreatID=$_.ThreatID;InitialDetectionTime=if($_.InitialDetectionTime){{$_.InitialDetectionTime.ToString('o')}}else{{$null}};LastThreatStatusChangeTime=if($_.LastThreatStatusChangeTime){{$_.LastThreatStatusChangeTime.ToString('o')}}else{{$null}};ActionSuccess=$_.ActionSuccess;CurrentThreatExecutionStatusID=$_.CurrentThreatExecutionStatusID;ThreatStatusID=$_.ThreatStatusID;Resources=@($_.Resources);ProcessName=$_.ProcessName;RemediationTime=$_.RemediationTime;DomainUser=$_.DomainUser}}}} | ConvertTo-Json -Compress -Depth 5"
    raw=_ps(script,error_cls);items=raw if isinstance(raw,list) else ([raw] if isinstance(raw,dict) else [])
    out=[]
    for row in items:
        out.append({'threat_id':int(row.get('ThreatID') or 0),'initial_detection_time':row.get('InitialDetectionTime'),'last_status_change_time':row.get('LastThreatStatusChangeTime'),'action_success':row.get('ActionSuccess'),'execution_status_id':row.get('CurrentThreatExecutionStatusID'),'threat_status_id':row.get('ThreatStatusID'),'resources':[_truncate(x,2048) for x in (row.get('Resources') or [])][:32],'process_name':_truncate(row.get('ProcessName'),2048) or None,'remediation_time':str(row.get('RemediationTime') or '') or None,'domain_user':_truncate(row.get('DomainUser'),256) or None})
    return {'ok':True,'scope':'operator_machine_read','platform':'windows','detections':out,'count':len(out),'limit':limit,'mutation_authority':False}

def failure_evidence(payload:JsonObject,error_cls:type[Exception])->JsonObject:
    try:hours=_hours(payload)
    except ValueError as exc:raise error_cls('BAD_REQUEST',str(exc),400) from exc
    text=str(payload.get('text_filter') or '').strip();path=str(payload.get('path_filter') or '').strip();limit=min(int(payload.get('limit',100)),100)
    ev=events_query({'lookback_hours':hours,'limit':limit,'text_filter':text} if text else {'lookback_hours':hours,'limit':limit},error_cls)
    de=defender_detections({'lookback_hours':hours,'limit':min(limit,50)},error_cls)
    signals=[]
    for d in de['detections']:
        resources=' '.join(d.get('resources') or []);proc=str(d.get('process_name') or '')
        path_match=bool(path and path.casefold() in (resources+' '+proc).casefold())
        text_match=bool(text and text.casefold() in (resources+' '+proc).casefold())
        if path_match or text_match or (not path and not text):signals.append({'kind':'defender_detection','threat_id':d['threat_id'],'time':d['initial_detection_time'],'path_match':path_match,'text_match':text_match,'action_success':d.get('action_success'),'resources':d.get('resources',[])})
    return {'ok':True,'scope':'operator_machine_read','lookback_hours':hours,'query':{'text_filter':text or None,'path_filter':path or None},'windows_events':ev['events'],'windows_channel_errors':ev.get('channel_errors',[]),'partial':bool(ev.get('channel_errors')),'defender_signals':signals,'security_signal_present':bool(signals),'causation_established':False,'interpretation':'Evidence correlation only; security events are not promoted to cause without causal linkage.','mutation_authority':False}

def register_windows_telemetry_tools(register_tool:Registrar,*,error_cls:type[Exception])->None:
    traits=['operator_scope','bounded_results','windows_event_identity','security_telemetry','does_not_grant_mutation_authority']
    @register_tool('windows.events.query','Query bounded Windows Event Viewer evidence by channel/time/provider/event/text filters.','low',category='windows',approval_required=False,mutating=False,side_effect_class='read',effect_traits=traits,input_schema={'type':'object','properties':{'logs':{'type':'array','items':{'type':'string'},'maxItems':4},'lookback_hours':{'type':'number','exclusiveMinimum':0,'maximum':168},'provider':{'type':'string'},'event_ids':{'type':'array','items':{'type':'integer'},'maxItems':64},'text_filter':{'type':'string'},'limit':{'type':'integer','minimum':1,'maximum':250}},'additionalProperties':False})
    def tool_windows_events_query(payload:JsonObject)->JsonObject:return events_query(payload,error_cls)
    @register_tool('windows.defender.detections','Read bounded Microsoft Defender detection/remediation history.','low',category='windows',approval_required=False,mutating=False,side_effect_class='read',effect_traits=traits,input_schema={'type':'object','properties':{'lookback_hours':{'type':'number','exclusiveMinimum':0,'maximum':168},'limit':{'type':'integer','minimum':1,'maximum':100}},'additionalProperties':False})
    def tool_windows_defender(payload:JsonObject)->JsonObject:return defender_detections(payload,error_cls)
    @register_tool('windows.failure_evidence.inspect','Correlate bounded Windows EventLog and Defender evidence for a project/server failure without asserting cause.','low',category='windows',approval_required=False,mutating=False,side_effect_class='read',effect_traits=traits,input_schema={'type':'object','properties':{'lookback_hours':{'type':'number','exclusiveMinimum':0,'maximum':168},'text_filter':{'type':'string'},'path_filter':{'type':'string'},'limit':{'type':'integer','minimum':1,'maximum':100}},'additionalProperties':False})
    def tool_windows_failure_evidence(payload:JsonObject)->JsonObject:return failure_evidence(payload,error_cls)
