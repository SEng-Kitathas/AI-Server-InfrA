from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

MODE_RANK={'NAKED':0,'EQUIPPED':1,'FEDERATED':2}

@dataclass(frozen=True)
class Observation:
    capture_id:str
    origin:str
    referent:str
    observed_at:str|None
    acquired_at:str|None
    value:Any
    currentness_basis:str
    resource_mode:str
    authority:str='OBSERVATION_ONLY'

def _dt(s:str):
    return datetime.fromisoformat(s.replace('Z','+00:00'))

def compose_mode(*modes:str)->str:
    return max(modes,key=lambda x:MODE_RANK[x])

def currentness(obs:Observation, now_iso:str, max_age_seconds:int):
    if not obs.observed_at:
        return 'UNKNOWN_INCOMPLETE'
    try:
        age=(_dt(now_iso)-_dt(obs.observed_at)).total_seconds()
    except Exception:
        return 'UNKNOWN_INCOMPLETE'
    if age < -5:
        return 'UNKNOWN_INCOMPLETE'
    return 'CURRENT' if age <= max_age_seconds else 'STALE'

def exact_observation_witness(obs:Observation, *, query_referent:str, now_iso:str, max_age_seconds:int, query_obligation_id:str):
    if obs.referent != query_referent:
        return {'status':'UNKNOWN_INCOMPLETE','reason':'REFERENT_MISMATCH'}
    c=currentness(obs,now_iso,max_age_seconds)
    if c!='CURRENT':
        return {'status':'UNKNOWN_INCOMPLETE','reason':c}
    if obs.authority!='OBSERVATION_ONLY':
        return {'status':'UNKNOWN_INCOMPLETE','reason':'AUTHORITY_CONTRACT_MISMATCH'}
    return {'status':'WITNESS','capture_id':obs.capture_id,'query_obligation_id':query_obligation_id,'value':obs.value,'mode':obs.resource_mode,'authority':'OBSERVATION_ONLY'}

def daylight_witness(time_obs:Observation, sunref:dict, *, query_place:str, query_date:str, query_obligation_id:str):
    if time_obs.referent not in ('UTC-04:00 civil clock','Charlotte local civil clock'):
        return {'status':'UNKNOWN_INCOMPLETE','reason':'TIME_REFERENT_MISMATCH'}
    if sunref.get('place') != query_place or sunref.get('date') != query_date:
        return {'status':'UNKNOWN_INCOMPLETE','reason':'SUN_REFERENT_OR_DATE_MISMATCH'}
    t=_dt(time_obs.observed_at)
    if t.date().isoformat()!=query_date:
        return {'status':'UNKNOWN_INCOMPLETE','reason':'TIME_DATE_MISMATCH'}
    hhmmss=t.time().replace(tzinfo=None)
    sr=datetime.strptime(sunref['sunrise_local'],'%H:%M:%S').time()
    ss=datetime.strptime(sunref['sunset_local'],'%H:%M:%S').time()
    return {'status':'WITNESS','query_obligation_id':query_obligation_id,'daylight':sr<=hhmmss<ss,'mode':compose_mode(time_obs.resource_mode,sunref.get('resource_mode','FEDERATED')),'authority':'DERIVED_READ_ONLY'}

def admit_shadow(candidate_id:str, oarr_valid:bool, evidence_resolved:bool, authority:str, parent_hash_ok:bool):
    if not (oarr_valid and evidence_resolved and parent_hash_ok): return 'REJECT'
    if authority not in ('OBSERVATION_ONLY','REFERENCE_ONLY','DERIVED_READ_ONLY'): return 'REJECT'
    return 'SHADOW_ADMITTED'
