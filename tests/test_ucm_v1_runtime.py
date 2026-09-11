from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baseline"))

import lab_tools
import ucm_v1_runtime as ucm
import user_continuity_store as backend


NOW = "2026-09-09T12:00:00+00:00"


def provenance(label="fixture"):
    return [{
        "source_instance": "test",
        "source_artifact": f"artifact:{label}",
        "source_pointer": "L1-L2",
        "independence_group": f"ind:{label}",
    }]


def source_provenance(label="fixture"):
    return {
        "source_artifact": f"artifact:{label}",
        "source_pointer": "L1-L2",
        "independence_group": f"ind:{label}",
    }


def utility(priority=20):
    return {
        "why_it_matters": "fixture utility",
        "expected_reuse": "HIGH",
        "decision_impact": "MEDIUM",
        "retrieval_cues": ["fixture", "continuity"],
        "recurrence_count": 2,
        "rediscovery_cost": "MEDIUM",
        "negative_instruction": False,
        "unresolved_dependency": False,
        "contradiction_risk": "LOW",
        "staleness_risk": "LOW",
        "hydration_priority": priority,
        "usage": {"offered_count": 0, "hydrated_count": 0, "consumed_count": 0, "decision_use_count": 0},
    }


def fact(key="fact.alpha", *, value="alpha", tags=None, target_plane="USER_CONTINUITY", source_role="CONTINUITY", currentness="CURRENT", requirement="NOT_REQUIRED", verified=False, verification_ref=None, sensitivity="NORMAL", export_class="USER", groups=None):
    return {
        "fact_key": key,
        "value": value,
        "descriptive_tags": list(tags or ["USER_PREFERENCE"]),
        "lifecycle": "ACTIVE",
        "authority": {"target_plane": target_plane, "source_role": source_role},
        "currentness": {"status": currentness, "last_verified_at": NOW if verified else None},
        "verification": {"requirement": requirement, "verified_live": verified, "verification_ref": verification_ref, "revalidate_after": None, "revalidate_when": []},
        "temporal": {"recorded_at": NOW, "asserted_at": NOW, "observed_at": None},
        "provenance": provenance(key),
        "sensitivity": sensitivity,
        "export_class": export_class,
        "hydration_groups": list(groups or ["global_constraints"]),
        "relations": [],
        "assistant_utility": utility(),
    }


def collaboration(key="collab.current"):
    return {
        "contract_key": key,
        "scope": ["*"],
        "addressing": {"identity_use": "NORMAL_ADDRESS", "ceremony": "MINIMAL"},
        "control_signals": [{"signal": "Proceed", "meaning": "continue current authorized work", "urgency_implied": False, "authorization_effect": "NONE"}],
        "communication": {"verbosity": "adaptive"},
        "initiative": {"level": "HIGH", "challenge_when_evidence_warrants": True, "suggest_improvements": True},
        "correction": {"style": "direct"},
        "teaching": {"progression": "evidence-first"},
        "output": {"default": "compact"},
        "authority_boundary": {"preference_grants_tool_authority": False, "preference_grants_project_authority": False},
        "provenance": provenance("collaboration"),
    }


def identity(key, value, kind="PREFERRED_NAME", use="NORMAL_ADDRESS", precedence=50, status="ACTIVE", scope=None):
    return {"identity_key": key, "kind": kind, "value": value, "status": status, "use_for": [use], "scope": list(scope or ["*"]), "precedence": precedence, "valid_from": None, "valid_to": None, "provenance": provenance(key)}


def referent(key, term, meaning, *, precedence=50, status="ACTIVE", scope=None):
    return {"referent_key": key, "term": term, "meaning": meaning, "status": status, "scope": list(scope or ["*"]), "precedence": precedence, "supersedes": [], "provenance": provenance(key)}


def decision(key="decision.a", status="ACTIVE"):
    return {"decision_id": key, "scope": ["global"], "statement": "composition before invention", "status": status, "authority_owner": "USER", "rationale": "avoid duplicate mechanisms", "evidence_refs": ["evidence:user"], "alternatives": ["invent first"], "supersession_triggers": ["new evidence"], "related_fact_keys": [], "created_at": NOW, "provenance": provenance(key)}


