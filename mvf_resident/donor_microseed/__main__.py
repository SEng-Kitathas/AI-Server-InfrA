from __future__ import annotations
import argparse, json, tempfile
from pathlib import Path
from .runtime.entity import Microseed


def main() -> int:
    ap = argparse.ArgumentParser(description="Proto-Microseed Main-Dev embodiment")
    ap.add_argument("--state-dir", default=None)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--status", action="store_true")
    ns = ap.parse_args()

    if ns.self_test:
        with tempfile.TemporaryDirectory(prefix="proto-microseed-") as td:
            ms = Microseed(Path(td))
            result = ms.self_test()
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["all_pass"] else 1

    state = Path(ns.state_dir or ".microseed-state")
    ms = Microseed(state)
    print(json.dumps(ms.status(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
