from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HANDOFF = PROJECT_ROOT / "handoff" / "current"
INGRESS = PROJECT_ROOT / "CURRENT_INGRESS.md"
MANIFEST = HANDOFF / "SNAPSHOT_MANIFEST_SHA256.json"


class GitHandoffCurrentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ingress = INGRESS.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.duality = (HANDOFF / "RUNTIME_OBE_SKILLS_DUALITY.md").read_text(
            encoding="utf-8"
        )

    def test_snapshot_manifest_hashes_all_declared_members(self) -> None:
        self.assertEqual(self.manifest["schema"], "pcmmad.git-handoff-snapshot.v1")
        self.assertIn("recovery mirror", self.manifest["authority_ceiling"])
        for name, spec in self.manifest["files"].items():
            path = HANDOFF / name
            self.assertTrue(path.is_file(), name)
            data = path.read_bytes()
            self.assertEqual(len(data), spec["bytes"], name)
            self.assertEqual(hashlib.sha256(data).hexdigest(), spec["sha256"], name)

    def test_required_icf_authority_and_history_surfaces_are_present(self) -> None:
        required = {
            "CURRENT_STATE.md",
            "ICF_CS_CURRENT.md",
            "INTENT_CONSTRAINT_FRONTIER_CONTINUITY_STANDARD.md",
            "CURRENT_CANONICAL_SOP_POINTER.md",
            "COMMANDERS_INTENT_CURRENT.md",
            "NEXT_STEPS.md",
            "DOCTRINE_SNAPSHOT.md",
            "REVISIT_LEDGER.md",
            "TRACE_MATRIX.md",
            "LIVE_SHADOW.md",
            "DESIGN_THREAD_STREAM.md",
            "ICF_CS_V1_0_MACHINE.json",
            "ICF_CS_CLAIM_CEILING.md",
            "ICF_CS_ADDENDUM_QUALIFICATION_RECEIPT.md",
            "RUNTIME_OBE_SKILLS_DUALITY.md",
            "SERVER_THREAD_HANDOFF_CURRENT.md",
            "NEW_THREAD_HANDOFF_PROMPT_CURRENT.md",
            "GIT_PUBLICATION_CURRENT.md",
            "A042_ENGINEERING_QUALIFICATION_2026-09-07.md",
            "wip/A042_PROJECT_MUTATION_AUTHORITY_WIP.py",
            "wip/A042_EXECUTION_ROUTES_WIP.py",
            "wip/A042_POWER_ROUTES_WIP.py",
            "wip/A042_WIP_INVENTORY.json",
        }
        self.assertTrue(required.issubset(set(self.manifest["files"])))

    def test_ingress_uses_qualified_version_agnostic_cold_start(self) -> None:
        self.assertIn(
            "CURRENT STATE -> ICF-CS -> CURRENT CANONICAL SOP + NEXT/DOCTRINE/REVISIT/TRACE -> LIVE SHADOW -> DTS -> LIVE READBACK BEFORE MUTATION",
            self.ingress,
        )
        self.assertIn(
            "CONFLICT -> RECOVERY/AUDIT -> LOCALIZE -> REPAIR/SUPERSEDE -> READBACK -> RESUME",
            self.ingress,
        )
        self.assertIn("CURRENT_INGRESS_POINTER != CURRENT_STATE_PROOF", self.ingress)
        self.assertIn("GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION", self.ingress)
        self.assertIn("INTENT IS A CONSTRAINT, NOT A CEILING", self.ingress)

    def test_ingress_points_to_cross_thread_meeting_surfaces(self) -> None:
        for rel in (
            "reports/PCMMAD_RUNTIME_ADAPTER_COMPATIBILITY_CONTRACT_V0_1.md",
            "reports/PCMMAD_RUNTIME_ADAPTER_PROJECTION_MATRIX_V0_1.md",
            "reports/PCMMAD_RUNTIME_ADAPTER_PROJECTION_MATRIX_V0_1.json",
            "handoff/current/RUNTIME_OBE_SKILLS_DUALITY.md",
        ):
            self.assertIn(rel, self.ingress)
            self.assertTrue((PROJECT_ROOT / rel).exists(), rel)

    def test_runtime_skill_duality_preserves_authority_boundaries(self) -> None:
        required = (
            "TRANSPORT IS NOT ARCHITECTURE AUTHORITY",
            "MECHANISM LIVES WHERE STATE LIVES",
            "A second PCMMAD ontology SHALL NOT emerge in the Skill thread",
            "EMERGENT CAPABILITY IS ALLOWED. EMERGENT AUTHORITY IS NOT",
            "LONG-RUNNING WORK SHALL NOT REQUIRE LONG-RUNNING MODEL ATTENTION",
            "final OBE↔Runtime interface vocabulary SHALL NOT freeze",
        )
        for text in required:
            self.assertIn(text, self.duality)

    def test_snapshot_does_not_claim_live_authority(self) -> None:
        combined = self.ingress + "\n" + self.duality
        self.assertIn("recovery mirror", combined.lower())
        self.assertIn("fresh Git/local/runtime readback", combined)
        self.assertIn("V30_WORKING_TREE_SUCCESS != RELEASE_QUALIFICATION != LIVE_DEPLOYMENT", combined)

    def test_rollover_frontier_is_current_and_historical_wip_is_not_authority(self) -> None:
        handoff = (HANDOFF / "SERVER_THREAD_HANDOFF_CURRENT.md").read_text(encoding="utf-8")
        self.assertIn("a97a00f67f3b79dbbe18e092d29b8971e588d4a2", handoff)
        self.assertIn("QUALIFIED 23-file engineering candidate", handoff)
        self.assertIn("e2dcb52475bf5869b6f3ebc4561955e27ef52669291bb7e06aa96ca196b2f31e", handoff)
        self.assertIn("345 collected / 344 passed / 0 failed / 1 conditional skip", handoff)
        self.assertIn("SESSION_IDENTITY != FENCED_MUTATION_AUTHORITY", handoff)
        self.assertIn("A-001", handoff)
        self.assertIn("Final schema", handoff)

    def test_wip_recovery_copy_matches_declared_a042_identity(self) -> None:
        path = HANDOFF / "wip" / "A042_PROJECT_MUTATION_AUTHORITY_WIP.py"
        self.assertTrue(path.is_file())
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), "5e294d1ae20601d9a5404f5b4712d82c676ca6acc55c9530a5787dc6239ed04e")
        self.assertEqual(path.stat().st_size, 20926)

    def test_a042_wip_inventory_is_complete_and_hashes_recovery_copies(self) -> None:
        inventory = json.loads((HANDOFF / "wip" / "A042_WIP_INVENTORY.json").read_text(encoding="utf-8"))
        self.assertEqual(inventory["schema"], "pcmmad.a042-wip-recovery.v2")
        self.assertEqual(inventory["file_count"], 13)
        self.assertEqual(len(inventory["files"]), 13)
        sources = {row["source_path"] for row in inventory["files"]}
        self.assertIn("baseline/pcmmad_receiver/execution_routes.py", sources)
        self.assertIn("baseline/pcmmad_receiver/power_routes.py", sources)
        for row in inventory["files"]:
            path = HANDOFF / row["recovery_path"]
            self.assertTrue(path.is_file(), row["recovery_path"])
            data = path.read_bytes()
            self.assertEqual(len(data), row["bytes"], row["recovery_path"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"], row["recovery_path"])

    def test_new_thread_prompt_preserves_current_frontier_and_claim_ceiling(self) -> None:
        prompt = (HANDOFF / "NEW_THREAD_HANDOFF_PROMPT_CURRENT.md").read_text(encoding="utf-8")
        self.assertIn("QUALIFIED 23-file engineering candidate", prompt)
        self.assertIn("345 collected / 344 passed / 0 failed / 1 conditional skip", prompt)
        self.assertIn("SESSION_IDENTITY != FENCED_MUTATION_AUTHORITY", prompt)
        self.assertIn("RuntimeAuthorityEnvelope", prompt)
        self.assertIn("A-001", prompt)
        self.assertIn("Final schema", prompt)

    def test_a001_currentness_lineage_is_preserved_without_staling_current_ingress(self) -> None:
        handoff = (HANDOFF / "SERVER_THREAD_HANDOFF_CURRENT.md").read_text(encoding="utf-8")
        prompt = (HANDOFF / "NEW_THREAD_HANDOFF_PROMPT_CURRENT.md").read_text(encoding="utf-8")
        qualification = (HANDOFF / "HANDOFF_QUALIFICATION.md").read_text(encoding="utf-8")
        for text in (handoff, prompt, qualification):
            self.assertIn("expected_contract_digest", text)
            self.assertIn("CAPABILITY_CONTRACT_STALE", text)
            self.assertIn("352 collected / 351 passed / 0 failed / 1 conditional skip", text)
            self.assertIn("IDEMPOTENCY_INDEX != CONSEQUENCE_AUTHORITY", text)
            self.assertIn("RETRY_SAFETY_REQUIRES_DURABLE_PRE_POST_CONSEQUENCE_WITNESS", text)
            self.assertIn("364 collected / 363 passed / 0 failed / 1 conditional skip", text)
        self.assertIn("expected_contract_digest", self.ingress)
        self.assertIn("CAPABILITY_CONTRACT_STALE", self.ingress)
        self.assertIn("IDEMPOTENCY_INDEX != CONSEQUENCE_AUTHORITY", self.ingress)
        self.assertIn("RETRY_SAFETY_REQUIRES_DURABLE_PRE_POST_CONSEQUENCE_WITNESS", self.ingress)
        self.assertIn("UNPROVEN_EFFECTS_DEFAULT_TO_UNSAFE_RETRY", self.ingress)
        self.assertIn("Windows Job Object resource envelope", self.ingress)
        self.assertIn("Final schema redesign remains LAST", self.ingress)

    def test_ingress_tracks_current_published_frontier_not_historical_candidate(self) -> None:
        self.assertIn("8714dd87d2092e0f4c66f261fcf5cee8b75a0798", self.ingress)
        self.assertIn("126 native tools", self.ingress)
        self.assertIn("continuity.res.handoff.readiness", self.ingress)
        self.assertIn("RES_CONTENT != GOVERNING_DOCTRINE", self.ingress)
        self.assertIn("RUNTIME_RES_EMBODIMENT != ICF_CS_SUCCESSOR_RELEASE", self.ingress)
        self.assertIn("SESSION_IDENTITY != FENCED_MUTATION_AUTHORITY", self.ingress)
        self.assertIn("runtime-authority-envelope-v1", self.ingress)
        self.assertIn("Final schema redesign remains LAST", self.ingress)
        self.assertNotIn("7/8 PASS", self.ingress)
        self.assertNotIn("328 PASS / 2 FAIL", self.ingress)



if __name__ == "__main__":
    unittest.main()