def candidate(key="candidate.a"):
    return {"candidate_id": key, "proposed_fact_key": "fact.proposed", "signal_type": "REPEATED_PREFERENCE", "proposal": {"value": "maybe"}, "source_role": "INFERENCE", "write_posture": "PROPOSE_ONLY", "status": "PENDING_USER_CONFIRMATION", "evidence_refs": ["event:1"], "created_at": NOW}


class UcmFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pcmmad-ucm-v1-")
        self.old_root = backend.MEMORY_ROOT
        backend.MEMORY_ROOT = Path(self.temp.name) / "memory"
        with backend._CACHE_GUARD:
            backend._STATE_CACHE.clear()
        with backend._LOCKS_GUARD:
            backend._PROFILE_LOCKS.clear()
        self.profile = "test-user"

    def tearDown(self):
        backend.MEMORY_ROOT = self.old_root
        with backend._CACHE_GUARD:
            backend._STATE_CACHE.clear()
        with backend._LOCKS_GUARD:
            backend._PROFILE_LOCKS.clear()
        self.temp.cleanup()

    def head(self):
        return ucm.head(self.profile)

    def write(self, **extra):
        h = self.head()
        payload = {
            "profile_id": self.profile,
            "actor": "assistant",
            "source_instance": "test",
            "provenance": source_provenance(extra.pop("label", "write")),
            "idempotency_key": extra.pop("idempotency_key", f"idem-{h['ledger_head_seq']+1}"),
            "expected_head_seq": h["ledger_head_seq"],
            "expected_head_hash": h["ledger_head_hash"],
            "write_posture": extra.pop("write_posture", "DIRECT_USER_AUTHORIZED"),
        }
        payload.update(extra)
        return payload

    def add_record(self, record_type, record, **extra):
        return ucm.add(self.write(record_type=record_type, record=record, **extra))

    def initialize_ingress(self):
        self.add_record("COLLABORATION_CONTRACT", collaboration(), idempotency_key="collab")


class ContractAndCompositionTests(UcmFixture):
    def test_system_descriptor_matches_donor_identity_and_authority(self):
        out = ucm.describe()
        d = out["system_descriptor"]
        self.assertEqual(d["version"], "1.0")
        self.assertEqual(d["donor_archive_sha256"], "055a25fd8c02856d2a875aadc714dfa4ff49c0edeb0e63dd4d67415849fd5909")
        self.assertEqual(set(d["authority_traits"]), set(ucm.AUTHORITY_TRAITS))
        self.assertEqual(sum(len(v) for v in d["logical_operations"].values()), 31)

    def test_all_31_ucm_tools_registered_in_existing_memory_family(self):
        names = sorted(n for n in lab_tools._TOOL_REGISTRY if n.startswith("ucm."))
        self.assertEqual(len(names), 31)
        self.assertEqual({lab_tools._TOOL_REGISTRY[n].category for n in names}, {"memory"})
        self.assertEqual(len([n for n in lab_tools._TOOL_REGISTRY if n.startswith("memory.")]), 8)

    def test_all_ucm_tools_expose_contract_digests_and_authority_traits(self):
        for name, spec in lab_tools._TOOL_REGISTRY.items():
            if not name.startswith("ucm."):
                continue
            self.assertTrue(spec.contract_digest)
            traits = set(spec.effect_traits)
            self.assertTrue(set(ucm.AUTHORITY_TRAITS).issubset(traits))

    def test_stale_tool_contract_rejected_before_handler(self):
        name = "ucm.describe"
        with self.assertRaises(lab_tools.LabToolError) as ctx:
            lab_tools.dispatch_tool(name, {}, expected_contract_digest="0" * 64)
        self.assertEqual(ctx.exception.error_code, "CAPABILITY_CONTRACT_STALE")

    def test_existing_backend_remains_single_authoritative_ledger(self):
        self.initialize_ingress()
        paths = backend._paths(self.profile)
        self.assertTrue(paths.ledger.is_file())
        self.assertTrue(paths.current.is_file())
        self.assertFalse((paths.root / "ucm-v1.db").exists())
        self.assertEqual(backend.verify_events(self.profile)["event_count"], 1)

    def test_legacy_memory_surface_remains_registered(self):
        expected = {"memory.add", "memory.update", "memory.supersede", "memory.verify", "memory.forget_request", "memory.compact_snapshot", "memory.read", "memory.search"}
        self.assertTrue(expected.issubset(lab_tools._TOOL_REGISTRY))


