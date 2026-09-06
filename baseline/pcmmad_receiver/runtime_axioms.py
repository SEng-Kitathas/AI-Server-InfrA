"""Tiny ambient runtime doctrine seed.

This is intentionally small.  It exists so ordinary identity/health/bootstrap
surfaces can inject the governing search-space law without hauling the SOP into
every client response.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

AXIOM_VERSION = "1"
PRIMARY_AXIOM_ID = "AXIOM-01"
PRIMARY_AXIOM_TEXT = "INTENT IS A CONSTRAINT, NOT A CEILING."


def constitutional_seed() -> dict[str, Any]:
    primary = {
        "id": PRIMARY_AXIOM_ID,
        "version": AXIOM_VERSION,
        "text": PRIMARY_AXIOM_TEXT,
    }
    raw = json.dumps(primary, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {
        "primary_axiom": primary,
        "digest": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    }
