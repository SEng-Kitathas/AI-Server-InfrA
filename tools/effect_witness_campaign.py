#!/usr/bin/env python3
from __future__ import annotations
import argparse, concurrent.futures, hashlib, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import lab_tools
from pcmmad_receiver.shared_core import get_project_root

VOLATILE_TOP={"worktrees",".git","research","browser","execution"}
VOLATILE_SYSTEM={"lab/results","cache","tmp"}

def canonical_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()

def authoritative_fingerprint(project_id: str|None):
    if not project_id: return None
    root=get_project_root(project_id)
    rows=[]
    if not root.exists(): return canonical_hash(rows)
    for p in sorted(root.rglob('*')):
        if not p.is_file(): continue
        rel=p.relative_to(root).as_posix()
        first=rel.split('/',1)[0]
        if first in VOLATILE_TOP: continue
        if any(rel.startswith('system/'+x+'/') or rel=='system/'+x for x in VOLATILE_SYSTEM): continue
        try: data=p.read_bytes()
        except OSError: continue
        rows.append((rel,len(data),hashlib.sha256(data).hexdigest()))
    return canonical_hash(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--tool',required=True);ap.add_argument('--payload-json',required=True);ap.add_argument('--sequential',type=int,default=3);ap.add_argument('--parallel',type=int,default=4);ap.add_argument('--out',required=True);args=ap.parse_args()
    payload=json.loads(args.payload_json)
    cards={row['name']:row for row in lab_tools.list_tools()}
    card=cards[args.tool]
    if str(card.get('side_effect_class') or '') not in {'read','external_read'}:
        raise SystemExit('refusing witness: only declared pure read/external_read tools are eligible')
    digest=card['contract_digest'];project_id=payload.get('project_id') if isinstance(payload,dict) else None
    before=authoritative_fingerprint(project_id)
    def invoke():
        env=lab_tools.dispatch_tool(args.tool,payload,expected_contract_digest=digest)
        return env['result']
    seq=[invoke() for _ in range(args.sequential)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as ex:
        par=list(ex.map(lambda _i: invoke(),range(args.parallel)))
    after=authoritative_fingerprint(project_id)
    hashes=[canonical_hash(x) for x in seq+par]
    passed=len(set(hashes))==1 and before==after
    receipt={"schema":"pcmmad.effect-witness-receipt.v1","tool":args.tool,"contract_digest":digest,"declared_side_effect_class":card.get('side_effect_class'),"payload_sha256":canonical_hash(payload),"sequential_runs":args.sequential,"parallel_runs":args.parallel,"result_sha256":hashes[0] if hashes else None,"all_results_identical":len(set(hashes))==1,"authoritative_state_fingerprint_before":before,"authoritative_state_fingerprint_after":after,"authoritative_state_unchanged":before==after,"passed":passed}
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(receipt,sort_keys=True));raise SystemExit(0 if passed else 2)
if __name__=='__main__': main()
