#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import lab_tools
from pcmmad_receiver.scheduler_effect_profile import SIDE_EFFECT_TO_KIND

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--receipt',action='append',required=True);ap.add_argument('--out',default=str(ROOT/'baseline/pcmmad_receiver/scheduler_effect_witnesses_v1.json'));ap.add_argument('--approve',action='store_true');args=ap.parse_args()
    if not args.approve: raise SystemExit('explicit --approve is required to compile scheduler witnesses')
    cards={row['name']:row for row in lab_tools.list_tools()};doc={"schema":"pcmmad.scheduler-effect-witnesses.v1","effect_truth":{},"parallel":{},"resume_replay":{}}
    for path in args.receipt:
        r=json.loads(Path(path).read_text(encoding='utf-8'));name=r.get('tool');card=cards.get(name)
        if not r.get('passed') or not card or r.get('contract_digest')!=card.get('contract_digest'): raise SystemExit(f'invalid/stale witness receipt: {path}')
        side=str(card.get('side_effect_class') or '');kind=SIDE_EFFECT_TO_KIND.get(side)
        if kind not in {'READ_LOCAL','READ_EXTERNAL'}: raise SystemExit(f'unsupported witness effect: {name}/{side}')
        witness={"contract_digest":card['contract_digest'],"effect_kind":kind,"receipt":str(Path(path).as_posix())}
        doc['effect_truth'][name]=witness;doc['parallel'][name]={"contract_digest":card['contract_digest'],"receipt":str(Path(path).as_posix())}
        if str(card.get('idempotency_semantics') or '').lower()=='safe_repeat': doc['resume_replay'][name]={"contract_digest":card['contract_digest'],"receipt":str(Path(path).as_posix())}
    Path(args.out).write_text(json.dumps(doc,indent=2,sort_keys=True)+'\n',encoding='utf-8');print(json.dumps({"ok":True,"count":len(doc['effect_truth']),"out":args.out},sort_keys=True))
if __name__=='__main__': main()
