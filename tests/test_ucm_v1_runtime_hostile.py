from __future__ import annotations

import copy
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baseline"))

import lab_tools
import ucm_v1_runtime as ucm
import user_continuity_store as backend
from test_ucm_v1_runtime import UcmFixture, candidate, collaboration, decision, fact, identity, provenance, referent, source_provenance, utility


class HostileContractTests(UcmFixture):
    def assert_code(self, code, fn):
        with self.assertRaises(ucm.UcmError) as ctx:
            fn()
        self.assertEqual(ctx.exception.error_code, code)

    def test_fact_extra_field_rejected(self):
        f = fact(); f["surprise"] = "schema drift"
        self.assert_code("UCM_CONTRACT_INVALID", lambda: ucm.validate_fact(f))

    def test_fact_missing_required_field_rejected(self):
        f = fact(); del f["descriptive_tags"]
        self.assert_code("UCM_CONTRACT_INVALID", lambda: ucm.validate_fact(f))

    def test_fact_authority_extra_field_rejected(self):
        f = fact(); f["authority"]["magic"] = True
        self.assert_code("UCM_CONTRACT_INVALID", lambda: ucm.validate_fact(f))

    def test_fact_verification_missing_required_ref_field_rejected(self):
        f = fact(); del f["verification"]["verification_ref"]
        self.assert_code("UCM_CONTRACT_INVALID", lambda: ucm.validate_fact(f))

    def test_fact_provenance_extra_field_rejected(self):
        f = fact(); f["provenance"][0]["authority"] = "smuggle"
        self.assert_code("UCM_CONTRACT_INVALID", lambda: ucm.validate_fact(f))

    def test_assistant_utility_extra_field_rejected(self):
        f = fact(); f["assistant_utility"]["truth_score"] = 100
        self.assert_code("UCM_CONTRACT_INVALID", lambda: ucm.validate_fact(f))

    def test_high_utility_never_changes_truth(self):
        self.assertFalse(ucm.utility_can_change_truth(utility(100)))

    def test_hydration_priority_never_changes_required_verification(self):
        f = fact(target_plane="PROJECT", requirement="REQUIRED", currentness="UNVERIFIED")
        f["assistant_utility"] = utility(100)
        validated = ucm.validate_fact(f)
        self.assertFalse(ucm.current_usable(validated))

    def test_required_verifier_available_without_ref_is_not_verified(self):
        f = fact(target_plane="PROJECT", requirement="REQUIRED", currentness="CURRENT", verified=True, verification_ref=None)
        self.assertFalse(ucm.current_usable(ucm.validate_fact(f)))

    def test_reporter_count_does_not_mint_independence(self):
        f = fact(); f["provenance"] = [provenance("same")[0], {**provenance("same")[0], "source_instance": "other"}]
        self.assertEqual(ucm.evidence_independence_count(f), 1)

    def test_recorded_at_does_not_override_asserted_or_observed_time(self):
        f = fact(); f["temporal"] = {"recorded_at": "2099-01-01", "asserted_at": "2025-01-01", "observed_at": "2024-01-01"}
        self.assertEqual(ucm.effective_fact_time(f), "2024-01-01")

    def test_project_local_scope_inference_does_not_become_global(self):
        self.assertEqual(ucm.infer_memory_scope("for this repo use X", "RECURRING_WORKFLOW"), "PROJECT_LOCAL")

    def test_sensitive_implicit_classification_is_propose_only(self):
        out = ucm.classify_durable_user_statement(semantic_kind="DURABLE_PERSONAL_FACT", durable=True, sensitivity="SENSITIVE")
        self.assertEqual(out["write_posture"], "PROPOSE_ONLY")
        self.assertEqual(out["proposed_operation"], "PROPOSE")

    def test_project_local_durable_statement_is_do_not_persist(self):
        out = ucm.classify_durable_user_statement(semantic_kind="PREFERENCE", durable=True, target_scope="PROJECT_LOCAL")
        self.assertEqual(out["write_posture"], "DO_NOT_PERSIST")

    def test_unknown_durable_semantic_kind_is_propose_only(self):
        out = ucm.classify_durable_user_statement(semantic_kind="GUESS", durable=True)
        self.assertEqual(out["write_posture"], "PROPOSE_ONLY")

    def test_collaboration_cannot_widen_authority_even_if_high_initiative(self):
        c = collaboration(); c["initiative"]["level"] = "HIGH"
        self.assertFalse(ucm.collaboration_can_widen_authority(c))

    def test_decision_can_never_be_project_authority(self):
        self.assertFalse(ucm.decision_can_be_project_authority(decision()))

    def test_session_reset_never_deletes_durable_memory_by_contract(self):
        self.assertFalse(ucm.session_reset_deletes_durable_memory())

    def test_manual_lock_overrides_automatic_write(self):
        ctl = ucm.default_control_state(); ctl["memory_admission_locked"] = True
        self.assertFalse(ucm.automatic_memory_write_allowed(ctl))

    def test_retrieval_failure_changes_strategy(self):
        first = ucm.next_retrieval_strategy(previous_strategy=None, previous_succeeded=False)
        second = ucm.next_retrieval_strategy(previous_strategy=first, previous_succeeded=False)
        third = ucm.next_retrieval_strategy(previous_strategy=second, previous_succeeded=False)
        self.assertEqual((first, second, third), ("EXACT_KEY", "SNAPSHOT_SHARD", "LEXICAL_STRUCTURED"))

    def test_semantic_locator_is_never_truth_authority(self):
        self.assertFalse(ucm.retrieval_strategy_is_truth_authority("SEMANTIC_LOCATOR"))

    def test_neutral_export_never_accepts_sensitive_portable_fact(self):
        f = fact(sensitivity="SECRET", export_class="PORTABLE")
        self.assertFalse(ucm.export_allowed(f, "NEUTRAL_SYSTEM"))


