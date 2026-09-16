from __future__ import annotations
from datetime import datetime
from .types import Observation, ResourceMode

_MODE_RANK = {ResourceMode.NAKED: 0, ResourceMode.EQUIPPED: 1, ResourceMode.FEDERATED: 2}


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def compose_mode(*modes: ResourceMode) -> ResourceMode:
    return max(modes, key=lambda x: _MODE_RANK[x])


def currentness(obs: Observation, now_iso: str, max_age_seconds: int) -> str:
    if not obs.observed_at:
        return "UNKNOWN_INCOMPLETE"
    try:
        age = (_dt(now_iso) - _dt(obs.observed_at)).total_seconds()
    except Exception:
        return "UNKNOWN_INCOMPLETE"
    if age < -5:
        return "UNKNOWN_INCOMPLETE"
    return "CURRENT" if age <= max_age_seconds else "STALE"
