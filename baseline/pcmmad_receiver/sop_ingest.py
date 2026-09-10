"""SOP package inspection, registration, and governed chunked ingestion boundary."""

from __future__ import annotations

import csv
import hashlib
import math
import re
import threading
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from collections.abc import MutableMapping

from .server_hardening import safe_json_dumps, safe_json_loads
from .shared_core import (
    ensure_parent,
    get_project_root,
    resolve_mount_spec,
    sha256_bytes,
    sha256_file,
    utc_now,
    validate_project_id,
)

JsonObject = MutableMapping[str, Any]

MANIFEST_NAME = "manifest-sha256.txt"
LEDGER_NAME = "92 CORPUS_CHAIN_LEDGER.csv"
MERKLE_NAME = "93 CORPUS_MERKLE_ROOT.txt"
README_NAME = "README__SHALL_START_AT_00.md"
ZERO_SHA256 = "0" * 64
TRAVERSAL_RE = re.compile(r"^\s*\d+[A-Z]?\.\s+`([^`]+)`\s*$")
MERKLE_ROOT_RE = re.compile(r"^Merkle root .*?:\s*([0-9a-f]{64})\s*$", re.IGNORECASE)
SAFE_CORPUS_RE = re.compile(r"[^A-Za-z0-9._-]+")
SOP_MAX_FILES = 5000
SOP_MAX_TOTAL_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
SOP_MAX_SINGLE_FILE_BYTES = 64 * 1024 * 1024
_CORPUS_LOCKS_GUARD = threading.RLock()
_CORPUS_LOCKS: dict[str, threading.RLock] = {}


def _corpus_lock(project_id: str, corpus_id: str) -> threading.RLock:
    key = f"{project_id}:{corpus_id}"
    with _CORPUS_LOCKS_GUARD:
        return _CORPUS_LOCKS.setdefault(key, threading.RLock())


@dataclass(frozen=True)
class RegisterPackageSpec:
    project_id: str
    source_path_spec: str
    corpus_id: str | None = None
    chunk_chars: int = 6000
    reset: bool = False


@dataclass(frozen=True)
class FileReceiptRequest:
    project_id: str
    corpus_id: str
    state: JsonObject
    current: JsonObject
    message: str


@dataclass(frozen=True)
class ChunkIssueSpec:
    current: JsonObject
    chunk_index: int
    total_chunks: int
    start: int
    end: int
    chunk_sha: str
    ack_token: str
    chunk_text: str = ""


@dataclass(frozen=True)
class ChunkResponseSpec:
    project_id: str
    corpus_id: str
    chunk: ChunkIssueSpec