class CasAndDurabilityTests(UcmFixture):
    def test_canonical_write_requires_seq_and_hash_cas(self):
        payload = self.write(record_type="FACT", record=fact())
        payload.pop("expected_head_seq")
        with self.assertRaises(ucm.UcmError) as ctx:
            ucm.add(payload)
        self.assertEqual(ctx.exception.error_code, "UCM_CAS_REQUIRED")
        self.assertEqual(self.head()["ledger_head_seq"], 0)

    def test_wrong_seq_or_hash_fails_currentness_before_append(self):
        payload = self.write(record_type="FACT", record=fact())
        payload["expected_head_seq"] = 99
        with self.assertRaises(ucm.UcmError) as ctx:
            ucm.add(payload)
        self.assertEqual(ctx.exception.error_code, "UCM_CURRENTNESS_FAILURE")
        self.assertEqual(self.head()["ledger_head_seq"], 0)

    def test_write_returns_authoritative_post_write_readback(self):
        out = self.add_record("FACT", fact())
        self.assertTrue(out["post_write_readback"])
        self.assertEqual(out["event_seq"], out["ledger_head_seq"])
        self.assertEqual(out["event_hash"], out["ledger_head_hash"])
        self.assertEqual(out["authority_effect"], "NONE")

    def test_response_loss_replay_precedes_stale_cas(self):
        payload = self.write(record_type="FACT", record=fact("fact.one"), idempotency_key="idem-one")
        first = ucm.add(payload)
        self.add_record("FACT", fact("fact.two"), idempotency_key="idem-two")
        replay = ucm.add(payload)
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["event_id"], first["event_id"])
        self.assertEqual(self.head()["ledger_head_seq"], 2)

    def test_same_idempotency_key_different_semantics_rejected(self):
        p1 = self.write(record_type="FACT", record=fact("fact.one"), idempotency_key="same")
        ucm.add(p1)
        p2 = self.write(record_type="FACT", record=fact("fact.two"), idempotency_key="same")
        with self.assertRaises(backend.UserContinuityConflict):
            ucm.add(p2)

    def test_materialize_is_fold_not_ingress_authority(self):
        self.add_record("FACT", fact("fact.only"))
        payload = self.write(idempotency_key="mat")
        out = ucm.materialize(payload)
        self.assertTrue(out["snapshot"]["ledger_verified"])
        self.assertEqual(out["ingress"]["status"], "FAIL")
        self.assertEqual(out["ingress"]["taxonomy"], "USER_CONTINUITY_INCOMPLETE")


