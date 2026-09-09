from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baseline" / "pcmmad_receiver"))

import protocol_store
import res_runtime as res
import shared_core
from protocol_models import ContinuityKind
from test_res_runtime import create_addendum, valid_snapshot


class AddendumHostileTests(unittest.TestCase):
    def assert_code(self, code, fn):
        with self.assertRaises(res.ResPolicyError) as ctx:
            fn()
        self.assertEqual(ctx.exception.code, code)

    def test_unknown_truth_state_rejected(self):
        item = create_addendum(status="CERTAIN")
        self.assert_code("RES_TRUTH_STATE_INVALID", lambda: res.validate_addendum(item))

    def test_missing_provenance_rejected(self):
        item = create_addendum()
        item["claims"][0]["provenance_refs"] = []
        self.assert_code("RES_PROVENANCE_REQUIRED", lambda: res.validate_addendum(item))

    def test_verified_without_evidence_rejected(self):
        item = create_addendum(status="VERIFIED")
        self.assert_code("RES_EVIDENCE_REQUIRED", lambda: res.validate_addendum(item))

    def test_observed_without_evidence_rejected(self):
        item = create_addendum(status="OBSERVED")
        self.assert_code("RES_EVIDENCE_REQUIRED", lambda: res.validate_addendum(item))

    def test_rejected_without_defeating_evidence_rejected(self):
        item = create_addendum(status="REJECTED_DEMOTED")
        self.assert_code("RES_EVIDENCE_REQUIRED", lambda: res.validate_addendum(item))

    def test_authority_smuggling_rejected(self):
        item = create_addendum()
        item["authority_effect"] = "PROMOTE_DOCTRINE"
        self.assert_code("RES_AUTHORITY_FIREWALL", lambda: res.validate_addendum(item))

    def test_unknown_material_event_rejected(self):
        item = create_addendum(event="EVERY_CHAT_TURN")
        self.assert_code("RES_MATERIAL_EVENT_INVALID", lambda: res.validate_addendum(item))

    def test_duplicate_claim_in_one_addendum_rejected(self):
        item = create_addendum()
        item["claims"].append(copy.deepcopy(item["claims"][0]))
        self.assert_code("RES_ADDENDUM_INVALID", lambda: res.validate_addendum(item))

    def test_empty_claim_set_rejected(self):
        item = create_addendum()
        item["claims"] = []
        self.assert_code("RES_ADDENDUM_INVALID", lambda: res.validate_addendum(item))

    def test_stale_addendum_head_rejected(self):
        first = create_addendum()
        p1 = res.project_addenda([first])
        second = create_addendum(prior_projection=p1)
        second["prior_addendum_digest"] = "0" * 64
        self.assert_code(
            "RES_ADDENDUM_CURRENTNESS_STALE",
            lambda: res.validate_addendum(second, prior_projection=p1),
        )

    def test_existing_claim_cannot_restart_as_create(self):
        first = create_addendum()
        p1 = res.project_addenda([first])
        second = create_addendum(prior_projection=p1)
        second["claims"][0]["transition_kind"] = "CREATE"
        self.assert_code(
            "RES_TRANSITION_INVALID",
            lambda: res.validate_addendum(second, prior_projection=p1),
        )

    def test_silent_status_change_under_reaffirm_rejected(self):
        first = create_addendum()
        p1 = res.project_addenda([first])
        second = create_addendum(
            prior_projection=p1,
            status="INFERRED",
            transition="REAFFIRM",
        )
        self.assert_code(
            "RES_TRANSITION_INVALID",
            lambda: res.validate_addendum(second, prior_projection=p1),
        )

    def test_demotion_must_be_visible_rejected_state(self):
        first = create_addendum()
        p1 = res.project_addenda([first])
        second = create_addendum(
            prior_projection=p1,
            status="UNKNOWN",
            transition="DEMOTE",
            evidence=["evidence:defeat"],
        )
        self.assert_code(
            "RES_TRANSITION_INVALID",
            lambda: res.validate_addendum(second, prior_projection=p1),
        )

    def test_promotion_requires_evidence(self):
        first = create_addendum()
        p1 = res.project_addenda([first])
        second = create_addendum(
            prior_projection=p1,
            status="INFERRED",
            transition="PROMOTE",
        )
        self.assert_code(
            "RES_TRANSITION_EVIDENCE_REQUIRED",
            lambda: res.validate_addendum(second, prior_projection=p1),
        )

    def test_promotion_cannot_target_unknown(self):
        first = create_addendum()
        p1 = res.project_addenda([first])
        second = create_addendum(
            prior_projection=p1,
            status="UNKNOWN",
            transition="PROMOTE",
            evidence=["evidence:x"],
        )
        self.assert_code(
            "RES_TRANSITION_INVALID",
            lambda: res.validate_addendum(second, prior_projection=p1),
        )

    def test_wrong_previous_claim_digest_rejected(self):
        first = create_addendum()
        p1 = res.project_addenda([first])
        second = create_addendum(prior_projection=p1)
        second["claims"][0]["previous_claim_digest"] = "0" * 64
        self.assert_code(
            "RES_CLAIM_CURRENTNESS_STALE",
            lambda: res.validate_addendum(second, prior_projection=p1),
        )

    def test_reordered_chain_rejected(self):
        first = create_addendum()
        p1 = res.project_addenda([first])
        second = create_addendum(prior_projection=p1)
        self.assert_code(
            "RES_ADDENDUM_CURRENTNESS_STALE",
            lambda: res.project_addenda([second, first]),
        )


