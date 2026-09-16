from __future__ import annotations
import hashlib, json
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class DevelopmentEvent:
    seq: int
    event_type: str
    payload: dict[str, Any]


class DevelopmentPath:
    """Deterministic presentation of developmental events, not identity authority.

    v0.6 can mirror new events into the content-bound causal biography ledger.
    The linear sequence remains a convenience view; causal biography authority
    lives in DevelopmentalBiography.
    """
    def __init__(self, on_append=None):
        self.events: list[DevelopmentEvent] = []
        self._on_append = on_append

    def restore(self, events: list[dict[str, Any]]) -> None:
        self.events = [DevelopmentEvent(i, str(x["event_type"]), dict(x["payload"])) for i, x in enumerate(events)]

    def append(self, event_type: str, payload: dict[str, Any]) -> DevelopmentEvent:
        normalized = json.loads(json.dumps(payload, sort_keys=True))
        ev = DevelopmentEvent(len(self.events), event_type, normalized)
        self.events.append(ev)
        if self._on_append is not None:
            self._on_append(event_type, normalized)
        return ev

    def digest(self) -> str:
        raw = json.dumps([asdict(x) for x in self.events], sort_keys=True,
                         separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()

    def export(self) -> list[dict[str, Any]]:
        return [asdict(x) for x in self.events]