class SopError(Exception):
    def __init__(self, code: str, message: str, *, extra: JsonObject | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.extra = extra or {}


@dataclass(frozen=True)
class LedgerMismatchSpec:
    seq: int
    row: dict[str, str]
    kind: str
    expected: str
    actual: str | None


@dataclass(frozen=True)
class AckResponseSpec:
    project_id: str
    corpus_id: str
    current: JsonObject
    issued: JsonObject
    delivered_final: bool


@dataclass(frozen=True)
class CompletionResponseSpec:
    project_id: str
    corpus_id: str
    meta: JsonObject
    state: JsonObject
    current: JsonObject


@dataclass(frozen=True)
class PackageFile:
    name: str
    data: bytes

    @property
    def sha256(self) -> str:
        return sha256_bytes(self.data)

    @property
    def text(self) -> str:
        return self.data.decode("utf-8", errors="replace")


@dataclass(frozen=True)
class PackageIntegrity:
    manifest: dict[str, str]
    manifest_mismatches: list[JsonObject]
    ledger_rows: list[dict[str, str]]
    ledger: JsonObject
    declared_root: str
    computed_root: str
    leaf_names: list[str]
    readme_order: list[str]
    traversal_order: list[str]


class PackageSource:
    def __init__(self, source_path: Path) -> None:
        self.source_path = source_path.resolve()
        self.is_zip = self.source_path.is_file()
        self.is_dir = self.source_path.is_dir()
        if not self.is_zip and not self.is_dir:
            raise SopError("SOP_SOURCE_NOT_FOUND", f"source path not found: {self.source_path}")
        if self.is_zip and self.source_path.suffix.lower() != ".zip":
            raise SopError(
                "SOP_UNSUPPORTED_SOURCE",
                "only .zip archives or extracted directories are supported",
            )
        if self.is_zip:
            with zipfile.ZipFile(self.source_path) as zf:
                infos = [info for info in zf.infolist() if not info.is_dir()]
                self._names = [info.filename for info in infos]
                sizes = [int(info.file_size) for info in infos]
        else:
            file_paths = [p for p in sorted(self.source_path.rglob("*")) if p.is_file()]
            self._names = [
                str(p.relative_to(self.source_path)).replace("\\", "/")
                for p in file_paths
            ]
            sizes = [int(p.stat().st_size) for p in file_paths]
        if len(self._names) > SOP_MAX_FILES:
            raise SopError(
                "SOP_PACKAGE_TOO_LARGE",
                f"package contains {len(self._names)} files; limit is {SOP_MAX_FILES}",
            )
        if sizes and max(sizes) > SOP_MAX_SINGLE_FILE_BYTES:
            raise SopError(
                "SOP_PACKAGE_TOO_LARGE",
                f"package contains a file larger than {SOP_MAX_SINGLE_FILE_BYTES} bytes",
            )
        if sum(sizes) > SOP_MAX_TOTAL_UNCOMPRESSED_BYTES:
            raise SopError(
                "SOP_PACKAGE_TOO_LARGE",
                f"package uncompressed size exceeds {SOP_MAX_TOTAL_UNCOMPRESSED_BYTES} bytes",
            )
        self._uncompressed_bytes = sum(sizes)

    def names(self) -> list[str]:
        return list(self._names)

    def read_bytes(self, name: str) -> bytes:
        if self.is_zip:
            with zipfile.ZipFile(self.source_path) as zf:
                return zf.read(name)
        return (self.source_path / name).read_bytes()

    def read_text(self, name: str) -> str:
        return self.read_bytes(name).decode("utf-8", errors="replace")

    def file(self, name: str) -> PackageFile:
        return PackageFile(name=name, data=self.read_bytes(name))

    def archive_meta(self) -> JsonObject:
        if self.is_zip:
            return {
                "source_kind": "zip",
                "source_path": str(self.source_path),
                "archive_bytes": int(self.source_path.stat().st_size),
                "archive_sha256": sha256_file(self.source_path),
                "uncompressed_bytes": self._uncompressed_bytes,
            }
        return {
            "source_kind": "directory",
            "source_path": str(self.source_path),
            "archive_bytes": None,
            "archive_sha256": None,
            "uncompressed_bytes": self._uncompressed_bytes,
        }


def _corpora_root(project_id: str) -> Path:
    return get_project_root(validate_project_id(project_id)) / "system" / "lab" / "corpora"


def _corpus_dir(project_id: str, corpus_id: str) -> Path:
    return _corpora_root(project_id) / corpus_id


def _meta_path(project_id: str, corpus_id: str) -> Path:
    return _corpus_dir(project_id, corpus_id) / "meta.json"


def _state_path(project_id: str, corpus_id: str) -> Path:
    return _corpus_dir(project_id, corpus_id) / "state.json"


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return safe_json_loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, payload: Any) -> None:
    ensure_parent(path)
    path.write_text(safe_json_dumps(payload), encoding="utf-8")


def _sanitize_corpus_id(raw: str) -> str:
    cleaned = SAFE_CORPUS_RE.sub("-", raw.strip()).strip("-._")
    return cleaned[:96] or f"corpus-{uuid.uuid4().hex[:10]}"


def _parse_manifest(text: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r"\s{2,}", line, maxsplit=1)
        if len(parts) != 2:
            continue
        digest, name = parts[0].strip(), parts[1].strip()
        if re.fullmatch(r"[0-9a-f]{64}", digest):
            rows[name] = digest
    if not rows:
        raise SopError(
            "SOP_MANIFEST_INVALID", "manifest-sha256.txt did not yield any file hash rows"
        )
    return rows