class HostileMutationTests(UcmFixture):
    def assert_code(self, code, fn):
        with self.assertRaises(ucm.UcmError) as ctx:
            fn()
        self.assertEqual(ctx.exception.error_code, code)

    def test_missing_head_hash_rejected_before_append(self):
        p = self.write(record_type="FACT", record=fact()); del p["expected_head_hash"]
        self.assert_code("UCM_CAS_REQUIRED", lambda: ucm.add(p))
        self.assertEqual(self.head()["ledger_head_seq"], 0)

    def test_missing_head_seq_rejected_before_append(self):
        p = self.write(record_type="FACT", record=fact()); del p["expected_head_seq"]
        self.assert_code("UCM_CAS_REQUIRED", lambda: ucm.add(p))
        self.assertEqual(self.head()["ledger_head_seq"], 0)

    def test_stale_head_hash_rejected_before_append(self):
        p = self.write(record_type="FACT", record=fact()); p["expected_head_hash"] = "0" * 64
        self.assert_code("UCM_CURRENTNESS_FAILURE", lambda: ucm.add(p))
        self.assertEqual(self.head()["ledger_head_seq"], 0)

    def test_missing_write_posture_rejected(self):
        p = self.write(record_type="FACT", record=fact()); del p["write_posture"]
        self.assert_code("UCM_WRITE_POSTURE_REQUIRED", lambda: ucm.add(p))

    def test_missing_write_provenance_rejected(self):
        p = self.write(record_type="FACT", record=fact()); del p["provenance"]
        self.assert_code("UCM_PROVENANCE_FAILURE", lambda: ucm.add(p))

    def test_project_authority_smuggling_rejected_before_append(self):
        p = self.write(record_type="FACT", record=fact(target_plane="PROJECT", source_role="AUTHORITATIVE", requirement="REQUIRED"))
        self.assert_code("AUTHORITY_FIREWALL", lambda: ucm.add(p))
        self.assertEqual(self.head()["ledger_head_seq"], 0)

    def test_sensitive_implicit_write_rejected_before_append(self):
        p = self.write(record_type="FACT", record=fact(sensitivity="SECRET"), write_posture="USER_STATED_DURABLE")
        self.assert_code("AUTHORITY_FIREWALL", lambda: ucm.add(p))
        self.assertEqual(self.head()["ledger_head_seq"], 0)

    def test_propose_only_cannot_create_active_fact(self):
        p = self.write(record_type="FACT", record=fact(), write_posture="PROPOSE_ONLY")
        self.assert_code("AUTHORITY_FIREWALL", lambda: ucm.add(p))
        self.assertEqual(self.head()["ledger_head_seq"], 0)

    def test_candidate_direct_write_posture_rejected(self):
        p = self.write(record_type="MEMORY_CANDIDATE", record=candidate(), write_posture="DIRECT_USER_AUTHORIZED")
        self.assert_code("AUTHORITY_FIREWALL", lambda: ucm.add(p))

    def test_generic_update_cannot_change_fact_value(self):
        self.add_record("FACT", fact("fact.a"))
        p = self.write(record_type="FACT", record_key="fact.a", patch={"value": "new"})
        self.assert_code("UCM_MATERIAL_CHANGE_REQUIRES_SUPERSEDE", lambda: ucm.update(p))

    def test_generic_update_cannot_forge_verification(self):
        self.add_record("FACT", fact("fact.a", target_plane="PROJECT", requirement="REQUIRED", currentness="UNVERIFIED"))
        p = self.write(record_type="FACT", record_key="fact.a", patch={"currentness": {"status": "CURRENT"}})
        self.assert_code("UCM_MATERIAL_CHANGE_REQUIRES_SUPERSEDE", lambda: ucm.update(p))

    def test_supersede_without_correction_evidence_rejected(self):
        self.add_record("FACT", fact("fact.a"))
        p = self.write(record_type="FACT", record_key="fact.a", replacement=fact("fact.a", value="new"), evidence_refs=[])
        self.assert_code("UCM_PROVENANCE_FAILURE", lambda: ucm.supersede(p))

    def test_supersede_cannot_move_stable_fact_key(self):
        self.add_record("FACT", fact("fact.a"))
        p = self.write(record_type="FACT", record_key="fact.a", replacement=fact("fact.b", value="new"), evidence_refs=["evidence:correction"])
        self.assert_code("UCM_STABLE_KEY_REQUIRED", lambda: ucm.supersede(p))

    def test_rediscover_active_fact_rejected(self):
        self.add_record("FACT", fact("fact.a"))
        p = self.write(fact_key="fact.a", evidence_refs=["evidence:return"])
        self.assert_code("UCM_REDISCOVERY_INVALID", lambda: ucm.rediscover(p))

    def test_forget_without_direct_user_authorization_rejected(self):
        self.add_record("FACT", fact("fact.a"))
        p = self.write(fact_key="fact.a", write_posture="USER_STATED_DURABLE")
        self.assert_code("AUTHORITY_FIREWALL", lambda: ucm.forget_request(p))

    def test_unlock_without_direct_user_authorization_rejected(self):
        p = self.write(lock="MEMORY_ADMISSION", write_posture="SYSTEM_MAINTENANCE")
        self.assert_code("AUTHORITY_FIREWALL", lambda: ucm.unlock(p))

    def test_session_reset_without_direct_user_authorization_rejected(self):
        p = self.write(scope="SESSION_ADAPTIVE", write_posture="SYSTEM_MAINTENANCE")
        self.assert_code("AUTHORITY_FIREWALL", lambda: ucm.session_reset(p))

    def test_candidate_confirmation_without_direct_user_authorization_rejected(self):
        self.add_record("MEMORY_CANDIDATE", candidate(), write_posture="PROPOSE_ONLY")
        p = self.write(candidate_id="candidate.a", user_confirmed=True, write_posture="SYSTEM_MAINTENANCE")
        self.assert_code("AUTHORITY_FIREWALL", lambda: ucm.memory_candidate_confirm(p))

    def test_core_headroom_failure_is_preappend_not_postappend(self):
        p = self.write(record_type="FACT", record=fact("fact.huge-core", value="x" * 10000))
        self.assert_code("UCM_CORE_BUDGET_EXCEEDED", lambda: ucm.add(p))
        self.assertEqual(self.head()["ledger_head_seq"], 0)


