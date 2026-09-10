from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baseline" / "pcmmad_receiver"))

import icf_cs_v12_ingress as ingress
import lab_tools
import protocol_store
import res_runtime as res
import shared_core
import ucm_v1_runtime as ucm
import user_continuity_store as memory_backend
from protocol_models import ContinuityKind
from test_res_runtime import valid_snapshot
from test_ucm_v1_runtime import collaboration, source_provenance


class IcfV12IngressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pcmmad-icf-v12-ingress-")
        self.base = Path(self.temp.name)
        self.old_projects = shared_core.PROJECTS_ROOT
        self.old_memory = memory_backend.MEMORY_ROOT
        shared_core.PROJECTS_ROOT = self.base / "projects"
        memory_backend.MEMORY_ROOT = self.base / "memory"
        with memory_backend._CACHE_GUARD:
            memory_backend._STATE_CACHE.clear()
        with memory_backend._LOCKS_GUARD:
            memory_backend._PROFILE_LOCKS.clear()
        self.project_id = "ingress-project"
        self.root = shared_core.init_project_layout(self.project_id)
        self._install_current_icf()

    def tearDown(self):
        shared_core.PROJECTS_ROOT = self.old_projects
        memory_backend.MEMORY_ROOT = self.old_memory
        with memory_backend._CACHE_GUARD:
            memory_backend._STATE_CACHE.clear()
        with memory_backend._LOCKS_GUARD:
            memory_backend._PROFILE_LOCKS.clear()
        self.temp.cleanup()

    def _install_current_icf(self):
        src = ROOT / "handoff/current/INTENT_CONSTRAINT_FRONTIER_CONTINUITY_STANDARD.md"
        target = self.root / ingress.ICF_CS_STANDARD_REL
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
        self.assertEqual(ingress._sha256(target), ingress.ICF_CS_STANDARD_SHA256)

    def _write_res(self):
        path = self.root / res.RES_CANONICAL_SNAPSHOT_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(valid_snapshot(), encoding="utf-8")
        protocol_store.ensure_protocol(self.project_id, actor="test")
        protocol_store.register_artifact(
            self.project_id,
            artifact_id="res-snapshot",
            artifact_class=res.RES_ARTIFACT_CLASS_SNAPSHOT,
            path=res.RES_CANONICAL_SNAPSHOT_PATH,
            sealed=True,
            actor="test",
        )
        protocol_store.record_continuity(
            self.project_id,
            continuity_id="res-snapshot",
            kind=ContinuityKind.RESEARCH_EPISTEMIC_SHADOW,
            summary="current RES",
            artifact_ref=res.RES_CANONICAL_SNAPSHOT_PATH,
            actor="test",
        )

    def _ucm_payload(self, profile: str, **extra):
        h = ucm.head(profile)
        payload = {
            "profile_id": profile,
            "actor": "assistant",
            "source_instance": "test",
            "provenance": source_provenance("ingress"),
            "idempotency_key": f"idem-{h['ledger_head_seq']+1}",
            "expected_head_seq": h["ledger_head_seq"],
            "expected_head_hash": h["ledger_head_hash"],
            "write_posture": "DIRECT_USER_AUTHORIZED",
        }
        payload.update(extra)
        return payload

    def _write_ucm(self, profile="user-1"):
        ucm.add(self._ucm_payload(profile, record_type="COLLABORATION_CONTRACT", record=collaboration()))
        return profile

    def test_native_tool_registered_as_current_continuity_ingress(self):
        spec = lab_tools._TOOL_REGISTRY["continuity.ingress.rehydrate"]
        self.assertEqual(spec.category, "continuity")
        self.assertFalse(spec.mutating)
        self.assertIn("icf_cs_v1_2_currentness", set(spec.effect_traits))
        self.assertTrue(spec.contract_digest)

    def test_missing_session_mode_fails_closed(self):
        with self.assertRaises(ingress.IcfIngressError) as ctx:
            ingress.rehydrate_icf_v12(project_id=self.project_id, topic="frontier", session_mode="")
        self.assertEqual(ctx.exception.error_code, "ICF_CS_SESSION_MODE_REQUIRED")

    def test_stale_icf_standard_fails_before_res_or_ucm(self):
        target = self.root / ingress.ICF_CS_STANDARD_REL
        target.write_text("ICF-CS v1.1 stale\n", encoding="utf-8")
        with self.assertRaises(ingress.IcfIngressError) as ctx:
            ingress.rehydrate_icf_v12(
                project_id=self.project_id,
                topic="frontier",
                session_mode="NONUSER_NONRESEARCH_AUTOMATION",
            )
        self.assertEqual(ctx.exception.error_code, "ICF_CS_CURRENTNESS_FAILURE")

    def test_nonuser_nonresearch_can_mark_both_not_applicable_with_basis(self):
        out = ingress.rehydrate_icf_v12(
            project_id=self.project_id,
            topic="frontier",
            session_mode="NONUSER_NONRESEARCH_AUTOMATION",
        )
        self.assertEqual(out["status"], "FRESH_INSTANCE_CONTINUITY_READY")
        self.assertEqual(out["applicability"]["RES"]["state"], "NOT_APPLICABLE_WITH_BASIS")
        self.assertEqual(out["applicability"]["UCM"]["state"], "NOT_APPLICABLE_WITH_BASIS")
        self.assertTrue(out["applicability"]["RES"]["basis"])
        self.assertTrue(out["applicability"]["UCM"]["basis"])

    def test_interactive_user_requires_explicit_ucm_profile(self):
        with self.assertRaises(ingress.IcfIngressError) as ctx:
            ingress.rehydrate_icf_v12(
                project_id=self.project_id,
                topic="frontier",
                session_mode="INTERACTIVE_NONRESEARCH_USER_SESSION",
            )
        self.assertEqual(ctx.exception.error_code, "USER_CONTINUITY_INCOMPLETE")

    def test_interactive_nonresearch_with_complete_ucm_passes(self):
        profile = self._write_ucm()
        out = ingress.rehydrate_icf_v12(
            project_id=self.project_id,
            topic="frontier",
            session_mode="INTERACTIVE_NONRESEARCH_USER_SESSION",
            ucm_profile_id=profile,
        )
        self.assertEqual(out["status"], "FRESH_INSTANCE_CONTINUITY_READY")
        self.assertEqual(out["ucm"]["ingress_status"], "PASS")
        self.assertEqual(out["res"]["status"], "NOT_APPLICABLE_WITH_BASIS")
        self.assertEqual(out["required_next_gate"], "OWNING_PLANE_LIVE_VERIFICATION_THEN_LIVE_READBACK_BEFORE_MUTATION")

    def test_research_session_missing_res_fails_exact_taxonomy(self):
        with self.assertRaises(ingress.IcfIngressError) as ctx:
            ingress.rehydrate_icf_v12(
                project_id=self.project_id,
                topic="research frontier",
                session_mode="NONUSER_RESEARCH_AUTOMATION",
            )
        self.assertEqual(ctx.exception.error_code, "HANDOFF_EPISTEMIC_CONTINUITY_INCOMPLETE")

    def test_nonuser_research_with_res_passes_and_res_is_seeded(self):
        self._write_res()
        out = ingress.rehydrate_icf_v12(
            project_id=self.project_id,
            topic="research frontier",
            session_mode="NONUSER_RESEARCH_AUTOMATION",
            project_budget_bytes=30000,
        )
        self.assertEqual(out["status"], "FRESH_INSTANCE_CONTINUITY_READY")
        self.assertEqual(out["applicability"]["RES"]["state"], "REQUIRED")
        self.assertEqual(out["applicability"]["UCM"]["state"], "NOT_APPLICABLE_WITH_BASIS")
        selected = out["project_context"]["selected"]
        self.assertIn("continuity.research_epistemic_shadow", {row.get("artifact_class") for row in selected})
        res_rows = [row for row in selected if row.get("artifact_class") == "continuity.research_epistemic_shadow"]
        self.assertTrue(res_rows)
        self.assertEqual(res_rows[0].get("authority_role"), "epistemic")

    def test_interactive_research_requires_both_and_passes_when_both_current(self):
        self._write_res()
        profile = self._write_ucm()
        out = ingress.rehydrate_icf_v12(
            project_id=self.project_id,
            topic="research frontier",
            session_mode="INTERACTIVE_RESEARCH_USER_SESSION",
            ucm_profile_id=profile,
        )
        self.assertEqual(out["applicability"]["RES"]["state"], "REQUIRED")
        self.assertEqual(out["applicability"]["UCM"]["state"], "REQUIRED")
        self.assertEqual(out["ucm"]["ingress_status"], "PASS")
        self.assertTrue(out["res"]["ready"])

    def test_nonuser_mode_rejects_supplied_ucm_profile_as_applicability_conflict(self):
        with self.assertRaises(ingress.IcfIngressError) as ctx:
            ingress.rehydrate_icf_v12(
                project_id=self.project_id,
                topic="frontier",
                session_mode="NONUSER_NONRESEARCH_AUTOMATION",
                ucm_profile_id="unexpected-user",
            )
        self.assertEqual(ctx.exception.error_code, "ICF_CS_APPLICABILITY_CONFLICT")

    def test_project_override_requires_res_even_in_nonresearch_session(self):
        profile = self._write_ucm()
        with self.assertRaises(ingress.IcfIngressError) as ctx:
            ingress.rehydrate_icf_v12(
                project_id=self.project_id,
                topic="frontier",
                session_mode="INTERACTIVE_NONRESEARCH_USER_SESSION",
                ucm_profile_id=profile,
                res_required_by_project=True,
            )
        self.assertEqual(ctx.exception.error_code, "HANDOFF_EPISTEMIC_CONTINUITY_INCOMPLETE")

    def test_stale_ucm_taxonomy_is_preserved(self):
        profile = self._write_ucm()
        memory_backend.memory_add({
            "profile_id": profile,
            "target": "legacy-late",
            "section": "legacy",
            "class": "USER_STATED",
            "status": "ACTIVE",
            "value": "late",
            "reason": "force snapshot lag after canonical UCM materialization",
            "provenance": "test",
            "actor": "server",
            "source_instance": "test",
            "idempotency_key": "legacy-late",
            "confidence": "high",
            "sensitivity": "normal",
            "export_class": "USER",
            "always_load": False,
            "hydration_priority": 1,
        })
        # Canonical write above produced a current snapshot; legacy append also materializes,
        # so force exact stale currentness by removing the current manifest.
        memory_backend._paths(profile).current.unlink()
        with self.assertRaises(ingress.IcfIngressError) as ctx:
            ingress.rehydrate_icf_v12(
                project_id=self.project_id,
                topic="frontier",
                session_mode="INTERACTIVE_NONRESEARCH_USER_SESSION",
                ucm_profile_id=profile,
            )
        self.assertEqual(ctx.exception.error_code, "UCM_CURRENTNESS_FAILURE")

    def test_stale_native_capability_contract_rejected_before_execution(self):
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            lab_tools.dispatch_tool(
                "continuity.ingress.rehydrate",
                {
                    "project_id": self.project_id,
                    "topic": "frontier",
                    "session_mode": "NONUSER_NONRESEARCH_AUTOMATION",
                },
                expected_contract_digest="0" * 64,
            )
        self.assertEqual(ctx.exception.error_code, "CAPABILITY_CONTRACT_STALE")


if __name__ == "__main__":
    unittest.main()
