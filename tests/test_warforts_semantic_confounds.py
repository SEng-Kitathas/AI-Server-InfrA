from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baseline" / "pcmmad_receiver"))

import icf_cs_v12_ingress as ingress
import shared_core
import ucm_v1_runtime as ucm
import user_continuity_store as backend
from test_ucm_v1_runtime import collaboration, fact, identity, referent, source_provenance


class SemanticFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pcmmad-warfort-confounds-")
        self.old_memory = backend.MEMORY_ROOT
        backend.MEMORY_ROOT = Path(self.temp.name) / "memory"
        with backend._CACHE_GUARD:
            backend._STATE_CACHE.clear()
        with backend._LOCKS_GUARD:
            backend._PROFILE_LOCKS.clear()

    def tearDown(self):
        backend.MEMORY_ROOT = self.old_memory
        with backend._CACHE_GUARD:
            backend._STATE_CACHE.clear()
        with backend._LOCKS_GUARD:
            backend._PROFILE_LOCKS.clear()
        self.temp.cleanup()

    def payload(self, profile: str, idem: str, **extra):
        h = ucm.head(profile)
        out = {
            "profile_id": profile,
            "actor": "assistant",
            "source_instance": "warfort",
            "provenance": source_provenance(idem),
            "idempotency_key": idem,
            "expected_head_seq": h["ledger_head_seq"],
            "expected_head_hash": h["ledger_head_hash"],
            "write_posture": "DIRECT_USER_AUTHORIZED",
        }
        out.update(extra)
        return out

    def add(self, profile: str, record_type: str, record: dict, idem: str):
        return ucm.add(self.payload(profile, idem, record_type=record_type, record=record))


class IdentityReferentAmbiguityTests(SemanticFixture):
    def test_equal_precedence_conflicting_identity_is_ambiguous_not_arbitrary(self):
        profile = "identity-ambiguous"
        self.add(profile, "IDENTITY", identity("id.a", "Alpha", precedence=50), "a")
        self.add(profile, "IDENTITY", identity("id.b", "Beta", precedence=50), "b")
        with self.assertRaises(ucm.UcmError) as ctx:
            ucm.resolve_identity(profile, use_for="NORMAL_ADDRESS")
        self.assertEqual(ctx.exception.error_code, "UCM_IDENTITY_AMBIGUOUS")

    def test_equal_precedence_same_identity_value_can_resolve_without_false_conflict(self):
        profile = "identity-same"
        self.add(profile, "IDENTITY", identity("id.a", "Same", precedence=50), "a")
        self.add(profile, "IDENTITY", identity("id.b", "Same", precedence=50), "b")
        out = ucm.resolve_identity(profile, use_for="NORMAL_ADDRESS")
        self.assertEqual(out["value"], "Same")

    def test_equal_precedence_conflicting_referent_is_ambiguous_not_arbitrary(self):
        profile = "referent-ambiguous"
        self.add(profile, "REFERENT", referent("ref.a", "Thing", "Meaning A", precedence=50), "a")
        self.add(profile, "REFERENT", referent("ref.b", "Thing", "Meaning B", precedence=50), "b")
        with self.assertRaises(ucm.UcmError) as ctx:
            ucm.resolve_referent(profile, term="thing")
        self.assertEqual(ctx.exception.error_code, "UCM_REFERENT_AMBIGUOUS")

    def test_historical_equal_precedence_entry_does_not_create_active_ambiguity(self):
        profile = "referent-historical"
        self.add(profile, "REFERENT", referent("ref.a", "Thing", "Current", precedence=50), "a")
        self.add(profile, "REFERENT", referent("ref.b", "Thing", "Old", precedence=50, status="HISTORICAL"), "b")
        self.assertEqual(ucm.resolve_referent(profile, term="thing")["meaning"], "Current")


