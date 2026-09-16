"""Deterministic generation/checks for source-controlled control-plane artifacts."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from lab_tools import list_tools
from scheduler_effect_profile import PROFILE_PATH, build_profile


def current_capability_cards() -> dict[str, dict[str, Any]]:
    return {str(row.get("name")): dict(row) for row in list_tools()}


def render_scheduler_effect_profile() -> str:
    profile=build_profile(current_capability_cards())
    return json.dumps(profile,indent=2,sort_keys=True)+"\n"

def scheduler_effect_profile_is_current(path: Path=PROFILE_PATH) -> bool:
    try:
        return path.read_text(encoding="utf-8")==render_scheduler_effect_profile()
    except OSError:
        return False

def write_scheduler_effect_profile(path: Path=PROFILE_PATH) -> dict[str, Any]:
    rendered=render_scheduler_effect_profile()
    path.write_text(rendered,encoding="utf-8",newline="\n")
    profile=json.loads(rendered)
    return {
        "path":str(path),
        "catalog_digest":profile["catalog_digest"],
        "profile_digest":profile["profile_digest"],
        "capability_count":profile["capability_count"],
    }
