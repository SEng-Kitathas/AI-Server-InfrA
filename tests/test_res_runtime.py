from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baseline" / "pcmmad_receiver"))

import context_engine
import lab_tools
import protocol_store
import res_runtime as res
import shared_core
from protocol_models import ContinuityKind


def valid_snapshot() -> str:
    lines = [
        "# Research Epistemic Shadow (RES) — fixture",
        "",
        "Form: `RES CONSOLIDATED SNAPSHOT`",
        "Authority rule: `RES_CONTENT != GOVERNING_DOCTRINE`",
        "",
    ]
    for index, title in enumerate(res.REQUIRED_SECTIONS, start=1):
        lines.extend([f"## {index}. {title}", "`UNKNOWN` — fixture epistemic statement.", ""])
    return "\n".join(lines)


def create_addendum(*, prior_projection=None, status="HYPOTHESIZED", transition=None, evidence=None, event="FRONTIER_MOVEMENT"):
    prior = dict(prior_projection or {})
    claim = {
        "claim_id": "claim-a",
        "statement": "fixture claim",
        "truth_status": status,
        "provenance_refs": ["artifact:source-a"],
        "evidence_refs": list(evidence or []),
    }
    if prior.get("claims", {}).get("claim-a"):
        claim["previous_claim_digest"] = prior["claims"]["claim-a"]["claim_digest"]
        claim["transition_kind"] = transition or "REAFFIRM"
    else:
        claim["transition_kind"] = transition or "CREATE"
    return {
        "schema": "pcmmad.res-addendum.v1",
        "addendum_id": f"add-{int(prior.get('addendum_count') or 0) + 1}",
        "material_event_class": event,
        "prior_addendum_digest": prior.get("addendum_head_digest"),
        "claims": [claim],
        "authority_effect": "NONE",
    }


class ResPolicyTests(unittest.TestCase):
    def test_canonical_truth_states_are_exact(self):
        self.assertEqual(
            res.TRUTH_STATES,
            (
                "VERIFIED",
                "OBSERVED",
                "INFERRED",
                "HYPOTHESIZED",
                "INTUITION_SIGNAL",
                "UNKNOWN",
                "REJECTED_DEMOTED",
            ),
        )

    def test_snapshot_validates_all_22_sections(self):
        out = res.validate_snapshot(valid_snapshot())
        self.assertEqual(out["state"], "VALID")
        self.assertEqual(out["required_section_count"], 22)
        self.assertEqual(out["authority_effect"], "NONE")
        self.assertIn("content_utf8_sha256", out)
        self.assertNotIn("sha256", out)

    def test_addendum_chain_projects_visible_promotion(self):
        first = create_addendum()
        p1 = res.project_addenda([first])
        second = create_addendum(
            prior_projection=p1,
            status="VERIFIED",
            transition="PROMOTE",
            evidence=["evidence:verification-a"],
        )
        out = res.project_addenda([first, second])
        self.assertEqual(out["addendum_count"], 2)
        self.assertEqual(out["claims"]["claim-a"]["truth_status"], "VERIFIED")
        self.assertEqual(out["claims"]["claim-a"]["transition_kind"], "PROMOTE")
        self.assertEqual(out["authority_effect"], "NONE")

    def test_materiality_handoff_is_required(self):
        out = res.classify_material_change("RESEARCH_HANDOFF_CHECKPOINT", material=False)
        self.assertEqual(out["disposition"], "RES_UPDATE_REQUIRED")

    def test_context_engine_recognizes_res(self):
        path = Path("continuity/research_epistemic_shadow/RESEARCH_EPISTEMIC_SHADOW.md")
        self.assertEqual(
            context_engine._artifact_class_from_path(path),
            "continuity.research_epistemic_shadow",
        )
        self.assertGreater(
            context_engine.ARTIFACT_PRIORS["continuity.research_epistemic_shadow"],
            context_engine.ARTIFACT_PRIORS["continuity.design_thread_stream"],
        )

    def test_project_layout_and_artifact_target_include_res(self):
        old = shared_core.PROJECTS_ROOT
        with tempfile.TemporaryDirectory() as td:
            shared_core.PROJECTS_ROOT = Path(td)
            try:
                root = shared_core.init_project_layout("res-fixture")
                self.assertTrue((root / "continuity/research_epistemic_shadow/addenda").is_dir())
                target = shared_core.resolve_target(
                    "res-fixture",
                    "continuity.research_epistemic_shadow",
                    "RESEARCH_EPISTEMIC_SHADOW.md",
                )
                self.assertEqual(
                    target,
                    (root / "continuity/research_epistemic_shadow/RESEARCH_EPISTEMIC_SHADOW.md").resolve(),
                )
            finally:
                shared_core.PROJECTS_ROOT = old

    def test_protocol_continuity_kind_accepts_res(self):
        self.assertEqual(
            ContinuityKind.RESEARCH_EPISTEMIC_SHADOW.value,
            "RESEARCH_EPISTEMIC_SHADOW",
        )

    def test_tools_are_thin_read_only_continuity_capabilities(self):
        names = (
            "continuity.res.addendum.validate",
            "continuity.res.addenda.project",
            "continuity.res.snapshot.validate",
            "continuity.res.materiality.classify",
            "continuity.res.handoff.readiness",
        )
        for name in names:
            spec = lab_tools._TOOL_REGISTRY[name]
            self.assertEqual(spec.category, "continuity")
            self.assertEqual(spec.side_effect_class, "read")
            self.assertFalse(spec.mutating)
            self.assertTrue(spec.contract_digest)

    def test_contract_currentness_rejects_stale_res_invocation(self):
        name = "continuity.res.snapshot.validate"
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            lab_tools.dispatch_tool(
                name,
                {"content": valid_snapshot()},
                expected_contract_digest="0" * 64,
            )
        self.assertEqual(ctx.exception.error_code, "CAPABILITY_CONTRACT_STALE")