class FactSemanticTests(UcmFixture):
    def test_descriptive_project_tag_does_not_drive_verification(self):
        f = fact(tags=["PROJECT_STATE"], target_plane="USER_CONTINUITY", requirement="NOT_REQUIRED")
        out = ucm.validate_fact(f)
        self.assertEqual(ucm.verification_requirement(out), "NOT_REQUIRED")
        self.add_record("FACT", f)
        self.assertEqual(self.head()["ledger_head_seq"], 1)

    def test_project_target_requires_explicit_required_verification_component(self):
        f = fact(target_plane="PROJECT", source_role="CONTINUITY", requirement="CONDITIONAL")
        with self.assertRaises(ucm.UcmError) as ctx:
            ucm.validate_fact(f)
        self.assertEqual(ctx.exception.error_code, "UCM_VERIFICATION_POLICY_REQUIRED")

    def test_ucm_cannot_be_authoritative_project_runtime_or_doctrine(self):
        for plane in ("PROJECT", "RUNTIME", "DEPLOYMENT", "DOCTRINE"):
            with self.subTest(plane=plane), self.assertRaises(ucm.UcmError) as ctx:
                ucm.validate_fact(fact(target_plane=plane, source_role="AUTHORITATIVE", requirement="REQUIRED"))
            self.assertEqual(ctx.exception.error_code, "AUTHORITY_FIREWALL")

    def test_required_verification_needs_live_verifier_ref(self):
        f = ucm.validate_fact(fact(target_plane="PROJECT", requirement="REQUIRED", currentness="CURRENT", verified=False))
        self.assertFalse(ucm.current_usable(f))
        f["verification"]["verified_live"] = True
        self.assertFalse(ucm.current_usable(f))
        f["verification"]["verification_ref"] = "project:live-readback"
        self.assertTrue(ucm.current_usable(f))

    def test_verify_is_dedicated_transition_not_generic_update(self):
        self.add_record("FACT", fact("fact.verify", target_plane="PROJECT", requirement="REQUIRED", currentness="UNVERIFIED"))
        bad = self.write(record_type="FACT", record_key="fact.verify", patch={"verification": {"requirement": "REQUIRED", "verified_live": True, "verification_ref": "fake"}})
        with self.assertRaises(ucm.UcmError) as ctx:
            ucm.update(bad)
        self.assertEqual(ctx.exception.error_code, "UCM_MATERIAL_CHANGE_REQUIRES_SUPERSEDE")
        verified = ucm.verify(self.write(fact_key="fact.verify", verification_ref="project:verified"))
        self.assertTrue(verified["post_write_readback"])
        self.assertTrue(ucm.current_usable(ucm.get_fact(self.profile, "fact.verify")))

    def test_temporal_effective_time_ignores_recorded_at(self):
        f = fact()
        f["temporal"] = {"recorded_at": "2026-09-09T13:00:00Z", "asserted_at": "2026-09-08T10:00:00Z", "observed_at": "2026-09-07T09:00:00Z"}
        self.assertEqual(ucm.effective_fact_time(f), "2026-09-07T09:00:00Z")

    def test_independence_counts_groups_not_reporters(self):
        f = fact()
        f["provenance"] = [*provenance("same"), *provenance("same")]
        self.assertEqual(ucm.evidence_independence_count(f), 1)

    def test_sensitive_implicit_durable_statement_cannot_auto_persist(self):
        payload = self.write(record_type="FACT", record=fact(sensitivity="SENSITIVE"), write_posture="USER_STATED_DURABLE")
        with self.assertRaises(ucm.UcmError) as ctx:
            ucm.add(payload)
        self.assertEqual(ctx.exception.error_code, "AUTHORITY_FIREWALL")
        self.assertEqual(self.head()["ledger_head_seq"], 0)

    def test_utility_metadata_cannot_change_currentness_or_verification(self):
        f = ucm.validate_fact(fact(currentness="UNVERIFIED", requirement="REQUIRED", target_plane="PROJECT"))
        high = copy.deepcopy(f); high["assistant_utility"] = utility(100)
        self.assertFalse(ucm.current_usable(high))
        self.assertGreater(ucm.derive_hydration_score(high["assistant_utility"]), 0)

    def test_supersede_requires_evidence_and_stable_key(self):
        self.add_record("FACT", fact("fact.old"))
        base = self.write(record_type="FACT", record_key="fact.old", replacement=fact("fact.old", value="new"), evidence_refs=[])
        with self.assertRaises(ucm.UcmError) as ctx:
            ucm.supersede(base)
        self.assertEqual(ctx.exception.error_code, "UCM_PROVENANCE_FAILURE")
        bad = self.write(record_type="FACT", record_key="fact.old", replacement=fact("fact.other", value="new"), evidence_refs=["evidence:new"])
        with self.assertRaises(ucm.UcmError) as ctx:
            ucm.supersede(bad)
        self.assertEqual(ctx.exception.error_code, "UCM_STABLE_KEY_REQUIRED")

    def test_conflict_is_preserved_not_smoothed(self):
        self.add_record("FACT", fact("fact.conflict"))
        ucm.conflict(self.write(fact_key="fact.conflict", evidence_refs=["source:contradiction"]))
        f = ucm.get_fact(self.profile, "fact.conflict")
        self.assertEqual(f["lifecycle"], "CONFLICT")
        self.assertEqual(f["currentness"]["status"], "CONFLICT")
        self.assertTrue(any(r["type"] == "CONFLICTS_WITH" for r in f["relations"]))

    def test_retire_then_rediscover_preserves_lineage(self):
        self.add_record("FACT", fact("fact.rediscover"))
        ucm.retire(self.write(fact_key="fact.rediscover"))
        ucm.rediscover(self.write(fact_key="fact.rediscover", evidence_refs=["source:return"]))
        f = ucm.get_fact(self.profile, "fact.rediscover")
        self.assertEqual(f["lifecycle"], "ACTIVE")
        self.assertTrue(any(r["type"] == "REDISCOVERED_FROM" for r in f["relations"]))

    def test_forget_requires_direct_user_authorization_and_retains_ledger(self):
        self.add_record("FACT", fact("fact.forget"))
        bad = self.write(fact_key="fact.forget", write_posture="SYSTEM_MAINTENANCE")
        with self.assertRaises(ucm.UcmError) as ctx:
            ucm.forget_request(bad)
        self.assertEqual(ctx.exception.error_code, "AUTHORITY_FIREWALL")
        ucm.forget_request(self.write(fact_key="fact.forget", write_posture="DIRECT_USER_AUTHORIZED"))
        self.assertEqual(ucm.get_fact(self.profile, "fact.forget")["lifecycle"], "FORGET_REQUESTED")
        self.assertEqual(backend.verify_events(self.profile)["event_count"], 2)


