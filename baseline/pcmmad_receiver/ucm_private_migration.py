"""Private UCS/UCM v1 release verification and lossless server migration.

This is an administrative migration helper, not a model-facing native capability.
It deliberately emits structural receipts only: counts, hashes, currentness and
qualification state. Private record values are never included in its report.

Migration law:

* sealed donor archive + original donor event ledger remain immutable evidence;
* normalized private records are validated against the neutral UCS v1 contract;
* server-native events receive new Runtime hashes/sequence lineage;
* target profile must be empty, so migration never overwrites existing user state;
* one final snapshot fold is built from the new authoritative server ledger;
* fresh-instance ingress must pass before migration is called complete.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import stat
import tempfile
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from . import ucm_v1_runtime as ucm
from . import user_continuity_store as backend

JsonObject = dict[str, Any]

PRIVATE_RELEASE_SCHEMA = "PRIVATE_USER_CONTINUITY_INSTANCE_V1_0_2026-09-09"
EXPECTED_PRIVATE_SHA256 = "997d09e0691526cc5924e22fb5b5557a0de91b73c474d2261c093c4b4eb1a731"
EXPECTED_PRIVATE_BYTES = 388252
DONOR_SYSTEM_DESCRIPTOR_SHA256 = "489684104c9eadd4575689ae38d8686c1034c941e824fe6c0845583e7584c1a8"
DONOR_INGRESS_CONTRACT_SHA256 = "380a7265b076ea5833505a079c3cf61e1e4e3d3ab9fa2a04729d84f2e164b5b7"


class UcmMigrationError(RuntimeError):
    def __init__(self, error_code: str, message: str, *, status: int = 400, **extra: Any) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status = int(status)
        self.extra = extra


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _safe_zip_member(name: str) -> bool:
    raw = name.replace("\\", "/")
    path = PurePosixPath(raw)
    return bool(raw) and not path.is_absolute() and ".." not in path.parts and not raw.startswith("/")


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)


def _load_json(data: bytes, label: str) -> Any:
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise UcmMigrationError("UCM_PRIVATE_RELEASE_INVALID", f"invalid JSON: {label}") from exc


def _root_prefix(names: Sequence[str]) -> str:
    roots = {name.replace("\\", "/").split("/", 1)[0] for name in names if name and not name.endswith("/")}
    if len(roots) != 1:
        raise UcmMigrationError("UCM_PRIVATE_RELEASE_INVALID", "private release must contain exactly one top-level root")
    root = next(iter(roots))
    if root != PRIVATE_RELEASE_SCHEMA:
        raise UcmMigrationError("UCM_PRIVATE_RELEASE_INVALID", f"unexpected private release root: {root}")
    return root + "/"


def _verify_manifest(zf: zipfile.ZipFile, prefix: str) -> JsonObject:
    manifest_name = prefix + "MANIFEST_SHA256.json"
    try:
        manifest = _load_json(zf.read(manifest_name), "MANIFEST_SHA256.json")
    except KeyError as exc:
        raise UcmMigrationError("UCM_PRIVATE_MANIFEST_INVALID", "MANIFEST_SHA256.json missing") from exc
    if not isinstance(manifest, Mapping) or not isinstance(manifest.get("members"), list):
        raise UcmMigrationError("UCM_PRIVATE_MANIFEST_INVALID", "manifest shape invalid")
    rows = manifest["members"]
    expected_count = int(manifest.get("member_count_excluding_manifest") or -1)
    if expected_count != len(rows):
        raise UcmMigrationError("UCM_PRIVATE_MANIFEST_INVALID", "manifest member count mismatch")
    actual_files = {
        name[len(prefix):]
        for name in zf.namelist()
        if name.startswith(prefix) and not name.endswith("/") and name != manifest_name
    }
    expected_files: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise UcmMigrationError("UCM_PRIVATE_MANIFEST_INVALID", "manifest row invalid")
        rel = str(row.get("path") or "")
        if not _safe_zip_member(rel):
            raise UcmMigrationError("UCM_PRIVATE_MANIFEST_INVALID", f"unsafe manifest path: {rel}")
        if rel in expected_files:
            raise UcmMigrationError("UCM_PRIVATE_MANIFEST_INVALID", f"duplicate manifest path: {rel}")
        expected_files.add(rel)
        try:
            data = zf.read(prefix + rel)
        except KeyError as exc:
            raise UcmMigrationError("UCM_PRIVATE_MANIFEST_INVALID", f"manifest member missing: {rel}") from exc
        if len(data) != int(row.get("bytes") or -1):
            raise UcmMigrationError("UCM_PRIVATE_MANIFEST_INVALID", f"manifest byte mismatch: {rel}")
        if _sha256_bytes(data) != str(row.get("sha256") or ""):
            raise UcmMigrationError("UCM_PRIVATE_MANIFEST_INVALID", f"manifest SHA mismatch: {rel}")
    if actual_files != expected_files:
        raise UcmMigrationError(
            "UCM_PRIVATE_MANIFEST_INVALID",
            "archive contents differ from exact manifest",
            missing=sorted(expected_files - actual_files),
            extra=sorted(actual_files - expected_files),
        )
    return {"member_count": len(rows), "manifest_sha256": _sha256_bytes(zf.read(manifest_name))}


def _verify_donor_events(events: Sequence[Mapping[str, Any]]) -> JsonObject:
    expected_seq = 1
    previous = None
    for event in events:
        if int(event.get("seq") or 0) != expected_seq:
            raise UcmMigrationError("UCM_PRIVATE_EVENT_CHAIN_INVALID", f"event seq mismatch at {expected_seq}")
        if event.get("prev_hash") != previous:
            raise UcmMigrationError("UCM_PRIVATE_EVENT_CHAIN_INVALID", f"event prev_hash mismatch at {expected_seq}")
        body = dict(event)
        observed = str(body.pop("event_hash", ""))
        expected = _sha256_bytes(_canonical_json(body))
        if observed != expected:
            raise UcmMigrationError("UCM_PRIVATE_EVENT_CHAIN_INVALID", f"event hash mismatch at {expected_seq}")
        previous = observed
        expected_seq += 1
    return {"event_count": len(events), "ledger_head_seq": len(events), "ledger_head_hash": previous}


def _records_from_private(zf: zipfile.ZipFile, prefix: str) -> JsonObject:
    facts_raw = _load_json(zf.read(prefix + "normalized/facts.json"), "normalized/facts.json")
    if not isinstance(facts_raw, Mapping):
        raise UcmMigrationError("UCM_PRIVATE_NORMALIZATION_INVALID", "normalized facts must be an object keyed by fact_key")
    facts: list[JsonObject] = []
    for key, raw in facts_raw.items():
        try:
            record = ucm.validate_fact(raw)
        except ucm.UcmError as exc:
            raise UcmMigrationError("UCM_PRIVATE_NORMALIZATION_INVALID", f"invalid normalized fact: {key}", cause=exc.error_code) from exc
        if record["fact_key"] != key:
            raise UcmMigrationError("UCM_PRIVATE_NORMALIZATION_INVALID", f"fact dictionary key mismatch: {key}")
        facts.append(record)

    def list_records(rel: str, validator, label: str) -> list[JsonObject]:
        raw = _load_json(zf.read(prefix + rel), rel)
        if not isinstance(raw, list):
            raise UcmMigrationError("UCM_PRIVATE_NORMALIZATION_INVALID", f"{label} must be a list")
        out = []
        for idx, item in enumerate(raw):
            try:
                out.append(validator(item))
            except ucm.UcmError as exc:
                raise UcmMigrationError("UCM_PRIVATE_NORMALIZATION_INVALID", f"invalid {label} row {idx}", cause=exc.error_code) from exc
        return out

    identities = list_records("normalized/identities.json", ucm._validate_identity, "identity")
    referents = list_records("normalized/referents.json", ucm._validate_referent, "referent")
    decisions = list_records("normalized/decisions.json", ucm._validate_decision, "decision")
    assertions = list_records("normalized/source_assertions.json", ucm._validate_source_assertion, "source assertion")
    source_manifest_raw = _load_json(zf.read(prefix + "sources/SOURCE_MANIFEST.json"), "sources/SOURCE_MANIFEST.json")
    if not isinstance(source_manifest_raw, list):
        raise UcmMigrationError("UCM_PRIVATE_NORMALIZATION_INVALID", "source manifest must be a list")
    source_manifest = []
    for idx, item in enumerate(source_manifest_raw):
        try:
            source_manifest.append(ucm._validate_source_manifest(item))
        except ucm.UcmError as exc:
            raise UcmMigrationError("UCM_PRIVATE_NORMALIZATION_INVALID", f"invalid source manifest row {idx}", cause=exc.error_code) from exc
    collaboration_raw = _load_json(zf.read(prefix + "normalized/collaboration_contract.json"), "normalized/collaboration_contract.json")
    control_raw = _load_json(zf.read(prefix + "control/CONTROL_STATE.json"), "control/CONTROL_STATE.json")
    candidates_raw = _load_json(zf.read(prefix + "candidates/memory_candidates.json"), "candidates/memory_candidates.json")
    try:
        collaboration = ucm._validate_collaboration(collaboration_raw)
        control = ucm._validate_control(control_raw)
        candidates = [ucm._validate_candidate(x) for x in candidates_raw]
    except ucm.UcmError as exc:
        raise UcmMigrationError("UCM_PRIVATE_NORMALIZATION_INVALID", "invalid collaboration/control/candidate normalized state", cause=exc.error_code) from exc
    return {
        "facts": facts,
        "identities": identities,
        "referents": referents,
        "decisions": decisions,
        "source_assertions": assertions,
        "source_manifest": source_manifest,
        "collaboration": collaboration,
        "control": control,
        "candidates": candidates,
    }


def _verify_sources(zf: zipfile.ZipFile, prefix: str, source_manifest: Sequence[Mapping[str, Any]]) -> JsonObject:
    verified = []
    for source in source_manifest:
        blob_path = str(source.get("blob_path") or "")
        if not _safe_zip_member(blob_path):
            raise UcmMigrationError("UCM_PRIVATE_SOURCE_INVALID", f"unsafe source blob path: {blob_path}")
        data = zf.read(prefix + blob_path)
        if len(data) != int(source["bytes"]) or _sha256_bytes(data) != source["sha256"]:
            raise UcmMigrationError("UCM_PRIVATE_SOURCE_INVALID", f"source blob mismatch: {source['artifact']}")
        original_path = prefix + "sources/" + str(source["artifact"])
        original = zf.read(original_path)
        if original != data:
            raise UcmMigrationError("UCM_PRIVATE_SOURCE_INVALID", f"original source != content-addressed blob: {source['artifact']}")
        verified.append({"artifact": str(source["artifact"]), "bytes": len(data), "sha256": str(source["sha256"])})
    return {"source_count": len(verified), "sources": verified}


def _verify_package_bindings(zf: zipfile.ZipFile, prefix: str, records: Mapping[str, Any], event_chain: Mapping[str, Any]) -> JsonObject:
    system_ref = _load_json(zf.read(prefix + "SYSTEM_REF.json"), "SYSTEM_REF.json")
    if system_ref.get("system_version") != ucm.SYSTEM_VERSION:
        raise UcmMigrationError("UCM_PRIVATE_SYSTEM_MISMATCH", "private system version != server UCS version")
    if system_ref.get("system_descriptor_sha256") != DONOR_SYSTEM_DESCRIPTOR_SHA256 or system_ref.get("ingress_contract_sha256") != DONOR_INGRESS_CONTRACT_SHA256:
        raise UcmMigrationError("UCM_PRIVATE_SYSTEM_MISMATCH", "private release references a different neutral UCS contract")
    if set(system_ref.get("required_authority_traits") or []) != set(ucm.AUTHORITY_TRAITS):
        raise UcmMigrationError("AUTHORITY_FIREWALL", "private release authority traits differ from neutral UCS contract", status=409)

    store_head = _load_json(zf.read(prefix + "USER_STORE_HEAD.json"), "USER_STORE_HEAD.json")
    if int(store_head.get("ledger_head_seq") or 0) != int(event_chain["ledger_head_seq"]) or store_head.get("ledger_head_hash") != event_chain["ledger_head_hash"]:
        raise UcmMigrationError("UCM_PRIVATE_EVENT_CHAIN_INVALID", "USER_STORE_HEAD does not bind donor ledger head")
    if int(store_head.get("snapshot_from_seq") or 0) != int(event_chain["ledger_head_seq"]):
        raise UcmMigrationError("UCM_PRIVATE_SNAPSHOT_STALE", "private snapshot does not bind donor ledger head")

    binding = _load_json(zf.read(prefix + "INGRESS_BINDING.json"), "INGRESS_BINDING.json")
    if int(binding.get("core_budget_bytes") or 0) != ucm.CORE_BUDGET_BYTES or int(binding.get("min_headroom_bytes") or 0) != ucm.MIN_HEADROOM_BYTES:
        raise UcmMigrationError("UCM_PRIVATE_SYSTEM_MISMATCH", "private ingress budget differs from neutral UCS v1")
    present = set((binding.get("surfaces") or {}).keys())
    if present != set(ucm.REQUIRED_INGRESS_SURFACES):
        raise UcmMigrationError("USER_CONTINUITY_INCOMPLETE", "private ingress binding surface set differs from UCS v1", status=409, missing=sorted(set(ucm.REQUIRED_INGRESS_SURFACES)-present), extra=sorted(present-set(ucm.REQUIRED_INGRESS_SURFACES)))

    digest_map = {
        "CORE_SNAPSHOT": ("core_snapshot_sha256", "snapshot/core.json"),
        "IDENTITY_INDEX": ("identity_index_sha256", "snapshot/identity_index.json"),
        "COLLABORATION_CONTRACT": ("collaboration_contract_sha256", "snapshot/collaboration_contract.json"),
        "REFERENT_INDEX": ("referent_index_sha256", "snapshot/referent_index.json"),
        "DECISION_INDEX": ("decision_index_sha256", "snapshot/decision_index.json"),
        "CONTROL_STATE": ("control_state_sha256", "control/CONTROL_STATE.json"),
        "VERIFICATION_DEBT": ("verification_debt_sha256", "snapshot/verification_debt.json"),
        "CANDIDATE_QUEUE_HEAD": ("candidate_queue_head_sha256", "candidates/HEAD.json"),
    }
    for surface, (head_field, rel) in digest_map.items():
        observed = _sha256_bytes(zf.read(prefix + rel))
        if observed != store_head.get(head_field):
            raise UcmMigrationError("UCM_PRIVATE_BINDING_INVALID", f"{surface} digest differs from USER_STORE_HEAD")
    if _sha256_bytes(zf.read(prefix + "sources/SOURCE_MANIFEST.json")) != store_head.get("source_manifest_sha256"):
        raise UcmMigrationError("UCM_PRIVATE_BINDING_INVALID", "source manifest digest differs from USER_STORE_HEAD")

    expectations = _load_json(zf.read(prefix + "normalized/MIGRATION_EXPECTATIONS.json"), "normalized/MIGRATION_EXPECTATIONS.json")
    facts = {x["fact_key"]: x for x in records["facts"]}
    identities = {x["identity_key"]: x for x in records["identities"]}
    referents = {x["referent_key"]: x for x in records["referents"]}
    for field, mapping in (
        ("normal_address_identity_key", identities),
        ("current_employment_fact_key", facts),
        ("historical_employment_fact_key", facts),
        ("active_pcmmad_referent_key", referents),
        ("superseded_pcmmad_referent_key", referents),
    ):
        key = str(expectations.get(field) or "")
        if key not in mapping:
            raise UcmMigrationError("UCM_PRIVATE_MIGRATION_EXPECTATION_FAILED", f"missing expected normalized record: {field}")
    resolved = ucm.resolve_identity_from_records(records["identities"], use_for="NORMAL_ADDRESS")
    if resolved is None or resolved["identity_key"] != expectations["normal_address_identity_key"]:
        raise UcmMigrationError("UCM_PRIVATE_MIGRATION_EXPECTATION_FAILED", "normal-address identity resolution differs from release expectation")
    active_ref = referents[expectations["active_pcmmad_referent_key"]]
    old_ref = referents[expectations["superseded_pcmmad_referent_key"]]
    if active_ref["status"] not in {"ACTIVE", "CONTEXTUAL"} or old_ref["status"] != "SUPERSEDED":
        raise UcmMigrationError("UCM_PRIVATE_MIGRATION_EXPECTATION_FAILED", "PCMMAD referent currentness differs from release expectation")
    forbidden = set(expectations.get("forbidden_core_hydration_groups") or [])
    core_snapshot = _load_json(zf.read(prefix + "snapshot/core.json"), "snapshot/core.json")
    core_fact_keys = {str(item.get("fact_key")) for item in (core_snapshot.get("facts") or []) if isinstance(item, Mapping)}
    # Stronger semantic check uses actual normalized fact groups; string search is not relied on.
    for item in records["facts"]:
        if item["fact_key"] in core_fact_keys and forbidden.intersection(set(item["hydration_groups"])):
            raise UcmMigrationError("UCM_PRIVATE_MIGRATION_EXPECTATION_FAILED", "forbidden lazy hydration group leaked into core")
    for item in records["facts"]:
        if item["export_class"] in set(expectations.get("project_or_deployment_exports") or []):
            if item["verification"]["requirement"] != "REQUIRED":
                raise UcmMigrationError("UCM_PRIVATE_MIGRATION_EXPECTATION_FAILED", "project/deployment fact lacks REQUIRED verification")
    present_sources = {x["artifact"] for x in records["source_manifest"]}
    required_sources = set(expectations.get("source_artifacts_required") or [])
    if not required_sources.issubset(present_sources):
        raise UcmMigrationError("UCM_PRIVATE_MIGRATION_EXPECTATION_FAILED", "required migration source artifact missing")

    ingress_qualification = _load_json(zf.read(prefix + "receipts/INGRESS_QUALIFICATION.json"), "receipts/INGRESS_QUALIFICATION.json")
    if (ingress_qualification.get("result") or {}).get("status") != "PASS":
        raise UcmMigrationError("USER_CONTINUITY_INCOMPLETE", "private release ingress qualification is not PASS", status=409)
    if int(ingress_qualification.get("actual_headroom_bytes") or -1) < ucm.MIN_HEADROOM_BYTES:
        raise UcmMigrationError("UCM_CORE_BUDGET_EXCEEDED", "private release lacks required ingress headroom", status=409)
    return {
        "private_user_store_id": str(store_head.get("user_store_id") or ""),
        "donor_ledger_head_seq": event_chain["ledger_head_seq"],
        "donor_ledger_head_hash": event_chain["ledger_head_hash"],
        "private_ingress_bytes": int(ingress_qualification.get("always_load_bytes") or 0),
        "private_ingress_headroom_bytes": int(ingress_qualification.get("actual_headroom_bytes") or 0),
        "migration_expectations_sha256": _sha256_bytes(zf.read(prefix + "normalized/MIGRATION_EXPECTATIONS.json")),
    }


def verify_private_release(archive_path: Path, detached_receipt_path: Path | None = None) -> JsonObject:
    archive_path = archive_path.resolve()
    if not archive_path.is_file():
        raise UcmMigrationError("UCM_PRIVATE_RELEASE_NOT_FOUND", f"private release not found: {archive_path}", status=404)
    archive_bytes = archive_path.stat().st_size
    archive_sha = _sha256_file(archive_path)
    if archive_bytes != EXPECTED_PRIVATE_BYTES or archive_sha != EXPECTED_PRIVATE_SHA256:
        raise UcmMigrationError("UCM_PRIVATE_RELEASE_IDENTITY_MISMATCH", "private release bytes/SHA do not match qualified v1.0 identity", status=409, observed_bytes=archive_bytes, observed_sha256=archive_sha)
    if detached_receipt_path is not None:
        receipt = json.loads(detached_receipt_path.read_text(encoding="utf-8"))
        archived = receipt.get("archive") or {}
        if archived.get("bytes") != archive_bytes or archived.get("sha256") != archive_sha or archived.get("crc") != "PASS":
            raise UcmMigrationError("UCM_PRIVATE_RELEASE_IDENTITY_MISMATCH", "detached release receipt does not bind supplied archive", status=409)
    with zipfile.ZipFile(archive_path, "r") as zf:
        infos = zf.infolist()
        for info in infos:
            if not _safe_zip_member(info.filename) or _is_symlink(info):
                raise UcmMigrationError("UCM_PRIVATE_ARCHIVE_UNSAFE", f"unsafe ZIP member: {info.filename}", status=409)
        if zf.testzip() is not None:
            raise UcmMigrationError("UCM_PRIVATE_ARCHIVE_CORRUPT", "ZIP CRC failure", status=409)
        prefix = _root_prefix([info.filename for info in infos])
        manifest = _verify_manifest(zf, prefix)
        event_lines = zf.read(prefix + "events/events.jsonl").decode("utf-8").splitlines()
        events = [json.loads(line) for line in event_lines if line.strip()]
        event_chain = _verify_donor_events(events)
        records = _records_from_private(zf, prefix)
        sources = _verify_sources(zf, prefix, records["source_manifest"])
        bindings = _verify_package_bindings(zf, prefix, records, event_chain)
        import_receipt = _load_json(zf.read(prefix + "receipts/IMPORT_RECEIPT.json"), "receipts/IMPORT_RECEIPT.json")
        expected_counts = {
            "facts": int(import_receipt.get("normalized_fact_count") or -1),
            "source_assertions": int(import_receipt.get("source_assertion_count") or -1),
            "decisions": int(import_receipt.get("decision_count") or -1),
            "identities": int(import_receipt.get("identity_count") or -1),
            "referents": int(import_receipt.get("referent_count") or -1),
        }
        actual_counts = {
            "facts": len(records["facts"]),
            "source_assertions": len(records["source_assertions"]),
            "decisions": len(records["decisions"]),
            "identities": len(records["identities"]),
            "referents": len(records["referents"]),
        }
        if expected_counts != actual_counts:
            raise UcmMigrationError("UCM_PRIVATE_NORMALIZATION_INVALID", "private import receipt counts differ from normalized records", expected=expected_counts, actual=actual_counts)
        if int(import_receipt.get("ledger_event_count") or -1) != event_chain["event_count"] or import_receipt.get("ledger_head_hash") != event_chain["ledger_head_hash"]:
            raise UcmMigrationError("UCM_PRIVATE_EVENT_CHAIN_INVALID", "private import receipt does not bind donor event chain")
        return {
            "schema": "pcmmad.ucm-private-release-verification.v1",
            "status": "VERIFIED_PRIVATE_MIGRATION_SOURCE",
            "archive": {"name": archive_path.name, "bytes": archive_bytes, "sha256": archive_sha, "crc": "PASS"},
            "manifest": manifest,
            "donor_event_chain": event_chain,
            "normalized_counts": {**actual_counts, "collaboration": 1, "control": 1, "candidates": len(records["candidates"]), "source_manifest": len(records["source_manifest"])},
            "source_evidence": {"source_count": sources["source_count"], "all_originals_match_content_addressed_blobs": True},
            "bindings": bindings,
            "authority_effect": "NONE",
            "private_values_emitted": False,
            "migration_lineage_law": "DONOR_EVENT_HASH != SERVER_NATIVE_EVENT_HASH_AFTER_MIGRATION",
        }


def _native_import_records(zf: zipfile.ZipFile, prefix: str) -> list[tuple[str, JsonObject]]:
    records = _records_from_private(zf, prefix)
    ordered: list[tuple[str, JsonObject]] = []
    ordered.extend(("FACT", x) for x in records["facts"])
    ordered.extend(("IDENTITY", x) for x in records["identities"])
    ordered.extend(("REFERENT", x) for x in records["referents"])
    ordered.extend(("DECISION", x) for x in records["decisions"])
    ordered.extend(("COLLABORATION_CONTRACT", records["collaboration"]) for _ in range(1))
    ordered.extend(("CONTROL_STATE", records["control"]) for _ in range(1))
    ordered.extend(("MEMORY_CANDIDATE", x) for x in records["candidates"])
    ordered.extend(("SOURCE_MANIFEST", x) for x in records["source_manifest"])
    ordered.extend(("SOURCE_ASSERTION", x) for x in records["source_assertions"])
    return ordered


def _server_event_for_import(*, profile_id: str, state: Mapping[str, Any], event_seq: int, record_type: str, record: Mapping[str, Any], archive_sha: str) -> JsonObject:
    key = ucm._record_key(record_type, record)
    envelope = ucm._backend_envelope(
        record_type,
        record,
        {
            "actor": "server",
            "source_instance": "private_ucm_release_v1",
            "source_thread": None,
            "source_event": f"private-release:{archive_sha}",
            "evidence_independence_group": f"private-release:{archive_sha}",
            "source_artifact": PRIVATE_RELEASE_SCHEMA + ".zip",
            "source_pointer": f"normalized:{record_type}:{key}",
        },
    )
    payload = {
        "fact": envelope,
        "ucm_operation": "IMPORT_ADD",
        "ucm_record_type": record_type,
        "ucm_record_key": key,
        "import_source_archive_sha256": archive_sha,
    }
    idem = f"ucm-private-import-{event_seq}-{hashlib.sha256((record_type+'|'+key).encode()).hexdigest()[:24]}"
    fingerprint = backend._sha256_json({"operation": "UCM_IMPORT_ADD", "record_type": record_type, "record_key": key, "record_sha256": ucm._record_digest(record), "archive_sha256": archive_sha})
    body = backend._event_body(
        event_seq=event_seq,
        event_id=f"MEM-{event_seq:012d}-{uuid.uuid4().hex[:12]}",
        timestamp=backend._utc_now(),
        profile_id=profile_id,
        operation="ADD",
        provenance={"actor":"server","source_instance":"private_ucm_release_v1","source_thread":None,"source_event":f"private-release:{archive_sha}","evidence_independence_group":f"private-release:{archive_sha}"},
        payload=payload,
        previous_hash=state.get("head_hash"),
        idempotency_key=idem,
        request_fingerprint=fingerprint,
    )
    return {**body, "event_hash": backend._sha256_json(body)}


def import_private_release(archive_path: Path, *, profile_id: str, detached_receipt_path: Path | None = None) -> JsonObject:
    verification = verify_private_release(archive_path, detached_receipt_path)
    pid = backend._profile_id(profile_id)
    archive_path = archive_path.resolve()
    with backend._profile_lock(pid):
        state = backend._load_verified_state_locked(pid)
        if int(state.get("event_count") or 0) != 0 or state.get("facts"):
            raise UcmMigrationError("UCM_IMPORT_TARGET_NOT_EMPTY", "private migration requires an empty target profile", status=409)
        paths = backend._paths(pid)
        with zipfile.ZipFile(archive_path, "r") as zf:
            prefix = _root_prefix(zf.namelist())
            native_records = _native_import_records(zf, prefix)
            # Preserve sealed release and the donor event history as exact evidence.
            release_dir = paths.root / "sources" / "releases" / "sha256"
            release_dir.mkdir(parents=True, exist_ok=True)
            release_copy = release_dir / verification["archive"]["sha256"]
            if not release_copy.exists():
                shutil.copyfile(archive_path, release_copy)
            if _sha256_file(release_copy) != verification["archive"]["sha256"]:
                raise UcmMigrationError("UCM_PRIVATE_SOURCE_INVALID", "preserved private release copy failed SHA readback", status=500)
            source_root = paths.root / "sources" / "blobs" / "sha256"
            source_root.mkdir(parents=True, exist_ok=True)
            source_manifest = _records_from_private(zf, prefix)["source_manifest"]
            for source in source_manifest:
                data = zf.read(prefix + str(source["blob_path"]))
                target = source_root / source["sha256"]
                if not target.exists():
                    target.write_bytes(data)
                if _sha256_file(target) != source["sha256"]:
                    raise UcmMigrationError("UCM_PRIVATE_SOURCE_INVALID", f"server source blob readback failed: {source['artifact']}", status=500)
            donor_events_data = zf.read(prefix + "events/events.jsonl")
            donor_events_target = paths.root / "sources" / "donor_ledgers" / (verification["donor_event_chain"]["ledger_head_hash"] + ".jsonl")
            donor_events_target.parent.mkdir(parents=True, exist_ok=True)
            donor_events_target.write_bytes(donor_events_data)
            if _sha256_bytes(donor_events_data) != _sha256_file(donor_events_target):
                raise UcmMigrationError("UCM_PRIVATE_SOURCE_INVALID", "donor ledger evidence copy failed SHA readback", status=500)

        projected = copy.deepcopy(state)
        lines: list[bytes] = []
        for record_type, record in native_records:
            event = _server_event_for_import(
                profile_id=pid,
                state=projected,
                event_seq=int(projected.get("event_count") or 0) + 1,
                record_type=record_type,
                record=record,
                archive_sha=verification["archive"]["sha256"],
            )
            backend._apply_event(projected, event)
            lines.append(backend._canonical_bytes(event) + b"\n")
        ucm._preflight_canonical_core(projected)
        backend._preflight_snapshot_limits(projected)
        paths.ledger.parent.mkdir(parents=True, exist_ok=True)
        temp_ledger = paths.ledger.with_name(paths.ledger.name + ".migration.tmp")
        with temp_ledger.open("wb") as handle:
            for line in lines:
                handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
        # Verify the candidate ledger before atomic publication.
        original = paths.ledger
        backup = None
        if original.exists():
            backup = original.with_name(original.name + ".empty.bak")
            original.replace(backup)
        try:
            temp_ledger.replace(original)
            with backend._CACHE_GUARD:
                backend._STATE_CACHE.pop(pid, None)
            readback = backend.build_state(pid)
            if readback.get("head_hash") != projected.get("head_hash") or int(readback.get("event_count") or 0) != len(native_records):
                raise UcmMigrationError("UCM_IMPORT_READBACK_FAILED", "native ledger readback differs from staged migration", status=500)
            manifest = backend._materialize_locked(pid, readback, retain_snapshot_count=2)
            ingress = ucm.read_core(pid)
            if ingress.get("ingress_status") != "PASS":
                raise UcmMigrationError("USER_CONTINUITY_INCOMPLETE", "migrated profile did not satisfy fresh-instance ingress", status=409)
        except Exception:
            original.unlink(missing_ok=True)
            if backup is not None and backup.exists():
                backup.replace(original)
            with backend._CACHE_GUARD:
                backend._STATE_CACHE.pop(pid, None)
            raise
        else:
            if backup is not None:
                backup.unlink(missing_ok=True)
        return {
            "schema": "pcmmad.ucm-private-release-migration-receipt.v1",
            "status": "MIGRATED_AND_READ_BACK",
            "profile_id": pid,
            "source_archive": verification["archive"],
            "donor_event_chain": verification["donor_event_chain"],
            "server_native_event_count": int(readback["event_count"]),
            "server_native_head_hash": readback["head_hash"],
            "server_snapshot_from_seq": manifest["snapshot_from_seq"],
            "server_ingress": {
                "status": ingress["ingress_status"],
                "core_bytes": ingress["core_bytes"],
                "headroom_bytes": ingress["headroom_bytes"],
            },
            "normalized_counts": verification["normalized_counts"],
            "preserved_release_path": str(release_copy),
            "preserved_donor_ledger_path": str(donor_events_target),
            "authority_effect": "NONE",
            "private_values_emitted": False,
            "lineage_law": "DONOR_EVENT_HASH != SERVER_NATIVE_EVENT_HASH_AFTER_MIGRATION",
            "post_write_readback": True,
        }
