from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"baseline"/"pcmmad_receiver"
if str(BASE) not in sys.path: sys.path.insert(0,str(BASE))
from generated_control_artifacts import PROFILE_PATH, scheduler_effect_profile_is_current, write_scheduler_effect_profile

def main()->int:
    p=argparse.ArgumentParser()
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--check",action="store_true")
    g.add_argument("--write",action="store_true")
    args=p.parse_args()
    if args.check:
        ok=scheduler_effect_profile_is_current()
        print(json.dumps({"ok":ok,"path":str(PROFILE_PATH)}))
        return 0 if ok else 2
    print(json.dumps({"ok":True,**write_scheduler_effect_profile()},sort_keys=True))
    return 0
if __name__=="__main__": raise SystemExit(main())