class ResHandoffTests(unittest.TestCase):
    def setUp(self):
        self._old_projects_root = shared_core.PROJECTS_ROOT
        self._temp = tempfile.TemporaryDirectory()
        shared_core.PROJECTS_ROOT = Path(self._temp.name)
        self.project_id = "res-handoff-fixture"
        self.root = shared_core.init_project_layout(self.project_id)
        protocol_store.ensure_protocol(self.project_id, actor="test")

    def tearDown(self):
        shared_core.PROJECTS_ROOT = self._old_projects_root
        self._temp.cleanup()

    def _write_and_register_snapshot(self, artifact_id="res-snapshot-1"):
        path = self.root / res.RES_CANONICAL_SNAPSHOT_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(valid_snapshot(), encoding="utf-8")
        protocol_store.register_artifact(
            self.project_id,
            artifact_id=artifact_id,
            artifact_class=res.RES_ARTIFACT_CLASS_SNAPSHOT,
            path=res.RES_CANONICAL_SNAPSHOT_PATH,
            sealed=True,
            actor="test",
        )
        protocol_store.record_continuity(
            self.project_id,
            continuity_id=artifact_id,
            kind=ContinuityKind.RESEARCH_EPISTEMIC_SHADOW,
            summary="current RES snapshot",
            artifact_ref=res.RES_CANONICAL_SNAPSHOT_PATH,
            actor="test",
        )
        return path

    def test_current_registered_res_allows_research_handoff(self):
        self._write_and_register_snapshot()
        out = res.handoff_readiness(self.project_id)
        self.assertTrue(out["ready"])
        self.assertEqual(out["status"], "HANDOFF_READY")
        self.assertEqual(out["authority_effect"], "NONE")

    def test_material_claim_after_res_makes_handoff_stale(self):
        self._write_and_register_snapshot()
        protocol_store.record_claim(
            self.project_id,
            claim_id="new-research-claim",
            kind="HYPOTHESIS",
            statement="new frontier",
            actor="test",
        )
        out = res.handoff_readiness(self.project_id)
        self.assertFalse(out["ready"])
        self.assertIn("RES_STALE_AFTER_MATERIAL_PROTOCOL_CHANGE", out["reasons"])

    def test_fake_continuity_ack_without_new_res_artifact_does_not_clear_staleness(self):
        self._write_and_register_snapshot()
        protocol_store.record_claim(
            self.project_id,
            claim_id="new-research-claim",
            kind="HYPOTHESIS",
            statement="new frontier",
            actor="test",
        )
        protocol_store.record_continuity(
            self.project_id,
            continuity_id="fake-res-ack",
            kind=ContinuityKind.RESEARCH_EPISTEMIC_SHADOW,
            summary="ack without updated artifact",
            artifact_ref=res.RES_CANONICAL_SNAPSHOT_PATH,
            actor="test",
        )
        out = res.handoff_readiness(self.project_id)
        self.assertFalse(out["ready"])
        self.assertIn("RES_STALE_AFTER_MATERIAL_PROTOCOL_CHANGE", out["reasons"])

    def test_registered_addendum_after_claim_restores_currentness_without_rewriting_snapshot(self):
        self._write_and_register_snapshot()
        material_event = protocol_store.record_claim(
            self.project_id,
            claim_id="new-research-claim",
            kind="HYPOTHESIS",
            statement="new frontier",
            actor="test",
        )
        addendum = create_addendum(event="RESEARCH_HANDOFF_CHECKPOINT")
        addendum["claims"][0]["provenance_refs"].append(f"protocol:event:{material_event.event_hash}")
        addendum_path = self.root / "continuity/research_epistemic_shadow/addenda/0001.json"
        addendum_path.write_text(json.dumps(addendum, indent=2) + "\n", encoding="utf-8")
        protocol_store.register_artifact(
            self.project_id,
            artifact_id="res-addendum-1",
            artifact_class=res.RES_ARTIFACT_CLASS_ADDENDUM,
            path="continuity/research_epistemic_shadow/addenda/0001.json",
            sealed=True,
            actor="test",
        )
        protocol_store.record_continuity(
            self.project_id,
            continuity_id="res-addendum-1",
            kind=ContinuityKind.RESEARCH_EPISTEMIC_SHADOW,
            summary="handoff RES addendum",
            artifact_ref="continuity/research_epistemic_shadow/addenda/0001.json",
            actor="test",
        )
        out = res.handoff_readiness(self.project_id)
        self.assertTrue(out["ready"])
        self.assertEqual(out["addendum_projection"]["addendum_count"], 1)


if __name__ == "__main__":
    unittest.main()
