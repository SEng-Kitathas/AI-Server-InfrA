#!/usr/bin/env python3
"""Verify or import a sealed private UCS/UCM v1 release into Runtime.

This is an administrative migration utility, intentionally not a model-facing
native capability. Output is a structural receipt only; private record values
are never printed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "baseline" / "pcmmad_receiver"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from ucm_private_migration import UcmMigrationError, import_private_release, verify_private_release


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", required=True, help="server-local path to PRIVATE_USER_CONTINUITY_INSTANCE_V1_0_2026-09-09.zip")
    p.add_argument("--receipt", help="optional server-local detached release receipt JSON")
    p.add_argument("--profile-id", help="target Runtime UCM profile; required with --import")
    p.add_argument("--import", dest="do_import", action="store_true", help="perform one-time migration into an empty profile after full verification")
    return p


def main() -> int:
    args = parser().parse_args()
    archive = Path(args.archive)
    receipt = Path(args.receipt) if args.receipt else None
    try:
        if args.do_import:
            if not args.profile_id:
                raise UcmMigrationError("BAD_REQUEST", "--profile-id is required with --import")
            result = import_private_release(archive, profile_id=args.profile_id, detached_receipt_path=receipt)
        else:
            result = verify_private_release(archive, detached_receipt_path=receipt)
    except UcmMigrationError as exc:
        print(json.dumps({"ok": False, "error_code": exc.error_code, "message": exc.message, **exc.extra}, indent=2, sort_keys=True))
        return 2
    print(json.dumps({"ok": True, **result}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