class HostileIngressTests(UcmFixture):
    def _append_unmaterialized_backend_update(self):
        state = backend.build_state(self.profile)
        event_id = "MEM-hostile-unmaterialized"
        body = backend._event_body(
            event_seq=state["event_count"] + 1,
            event_id=event_id,
            timestamp=backend._utc_now(),
            profile_id=self.profile,
            operation="UPDATE",
            provenance={"actor": "server", "source_instance": "hostile", "source_thread": None, "source_event": None, "evidence_independence_group": None},
            payload={"memory_id": next(iter(state["facts"])), "patch": {"confidence": "medium"}},
            previous_hash=state["head_hash"],
            idempotency_key="hostile-unmaterialized",
            request_fingerprint="f" * 64,
        )
        event = {**body, "event_hash": backend._sha256_json(body)}
        with backend._paths(self.profile).ledger.open("ab") as handle:
            handle.write(backend._canonical_bytes(event) + b"\n")
            handle.flush(); os.fsync(handle.fileno())
        with backend._CACHE_GUARD:
            backend._STATE_CACHE.clear()

    def test_missing_collaboration_contract_fails_exact_taxonomy(self):
        self.add_record("FACT", fact("fact.a"))
        with self.assertRaises(ucm.UcmError) as ctx:
            ucm.read_core(self.profile)
        self.assertEqual(ctx.exception.error_code, "USER_CONTINUITY_INCOMPLETE")

    def test_snapshot_behind_ledger_fails_ucm_currentness_taxonomy(self):
        self.initialize_ingress()
        self._append_unmaterialized_backend_update()
        with self.assertRaises(ucm.UcmError) as ctx:
            ucm.read_core(self.profile)
        self.assertEqual(ctx.exception.error_code, "UCM_CURRENTNESS_FAILURE")

    def test_context_packet_overflow_is_visible_not_silent_truncation(self):
        self.initialize_ingress(); self.add_record("FACT", fact("fact.a", value="x" * 1500))
        with self.assertRaises(ucm.UcmError) as ctx:
            ucm.compile_context_packet(self.profile, max_bytes=256)
        self.assertEqual(ctx.exception.error_code, "CONTEXT_PACKET_BUDGET_EXCEEDED")

    def test_search_relevance_never_becomes_claim_support(self):
        self.add_record("FACT", fact("fact.a", value="this explicitly says we do not claim universal closure"))
        out = ucm.search(self.profile, "universal closure")
        self.assertTrue(out["results"])
        self.assertFalse(out["results"][0]["search_hit_is_evidentiary_support"])

    def test_export_unknown_destination_rejected(self):
        with self.assertRaises(ucm.UcmError) as ctx:
            ucm.export_filtered(self.profile, "INTERNET")
        self.assertEqual(ctx.exception.error_code, "UCM_CONTRACT_INVALID")

    def test_source_assertion_requires_exact_sha256(self):
        bad = {"source_key": "s", "source_instance": "x", "artifact": "a", "sha256": "nope", "bytes": 1, "preservation": "CONTENT_ADDRESSED", "blob_path": None, "coverage": {}, "policy_absences": [], "source_role": "CONTINUITY", "export_class": "USER"}
        p = self.write(record_type="SOURCE_MANIFEST", record=bad)
        with self.assertRaises(ucm.UcmError) as ctx:
            ucm.add(p)
        self.assertEqual(ctx.exception.error_code, "UCM_PROVENANCE_FAILURE")


