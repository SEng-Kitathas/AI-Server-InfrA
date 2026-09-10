from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baseline" / "pcmmad_receiver"))

import ucm_private_migration as migration
import ucm_v1_runtime as ucm
import user_continuity_store as backend
from test_ucm_v1_runtime import collaboration, decision, fact, identity, referent


PRIVATE_ROOT = migration.PRIVATE_RELEASE_SCHEMA
NOW = "2026-09-09T12:00:00+00:00"


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(root: Path, rel: str, obj) -> bytes:
    data = (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def donor_events(facts):
    events = []
    previous = None
    for idx, row in enumerate(facts, 1):
        body = {
            "seq": idx,
            "event_id": f"E{idx}",
            "prev_hash": previous,
            "operation": "ADD",
            "fact_key": row["fact_key"],
            "actor": "migration-fixture",
            "source_instance": "fixture",
            "source_thread": None,
            "recorded_at": NOW,
            "payload": row,
            "evidence_refs": [],
        }
        event_hash = sha(canonical(body))
        events.append({**body, "event_hash": event_hash})
        previous = event_hash
    return events


def build_private_fixture(base: Path) -> Path:
    root = base / PRIVATE_ROOT
    root.mkdir(parents=True)

    current = fact("employment.current", value="current", groups=["global_constraints"])
    historical = fact("employment.historical", value="historical", currentness="HISTORICAL", groups=["historical"])
    project = fact("project.pointer", value="project", target_plane="PROJECT", requirement="REQUIRED", currentness="UNVERIFIED", export_class="PROJECT", groups=["projects"])
    facts = [current, historical, project]
    facts_map = {x["fact_key"]: x for x in facts}
    events = donor_events(facts)
    events_data = b"".join(json.dumps(x, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n" for x in events)
    (root / "events").mkdir()
    (root / "events/events.jsonl").write_bytes(events_data)

    identities = [identity("identity.preferred.fixture", "Fixture", precedence=90)]
    referents = [
        referent("pcmmad.current", "PCMMAD", "current", precedence=90),
        referent("pcmmad.old", "PCMMAD", "old", precedence=10, status="SUPERSEDED"),
    ]
    decisions = [decision("decision.fixture")]
    # Match public decision schema: independence group is optional.
    decisions[0]["provenance"] = [{"source_instance": "fixture", "source_artifact": "fixture.md", "source_pointer": "L1"}]
    source_assertions = [{
        "assertion_id": "assertion.1", "source_instance": "fixture", "source_artifact": "RAHL_USER_CONTINUITY_MEMORY_2026-09-07.md",
        "source_pointer": "L1", "heading_path": "H", "line_start": 1, "line_end": 1, "text": "source context", "label": "context",
        "currentness_hint": "UNKNOWN", "verification_hint": "NONE", "lifecycle_hint": "ACTIVE", "sensitivity_hint": "NORMAL",
        "export_class_hint": "USER", "hydration_group_hint": "source_evidence", "import_disposition": "SOURCE_CONTEXT_ONLY",
    }]
    write_json(root, "normalized/facts.json", facts_map)
    write_json(root, "normalized/identities.json", identities)
    write_json(root, "normalized/referents.json", referents)
    write_json(root, "normalized/decisions.json", decisions)
    write_json(root, "normalized/source_assertions.json", source_assertions)
    write_json(root, "normalized/collaboration_contract.json", collaboration())
    control = ucm.default_control_state()
    write_json(root, "control/CONTROL_STATE.json", control)
    write_json(root, "candidates/memory_candidates.json", [])

    source_rows = []
    for name, data in [
        ("RAHL_USER_CONTINUITY_MEMORY_2026-09-07.md", b"source-one"),
        ("CLAUDE CONTINUITY EXPORT 2026-09-08.md", b"source-two"),
    ]:
        digest = sha(data)
        (root / "sources/blobs/sha256").mkdir(parents=True, exist_ok=True)
        (root / f"sources/{name}").write_bytes(data)
        (root / f"sources/blobs/sha256/{digest}").write_bytes(data)
        source_rows.append({
            "source_instance": "fixture", "artifact": name, "sha256": digest, "bytes": len(data),
            "preservation": "IMMUTABLE_IMPORT_SOURCE", "blob_path": f"sources/blobs/sha256/{digest}",
            "coverage": "fixture", "policy_absences": [], "source_role": "CONTINUITY_DONOR",
        })
    source_manifest_data = write_json(root, "sources/SOURCE_MANIFEST.json", source_rows)

    core = {"schema": "rahl.user-continuity.core-snapshot.v1", "snapshot_from_seq": len(events), "facts": [current]}
    core_data = write_json(root, "snapshot/core.json", core)
    identity_index_data = write_json(root, "snapshot/identity_index.json", {"schema": "x", "snapshot_from_seq": len(events), "normal_identity_key": identities[0]["identity_key"]})
    collaboration_data = write_json(root, "snapshot/collaboration_contract.json", {"v": 1, "authority": "NONE", "full": "../normalized/collaboration_contract.json"})
    referent_data = write_json(root, "snapshot/referent_index.json", {"v": 1, "e": [{"k": "pcmmad.current"}], "full": "../normalized/referents.json"})
    decision_data = write_json(root, "snapshot/decision_index.json", {"v": 1, "e": [{"k": "decision.fixture"}], "full": "../normalized/decisions.json"})
    verification_data = write_json(root, "snapshot/verification_debt.json", {"schema": "x", "snapshot_from_seq": len(events), "required_unverified_count": 1})
    candidate_head_data = write_json(root, "candidates/HEAD.json", {"schema": "x", "pending_count": 0, "candidate_count": 0, "queue_sha256": sha(b"[]\n")})

    store_head = {
        "schema": "rahl.user-continuity.private-store-head.v1", "system_version": "1.0", "user_store_id": "fixture-user",
        "not_project_authority": True, "not_doctrine_authority": True,
        "ledger_head_seq": len(events), "ledger_head_hash": events[-1]["event_hash"], "snapshot_from_seq": len(events),
        "source_manifest_sha256": sha(source_manifest_data), "core_snapshot_sha256": sha(core_data), "identity_index_sha256": sha(identity_index_data),
        "collaboration_contract_sha256": sha(collaboration_data), "referent_index_sha256": sha(referent_data), "decision_index_sha256": sha(decision_data),
        "verification_debt_sha256": sha(verification_data), "control_state_sha256": sha((root / "control/CONTROL_STATE.json").read_bytes()),
        "candidate_queue_head_sha256": sha(candidate_head_data),
    }
    write_json(root, "USER_STORE_HEAD.json", store_head)
    write_json(root, "SYSTEM_REF.json", {
        "schema": "rahl.user-continuity.system-ref.v1", "system_name": "User Continuity System", "system_version": "1.0",
        "system_descriptor_sha256": migration.DONOR_SYSTEM_DESCRIPTOR_SHA256, "ingress_contract_sha256": migration.DONOR_INGRESS_CONTRACT_SHA256,
        "required_authority_traits": list(ucm.AUTHORITY_TRAITS), "portable_system_embedded": False, "system_descriptor_bytes": 1820,
        "core_budget_bytes": 12000, "min_headroom_bytes": 2000, "budget_scope": "USER_CORE_SURFACES_EXCLUDING_SYSTEM_DESCRIPTOR",
    })
    write_json(root, "INGRESS_BINDING.json", {
        "schema": "rahl.user-continuity.private-ingress-binding.v1",
        "surfaces": {name: {} for name in sorted(ucm.REQUIRED_INGRESS_SURFACES)},
        "core_budget_bytes": 12000, "min_headroom_bytes": 2000, "budget_scope": "USER_CORE_SURFACES_EXCLUDING_SYSTEM_DESCRIPTOR",
    })
    write_json(root, "normalized/MIGRATION_EXPECTATIONS.json", {
        "schema": "x", "normal_address_identity_key": identities[0]["identity_key"], "current_employment_fact_key": "employment.current",
        "historical_employment_fact_key": "employment.historical", "active_pcmmad_referent_key": "pcmmad.current", "superseded_pcmmad_referent_key": "pcmmad.old",
        "forbidden_core_hydration_groups": ["personal_sensitive", "deployment", "projects"], "project_or_deployment_exports": ["PROJECT", "DEPLOYMENT"],
        "project_or_deployment_required_verification": True,
        "source_artifacts_required": ["RAHL_USER_CONTINUITY_MEMORY_2026-09-07.md", "CLAUDE CONTINUITY EXPORT 2026-09-08.md"],
    })
    always_load = [root / "USER_STORE_HEAD.json", root / "snapshot/core.json", root / "snapshot/identity_index.json", root / "snapshot/collaboration_contract.json", root / "snapshot/referent_index.json", root / "snapshot/decision_index.json", root / "control/CONTROL_STATE.json", root / "snapshot/verification_debt.json", root / "candidates/HEAD.json"]
    always_load_bytes = sum(x.stat().st_size for x in always_load)
    write_json(root, "receipts/INGRESS_QUALIFICATION.json", {
        "schema": "x", "always_load_bytes": always_load_bytes, "budget_bytes": 12000, "min_headroom_bytes": 2000,
        "actual_headroom_bytes": 12000 - always_load_bytes, "present_surfaces": sorted(ucm.REQUIRED_INGRESS_SURFACES),
        "result": {"status": "PASS", "taxonomy": None, "detail": "fresh-instance UCS ingress complete"},
    })
    write_json(root, "receipts/IMPORT_RECEIPT.json", {
        "schema": "x", "system_version": "1.0", "source_count": len(source_rows), "normalized_fact_count": len(facts),
        "source_assertion_count": len(source_assertions), "decision_count": len(decisions), "ledger_event_count": len(events),
        "ledger_head_seq": len(events), "ledger_head_hash": events[-1]["event_hash"], "ledger_chain_valid": True,
        "identity_count": len(identities), "referent_count": len(referents), "always_load_ingress_bytes": always_load_bytes,
        "ingress_budget_bytes": 12000, "ingress_result": {"status": "PASS"}, "not_project_authority": True,
        "ingress_min_headroom_bytes": 2000, "ingress_actual_headroom_bytes": 12000-always_load_bytes,
    })

    # Exact manifest over every member except itself.
    members = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.json":
            data = path.read_bytes()
            members.append({"path": path.relative_to(root).as_posix(), "bytes": len(data), "sha256": sha(data)})
    write_json(root, "MANIFEST_SHA256.json", {"schema": "rahl.artifact-sealer.manifest.v0.1", "member_count_excluding_manifest": len(members), "members": members})

    archive = base / "fixture-private.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                zf.write(path, f"{PRIVATE_ROOT}/{path.relative_to(root).as_posix()}")
    return archive


class PrivateMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pcmmad-ucm-migration-")
        self.base = Path(self.temp.name)
        self.archive = build_private_fixture(self.base)
        self.archive_sha = sha(self.archive.read_bytes())
        self.archive_bytes = self.archive.stat().st_size
        self.old_memory_root = backend.MEMORY_ROOT
        backend.MEMORY_ROOT = self.base / "runtime-memory"
        with backend._CACHE_GUARD: backend._STATE_CACHE.clear()
        with backend._LOCKS_GUARD: backend._PROFILE_LOCKS.clear()
        self.identity_patch = patch.object(migration, "EXPECTED_PRIVATE_SHA256", self.archive_sha)
        self.bytes_patch = patch.object(migration, "EXPECTED_PRIVATE_BYTES", self.archive_bytes)
        self.identity_patch.start(); self.bytes_patch.start()

    def tearDown(self):
        self.identity_patch.stop(); self.bytes_patch.stop()
        backend.MEMORY_ROOT = self.old_memory_root
        with backend._CACHE_GUARD: backend._STATE_CACHE.clear()
        with backend._LOCKS_GUARD: backend._PROFILE_LOCKS.clear()
        self.temp.cleanup()

    def test_verify_private_release_emits_structure_not_private_values(self):
        out = migration.verify_private_release(self.archive)
        self.assertEqual(out["status"], "VERIFIED_PRIVATE_MIGRATION_SOURCE")
        self.assertFalse(out["private_values_emitted"])
        self.assertEqual(out["normalized_counts"]["facts"], 3)
        self.assertEqual(out["normalized_counts"]["source_assertions"], 1)
        self.assertTrue(out["source_evidence"]["all_originals_match_content_addressed_blobs"])

    def test_tampered_archive_identity_rejected_before_semantic_read(self):
        bad = self.base / "bad.zip"; bad.write_bytes(self.archive.read_bytes() + b"tamper")
        with self.assertRaises(migration.UcmMigrationError) as ctx:
            migration.verify_private_release(bad)
        self.assertEqual(ctx.exception.error_code, "UCM_PRIVATE_RELEASE_IDENTITY_MISMATCH")

    def test_manifest_member_tamper_rejected(self):
        # Rebuild a ZIP with one changed member and patch identity so manifest, not outer SHA, is the discriminator.
        extract = self.base / "tampered"; extract.mkdir()
        with zipfile.ZipFile(self.archive) as zf: zf.extractall(extract)
        target = extract / PRIVATE_ROOT / "normalized/facts.json"
        target.write_bytes(target.read_bytes() + b" ")
        bad = self.base / "manifest-tampered.zip"
        with zipfile.ZipFile(bad, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in sorted((extract / PRIVATE_ROOT).rglob("*")):
                if path.is_file(): zf.write(path, f"{PRIVATE_ROOT}/{path.relative_to(extract / PRIVATE_ROOT).as_posix()}")
        with patch.object(migration, "EXPECTED_PRIVATE_SHA256", sha(bad.read_bytes())), patch.object(migration, "EXPECTED_PRIVATE_BYTES", bad.stat().st_size):
            with self.assertRaises(migration.UcmMigrationError) as ctx: migration.verify_private_release(bad)
        self.assertEqual(ctx.exception.error_code, "UCM_PRIVATE_MANIFEST_INVALID")

    def test_event_chain_tamper_rejected_when_outer_and_manifest_are_resigned(self):
        extract = self.base / "event-tampered"; extract.mkdir()
        with zipfile.ZipFile(self.archive) as zf: zf.extractall(extract)
        root = extract / PRIVATE_ROOT
        events = [json.loads(x) for x in (root / "events/events.jsonl").read_text().splitlines() if x]
        events[1]["prev_hash"] = "0" * 64
        (root / "events/events.jsonl").write_text("".join(json.dumps(x, sort_keys=True)+"\n" for x in events), encoding="utf-8")
        members=[]
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name != "MANIFEST_SHA256.json":
                data=path.read_bytes(); members.append({"path":path.relative_to(root).as_posix(),"bytes":len(data),"sha256":sha(data)})
        write_json(root,"MANIFEST_SHA256.json",{"schema":"rahl.artifact-sealer.manifest.v0.1","member_count_excluding_manifest":len(members),"members":members})
        bad=self.base/"event-resigned.zip"
        with zipfile.ZipFile(bad,"w",compression=zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(root.rglob("*")):
                if path.is_file(): zf.write(path,f"{PRIVATE_ROOT}/{path.relative_to(root).as_posix()}")
        with patch.object(migration,"EXPECTED_PRIVATE_SHA256",sha(bad.read_bytes())), patch.object(migration,"EXPECTED_PRIVATE_BYTES",bad.stat().st_size):
            with self.assertRaises(migration.UcmMigrationError) as ctx: migration.verify_private_release(bad)
        self.assertEqual(ctx.exception.error_code,"UCM_PRIVATE_EVENT_CHAIN_INVALID")

    def test_import_requires_empty_target(self):
        backend.memory_add({"profile_id":"dest","target":"legacy","section":"legacy","class":"USER_STATED","status":"ACTIVE","value":"x","reason":"x","provenance":"x","actor":"server","source_instance":"legacy","idempotency_key":"legacy","confidence":"high","sensitivity":"normal","export_class":"USER","always_load":False,"hydration_priority":10})
        with self.assertRaises(migration.UcmMigrationError) as ctx:
            migration.import_private_release(self.archive, profile_id="dest")
        self.assertEqual(ctx.exception.error_code, "UCM_IMPORT_TARGET_NOT_EMPTY")

    def test_lossless_migration_preserves_donor_evidence_and_builds_new_server_lineage(self):
        verified = migration.verify_private_release(self.archive)
        out = migration.import_private_release(self.archive, profile_id="dest")
        self.assertEqual(out["status"], "MIGRATED_AND_READ_BACK")
        self.assertTrue(out["post_write_readback"])
        self.assertEqual(out["server_ingress"]["status"], "PASS")
        self.assertGreaterEqual(out["server_ingress"]["headroom_bytes"], 2000)
        self.assertNotEqual(out["server_native_head_hash"], verified["donor_event_chain"]["ledger_head_hash"])
        self.assertEqual(out["lineage_law"], "DONOR_EVENT_HASH != SERVER_NATIVE_EVENT_HASH_AFTER_MIGRATION")
        self.assertTrue(Path(out["preserved_release_path"]).is_file())
        self.assertTrue(Path(out["preserved_donor_ledger_path"]).is_file())
        self.assertEqual(sha(Path(out["preserved_release_path"]).read_bytes()), self.archive_sha)
        self.assertEqual(ucm.resolve_identity("dest", use_for="NORMAL_ADDRESS")["identity_key"], "identity.preferred.fixture")
        self.assertEqual(ucm.resolve_referent("dest", term="PCMMAD")["referent_key"], "pcmmad.current")
        self.assertEqual([x["decision_id"] for x in ucm.read_decisions("dest")], ["decision.fixture"])
        self.assertEqual(len(ucm.source_manifest("dest")), 2)
        self.assertEqual(len(ucm._records("dest", "SOURCE_ASSERTION")), 1)


if __name__ == "__main__":
    unittest.main()
