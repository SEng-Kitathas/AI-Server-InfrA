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


if __name__ == "__main__":
    unittest.main()