class IdentityReferentDecisionTests(UcmFixture):
    def test_identity_resolution_is_use_and_precedence_specific(self):
        self.add_record("IDENTITY", identity("id.display", "Display", kind="DISPLAY_NAME", use="ACCOUNT_LOOKUP", precedence=90))
        self.add_record("IDENTITY", identity("id.preferred.low", "Low", precedence=20))
        self.add_record("IDENTITY", identity("id.preferred.high", "High", precedence=80))
        self.assertEqual(ucm.resolve_identity(self.profile, use_for="NORMAL_ADDRESS")["value"], "High")
        self.assertEqual(ucm.resolve_identity(self.profile, use_for="ACCOUNT_LOOKUP")["value"], "Display")

    def test_identity_scope_is_respected(self):
        self.add_record("IDENTITY", identity("id.global", "Global", precedence=20))
        self.add_record("IDENTITY", identity("id.project", "Project", precedence=90, scope=["project:x"]))
        self.assertEqual(ucm.resolve_identity(self.profile, use_for="NORMAL_ADDRESS", scope="project:x")["value"], "Project")
        self.assertEqual(ucm.resolve_identity(self.profile, use_for="NORMAL_ADDRESS", scope="project:y")["value"], "Global")

    def test_historical_referent_does_not_win(self):
        self.add_record("REFERENT", referent("ref.old", "PCMMAD", "old", precedence=100, status="HISTORICAL"))
        self.add_record("REFERENT", referent("ref.current", "PCMMAD", "current", precedence=50))
        self.assertEqual(ucm.resolve_referent(self.profile, term="pcmmad")["meaning"], "current")

    def test_decision_history_is_first_class_and_not_project_authority(self):
        self.add_record("COLLABORATION_CONTRACT", collaboration())
        d = ucm.decision_add(self.write(decision=decision("D1")))
        self.assertEqual(d["authority_effect"], "NONE")
        rows = ucm.read_decisions(self.profile)
        self.assertEqual([x["decision_id"] for x in rows], ["D1"])

    def test_decision_supersession_keeps_stable_id_and_evidence(self):
        ucm.decision_add(self.write(decision=decision("D1")))
        replacement = decision("D1"); replacement["statement"] = "new decision"; replacement["evidence_refs"] = []
        ucm.decision_supersede(self.write(decision_id="D1", replacement=replacement, evidence_refs=["evidence:change"]))
        row = ucm.read_decisions(self.profile)[0]
        self.assertEqual(row["decision_id"], "D1")
        self.assertIn("evidence:change", row["evidence_refs"])


