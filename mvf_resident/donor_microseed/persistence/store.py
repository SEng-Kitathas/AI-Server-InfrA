from __future__ import annotations
import json, sqlite3, time
from pathlib import Path
from typing import Any


class StateStore:
    """Event-sourced durable state. Persistence does not imply persistent identity."""
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute(
            "create table if not exists events(seq integer primary key autoincrement, kind text, payload text, created_ns integer)"
        )
        self.conn.execute(
            "create table if not exists kv(k text primary key, value text, updated_ns integer)"
        )
        self.conn.commit()

    def append(self, kind: str, payload: dict[str, Any]) -> int:
        cur = self.conn.execute("insert into events(kind,payload,created_ns) values(?,?,?)",
                                (kind, json.dumps(payload, sort_keys=True), time.time_ns()))
        self.conn.commit()
        return int(cur.lastrowid)

    def events(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("select seq,kind,payload,created_ns from events order by seq").fetchall()
        return [{"seq":r[0],"kind":r[1],"payload":json.loads(r[2]),"created_ns":r[3]} for r in rows]

    def set(self, key: str, value: Any) -> None:
        self.conn.execute(
            "insert into kv(k,value,updated_ns) values(?,?,?) on conflict(k) do update set value=excluded.value,updated_ns=excluded.updated_ns",
            (key, json.dumps(value, sort_keys=True), time.time_ns()),
        )
        self.conn.commit()

    def get(self, key: str, default: Any = None) -> Any:
        row = self.conn.execute("select value from kv where k=?", (key,)).fetchone()
        return default if row is None else json.loads(row[0])
