from __future__ import annotations
import hashlib, json, sqlite3, time
from pathlib import Path
from typing import Any, Iterable
from ..runtime.types import EpistemicStatus, EvidenceRef


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class EvidenceLedger:
    """Append-only evidence ledger.

    Evidence identity is content-bound. Negative evidence is first-class. Nothing
    in this class grants capability/action authority merely because a record exists.
    """
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute(
            """create table if not exists evidence(
            seq integer primary key autoincrement,
            evidence_id text unique not null,
            sha256 text not null,
            disposition text not null,
            negative integer not null,
            payload_json text not null,
            source text not null,
            created_ns integer not null
            )"""
        )
        self.conn.commit()

    def append(self, evidence_id: str, payload: Any, disposition: EpistemicStatus,
               *, negative: bool = False, source: str = "LOCAL") -> EvidenceRef:
        raw = canonical_json(payload)
        digest = sha256_bytes(raw)
        self.conn.execute(
            "insert into evidence(evidence_id,sha256,disposition,negative,payload_json,source,created_ns) values(?,?,?,?,?,?,?)",
            (evidence_id, digest, disposition.value, 1 if negative else 0,
             raw.decode("utf-8"), source, time.time_ns()),
        )
        self.conn.commit()
        return EvidenceRef(evidence_id, digest, disposition, negative)

    def get(self, evidence_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "select evidence_id,sha256,disposition,negative,payload_json,source,created_ns from evidence where evidence_id=?",
            (evidence_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "evidence_id": row[0], "sha256": row[1], "disposition": row[2],
            "negative": bool(row[3]), "payload": json.loads(row[4]),
            "source": row[5], "created_ns": row[6],
        }

    def resolve(self, refs: Iterable[EvidenceRef]) -> tuple[bool, list[str]]:
        missing: list[str] = []
        for ref in refs:
            row = self.get(ref.evidence_id)
            if row is None or row["sha256"] != ref.sha256:
                missing.append(ref.evidence_id)
        return not missing, missing

    def list(self) -> list[dict[str, Any]]:
        ids = [r[0] for r in self.conn.execute("select evidence_id from evidence order by seq")]
        return [self.get(i) for i in ids if self.get(i) is not None]