class ProfileIsolationTests(SemanticFixture):
    def test_path_traversal_profile_id_rejected(self):
        with self.assertRaises(backend.UserContinuityError) as ctx:
            backend._profile_id("../other-user")
        self.assertEqual(ctx.exception.error_code, "BAD_PROFILE_ID")

    def test_neighbor_profile_fact_never_appears_in_explicit_other_profile(self):
        self.add("alice", "COLLABORATION_CONTRACT", collaboration("alice-collab"), "alice-collab")
        self.add("alice", "FACT", fact("alice.secret", value="alice-only"), "alice-fact")
        self.add("bob", "COLLABORATION_CONTRACT", collaboration("bob-collab"), "bob-collab")
        alice = ucm.read_core("alice")
        bob = ucm.read_core("bob")
        self.assertIn("alice.secret", alice["CORE_SNAPSHOT"]["facts"])
        self.assertNotIn("alice.secret", bob["CORE_SNAPSHOT"]["facts"])
        self.assertNotIn("alice-only", repr(bob))

    def test_profile_case_variants_canonicalize_to_one_identity(self):
        self.assertEqual(backend._profile_id("CaseUser"), "caseuser")
        self.assertEqual(backend._profile_id("caseuser"), "caseuser")
        self.add("CaseUser", "COLLABORATION_CONTRACT", collaboration("upper"), "upper")
        with self.assertRaises(ucm.UcmError) as ctx:
            self.add("caseuser", "COLLABORATION_CONTRACT", collaboration("lower"), "lower")
        self.assertEqual(ctx.exception.error_code, "UCM_COLLABORATION_CONFLICT")
        self.assertEqual(ucm.head("CaseUser")["profile_id"], "caseuser")



class CurrentStateFixtureIngressTests(unittest.TestCase):
    def test_repository_current_carrier_is_rehydratable_nonuser(self):
        with tempfile.TemporaryDirectory(prefix="pcmmad-warfort-current-carrier-") as td:
            projects = Path(td) / "projects"
            fixture = projects / "current-carrier"
            standard = fixture / ingress.ICF_CS_STANDARD_REL
            standard.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / "handoff/current/INTENT_CONSTRAINT_FRONTIER_CONTINUITY_STANDARD.md", standard)
            (fixture / "state/current").mkdir(parents=True, exist_ok=True)
            (fixture / "state/current/CURRENT_STATE.md").write_text("current Git-facing carrier\n", encoding="utf-8")
            (fixture / "continuity/live_shadow").mkdir(parents=True, exist_ok=True)
            (fixture / "continuity/live_shadow/LIVE_SHADOW.md").write_text("live carrier\n", encoding="utf-8")
            (fixture / "continuity/design_thread_stream").mkdir(parents=True, exist_ok=True)
            (fixture / "continuity/design_thread_stream/DESIGN_THREAD_STREAM.md").write_text("dts carrier\n", encoding="utf-8")
            self.assertEqual(ingress._sha256(standard), ingress.ICF_CS_STANDARD_SHA256)
            old_projects = shared_core.PROJECTS_ROOT
            shared_core.PROJECTS_ROOT = projects
            try:
                out = ingress.rehydrate_icf_v12(
                    project_id=fixture.name,
                    topic="ICF-CS v1.2 RES UCM current frontier",
                    session_mode="NONUSER_NONRESEARCH_AUTOMATION",
                    project_budget_bytes=60000,
                )
            finally:
                shared_core.PROJECTS_ROOT = old_projects
        self.assertEqual(out["status"], "FRESH_INSTANCE_CONTINUITY_READY")
        self.assertEqual(out["icf_cs"]["sha256"], ingress.ICF_CS_STANDARD_SHA256)
        classes = {row.get("artifact_class") for row in out["project_context"]["selected"]}
        self.assertIn("continuity.live_shadow", classes)
        self.assertIn("continuity.design_thread_stream", classes)


if __name__ == "__main__":
    unittest.main()
