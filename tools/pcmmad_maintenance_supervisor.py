#!/usr/bin/env python3
"""Tiny out-of-process PCMMAD maintenance supervisor.
Uses the same maintenance_plane implementation; does not duplicate authority semantics.
Intended for local operator execution when the receiver is unavailable.
"""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import maintenance_plane
from pcmmad_receiver.project_mutation_authority import _state_path

def main(argv=None):
 ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='cmd',required=True)
 sub.add_parser('status')
 a=sub.add_parser('acquire');a.add_argument('--operator',required=True);a.add_argument('--reason',required=True);a.add_argument('--ttl',type=int,default=900)
 r=sub.add_parser('reconcile-authority');r.add_argument('--operator',required=True);r.add_argument('--token',required=True);r.add_argument('--generation',type=int,required=True);r.add_argument('--project',required=True);r.add_argument('--reason',required=True)
 z=sub.add_parser('release');z.add_argument('--operator',required=True);z.add_argument('--token',required=True);z.add_argument('--generation',type=int,required=True)
 ns=ap.parse_args(argv)
 if ns.cmd=='status':out=maintenance_plane.inspect()
 elif ns.cmd=='acquire':out=maintenance_plane.acquire(operator_id=ns.operator,reason=ns.reason,ttl_seconds=ns.ttl)
 elif ns.cmd=='release':out=maintenance_plane.release(token=ns.token,generation=ns.generation,operator_id=ns.operator)
 else:out=maintenance_plane.reconcile_authority_state(token=ns.token,generation=ns.generation,operator_id=ns.operator,project_id=ns.project,state_path=_state_path(ns.project),reason=ns.reason)
 print(json.dumps(out,indent=2,sort_keys=True,default=str));return 0
if __name__=='__main__':raise SystemExit(main())