class HostileNativeDispatchTests(UcmFixture):
    def test_mutating_ucm_tool_still_requires_runtime_bound_approval(self):
        h = self.head()
        payload = {
            **self.write(record_type="FACT", record=fact()),
        }
        with patch.dict(os.environ, {"PCMMAD_LAB_POLICY_MODE": "strict"}, clear=False):
            with self.assertRaises(lab_tools.LabToolError) as ctx:
                lab_tools.dispatch_tool("ucm.add", payload)
        self.assertEqual(ctx.exception.error_code, "APPROVAL_REQUIRED")
        self.assertEqual(self.head()["ledger_head_seq"], h["ledger_head_seq"])

    def test_ucm_write_posture_does_not_smuggle_project_mutation_authority(self):
        spec = lab_tools._TOOL_REGISTRY["ucm.add"]
        self.assertNotIn("project_mutation_fenced", set(spec.effect_traits))
        self.assertIn("not_project_authority", set(spec.effect_traits))
        self.assertTrue(spec.mutating)

    def test_read_tool_contract_is_nonmutating(self):
        for name in ("ucm.describe", "ucm.head", "ucm.read_core", "ucm.search", "ucm.resolve_identity", "ucm.resolve_referent", "ucm.source_manifest"):
            spec = lab_tools._TOOL_REGISTRY[name]
            self.assertFalse(spec.mutating)
            self.assertEqual(spec.side_effect_class, "read")


if __name__ == "__main__":
    unittest.main()