class SnapshotHostileTests(unittest.TestCase):
    def assert_code(self, code, content):
        with self.assertRaises(res.ResPolicyError) as ctx:
            res.validate_snapshot(content)
        self.assertEqual(ctx.exception.code, code)

    def test_missing_section_rejected(self):
        text = valid_snapshot().replace("## 22. Research Re-entry / Exact Next Move\n`UNKNOWN` — fixture epistemic statement.\n", "")
        self.assert_code("RES_SNAPSHOT_SECTION_INVALID", text)

    def test_reordered_sections_rejected(self):
        text = valid_snapshot()
        a = "## 1. Project / Research Identity"
        b = "## 2. Governing Intent"
        text = text.replace(a, "## TMP").replace(b, a).replace("## TMP", b)
        self.assert_code("RES_SNAPSHOT_SECTION_INVALID", text)

    def test_duplicate_section_rejected(self):
        text = valid_snapshot() + "\n## 22. Research Re-entry / Exact Next Move\n`UNKNOWN` — duplicate.\n"
        self.assert_code("RES_SNAPSHOT_SECTION_INVALID", text)

    def test_noncanonical_truth_prefix_rejected(self):
        text = valid_snapshot().replace("`UNKNOWN` — fixture", "`CERTAIN` — fixture", 1)
        self.assert_code("RES_TRUTH_STATE_INVALID", text)

    def test_missing_doctrine_firewall_rejected(self):
        text = valid_snapshot().replace("Authority rule: `RES_CONTENT != GOVERNING_DOCTRINE`\n", "")
        self.assert_code("RES_AUTHORITY_FIREWALL", text)

    def test_wrong_form_rejected(self):
        text = valid_snapshot().replace("Form: `RES CONSOLIDATED SNAPSHOT`", "Form: RES DOCTRINE")
        self.assert_code("RES_SNAPSHOT_INVALID", text)

    def test_snapshot_without_truth_state_claims_rejected(self):
        text = valid_snapshot().replace("`UNKNOWN` — fixture epistemic statement.", "fixture epistemic statement.")
        self.assert_code("RES_SNAPSHOT_INVALID", text)


