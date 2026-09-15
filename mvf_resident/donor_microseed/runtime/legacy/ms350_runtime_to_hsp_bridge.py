"""Research-only Microseed runtime→HSP→shadow admission bridge.

OARR protocol validity is necessary but not sufficient. Evidence IDs must resolve to exact durable artifacts.
A lab result cannot self-admit; admission is a separate exact-binding step. Capability may emerge; authority may not.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()

def resolve_evidence_ids(slice_doc:dict, evidence_dir:Path)->dict:
    ids=set()
    for ranger in slice_doc['rangers']:
        ids.update(ranger.get('output_evidence_ids',[]))
        ids.update(ranger.get('negative_evidence_ids',[]))
    missing=[]; resolved={}
    for eid in sorted(ids):
        p=evidence_dir/f'{eid}.json'
        if not p.exists(): missing.append(eid)
        else: resolved[eid]={'sha256':sha256_file(p),'bytes':p.stat().st_size}
    return {'ok':not missing,'missing':missing,'resolved':resolved}

def admission_matches(token:dict, *, candidate_id:str, candidate_contract_hash:str, parent_state_sha256:str, hsp_slice_sha256:str)->bool:
    return token.get('mode')=='SHADOW' and token.get('authority')=='NONE' and token.get('candidate_id')==candidate_id and token.get('candidate_contract_hash')==candidate_contract_hash and token.get('parent_state_sha256')==parent_state_sha256 and token.get('hsp_slice_sha256')==hsp_slice_sha256