def _parse_ledger(text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(text.splitlines())
    rows = [dict(row) for row in reader]
    if not rows:
        raise SopError("SOP_LEDGER_INVALID", "chain ledger is empty or unreadable")
    return rows


def _parse_readme_order(text: str) -> list[str]:
    order: list[str] = []
    for line in text.splitlines():
        traversal_match = TRAVERSAL_RE.match(line)
        if traversal_match:
            order.append(traversal_match.group(1))
    return order


def _compute_entry_sha(row: dict[str, str]) -> str:
    joined = "|".join(
        [
            str(row.get("seq", "")),
            str(row.get("file_name", "")),
            str(row.get("artifact_class", "")),
            str(row.get("authority_scope", "")),
            str(row.get("file_sha256", "")),
            str(row.get("prev_entry_sha256", "")),
            str(row.get("default_read_next_file", "")),
        ]
    )
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _ledger_mismatch(spec: LedgerMismatchSpec) -> JsonObject:
    return {
        "seq": spec.seq,
        "file_name": spec.row.get("file_name"),
        "kind": spec.kind,
        "expected": spec.expected,
        "actual": spec.actual,
    }


def _ledger_row_mismatches(
    seq: int, row: dict[str, str], prev: str, manifest: dict[str, str]
) -> list[JsonObject]:
    mismatches: list[JsonObject] = []
    expected = _compute_entry_sha(row)
    if row.get("prev_entry_sha256") != prev:
        mismatches.append(
            _ledger_mismatch(
                LedgerMismatchSpec(
                    seq, row, "prev_entry_sha256", prev, row.get("prev_entry_sha256")
                )
            )
        )
    if row.get("entry_sha256") != expected:
        mismatches.append(
            _ledger_mismatch(
                LedgerMismatchSpec(seq, row, "entry_sha256", expected, row.get("entry_sha256"))
            )
        )
    manifest_hash = manifest.get(row.get("file_name", ""))
    if manifest_hash and row.get("file_sha256") != manifest_hash:
        mismatches.append(
            _ledger_mismatch(
                LedgerMismatchSpec(seq, row, "file_sha256", manifest_hash, row.get("file_sha256"))
            )
        )
    return mismatches


def _verify_ledger(rows: list[dict[str, str]], manifest: dict[str, str]) -> JsonObject:
    prev = ZERO_SHA256
    mismatches: list[JsonObject] = []
    by_name: dict[str, dict[str, str]] = {}
    for idx, row in enumerate(rows, start=1):
        by_name[row["file_name"]] = row
        mismatches.extend(_ledger_row_mismatches(idx, row, prev, manifest))
        prev = _compute_entry_sha(row)
    return {
        "ok": not mismatches,
        "mismatches": mismatches,
        "by_name": by_name,
        "last_entry_sha256": prev,
    }


def _parse_merkle_root(text: str) -> str:
    for line in text.splitlines():
        merkle_match = MERKLE_ROOT_RE.match(line)
        if merkle_match:
            return merkle_match.group(1).lower()
    raise SopError(
        "SOP_MERKLE_INVALID", "93 CORPUS_MERKLE_ROOT.txt did not contain a parseable merkle root"
    )


def _compute_merkle_root(files: dict[str, PackageFile]) -> tuple[str, list[str]]:
    leaf_names = sorted(
        name for name in files if name not in {MANIFEST_NAME, LEDGER_NAME, MERKLE_NAME}
    )
    level = [files[name].sha256 for name in leaf_names]
    if not level:
        raise SopError("SOP_MERKLE_INVALID", "no payload leaves available for merkle fold")
    while len(level) > 1:
        if len(level) % 2 == 1:
            level = level + [level[-1]]
        next_level: list[str] = []
        for i in range(0, len(level), 2):
            next_level.append(hashlib.sha256((level[i] + level[i + 1]).encode("utf-8")).hexdigest())
        level = next_level
    return level[0], leaf_names


def _build_traversal_order(
    readme_order: list[str], ledger_rows: list[dict[str, str]], package_names: list[str]
) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    def add(name: str) -> None:
        if name in package_names and name not in seen:
            ordered.append(name)
            seen.add(name)

    for name in readme_order:
        add(name)
    for row in ledger_rows:
        add(str(row.get("file_name", "")))
    for name in sorted(package_names):
        add(name)
    return ordered


def _manifest_mismatches(
    files: dict[str, PackageFile], manifest: dict[str, str]
) -> list[JsonObject]:
    mismatches: list[JsonObject] = []
    for name, expected in manifest.items():
        if name not in files:
            mismatches.append(
                {
                    "file_name": name,
                    "kind": "missing_from_package",
                    "expected": expected,
                    "actual": None,
                }
            )
            continue
        actual = files[name].sha256
        if actual != expected:
            mismatches.append(
                {"file_name": name, "kind": "sha256", "expected": expected, "actual": actual}
            )
    return mismatches


def _package_index_files(
    traversal_order: list[str], files: dict[str, PackageFile], ledger_by_name: JsonObject
) -> list[JsonObject]:
    index_files: list[JsonObject] = []
    for seq, name in enumerate(traversal_order, start=1):
        package_file = files[name]
        ledger_row = ledger_by_name.get(name, {})
        index_files.append(
            {
                "seq": seq,
                "file_name": name,
                "bytes": len(package_file.data),
                "sha256": package_file.sha256,
                "chars": len(package_file.text),
                "artifact_class": ledger_row.get("artifact_class"),
                "authority_scope": ledger_row.get("authority_scope"),
                "default_read_next_file": ledger_row.get("default_read_next_file"),
            }
        )
    return index_files


def _required_package_files(files: dict[str, PackageFile]) -> list[str]:
    return [
        name for name in [README_NAME, MANIFEST_NAME, LEDGER_NAME, MERKLE_NAME] if name not in files
    ]


def _package_integrity(files: dict[str, PackageFile]) -> PackageIntegrity:
    manifest = _parse_manifest(files[MANIFEST_NAME].text)
    ledger_rows = _parse_ledger(files[LEDGER_NAME].text)
    computed_root, leaf_names = _compute_merkle_root(files)
    readme_order = _parse_readme_order(files[README_NAME].text)
    return PackageIntegrity(
        manifest=manifest,
        manifest_mismatches=_manifest_mismatches(files, manifest),
        ledger_rows=ledger_rows,
        ledger=_verify_ledger(ledger_rows, manifest),
        declared_root=_parse_merkle_root(files[MERKLE_NAME].text),
        computed_root=computed_root,
        leaf_names=leaf_names,
        readme_order=readme_order,
        traversal_order=_build_traversal_order(readme_order, ledger_rows, list(files.keys())),
    )


def _integrity_manifest_block(integrity: PackageIntegrity) -> JsonObject:
    return {
        "ok": not integrity.manifest_mismatches,
        "count": len(integrity.manifest),
        "mismatches": integrity.manifest_mismatches,
    }


def _integrity_ledger_block(integrity: PackageIntegrity) -> JsonObject:
    return {
        "ok": integrity.ledger["ok"],
        "count": len(integrity.ledger_rows),
        "mismatches": integrity.ledger["mismatches"],
        "last_entry_sha256": integrity.ledger["last_entry_sha256"],
    }


def _integrity_merkle_block(integrity: PackageIntegrity) -> JsonObject:
    return {
        "ok": integrity.declared_root == integrity.computed_root,
        "declared_root": integrity.declared_root,
        "computed_root": integrity.computed_root,
        "leaf_count": len(integrity.leaf_names),
        "leaf_names": integrity.leaf_names,
    }


def _inspection_verified(missing: list[str], integrity: PackageIntegrity) -> bool:
    return (
        not missing
        and not integrity.manifest_mismatches
        and integrity.ledger["ok"]
        and integrity.declared_root == integrity.computed_root
    )


def _inspection_response(
    source: PackageSource,
    files: dict[str, PackageFile],
    missing: list[str],
    integrity: PackageIntegrity,
) -> JsonObject:
    index_files = _package_index_files(
        integrity.traversal_order, files, integrity.ledger["by_name"]
    )
    return {
        **source.archive_meta(),
        "required_files_present": not missing,
        "required_files_missing": missing,
        "package_names": sorted(files.keys()),
        "manifest": _integrity_manifest_block(integrity),
        "ledger": _integrity_ledger_block(integrity),
        "merkle": _integrity_merkle_block(integrity),
        "readme_order": integrity.readme_order,
        "traversal_order": integrity.traversal_order,
        "files": index_files,
        "verified": _inspection_verified(missing, integrity),
    }


def inspect_package(source_path: str | Path) -> JsonObject:
    source = PackageSource(Path(source_path))
    files = {name: source.file(name) for name in source.names()}
    missing = _required_package_files(files)
    if missing:
        raise SopError(
            "SOP_PACKAGE_INCOMPLETE",
            "required package files are missing",
            extra={"missing": missing},
        )
    return _inspection_response(source, files, missing, _package_integrity(files))


def _registration_meta_state(
    project_id: str, cid: str, spec: RegisterPackageSpec, inspection: JsonObject
) -> tuple[JsonObject, JsonObject]:
    registered_at = utc_now()
    meta = {
        "project_id": project_id,
        "corpus_id": cid,
        "registered_at": registered_at,
        "chunk_chars": max(1000, min(int(spec.chunk_chars), 32000)),
        **inspection,
    }
    state = {
        "project_id": project_id,
        "corpus_id": cid,
        "registered_at": registered_at,
        "verified": inspection["verified"],
        "current_file_index": 0,
        "current_chunk_index": 0,
        "awaiting_file_completion": False,
        "issued_chunk": None,
        "completed_files": {},
        "acked_chunks": {},
        "completed_at": None,
        "last_action_at": registered_at,
    }
    return meta, state


def _registration_response(
    project_id: str, cid: str, inspection: JsonObject, meta: JsonObject
) -> JsonObject:
    return {
        "project_id": project_id,
        "corpus_id": cid,
        "verified": inspection["verified"],
        "source_kind": inspection["source_kind"],
        "source_path": inspection["source_path"],
        "file_count": len(inspection["files"]),
        "chunk_chars": meta["chunk_chars"],
        "traversal_order": inspection["traversal_order"],
        "integrity": {
            "manifest_ok": inspection["manifest"]["ok"],
            "ledger_ok": inspection["ledger"]["ok"],
            "merkle_ok": inspection["merkle"]["ok"],
        },
    }


def register_package(spec: RegisterPackageSpec) -> JsonObject:
    project_id = validate_project_id(spec.project_id)
    source_path = resolve_mount_spec(
        spec.source_path_spec, default_root=get_project_root(project_id), allow_absolute=True
    )
    inspection = inspect_package(source_path)
    cid = _sanitize_corpus_id(spec.corpus_id or Path(source_path).stem)
    with _corpus_lock(project_id, cid):
        if _meta_path(project_id, cid).exists() and not spec.reset:
            raise SopError("SOP_CORPUS_EXISTS", f"corpus_id already exists: {cid}")
        meta, state = _registration_meta_state(project_id, cid, spec, inspection)
        _save_json(_meta_path(project_id, cid), meta)
        _save_json(_state_path(project_id, cid), state)
    return _registration_response(project_id, cid, inspection, meta)


def _load_meta_state(project_id: str, corpus_id: str) -> tuple[JsonObject, JsonObject]:
    meta = _load_json(_meta_path(project_id, corpus_id), None)
    state = _load_json(_state_path(project_id, corpus_id), None)
    if not isinstance(meta, dict) or not isinstance(state, dict):
        raise SopError("SOP_CORPUS_NOT_FOUND", f"corpus not registered: {corpus_id}")
    return meta, state


def _source_from_meta(meta: JsonObject) -> PackageSource:
    return PackageSource(Path(meta["source_path"]))


def _current_file(meta: JsonObject, state: JsonObject) -> JsonObject | None:
    idx = int(state.get("current_file_index", 0))
    files = meta.get("files") or []
    if idx < 0 or idx >= len(files):
        return None
    return files[idx]


def ingestion_status(project_id: str, corpus_id: str) -> JsonObject:
    meta, state = _load_meta_state(project_id, corpus_id)
    current = _current_file(meta, state)
    completed_count = len(state.get("completed_files") or {})
    total = len(meta.get("files") or [])
    return {
        "project_id": project_id,
        "corpus_id": corpus_id,
        "verified": bool(state.get("verified", False)),
        "source_path": meta.get("source_path"),
        "chunk_chars": meta.get("chunk_chars"),
        "completed_files": completed_count,
        "total_files": total,
        "all_files_complete": completed_count == total and total > 0,
        "awaiting_file_completion": bool(state.get("awaiting_file_completion", False)),
        "current_file": current,
        "issued_chunk": state.get("issued_chunk"),
        "completed_at": state.get("completed_at"),
        "last_action_at": state.get("last_action_at"),
    }


def _mark_corpus_complete(project_id: str, corpus_id: str, state: JsonObject) -> JsonObject:
    if not state.get("completed_at"):
        state["completed_at"] = utc_now()
        _save_json(_state_path(project_id, corpus_id), state)
    return {
        "project_id": project_id,
        "corpus_id": corpus_id,
        "done": True,
        "completed_at": state.get("completed_at"),
    }


def _raise_file_receipt_required(request: FileReceiptRequest) -> None:
    request.state["awaiting_file_completion"] = True
    request.state["last_action_at"] = utc_now()
    _save_json(_state_path(request.project_id, request.corpus_id), request.state)
    raise SopError(
        "SOP_FILE_RECEIPT_REQUIRED",
        request.message,
        extra={"file_name": request.current["file_name"]},
    )


def _issued_chunk_state(spec: ChunkIssueSpec) -> JsonObject:
    return {
        "file_name": spec.current["file_name"],
        "chunk_index": spec.chunk_index,
        "total_chunks": spec.total_chunks,
        "char_start": spec.start,
        "char_end": spec.end,
        "content_sha256": spec.chunk_sha,
        "ack_token": spec.ack_token,
        "issued_at": utc_now(),
    }


def _chunk_response(spec: ChunkResponseSpec) -> JsonObject:
    current = spec.chunk.current
    return {
        "project_id": spec.project_id,
        "corpus_id": spec.corpus_id,
        "done": False,
        "file_name": current["file_name"],
        "file_seq": current["seq"],
        "file_sha256": current["sha256"],
        "artifact_class": current.get("artifact_class"),
        "authority_scope": current.get("authority_scope"),
        "default_read_next_file": current.get("default_read_next_file"),
        "chunk_index": spec.chunk.chunk_index,
        "total_chunks": spec.chunk.total_chunks,
        "char_start": spec.chunk.start,
        "char_end": spec.chunk.end,
        "content_sha256": spec.chunk.chunk_sha,
        "ack_token": spec.chunk.ack_token,
        "requires_file_receipt_after_ack": spec.chunk.chunk_index == (spec.chunk.total_chunks - 1),
        "content": spec.chunk.chunk_text,
    }


def _current_source_file(meta: JsonObject, current: JsonObject) -> PackageFile:
    package_file = _source_from_meta(meta).file(current["file_name"])
    expected = str(current.get("sha256") or "")
    actual = package_file.sha256
    if expected and actual != expected:
        raise SopError(
            "SOP_SOURCE_CHANGED",
            "registered package source changed after integrity verification",
            extra={
                "file_name": current.get("file_name"),
                "expected_sha256": expected,
                "actual_sha256": actual,
            },
        )
    return package_file


def _issue_next_chunk(meta: JsonObject, state: JsonObject, current: JsonObject) -> ChunkIssueSpec:
    text = _current_source_file(meta, current).text
    chunk_chars = int(meta.get("chunk_chars", 6000))
    total_chunks = max(1, math.ceil(len(text) / chunk_chars))
    chunk_index = int(state.get("current_chunk_index", 0))
    if chunk_index >= total_chunks:
        raise SopError(
            "SOP_FILE_RECEIPT_REQUIRED",
            "all chunks already delivered for current file; complete the file receipt",
            extra={"file_name": current["file_name"]},
        )
    start = chunk_index * chunk_chars
    end = min(len(text), start + chunk_chars)
    chunk_text = text[start:end]
    return ChunkIssueSpec(
        current,
        chunk_index,
        total_chunks,
        start,
        end,
        sha256_bytes(chunk_text.encode("utf-8")),
        f"ack-{uuid.uuid4().hex[:16]}",
        chunk_text,
    )


def _store_issued_chunk(
    project_id: str, corpus_id: str, state: JsonObject, chunk_spec: ChunkIssueSpec
) -> None:
    state["issued_chunk"] = _issued_chunk_state(chunk_spec)
    state["last_action_at"] = utc_now()
    _save_json(_state_path(project_id, corpus_id), state)


def _next_chunk_locked(project_id: str, corpus_id: str) -> JsonObject:
    meta, state = _load_meta_state(project_id, corpus_id)
    current = _current_file(meta, state)
    if current is None:
        return _mark_corpus_complete(project_id, corpus_id, state)
    issued = state.get("issued_chunk")
    if isinstance(issued, dict) and issued:
        if str(issued.get("file_name") or "") != str(current.get("file_name") or ""):
            raise SopError(
                "SOP_STATE_INVALID",
                "issued chunk file does not match current file cursor",
            )
        text = _current_source_file(meta, current).text
        start = int(issued.get("char_start", 0))
        end = int(issued.get("char_end", start))
        replay = ChunkIssueSpec(
            current=current,
            chunk_index=int(issued.get("chunk_index", 0)),
            total_chunks=int(issued.get("total_chunks", 1)),
            start=start,
            end=end,
            chunk_sha=str(issued.get("content_sha256") or ""),
            ack_token=str(issued.get("ack_token") or ""),
            chunk_text=text[start:end],
        )
        return {
            **_chunk_response(ChunkResponseSpec(project_id, corpus_id, replay)),
            "replayed": True,
        }
    if state.get("awaiting_file_completion"):
        raise SopError(
            "SOP_FILE_RECEIPT_REQUIRED",
            "current file is fully delivered; call sop.ingest.complete_file before proceeding",
            extra={"file_name": current["file_name"]},
        )
    chunk_spec = _issue_next_chunk(meta, state, current)
    _store_issued_chunk(project_id, corpus_id, state, chunk_spec)
    return _chunk_response(ChunkResponseSpec(project_id, corpus_id, chunk_spec))


def next_chunk(project_id: str, corpus_id: str) -> JsonObject:
    with _corpus_lock(project_id, corpus_id):
        return _next_chunk_locked(project_id, corpus_id)


def _ack_issued_chunk(state: JsonObject, current: JsonObject, issued: JsonObject) -> None:
    acked = state.setdefault("acked_chunks", {})
    acked.setdefault(current["file_name"], []).append(
        {
            "chunk_index": issued["chunk_index"],
            "content_sha256": issued["content_sha256"],
            "acked_at": utc_now(),
        }
    )
    state["current_chunk_index"] = int(issued["chunk_index"]) + 1
    state["issued_chunk"] = None
    state["last_action_at"] = utc_now()


def _ack_response(spec: AckResponseSpec) -> JsonObject:
    return {
        "project_id": spec.project_id,
        "corpus_id": spec.corpus_id,
        "file_name": spec.current["file_name"],
        "chunk_index": spec.issued["chunk_index"],
        "acked": True,
        "awaiting_file_completion": spec.delivered_final,
        "next_action": (
            "sop.ingest.complete_file" if spec.delivered_final else "sop.ingest.next_chunk"
        ),
    }


def _ack_chunk_locked(
    project_id: str, corpus_id: str, ack_token: str, *, content_sha256: str | None = None
) -> JsonObject:
    meta, state = _load_meta_state(project_id, corpus_id)
    issued = state.get("issued_chunk") or {}
    current = _current_file(meta, state)
    if not issued or not current:
        raise SopError("SOP_NO_ISSUED_CHUNK", "no issued chunk is waiting for acknowledgment")
    if ack_token != issued.get("ack_token"):
        raise SopError("SOP_BAD_ACK_TOKEN", "ack_token does not match the currently issued chunk")
    if not content_sha256:
        raise SopError(
            "SOP_CHUNK_SHA_REQUIRED",
            "content_sha256 is required to bind acknowledgment to the issued chunk",
            extra={"expected": issued.get("content_sha256")},
        )
    if content_sha256 != issued.get("content_sha256"):
        raise SopError(
            "SOP_BAD_CHUNK_SHA",
            "content_sha256 does not match the issued chunk",
            extra={"expected": issued.get("content_sha256"), "actual": content_sha256},
        )
    _ack_issued_chunk(state, current, issued)
    chunk_count = max(1, math.ceil(int(current["chars"]) / int(meta.get("chunk_chars", 6000))))
    delivered_final = state["current_chunk_index"] >= chunk_count
    state["awaiting_file_completion"] = bool(delivered_final)
    _save_json(_state_path(project_id, corpus_id), state)
    return _ack_response(AckResponseSpec(project_id, corpus_id, current, issued, delivered_final))


def ack_chunk(
    project_id: str, corpus_id: str, ack_token: str, *, content_sha256: str | None = None
) -> JsonObject:
    with _corpus_lock(project_id, corpus_id):
        return _ack_chunk_locked(
            project_id, corpus_id, ack_token, content_sha256=content_sha256
        )


def _completion_mismatches(current: JsonObject, receipt: JsonObject) -> list[JsonObject]:
    required = {
        "file_name": current["file_name"],
        "file_sha256": current["sha256"],
        "artifact_class": current.get("artifact_class"),
        "default_read_next_file": current.get("default_read_next_file"),
    }
    return [
        {"field": key, "expected": expected, "actual": receipt.get(key)}
        for key, expected in required.items()
        if expected is not None and receipt.get(key) != expected
    ]


def _mark_file_complete(
    meta: JsonObject, state: JsonObject, current: JsonObject, receipt: JsonObject
) -> None:
    state.setdefault("completed_files", {})[current["file_name"]] = {
        "completed_at": utc_now(),
        "receipt": receipt,
    }
    state["current_file_index"] = int(state.get("current_file_index", 0)) + 1
    state["current_chunk_index"] = 0
    state["awaiting_file_completion"] = False
    state["issued_chunk"] = None
    state["last_action_at"] = utc_now()
    if state["current_file_index"] >= len(meta.get("files") or []):
        state["completed_at"] = utc_now()


def _completion_response(spec: CompletionResponseSpec) -> JsonObject:
    return {
        "project_id": spec.project_id,
        "corpus_id": spec.corpus_id,
        "file_name": spec.current["file_name"],
        "completed": True,
        "all_files_complete": bool(spec.state.get("completed_at")),
        "completed_at": spec.state.get("completed_at"),
        "next_file": _current_file(spec.meta, spec.state),
    }


def _complete_file_locked(project_id: str, corpus_id: str, receipt: JsonObject) -> JsonObject:
    meta, state = _load_meta_state(project_id, corpus_id)
    current = _current_file(meta, state)
    if not current:
        raise SopError("SOP_ALREADY_COMPLETE", "ingestion is already complete")
    if not state.get("awaiting_file_completion"):
        raise SopError("SOP_FILE_NOT_READY", "current file is not yet ready for completion receipt")
    mismatches = _completion_mismatches(current, receipt)
    if mismatches:
        raise SopError(
            "SOP_BAD_FILE_RECEIPT",
            "file completion receipt does not match package metadata",
            extra={"mismatches": mismatches},
        )
    _mark_file_complete(meta, state, current, receipt)
    _save_json(_state_path(project_id, corpus_id), state)
    return _completion_response(CompletionResponseSpec(project_id, corpus_id, meta, state, current))


def complete_file(project_id: str, corpus_id: str, receipt: JsonObject) -> JsonObject:
    with _corpus_lock(project_id, corpus_id):
        return _complete_file_locked(project_id, corpus_id, receipt)


def _source_currentness(meta: JsonObject) -> JsonObject:
    try:
        inspection = inspect_package(Path(str(meta.get("source_path") or "")))
    except SopError as exc:
        return {
            "ok": False,
            "error_code": exc.code,
            "error": exc.message,
            "details": exc.extra,
        }
    registered_files = {
        str(row.get("file_name")): str(row.get("sha256"))
        for row in (meta.get("files") or [])
    }
    current_files = {
        str(row.get("file_name")): str(row.get("sha256"))
        for row in (inspection.get("files") or [])
    }
    same_files = registered_files == current_files
    archive_match = True
    if meta.get("archive_sha256") is not None:
        archive_match = meta.get("archive_sha256") == inspection.get("archive_sha256")
    return {
        "ok": bool(inspection.get("verified")) and same_files and archive_match,
        "inspection_verified": bool(inspection.get("verified")),
        "registered_file_count": len(registered_files),
        "current_file_count": len(current_files),
        "file_identity_match": same_files,
        "archive_identity_match": archive_match,
        "current_archive_sha256": inspection.get("archive_sha256"),
    }


def guard_check(project_id: str, corpus_id: str) -> JsonObject:
    with _corpus_lock(project_id, corpus_id):
        meta, state = _load_meta_state(project_id, corpus_id)
        files = meta.get("files") or []
        completed = set((state.get("completed_files") or {}).keys())
        missing = [row["file_name"] for row in files if row["file_name"] not in completed]
        source_current = _source_currentness(meta)
        proceed_allowed = (
            bool(state.get("verified"))
            and bool(source_current.get("ok"))
            and not missing
            and not state.get("awaiting_file_completion")
            and bool(state.get("completed_at"))
        )
        return {
            "project_id": project_id,
            "corpus_id": corpus_id,
            "registered": True,
            "integrity_verified_at_registration": bool(state.get("verified")),
            "source_current": source_current,
            "ingestion_started": bool(state.get("acked_chunks") or state.get("issued_chunk") or completed),
            "ingestion_complete": bool(state.get("completed_at")) and not missing,
            "proceed_allowed": proceed_allowed,
            "missing_files": missing,
            "awaiting_file_completion": bool(state.get("awaiting_file_completion")),
            "completed_files": len(completed),
            "total_files": len(files),
            "completed_at": state.get("completed_at"),
            "reason": None if proceed_allowed else "registration/integrity/currentness/ingestion gate not fully satisfied",
        }


def _reset_ingestion_locked(project_id: str, corpus_id: str) -> JsonObject:
    meta, state = _load_meta_state(project_id, corpus_id)
    state.update(
        {
            "current_file_index": 0,
            "current_chunk_index": 0,
            "awaiting_file_completion": False,
            "issued_chunk": None,
            "completed_files": {},
            "acked_chunks": {},
            "completed_at": None,
            "last_action_at": utc_now(),
        }
    )
    _save_json(_state_path(project_id, corpus_id), state)
    return {
        "project_id": project_id,
        "corpus_id": corpus_id,
        "reset": True,
        "verified": bool(meta.get("verified", False)),
        "file_count": len(meta.get("files") or []),
    }


def reset_ingestion(project_id: str, corpus_id: str) -> JsonObject:
    with _corpus_lock(project_id, corpus_id):
        return _reset_ingestion_locked(project_id, corpus_id)