class CandidateControlTests(UcmFixture):
    def test_candidate_must_remain_inference_propose_only(self):
        bad = candidate(); bad["write_posture"] = "DIRECT_USER_AUTHORIZED"
        with self.assertRaises(ucm.UcmError) as ctx:
            self.add_record("MEMORY_CANDIDATE", bad, write_posture="PROPOSE_ONLY")
        self.assertEqual(ctx.exception.error_code, "AUTHORITY_FIREWALL")

    def test_candidate_is_not_active_fact_after_confirmation(self):
        self.add_record("MEMORY_CANDIDATE", candidate(), write_posture="PROPOSE_ONLY")
        self.assertEqual(len(ucm.memory_candidates(self.profile)), 1)
        ucm.memory_candidate_confirm(self.write(candidate_id="candidate.a", user_confirmed=True, write_posture="DIRECT_USER_AUTHORIZED"))
        self.assertEqual(ucm.memory_candidates(self.profile), [])
        with self.assertRaises(ucm.UcmError):
            ucm.get_fact(self.profile, "fact.proposed")

    def test_manual_memory_lock_blocks_implicit_but_not_direct_write(self):
        ucm.lock(self.write(lock="MEMORY_ADMISSION", write_posture="DIRECT_USER_AUTHORIZED"))
        with self.assertRaises(ucm.UcmError) as ctx:
            self.add_record("FACT", fact("fact.blocked"), write_posture="USER_STATED_DURABLE")
        self.assertEqual(ctx.exception.error_code, "UCM_MEMORY_ADMISSION_LOCKED")
        self.add_record("FACT", fact("fact.direct"), write_posture="DIRECT_USER_AUTHORIZED")
        self.assertIsNotNone(ucm.get_fact(self.profile, "fact.direct"))

    def test_session_reset_does_not_delete_durable_memory(self):
        self.add_record("FACT", fact("fact.keep"))
        before = ucm.get_fact(self.profile, "fact.keep")
        out = ucm.session_reset(self.write(scope="SESSION_ADAPTIVE", write_posture="DIRECT_USER_AUTHORIZED"))
        after = ucm.get_fact(self.profile, "fact.keep")
        self.assertFalse(out["durable_memory_deleted"])
        self.assertEqual(before["fact_key"], after["fact_key"])
        self.assertEqual(ucm.read_control_state(self.profile)["session_generation"], 1)

    def test_collaboration_contract_cannot_widen_authority(self):
        c = collaboration(); c["authority_boundary"]["preference_grants_tool_authority"] = True
        with self.assertRaises(ucm.UcmError) as ctx:
            self.add_record("COLLABORATION_CONTRACT", c)
        self.assertEqual(ctx.exception.error_code, "AUTHORITY_FIREWALL")

    def test_control_signal_cannot_become_authorization(self):
        c = collaboration(); c["control_signals"][0]["authorization_effect"] = "ALLOW_TOOL"
        with self.assertRaises(ucm.UcmError) as ctx:
            self.add_record("COLLABORATION_CONTRACT", c)
        self.assertEqual(ctx.exception.error_code, "AUTHORITY_FIREWALL")


