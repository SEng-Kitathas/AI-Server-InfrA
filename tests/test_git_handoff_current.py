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
        cls.commander = (HANDOFF / "COMMANDERS_INTENT_CURRENT.md").read_text(encoding="utf-8")
        cls.canonical_pointer = (HANDOFF / "CURRENT_CANONICAL_SOP_POINTER.md").read_text(encoding="utf-8")
        cls.claim_ceiling = (HANDOFF / "ICF_CS_CLAIM_CEILING.md").read_text(encoding="utf-8")
        cls.server_handoff = (HANDOFF / "SERVER_THREAD_HANDOFF_CURRENT.md").read_text(encoding="utf-8")
        cls.new_thread = (HANDOFF / "NEW_THREAD_HANDOFF_PROMPT_CURRENT.md").read_text(encoding="utf-8")
        cls.git_current = (HANDOFF / "GIT_PUBLICATION_CURRENT.md").read_text(encoding="utf-8")
        cls.schema_current = (HANDOFF / "SCHEMA_CURRENT.md").read_text(encoding="utf-8")
        cls.rollover = (HANDOFF / "THREAD_ROLLOVER_CURRENT.md").read_text(encoding="utf-8")

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
            "ICF_CS_V1_2_MACHINE.json",
            "ICF_CS_V1_2_FRESH_INSTANCE_CONTRACT.json",
            "ICF_CS_V1_2_ACTIVATION_RECEIPT_2026-09-09.json",
            "ICF_CS_V1_2_DETACHED_RELEASE_RECEIPT_2026-09-09.json",
            "ICF_CS_CLAIM_CEILING.md",
            "ICF_CS_ADDENDUM_QUALIFICATION_RECEIPT.md",
            "RUNTIME_OBE_SKILLS_DUALITY.md",
            "SERVER_THREAD_HANDOFF_CURRENT.md",
            "NEW_THREAD_HANDOFF_PROMPT_CURRENT.md",
            "GIT_PUBLICATION_CURRENT.md",
            "SCHEMA_CURRENT.md",
            "A042_ENGINEERING_QUALIFICATION_2026-09-07.md",
            "A042_HISTORICAL_WIP_RECOVERY_POINTER.md",
        }
        self.assertTrue(required.issubset(set(self.manifest["files"])))

    def test_ingress_uses_qualified_version_agnostic_cold_start(self) -> None:
        self.assertIn(
            "CURRENT STATE -> CURRENT ICF-CS -> CURRENT CANONICAL SOP + NEXT/DOCTRINE/REVISIT/TRACE -> LIVE SHADOW -> DTS -> RES APPLICABILITY/CURRENTNESS -> UCM APPLICABILITY + SYSTEM DESCRIPTOR + USER STORE HEAD -> BOUNDED UCM CORE -> TASK-RELEVANT LAZY UCM HYDRATION -> OWNING-PLANE LIVE VERIFICATION -> LIVE READBACK BEFORE MUTATION",
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

    def test_current_server_handoff_tracks_v11_schema_successor_frontier(self) -> None:
        self.assertIn("e1b2b8eddd92e8ad9159a548f9e6d6b2beb895f4", self.server_handoff)
        self.assertIn("7e4c66a769884269d71babdb92217ba80eb66e74", self.server_handoff)
        self.assertIn("8 operations / 158 native capabilities", self.server_handoff)
        self.assertIn("34541018742", self.server_handoff)
        self.assertIn("Ubuntu cleanbox: **SUCCESS**", self.server_handoff)
        self.assertIn("Windows cleanbox: **FAILURE**", self.server_handoff)
        self.assertIn("ICF-CS: v1.2", self.server_handoff)
        self.assertIn("project-aware access logging", self.server_handoff)
        self.assertIn("12ccc208ec2e9183e3b280618f266211cc00179b", self.server_handoff)
        self.assertIn("SOURCE_SCHEMA_PUBLISHED != PRODUCT_SCHEMA_INSTALLED", self.server_handoff)
        self.assertIn("SOURCE_QUALIFIED != LIVE_PROMOTED", self.server_handoff)



    def test_wip_recovery_copy_matches_declared_a042_identity(self) -> None:
        path = PROJECT_ROOT / "handoff" / "archive" / "a042_wip_recovery_2026-09-07" / "A042_PROJECT_MUTATION_AUTHORITY_WIP.py"
        self.assertTrue(path.is_file())
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), "5e294d1ae20601d9a5404f5b4712d82c676ca6acc55c9530a5787dc6239ed04e")
        self.assertEqual(path.stat().st_size, 20926)

    def test_a042_wip_inventory_is_complete_and_hashes_recovery_copies(self) -> None:
        inventory = json.loads((PROJECT_ROOT / "handoff" / "archive" / "a042_wip_recovery_2026-09-07" / "A042_WIP_INVENTORY.json").read_text(encoding="utf-8"))
        self.assertEqual(inventory["schema"], "pcmmad.a042-wip-recovery.v2")
        self.assertEqual(inventory["file_count"], 13)
        self.assertEqual(len(inventory["files"]), 13)
        sources = {row["source_path"] for row in inventory["files"]}
        self.assertIn("baseline/pcmmad_receiver/execution_routes.py", sources)
        self.assertIn("baseline/pcmmad_receiver/power_routes.py", sources)
        for row in inventory["files"]:
            path = PROJECT_ROOT / "handoff" / "archive" / "a042_wip_recovery_2026-09-07" / Path(row["recovery_path"]).name
            self.assertTrue(path.is_file(), row["recovery_path"])
            data = path.read_bytes()
            self.assertEqual(len(data), row["bytes"], row["recovery_path"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"], row["recovery_path"])

    def test_new_thread_prompt_preserves_v11_frontier_and_claim_ceiling(self) -> None:
        self.assertIn("e1b2b8eddd92e8ad9159a548f9e6d6b2beb895f4", self.new_thread)
        self.assertIn("7e4c66a769884269d71babdb92217ba80eb66e74", self.new_thread)
        self.assertIn("8 operations over 158 native capabilities", self.new_thread)
        self.assertIn("34541018742", self.new_thread)
        self.assertIn("Ubuntu cleanbox **SUCCESS**", self.new_thread)
        self.assertIn("Windows cleanbox **FAILURE**", self.new_thread)
        self.assertIn("12ccc208ec2e9183e3b280618f266211cc00179b", self.new_thread)
        self.assertIn("schema-wire WIP is stale donor material", self.new_thread)
        self.assertIn("Loaded live Runtime is older", self.new_thread)
        self.assertIn("LOCAL_GREEN != HOSTED_CLEANBOX_GREEN", self.new_thread)
        self.assertIn("SOURCE_QUALIFIED != LIVE_PROMOTED", self.new_thread)



    def test_rollover_frontier_is_current_and_release_blocker_is_explicit(self) -> None:
        head = "e1b2b8eddd92e8ad9159a548f9e6d6b2beb895f4"
        tree = "8fbded01e519a938ded1f2177378cd6693d788b7"
        for text in (self.ingress, self.server_handoff, self.new_thread, self.git_current, self.rollover):
            self.assertIn(head, text)
        self.assertIn(tree, self.ingress)
        self.assertIn(tree, self.git_current)
        for text in (self.ingress, self.server_handoff, self.new_thread, self.git_current, self.rollover):
            self.assertIn("34541018742", text)
        self.assertIn("Add project-aware access logging", self.git_current)
        self.assertIn("12ccc208ec2e9183e3b280618f266211cc00179b", self.rollover)
        self.assertIn("HOSTED_UBUNTU_GREEN != HOSTED_WINDOWS_GREEN", self.rollover)
        self.assertIn("SOURCE_QUALIFIED != LIVE_PROMOTED", self.server_handoff)
        self.assertIn("LOCAL_GREEN != HOSTED_CLEANBOX_GREEN", self.new_thread)


    def test_latest_completed_hosted_parent_run_supersedes_old_both_red_status(self) -> None:
        for text in (self.ingress, self.server_handoff, self.new_thread, self.git_current, self.rollover):
            self.assertIn("fd9b42ad143d70ddda92b22372cbae767b12bea0", text)
            self.assertIn("34541018742", text)
        self.assertIn("Ubuntu cleanbox: **SUCCESS**", self.git_current)
        self.assertIn("Windows cleanbox: **FAILURE**", self.git_current)
        self.assertIn("Ubuntu cleanbox **SUCCESS**", self.new_thread)
        self.assertIn("Windows cleanbox **FAILURE**", self.new_thread)
        self.assertIn("generic exit code 1", self.rollover)

    def test_historical_a001_lineage_is_preserved_without_forcing_old_state_into_current_pointers(self) -> None:
        qualification = (HANDOFF / "HANDOFF_QUALIFICATION.md").read_text(encoding="utf-8")
        for text in (
            "expected_contract_digest",
            "CAPABILITY_CONTRACT_STALE",
            "352 collected / 351 passed / 0 failed / 1 conditional skip",
            "IDEMPOTENCY_INDEX != CONSEQUENCE_AUTHORITY",
            "RETRY_SAFETY_REQUIRES_DURABLE_PRE_POST_CONSEQUENCE_WITNESS",
            "364 collected / 363 passed / 0 failed / 1 conditional skip",
        ):
            self.assertIn(text, qualification)
        self.assertIn("expected_contract_digest", self.ingress)
        self.assertIn("CAPABILITY_CONTRACT_STALE", self.ingress)
        self.assertIn("IDEMPOTENCY_INDEX != CONSEQUENCE_AUTHORITY", self.ingress)
        self.assertIn("RETRY_SAFETY_REQUIRES_DURABLE_PRE_POST_CONSEQUENCE_WITNESS", self.ingress)
        self.assertIn("UNPROVEN_EFFECTS_DEFAULT_TO_UNSAFE_RETRY", self.ingress)
        self.assertIn("SOURCE_SCHEMA_PUBLISHED != PRODUCT_SCHEMA_INSTALLED", self.ingress)
        self.assertNotIn("Final schema redesign remains LAST / locked / untriggered", self.ingress)


    def test_ingress_tracks_current_published_frontier_not_historical_candidate(self) -> None:
        self.assertIn("7e4c66a769884269d71babdb92217ba80eb66e74", self.ingress)
        self.assertIn("967f108f235b4b42097f4b2d9d48ee61c591017c", self.ingress)
        self.assertIn("92010b57dfc275dd6f9753121cd8def98792ed41", self.ingress)
        self.assertIn("158 native", self.ingress)
        self.assertIn("v11.0", self.ingress)
        self.assertIn("8 Assistant-facing operations", self.ingress)
        self.assertIn("876 passed", self.ingress)
        self.assertIn("127/127 PASS", self.ingress)
        self.assertIn("SCHEMA_CURRENT.md", self.ingress)
        self.assertIn("CAPABILITY_LEASE != CAPABILITY_GRANT", self.ingress)
        self.assertIn("DECLARED_EFFECT_CLASS != VERIFIED_EFFECT_TRUTH", self.ingress)
        self.assertIn("CONTINUATION != CURRENTNESS", self.ingress)
        self.assertIn("PLAN_VM != SECOND_JOB_SCHEDULER", self.ingress)
        self.assertIn("SOURCE_SCHEMA_PUBLISHED != PRODUCT_SCHEMA_INSTALLED", self.ingress)
        self.assertIn("PATH_CONTAINMENT != INODE_OWNERSHIP", self.ingress)
        self.assertIn("PACKAGE_IMPORT_WORKS != SINGLE_RUNTIME_IDENTITY", self.ingress)
        self.assertIn("OBSERVATION != RECONCILIATION", self.ingress)
        self.assertIn("continuity.ingress.rehydrate", self.ingress)
        self.assertIn("31 canonical `ucm.*` tools", self.ingress)
        self.assertIn("ICF-CS v1.2", self.ingress)
        self.assertIn("f966029496fd6e31a76a36a6e967db37ca2147acfa890a880426ae6a7fa79d92", self.ingress)
        self.assertIn("RES_CONTENT != GOVERNING_DOCTRINE", self.ingress)
        self.assertIn("UCM != PROJECT_AUTHORITY", self.ingress)
        self.assertIn("MISSING != NOT_APPLICABLE", self.ingress)
        self.assertIn("SESSION_IDENTITY != FENCED_MUTATION_AUTHORITY", self.ingress)
        self.assertIn("runtime-authority-envelope-v1", self.ingress)
        self.assertNotIn("Final schema redesign remains LAST / locked / untriggered", self.ingress)
        self.assertNotIn("7/8 PASS", self.ingress)
        self.assertNotIn("328 PASS / 2 FAIL", self.ingress)



    def test_current_schema_pointer_binds_v11_source_successor_and_v10_compatibility(self) -> None:
        self.assertIn("V11 SOURCE SUCCESSOR PUBLISHED", self.schema_current)
        self.assertIn("ee62b261d6e5518b585faccd4af21a42d9b7bd6b3dc63f8af0e1242ef9fb9010", self.schema_current)
        self.assertIn("Operations: **8**", self.schema_current)
        self.assertIn("Capabilities covered: **158**", self.schema_current)
        self.assertIn("Effect-truth verified: **0**", self.schema_current)
        self.assertIn("v10.3 compatibility remains present", self.schema_current)
        self.assertIn("SOURCE_SCHEMA_PUBLISHED != PRODUCT_SCHEMA_INSTALLED", self.schema_current)

    def test_current_icf_pointer_and_claim_ceiling_are_v12_not_stale_v11_v10(self) -> None:
        self.assertIn("Active additive continuity/process doctrine: **ICF-CS v1.2**", self.canonical_pointer)
        self.assertIn("f966029496fd6e31a76a36a6e967db37ca2147acfa890a880426ae6a7fa79d92", self.canonical_pointer)
        self.assertNotIn("Active additive continuity/process doctrine: ICF-CS v1.1", self.canonical_pointer)
        self.assertTrue(self.claim_ceiling.startswith("# ICF-CS v1.2 — Claim Ceiling"))
        self.assertIn("RES_CONTENT != GOVERNING_DOCTRINE", self.claim_ceiling)
        self.assertIn("UCM != PROJECT_AUTHORITY", self.claim_ceiling)

    def test_commander_current_precedence_supersedes_retained_historical_body(self) -> None:
        marker = "## ROLLOVER PRECEDENCE — 2026-09-10 18:40 ET"
        self.assertIn(marker, self.commander)
        self.assertIn("e1b2b8eddd92e8ad9159a548f9e6d6b2beb895f4", self.commander)
        self.assertIn("34537723493", self.commander)
        self.assertIn("38 != 50", self.commander)
        self.assertIn("12ccc208ec2e9183e3b280618f266211cc00179b", self.commander)
        self.assertIn("checkpoints/THREAD_ROLLOVER_CHECKPOINT_2026-09-10.md", self.commander)



    def test_manifest_top_level_metadata_tracks_v11_source_successor(self) -> None:
        self.assertEqual(self.manifest["engineering_feature_head"], "e1b2b8eddd92e8ad9159a548f9e6d6b2beb895f4")
        self.assertEqual(self.manifest["engineering_feature_tree"], "8fbded01e519a938ded1f2177378cd6693d788b7")
        self.assertEqual(self.manifest["substrate_feature_head"], "673e3b15fa16053e6da6594604d9ce6db7faad1c")
        self.assertEqual(self.manifest["current_source_tool_count"], 158)
        self.assertEqual(self.manifest["current_icf_cs_version"], "1.2")
        self.assertEqual(self.manifest["current_icf_cs_standard_sha256"], "f966029496fd6e31a76a36a6e967db37ca2147acfa890a880426ae6a7fa79d92")
        self.assertIn("HOSTED_CI_RED", self.manifest["current_source_qualification"])
        self.assertEqual(self.manifest["final_schema"], "V11_SOURCE_SUCCESSOR_PUBLISHED_PRODUCT_INSTALLATION_PENDING")
        self.assertEqual(self.manifest["schema_v11"]["operations"], 8)
        self.assertEqual(self.manifest["schema_v11"]["native_capabilities"], 158)
        self.assertEqual(self.manifest["schema_v11"]["effect_truth_verified"], 0)
        self.assertIn("CONVERGED", self.manifest["architecture_status"])
        self.assertIn("4 generic behavior consumers", self.manifest["effect_trait_status"])


    def test_current_pointer_set_has_current_source_and_v11_schema_boundaries(self) -> None:
        for text in (self.git_current, self.server_handoff, self.new_thread):
            self.assertIn("e1b2b8eddd92e8ad9159a548f9e6d6b2beb895f4", text)
            self.assertIn("7e4c66a769884269d71babdb92217ba80eb66e74", text)
            self.assertIn("34541018742", text)
        self.assertIn("Ubuntu cleanbox: **SUCCESS**", self.git_current)
        self.assertIn("Windows cleanbox: **FAILURE**", self.git_current)
        self.assertIn("final exact-Git live promotion/restart/readback", self.server_handoff)
        self.assertIn("canonical restart", self.new_thread)
        self.assertIn("GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION", self.git_current)
        self.assertIn("SOURCE_SCHEMA_PUBLISHED != PRODUCT_SCHEMA_INSTALLED", self.server_handoff)



    def test_runtime_skill_duality_supersedes_obsolete_contract_digest_gap(self) -> None:
        self.assertIn("## 2026-09-10 current reconciliation", self.duality)
        self.assertIn("expected_contract_digest", self.duality)
        self.assertIn("historical and superseded", self.duality)
        self.assertIn("Current Runtime implements and tests that binding", self.duality)
        self.assertIn("CORE_RUNTIME_ARCHITECTURE_CONVERGED != FINAL_COMPOSITION_SCHEMA_COMPLETE", self.duality)

    def test_effect_trait_truth_boundary_is_explicit_in_current_ingress(self) -> None:
        self.assertIn("204 distinct trait strings", self.ingress)
        self.assertIn("only four currently alter Runtime behavior", self.ingress)
        self.assertIn("TRAIT_DECLARED != PROPERTY_HELD_BY_TYPE_SYSTEM", self.ingress)
        self.assertIn("DESCRIPTIVE_EFFECT != SCHEDULING_AUTHORITY", self.ingress)
        self.assertIn("DECLARED_EFFECT_CLASS != VERIFIED_EFFECT_TRUTH", self.ingress)
        self.assertIn("zero", self.ingress.lower())
        self.assertIn("legacy `memory.*`", self.ingress)





if __name__ == "__main__":
    unittest.main()