class HandoffHostileTests(unittest.TestCase):
    def setUp(self):
        self.old = shared_core.PROJECTS_ROOT
        self.temp = tempfile.TemporaryDirectory()
        shared_core.PROJECTS_ROOT = Path(self.temp.name)
        self.project_id = "res-hostile"
        self.root = shared_core.init_project_layout(self.project_id)
        protocol_store.ensure_protocol(self.project_id, actor="test")

    def tearDown(self):
        shared_core.PROJECTS_ROOT = self.old
        self.temp.cleanup()

    def register_snapshot(self):
        path = self.root / res.RES_CANONICAL_SNAPSHOT_PATH
        path.write_text(valid_snapshot(), encoding="utf-8")
        protocol_store.register_artifact(
            self.project_id,
            artifact_id="snapshot-1",
            artifact_class=res.RES_ARTIFACT_CLASS_SNAPSHOT,
            path=res.RES_CANONICAL_SNAPSHOT_PATH,
            sealed=True,
            actor="test",
        )
        protocol_store.record_continuity(
            self.project_id,
            continuity_id="snapshot-1",
            kind=ContinuityKind.RESEARCH_EPISTEMIC_SHADOW,
            summary="snapshot",
            artifact_ref=res.RES_CANONICAL_SNAPSHOT_PATH,
            actor="test",
        )
        return path

    def test_missing_snapshot_fails_handoff(self):
        out = res.handoff_readiness(self.project_id)
        self.assertFalse(out["ready"])
        self.assertIn("RES_SNAPSHOT_MISSING", out["reasons"])

    def test_unregistered_snapshot_fails_handoff(self):
        path = self.root / res.RES_CANONICAL_SNAPSHOT_PATH
        path.write_text(valid_snapshot(), encoding="utf-8")
        out = res.handoff_readiness(self.project_id)
        self.assertIn("RES_SNAPSHOT_NOT_REGISTERED", out["reasons"])

    def test_snapshot_hash_drift_fails_handoff(self):
        path = self.register_snapshot()
        path.write_text(valid_snapshot() + "\n<!-- drift -->\n", encoding="utf-8")
        out = res.handoff_readiness(self.project_id)
        self.assertIn("RES_SNAPSHOT_REGISTERED_HASH_STALE", out["reasons"])

    def test_protocol_claim_after_snapshot_cannot_be_hidden_by_continuity_ack(self):
        self.register_snapshot()
        protocol_store.record_claim(
            self.project_id,
            claim_id="claim-new",
            kind="HYPOTHESIS",
            statement="material change",
            actor="test",
        )
        protocol_store.record_continuity(
            self.project_id,
            continuity_id="ack-only",
            kind=ContinuityKind.RESEARCH_EPISTEMIC_SHADOW,
            summary="ACK",
            artifact_ref=res.RES_CANONICAL_SNAPSHOT_PATH,
            actor="test",
        )
        out = res.handoff_readiness(self.project_id)
        self.assertIn("RES_STALE_AFTER_MATERIAL_PROTOCOL_CHANGE", out["reasons"])

    def test_unrelated_addendum_cannot_mask_material_change(self):
        self.register_snapshot()
        protocol_store.record_claim(
            self.project_id,
            claim_id="claim-new",
            kind="HYPOTHESIS",
            statement="material change",
            actor="test",
        )
        addendum = create_addendum(event="RESEARCH_HANDOFF_CHECKPOINT")
        path = self.root / "continuity/research_epistemic_shadow/addenda/0001.json"
        path.write_text(json.dumps(addendum, indent=2) + "\n", encoding="utf-8")
        protocol_store.register_artifact(
            self.project_id, artifact_id="add-1", artifact_class=res.RES_ARTIFACT_CLASS_ADDENDUM,
            path="continuity/research_epistemic_shadow/addenda/0001.json", sealed=True, actor="test"
        )
        protocol_store.record_continuity(
            self.project_id, continuity_id="add-1", kind=ContinuityKind.RESEARCH_EPISTEMIC_SHADOW,
            summary="unrelated update", artifact_ref="continuity/research_epistemic_shadow/addenda/0001.json", actor="test"
        )
        out = res.handoff_readiness(self.project_id)
        self.assertFalse(out["ready"])
        self.assertIn("RES_ADDENDUM_MATERIAL_EVENT_UNBOUND", out["reasons"])

    def test_research_intensive_false_does_not_mint_authority(self):
        out = res.handoff_readiness(self.project_id, research_intensive=False)
        self.assertTrue(out["ready"])
        self.assertEqual(out["status"], "NOT_APPLICABLE")
        self.assertEqual(out["authority_effect"], "NONE")


if __name__ == "__main__":
    unittest.main()