class IngressHydrationExportTests(UcmFixture):
    def test_incomplete_ingress_has_exact_taxonomy(self):
        self.add_record("FACT", fact("fact.one"))
        with self.assertRaises(ucm.UcmError) as ctx:
            ucm.read_core(self.profile)
        self.assertEqual(ctx.exception.error_code, "USER_CONTINUITY_INCOMPLETE")

    def test_minimal_complete_ingress_passes_and_has_headroom(self):
        self.initialize_ingress()
        out = ucm.read_core(self.profile)
        self.assertEqual(out["ingress_status"], "PASS")
        self.assertGreaterEqual(out["headroom_bytes"], 2000)
        self.assertEqual(set(ucm.REQUIRED_INGRESS_SURFACES), set(ucm.INGRESS_CONTRACT["required_surfaces"]))
        self.assertEqual(out["SYSTEM_DESCRIPTOR"]["authority_traits"], list(ucm.AUTHORITY_TRAITS))

    def test_canonical_core_budget_fails_before_authoritative_append(self):
        huge = fact("fact.huge-core", value="x" * 11000)
        payload = self.write(record_type="FACT", record=huge)
        with self.assertRaises(ucm.UcmError) as ctx:
            ucm.add(payload)
        self.assertEqual(ctx.exception.error_code, "UCM_CORE_BUDGET_EXCEEDED")
        self.assertEqual(self.head()["ledger_head_seq"], 0)

    def test_read_hydration_distinguishes_hydrated_from_consumed(self):
        self.initialize_ingress()
        self.add_record("FACT", fact("fact.core"))
        out = ucm.read_core(self.profile)
        telemetry = out["hydration_telemetry"]
        self.assertEqual(telemetry["HYDRATED"], 1)
        self.assertEqual(telemetry["CONSUMED"], 0)
        self.assertTrue(telemetry["read_is_nonmutating"])

    def test_populated_ingress_uses_compact_indexes_and_preserves_rich_lazy_records(self):
        self.initialize_ingress()
        for idx in range(10):
            self.add_record(
                "IDENTITY",
                identity(f"identity.{idx}", f"Display Name {idx} " + "x" * 300, precedence=50 + idx),
                idempotency_key=f"identity-{idx}",
            )
        for idx in range(12):
            self.add_record(
                "REFERENT",
                referent(f"referent.{idx}", f"term-{idx}", "meaning " + "y" * 450, precedence=40 + idx),
                idempotency_key=f"referent-{idx}",
            )
        for idx in range(10):
            row = decision(f"decision.{idx}")
            row["statement"] = "decision statement " + "z" * 350
            ucm.decision_add(self.write(decision=row, idempotency_key=f"decision-{idx}"))
        for idx in range(6):
            self.add_record("FACT", fact(f"fact.core.{idx}", value=f"core-{idx}"), idempotency_key=f"fact-{idx}")

        ingress = ucm.read_core(self.profile)
        self.assertEqual(ingress["ingress_status"], "PASS")
        self.assertGreaterEqual(ingress["headroom_bytes"], ucm.MIN_HEADROOM_BYTES)

        core_row = next(iter(ingress["CORE_SNAPSHOT"]["facts"].values()))
        self.assertEqual(
            set(core_row),
            {"fact_key", "value", "currentness", "verification_requirement", "source_refs", "full_record"},
        )
        self.assertNotIn("provenance", core_row)
        self.assertNotIn("lifecycle", core_row)

        identity_entry = ingress["IDENTITY_INDEX"]["e"][0]
        referent_entry = ingress["REFERENT_INDEX"]["e"][0]
        decision_entry = ingress["DECISION_INDEX"]["e"][0]
        self.assertEqual(len(identity_entry), 3)
        self.assertEqual(len(referent_entry), 3)
        self.assertEqual(len(decision_entry), 2)
        self.assertEqual(ingress["IDENTITY_INDEX"]["full"], "ucm:IDENTITY")
        self.assertEqual(ingress["REFERENT_INDEX"]["full"], "ucm:REFERENT")
        self.assertEqual(ingress["DECISION_INDEX"]["full"], "ucm:DECISION")
        self.assertNotIn("communication", ingress["COLLABORATION_CONTRACT"])
        self.assertNotIn("provenance", ingress["COLLABORATION_CONTRACT"])
        self.assertIn("full", ingress["COLLABORATION_CONTRACT"])
        self.assertIn("required_unverified_count", ingress["VERIFICATION_DEBT"])
        self.assertIn("by_plane", ingress["VERIFICATION_DEBT"])
        self.assertEqual(ingress["VERIFICATION_DEBT"]["full_index"], "ucm.verification_debt")
        self.assertNotIn("items", ingress["VERIFICATION_DEBT"])
        self.assertIsInstance(ucm.verification_debt(self.profile), list)

        resolved_identity = ucm.resolve_identity(self.profile, use_for="NORMAL_ADDRESS")
        self.assertIn("value", resolved_identity)
        resolved_referent = ucm.resolve_referent(self.profile, term="term-0")
        self.assertIn("meaning", resolved_referent)
        decisions = ucm.read_decisions(self.profile, include_historical=True)
        self.assertTrue(decisions)
        self.assertIn("statement", decisions[0])

    def test_lazy_groups_do_not_auto_hydrate_into_core(self):
        self.initialize_ingress()
        self.add_record("FACT", fact("fact.project", target_plane="PROJECT", requirement="REQUIRED", currentness="UNVERIFIED", groups=["projects"]))
        core = ucm.read_core(self.profile)
        self.assertNotIn("fact.project", core["CORE_SNAPSHOT"]["facts"])
        lazy = ucm.read_sections(self.profile, ["projects"])
        self.assertIn("fact.project", lazy["facts"])

    def test_search_hit_explicitly_is_not_support(self):
        self.add_record("FACT", fact("fact.search", value="alpha connector"))
        out = ucm.search(self.profile, "alpha connector")
        self.assertTrue(out["results"])
        self.assertFalse(out["results"][0]["search_hit_is_evidentiary_support"])
        self.assertEqual(out["law"], "SEARCH_HIT != CLAIM_SUPPORT")

    def test_context_packet_is_bounded_and_not_authority(self):
        self.initialize_ingress()
        self.add_record("FACT", fact("fact.context"))
        out = ucm.compile_context_packet(self.profile, max_bytes=12000)
        self.assertLessEqual(out["bytes"], 12000)
        self.assertEqual(out["authority_effect"], "NONE")
        self.assertEqual(out["law"], "RETRIEVAL_PACKET != AUTHORITY")

    def test_context_packet_overflow_fails_visible(self):
        self.initialize_ingress()
        self.add_record("FACT", fact("fact.context", value="x" * 2000))
        with self.assertRaises(ucm.UcmError) as ctx:
            ucm.compile_context_packet(self.profile, max_bytes=256)
        self.assertEqual(ctx.exception.error_code, "CONTEXT_PACKET_BUDGET_EXCEEDED")

    def test_export_user_backup_does_not_include_deployment_fact(self):
        self.add_record("FACT", fact("fact.user", export_class="USER"))
        self.add_record("FACT", fact("fact.deploy", export_class="DEPLOYMENT", groups=["deployment"]))
        out = ucm.export_filtered(self.profile, "USER_BACKUP")
        keys = {x["fact_key"] for x in out["facts"]}
        self.assertIn("fact.user", keys)
        self.assertNotIn("fact.deploy", keys)

    def test_neutral_export_excludes_sensitive_even_if_portable(self):
        self.add_record("FACT", fact("fact.secret", sensitivity="SENSITIVE", export_class="PORTABLE"), write_posture="DIRECT_USER_AUTHORIZED")
        out = ucm.export_filtered(self.profile, "NEUTRAL_SYSTEM")
        self.assertNotIn("fact.secret", {x["fact_key"] for x in out["facts"]})

    def test_verification_debt_uses_explicit_components(self):
        self.add_record("FACT", fact("fact.project", target_plane="PROJECT", requirement="REQUIRED", currentness="UNVERIFIED", groups=["projects"]))
        debt = ucm.verification_debt(self.profile)
        self.assertEqual(debt[0]["fact_key"], "fact.project")
        self.assertIn("required_live_verification_missing", debt[0]["reasons"])


class SourceEvidenceTests(UcmFixture):
    def test_content_addressed_source_bytes_are_preserved_and_deduplicated(self):
        data = b"exact source bytes"
        first = ucm.import_source_bytes(self.profile, original_name="source.md", data=data, source_instance="user", imported_at=NOW, coverage={"complete": True})
        second = ucm.import_source_bytes(self.profile, original_name="copy.md", data=data, source_instance="user", imported_at=NOW, coverage={})
        self.assertEqual(first["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(first["blob_path"], second["blob_path"])
        self.assertEqual((backend._paths(self.profile).root / first["blob_path"]).read_bytes(), data)

    def test_source_manifest_preserves_policy_absence_without_negation(self):
        data = b"source"
        src = ucm.import_source_bytes(self.profile, original_name="source.md", data=data, source_instance="platform-a", imported_at=NOW, coverage={"health": "not_retained"})
        src["policy_absences"] = ["health"]
        self.add_record("SOURCE_MANIFEST", src)
        out = ucm.source_manifest(self.profile)[0]
        self.assertEqual(out["policy_absences"], ["health"])
        self.assertEqual(out["source_role"], "CONTINUITY")


if __name__ == "__main__":
    unittest.main()
