from __future__ import annotations
import hashlib, json, sqlite3, time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


class BiographyIntegrityError(RuntimeError):
    pass


def _canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _event_id(kind: str, payload: dict[str, Any], parents: Iterable[str]) -> str:
    body = {"kind": kind, "payload": payload, "parents": sorted(str(x) for x in parents)}
    return hashlib.sha256(_canonical(body)).hexdigest()


@dataclass(frozen=True)
class BiographyEvent:
    event_id: str
    kind: str
    payload: dict[str, Any]
    parents: tuple[str, ...]

    def serializable(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind,
            "payload": self.payload,
            "parents": list(self.parents),
        }


class DevelopmentalBiography:
    """Content-bound causal developmental-history ledger.

    This object establishes bounded operational lineage/integrity relations only.
    It is deliberately not selfhood, semantic truth, or external-reference authority.
    """

    def __init__(self, db_path: Path, *, legacy_anchor: dict[str, Any] | None = None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute(
            "create table if not exists biography_events("
            "event_id text primary key, kind text not null, payload text not null, "
            "parents text not null, created_ns integer not null)"
        )
        self.conn.commit()
        self._events = self._load_and_verify()
        if not self._events:
            anchor = dict(legacy_anchor or {})
            anchor.setdefault("historical_biography_before_v0_6", "UNKNOWN_INCOMPLETE")
            anchor.setdefault("authority", "OPERATIONAL_LINEAGE_ANCHOR_ONLY")
            self.append("BIOGRAPHY_GENESIS", anchor, parents=())

    @property
    def events(self) -> dict[str, BiographyEvent]:
        return dict(self._events)

    def close(self) -> None:
        self.conn.close()

    def _load_and_verify(self) -> dict[str, BiographyEvent]:
        rows = self.conn.execute(
            "select event_id,kind,payload,parents from biography_events"
        ).fetchall()
        events: dict[str, BiographyEvent] = {}
        errors: list[str] = []
        for eid, kind, payload_raw, parents_raw in rows:
            try:
                payload = json.loads(payload_raw)
                parents = tuple(json.loads(parents_raw))
            except Exception as exc:
                errors.append(f"decode:{eid}:{exc}")
                continue
            want = _event_id(kind, payload, parents)
            if want != eid:
                errors.append(f"content_hash:{eid}")
            events[eid] = BiographyEvent(eid, kind, payload, tuple(str(x) for x in parents))
        for eid, ev in events.items():
            for p in ev.parents:
                if p not in events:
                    errors.append(f"missing_parent:{eid}:{p}")
        # cycle check despite content hashes making accidental cycles extremely unlikely
        visiting: set[str] = set(); done: set[str] = set()
        def visit(eid: str) -> bool:
            if eid in visiting:
                return False
            if eid in done:
                return True
            visiting.add(eid)
            for p in events[eid].parents:
                if p in events and not visit(p):
                    return False
            visiting.remove(eid); done.add(eid); return True
        for eid in events:
            if not visit(eid):
                errors.append(f"cycle:{eid}")
                break
        if errors:
            raise BiographyIntegrityError(";".join(errors))
        return events

    def verify(self) -> tuple[bool, tuple[str, ...]]:
        try:
            current = self._load_and_verify()
        except BiographyIntegrityError as exc:
            return False, tuple(str(exc).split(";"))
        if set(current) != set(self._events):
            return False, ("in_memory_database_event_set_mismatch",)
        return True, ()

    def heads(self) -> tuple[str, ...]:
        all_ids = set(self._events)
        parents = {p for ev in self._events.values() for p in ev.parents}
        return tuple(sorted(all_ids - parents))

    def append(
        self,
        kind: str,
        payload: dict[str, Any],
        *,
        parents: Iterable[str] | None = None,
    ) -> BiographyEvent:
        parent_ids = tuple(sorted(self.heads() if parents is None else tuple(str(x) for x in parents)))
        for p in parent_ids:
            if p not in self._events:
                raise ValueError(f"unknown biography parent:{p}")
        normalized = json.loads(json.dumps(payload, sort_keys=True))
        eid = _event_id(str(kind), normalized, parent_ids)
        existing = self._events.get(eid)
        if existing is not None:
            return existing
        self.conn.execute(
            "insert into biography_events(event_id,kind,payload,parents,created_ns) values(?,?,?,?,?)",
            (eid, str(kind), json.dumps(normalized, sort_keys=True),
             json.dumps(list(parent_ids)), time.time_ns()),
        )
        self.conn.commit()
        ev = BiographyEvent(eid, str(kind), normalized, parent_ids)
        self._events[eid] = ev
        return ev

    def ancestors(self, event_id: str) -> set[str]:
        if event_id not in self._events:
            raise KeyError(event_id)
        out: set[str] = set(); stack = [event_id]
        while stack:
            x = stack.pop()
            if x in out:
                continue
            out.add(x)
            stack.extend(self._events[x].parents)
        return out

    def canonical_order(self) -> list[BiographyEvent]:
        """Deterministic causal topological presentation; not wall-clock authority."""
        remaining = set(self._events); emitted: set[str] = set(); out: list[BiographyEvent] = []
        while remaining:
            ready = sorted(
                eid for eid in remaining
                if set(self._events[eid].parents) <= emitted
            )
            if not ready:
                raise BiographyIntegrityError("no_topological_progress")
            for eid in ready:
                out.append(self._events[eid]); emitted.add(eid); remaining.remove(eid)
        return out

    def graph_digest(self) -> str:
        # Event IDs already bind payload and causal parents. Sorting avoids making
        # irrelevant database insertion order part of the developmental claim.
        return hashlib.sha256(_canonical(sorted(self._events))).hexdigest()

    def export(self) -> dict[str, Any]:
        ok, errors = self.verify()
        return {
            "schema": "microseed.developmental-biography.v0.6",
            "integrity": "VERIFIED" if ok else "VIOLATED",
            "errors": list(errors),
            "graph_digest": self.graph_digest() if ok else None,
            "heads": list(self.heads()) if ok else [],
            "events": [ev.serializable() for ev in self.canonical_order()] if ok else [],
            "authority": "OPERATIONAL_DEVELOPMENTAL_LINEAGE_ONLY",
            "identity_claim": "NOT_QUALIFIED",
        }

    @staticmethod
    def _validate_export(data: dict[str, Any]) -> dict[str, BiographyEvent]:
        events: dict[str, BiographyEvent] = {}
        for raw in data.get("events", []):
            parents = tuple(str(x) for x in raw.get("parents", ()))
            payload = raw.get("payload", {})
            eid = str(raw.get("event_id", ""))
            if _event_id(str(raw.get("kind", "")), payload, parents) != eid:
                raise BiographyIntegrityError(f"export_content_hash:{eid}")
            events[eid] = BiographyEvent(eid, str(raw["kind"]), payload, parents)
        for eid, ev in events.items():
            if any(p not in events for p in ev.parents):
                raise BiographyIntegrityError(f"export_missing_parent:{eid}")
        return events

    @staticmethod
    def relation(a: dict[str, Any], b: dict[str, Any]) -> str:
        """Typed lineage relation. Never returns a selfhood assertion."""
        try:
            ae = DevelopmentalBiography._validate_export(a)
            be = DevelopmentalBiography._validate_export(b)
        except BiographyIntegrityError:
            return "UNKNOWN_INCOMPLETE"
        aset, bset = set(ae), set(be)
        if not aset or not bset or not (aset & bset):
            return "UNRELATED_OR_UNKNOWN"
        def heads(events):
            parents={p for ev in events.values() for p in ev.parents}
            return set(events)-parents
        def ancestors(events, starts):
            out=set(); stack=list(starts)
            while stack:
                x=stack.pop()
                if x in out: continue
                out.add(x); stack.extend(events[x].parents)
            return out
        ah,bh=heads(ae),heads(be)
        if aset==bset and ah==bh:
            return "SAME_BIOGRAPHY_STATE"
        ba=ancestors(be,bh); aa=ancestors(ae,ah)
        if ah <= ba and not bh <= aa:
            return "DESCENDANT_CONTINUATION"
        if bh <= aa and not ah <= ba:
            return "ANCESTOR_STATE"
        return "COMMON_ANCESTRY_DIVERGED"
