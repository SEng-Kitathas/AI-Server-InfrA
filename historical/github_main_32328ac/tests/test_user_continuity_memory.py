from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import user_continuity_store as ucs


class UserContinuityMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="pcmmad-user-memory-")
        self.root = Path(self.tmp.name) / "memory"
        self.root_patch = patch.object(ucs, "MEMORY_ROOT", self.root)
        self.root_patch.start()
        with ucs._CACHE_GUARD:
            ucs._STATE_CACHE.clear()
        with ucs._LOCKS_GUARD:
            ucs._PROFILE_LOCKS.clear()

    def tearDown(self) -> None:
        self.root_patch.stop()
        self.tmp.cleanup()

    def _base(self, idem: str, **extra: object) -> dict[str, object]:
        payload: dict[str, object] = {
            "profile_id": "test-user",
            "actor": "assistant",
            "source_instance": "gpt",
            "source_thread": "thread-a",
            "idempotency_key": idem,
        }
        payload.update(extra)
        return payload

    def _add(self, idem: str, target: str, *, section: str = "collaboration", **extra: object) -> dict:
        payload = self._base(
            idem,
            target=target,
            section=section,
            **{
                "class": "USER_PREFERENCE",
                "status": "ACTIVE",
                "value": f"value for {target}",
                "reason": "durable collaboration preference",
                "provenance": "test fixture",
                "confidence": "high",
                "requires_live_verification": False,
                "sensitivity": "normal",
                "export_class": "USER",
                "always_load": False,
                "hydration_priority": 100,
                **extra,
            },
        )
        return ucs.memory_add(payload)

    def _facts(self, *, sections: list[str], include_superseded: bool = False) -> list[dict]:
        read = ucs.memory_read(
            {
                "profile_id": "test-user",
                "sections": sections,
                "include_superseded": include_superseded,
            }
        )
        out: list[dict] = []
        for section in sections:
            out.extend(read["sections"][section]["facts"])
        return out

    def test_empty_read_is_non_initializing(self) -> None:
        result = ucs.memory_read({"profile_id": "test-user"})
        self.assertTrue(result["ok"])
        self.assertFalse(result["initialized"])
        self.assertTrue(result["snapshot_current"])
        self.assertEqual(result["ledger_head_seq"], 0)
        self.assertFalse(self.root.exists(), "read path must not initialize durable memory")

    def test_add_materializes_core_and_lazy_section_without_full_ledger_read_on_hydration(self) -> None:
        receipt = self._add(
            "add-core",
            "preferences.communication.proceed_semantics",
            always_load=True,
            hydration_priority=5,
        )
        self.assertEqual(receipt["event"]["event_seq"], 1)
        self.assertTrue(receipt["snapshot_current"])

        with patch.object(ucs, "read_events", side_effect=AssertionError("healthy hydration must not fold ledger")):
            result = ucs.memory_read(
                {"profile_id": "test-user", "sections": ["collaboration"], "ledger_tail": 0}
            )
        self.assertEqual(result["snapshot_from_seq"], 1)
        self.assertEqual(len(result["core"]["facts"]), 1)
        self.assertEqual(len(result["sections"]["collaboration"]["facts"]), 1)
        self.assertIn("core + relevant lazy sections", result["hydration_rule"])

    def test_lazy_read_does_not_materialize_unrequested_sections(self) -> None:
        self._add("add-a", "preferences.a", section="collaboration")
        self._add("add-b", "projects.pcmmad.pointer", section="projects")
        result = ucs.memory_read({"profile_id": "test-user", "sections": ["projects"]})
        self.assertEqual(set(result["sections"]), {"projects"})
        self.assertEqual({f["target"] for f in result["sections"]["projects"]["facts"]}, {"projects.pcmmad.pointer"})
        self.assertEqual(result["core"]["facts"], [])

    def test_response_loss_replay_returns_original_event_after_unrelated_head_advance(self) -> None:
        first_payload = self._base(
            "idem-first",
            target="preferences.first",
            section="collaboration",
            **{
                "class": "USER_PREFERENCE",
                "value": "first",
                "reason": "first fact",
                "export_class": "USER",
            },
        )
        first = ucs.memory_add(first_payload)
        self._add("idem-second", "preferences.second")
        replay = ucs.memory_add(first_payload)
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["event"]["event_id"], first["event"]["event_id"])
        self.assertEqual(replay["event"]["event_seq"], 1)
        self.assertEqual(replay["ledger_head_seq"], 2)
        self.assertEqual(ucs.verify_events("test-user")["event_count"], 2)

    def test_same_idempotency_key_with_different_semantics_conflicts(self) -> None:
        self._add("same-key", "preferences.one")
        with self.assertRaises(ucs.UserContinuityConflict) as raised:
            self._add("same-key", "preferences.two")
        self.assertEqual(raised.exception.error_code, "MEMORY_IDEMPOTENCY_CONFLICT")
        self.assertEqual(ucs.verify_events("test-user")["event_count"], 1)

    def test_head_cas_detects_stale_writer(self) -> None:
        self._add("first", "preferences.one")
        with self.assertRaises(ucs.UserContinuityConflict) as raised:
            self._add(
                "stale-writer",
                "preferences.two",
                expected_ledger_head_hash="genesis",
            )
        self.assertEqual(raised.exception.error_code, "MEMORY_HEAD_CONFLICT")
        self.assertEqual(ucs.verify_events("test-user")["event_count"], 1)

    def test_existing_target_requires_causal_supersession(self) -> None:
        first = self._add("first", "identity.naming.preferred")
        with self.assertRaises(ucs.UserContinuityConflict) as raised:
            self._add("second", "identity.naming.preferred")
        self.assertEqual(raised.exception.error_code, "MEMORY_TARGET_EXISTS")
        self.assertEqual(first["event"]["event_seq"], 1)

    def test_supersession_preserves_old_fact_and_records_forcing_evidence(self) -> None:
        first = self._add("old-job", "identity.employment.current", section="identity")
        old_id = first["affected_memory_ids"][0]
        supersede = ucs.memory_supersede(
            self._base(
                "new-job",
                memory_id=old_id,
                replacement={
                    "value": "quick-lube role",
                    "reason": "newer direct user statement",
                    "confidence": "high",
                    "revalidate_when": ["decision_relevant"],
                },
                superseded_by_evidence=[
                    {
                        "type": "user_statement",
                        "ref": "conversation:2026-08-22",
                        "independence_group": "user-statement-2026-08-22-employment",
                    }
                ],
            )
        )
        new_id = supersede["affected_memory_ids"][1]
        visible = self._facts(sections=["identity"])
        self.assertEqual([f["memory_id"] for f in visible], [new_id])
        all_facts = {f["memory_id"]: f for f in self._facts(sections=["identity"], include_superseded=True)}
        self.assertEqual(all_facts[old_id]["status"], "SUPERSEDED")
        self.assertEqual(all_facts[old_id]["superseded_by_memory_id"], new_id)
        self.assertEqual(
            all_facts[old_id]["superseded_by_evidence"][0]["ref"], "conversation:2026-08-22"
        )
        self.assertEqual(all_facts[new_id]["supersedes_memory_id"], old_id)

    def test_supersede_cannot_move_stable_target(self) -> None:
        first = self._add("old", "identity.name", section="identity")
        with self.assertRaises(ucs.UserContinuityError) as raised:
            ucs.memory_supersede(
                self._base(
                    "bad-move",
                    memory_id=first["affected_memory_ids"][0],
                    replacement={
                        "target": "identity.other",
                        "value": "new",
                        "reason": "attempt to move slot",
                    },
                    superseded_by_evidence=[{"type": "user_statement", "ref": "event:x"}],
                )
            )
        self.assertEqual(raised.exception.error_code, "MATERIAL_MEMORY_CHANGE_REQUIRES_STABLE_TARGET")

    def test_update_rejects_value_change_and_dedicated_lifecycle_transitions(self) -> None:
        first = self._add("first", "preferences.one")
        memory_id = first["affected_memory_ids"][0]
        with self.assertRaises(ucs.UserContinuityError) as raised:
            ucs.memory_update(self._base("update-value", memory_id=memory_id, patch={"value": "changed"}))
        self.assertEqual(raised.exception.error_code, "MATERIAL_MEMORY_CHANGE_REQUIRES_SUPERSEDE")
        with self.assertRaises(ucs.UserContinuityError) as raised:
            ucs.memory_update(self._base("update-status", memory_id=memory_id, patch={"status": "SUPERSEDED"}))
        self.assertEqual(raised.exception.error_code, "SEMANTIC_MEMORY_TRANSITION_REQUIRED")

    def test_exact_target_read_uses_addressable_index_and_auto_selects_section(self) -> None:
        self._add("alpha", "preferences.alpha", section="collaboration")
        self._add("beta", "projects.pcmmad.pointer", section="projects")
        result = ucs.memory_read(
            {"profile_id": "test-user", "target": "projects.pcmmad.pointer"}
        )
        self.assertEqual(set(result["sections"]), {"projects"})
        facts = result["sections"]["projects"]["facts"]
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0]["target"], "projects.pcmmad.pointer")

    def test_export_class_filter_is_mechanical_for_neutral_stack_projection(self) -> None:
        self._add(
            "user", "preferences.personal", section="collaboration", export_class="USER"
        )
        self._add(
            "portable", "doctrine.portable", section="doctrine", export_class="PORTABLE"
        )
        result = ucs.memory_read(
            {
                "profile_id": "test-user",
                "sections": ["collaboration", "doctrine"],
                "export_classes": ["PORTABLE"],
            }
        )
        facts = [
            fact
            for doc in result["sections"].values()
            for fact in doc["facts"]
        ]
        self.assertEqual([fact["target"] for fact in facts], ["doctrine.portable"])
        self.assertEqual(result["export_filter"], ["PORTABLE"])
        search = ucs.memory_search(
            {
                "profile_id": "test-user",
                "query": "value",
                "export_classes": ["PORTABLE"],
            }
        )
        self.assertEqual([row["target"] for row in search["results"]], ["doctrine.portable"])

    def test_revalidation_hazard_is_computed_from_deadline_and_live_requirement(self) -> None:
        ucs.memory_add(
            self._base(
                "dated",
                target="projects.example.frontier",
                section="projects",
                **{
                    "class": "PROJECT_STATE",
                    "status": "UNKNOWN_CURRENTNESS",
                    "value": "old frontier",
                    "reason": "navigation",
                    "export_class": "PROJECT",
                    "requires_live_verification": True,
                    "revalidate_after": "2020-01-01T00:00:00+00:00",
                    "revalidate_when": ["project_activated"],
                },
            )
        )
        result = ucs.memory_read({"profile_id": "test-user", "sections": ["projects"]})
        fact = result["sections"]["projects"]["facts"][0]
        self.assertTrue(fact["revalidation"]["due"])
        self.assertIn("revalidate_after_elapsed", fact["revalidation"]["reasons"])
        self.assertIn("requires_live_verification", fact["revalidation"]["reasons"])
        self.assertEqual(fact["revalidation"]["event_triggers"], ["project_activated"])
        self.assertEqual(len(result["revalidation_hazards"]), 1)

    def test_revalidation_timestamp_requires_timezone(self) -> None:
        with self.assertRaises(ucs.UserContinuityError) as raised:
            self._add(
                "naive-time",
                "preferences.time",
                revalidate_after="2026-09-08T08:00:00",
            )
        self.assertEqual(raised.exception.error_code, "BAD_REQUEST")

    def test_two_assistants_same_independence_group_do_not_create_two_independent_groups(self) -> None:
        first = self._add(
            "fact",
            "doctrine.memory.navigation_not_proof",
            section="doctrine",
            evidence_independence_group="artifact:memory-spec-v1",
        )
        memory_id = first["affected_memory_ids"][0]
        ucs.memory_verify(
            {
                **self._base("verify-gpt", memory_id=memory_id),
                "source_instance": "gpt",
                "evidence_independence_group": "artifact:memory-spec-v1",
                "evidence": [
                    {
                        "type": "artifact",
                        "ref": "RAHL_USER_CONTINUITY_MEMORY_2026-09-07.md",
                        "independence_group": "artifact:memory-spec-v1",
                    }
                ],
            }
        )
        ucs.memory_verify(
            {
                **self._base("verify-claude", memory_id=memory_id),
                "source_instance": "claude",
                "evidence_independence_group": "artifact:memory-spec-v1",
                "evidence": [
                    {
                        "type": "artifact",
                        "ref": "RAHL_USER_CONTINUITY_MEMORY_2026-09-07.md",
                        "independence_group": "artifact:memory-spec-v1",
                    }
                ],
            }
        )
        fact = self._facts(sections=["doctrine"])[0]
        summary = fact["verification_summary"]
        self.assertEqual(summary["verification_count"], 2)
        self.assertEqual(summary["evidence_independence_groups"], ["artifact:memory-spec-v1"])
        self.assertEqual(summary["independent_evidence_count"], 1)

    def test_project_state_must_remain_live_verification_capable(self) -> None:
        with self.assertRaises(ucs.UserContinuityError) as raised:
            ucs.memory_add(
                self._base(
                    "project-state",
                    target="projects.pcmmad.frontier",
                    section="projects",
                    **{
                        "class": "PROJECT_STATE",
                        "status": "UNKNOWN_CURRENTNESS",
                        "value": "remembered frontier",
                        "reason": "navigation only",
                        "export_class": "PROJECT",
                        "requires_live_verification": False,
                    },
                )
            )
        self.assertEqual(raised.exception.error_code, "PROJECT_STATE_REQUIRES_LIVE_VERIFICATION")
        accepted = ucs.memory_add(
            self._base(
                "project-state-good",
                target="projects.pcmmad.frontier",
                section="projects",
                **{
                    "class": "PROJECT_STATE",
                    "status": "UNKNOWN_CURRENTNESS",
                    "value": "remembered frontier",
                    "reason": "navigation only",
                    "export_class": "PROJECT",
                    "requires_live_verification": True,
                },
            )
        )
        self.assertEqual(accepted["event"]["event_seq"], 1)

    def test_forget_request_is_tombstone_not_physical_erasure(self) -> None:
        first = self._add("fact", "preferences.temporary")
        memory_id = first["affected_memory_ids"][0]
        receipt = ucs.memory_forget_request(
            self._base("forget", memory_id=memory_id, reason="user requested forgetting")
        )
        self.assertFalse(receipt["physical_erasure"])
        self.assertEqual(self._facts(sections=["collaboration"]), [])
        historical = self._facts(sections=["collaboration"], include_superseded=True)
        self.assertEqual(historical[0]["status"], "FORGET_REQUESTED")
        self.assertEqual(ucs.verify_events("test-user")["event_count"], 2)

    def test_core_budget_is_checked_before_authoritative_append(self) -> None:
        big = "x" * (ucs.CORE_MAX_BYTES + 4096)
        with self.assertRaises(ucs.UserContinuityConflict) as raised:
            ucs.memory_add(
                self._base(
                    "too-big",
                    target="identity.too_big",
                    section="identity",
                    **{
                        "class": "USER_STATED",
                        "value": big,
                        "reason": "hostile core amplification",
                        "export_class": "USER",
                        "always_load": True,
                    },
                )
            )
        self.assertEqual(raised.exception.error_code, "MEMORY_CORE_BUDGET_EXCEEDED")
        self.assertEqual(ucs.ledger_head("test-user")["event_seq"], 0)

    def _append_valid_unmaterialized_update(self, memory_id: str) -> None:
        state = ucs.build_state("test-user")
        body = ucs._event_body(
            event_seq=state["event_count"] + 1,
            event_id="MEM-manual-valid-unmaterialized",
            timestamp=ucs._utc_now(),
            profile_id="test-user",
            operation="UPDATE",
            provenance={
                "actor": "server",
                "source_instance": "hostile-test",
                "source_thread": None,
                "source_event": None,
                "evidence_independence_group": None,
            },
            payload={"memory_id": memory_id, "patch": {"confidence": "medium"}},
            previous_hash=state["head_hash"],
            idempotency_key="manual-unmaterialized",
            request_fingerprint="f" * 64,
        )
        event = {**body, "event_hash": ucs._sha256_json(body)}
        path = ucs._paths("test-user").ledger
        with path.open("ab") as handle:
            handle.write(ucs._canonical_bytes(event) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        with ucs._CACHE_GUARD:
            ucs._STATE_CACHE.clear()

    def test_section_budget_is_checked_before_authoritative_append(self) -> None:
        with patch.object(ucs, "SECTION_MAX_BYTES", 700):
            with self.assertRaises(ucs.UserContinuityConflict) as raised:
                self._add(
                    "section-too-big",
                    "notes.large",
                    section="notes",
                    value="x" * 1200,
                    always_load=False,
                )
        self.assertEqual(raised.exception.error_code, "MEMORY_SECTION_BUDGET_EXCEEDED")
        self.assertEqual(ucs.ledger_head("test-user")["event_seq"], 0)

    def test_targeted_ledger_tail_folds_history_once_not_once_per_event(self) -> None:
        first = self._add("first", "preferences.one")
        memory_id = first["affected_memory_ids"][0]
        ucs.memory_update(
            self._base("meta-1", memory_id=memory_id, patch={"confidence": "medium"})
        )
        ucs.memory_update(
            self._base("meta-2", memory_id=memory_id, patch={"confidence": "high"})
        )
        original = ucs.build_state
        calls = {"count": 0}
        def counted(*args, **kwargs):
            calls["count"] += 1
            return original(*args, **kwargs)
        with patch.object(ucs, "build_state", side_effect=counted):
            read = ucs.memory_read(
                {
                    "profile_id": "test-user",
                    "sections": ["collaboration"],
                    "target": "preferences.one",
                    "ledger_tail": 10,
                }
            )
        self.assertEqual(calls["count"], 1)
        self.assertEqual(len(read["ledger_tail"]), 3)

    def test_stale_snapshot_fails_closed_and_compaction_recovers(self) -> None:
        first = self._add("first", "preferences.one")
        memory_id = first["affected_memory_ids"][0]
        self._append_valid_unmaterialized_update(memory_id)
        with self.assertRaises(ucs.UserContinuityConflict) as raised:
            ucs.memory_read({"profile_id": "test-user"})
        self.assertEqual(raised.exception.error_code, "MEMORY_SNAPSHOT_STALE")
        compact = ucs.memory_compact_snapshot({"profile_id": "test-user"})
        self.assertTrue(compact["ledger_verified"])
        self.assertEqual(compact["snapshot_from_seq"], 2)
        read = ucs.memory_read({"profile_id": "test-user", "sections": ["collaboration"]})
        self.assertEqual(read["sections"]["collaboration"]["facts"][0]["confidence"], "medium")

    def test_snapshot_object_tamper_is_detected(self) -> None:
        self._add("first", "preferences.one", always_load=True)
        manifest = json.loads(ucs._paths("test-user").current.read_text(encoding="utf-8"))
        core_path = ucs._paths("test-user").root / manifest["core"]["object"]
        core_path.write_text("{}", encoding="utf-8")
        with self.assertRaises(ucs.UserContinuityLedgerError) as raised:
            ucs.memory_read({"profile_id": "test-user"})
        self.assertEqual(raised.exception.error_code, "MEMORY_SNAPSHOT_CORRUPT")

    def test_hash_chain_corruption_blocks_recovery_compaction(self) -> None:
        self._add("first", "preferences.one")
        path = ucs._paths("test-user").ledger
        rows = path.read_text(encoding="utf-8").splitlines()
        first = json.loads(rows[0])
        first["actor"] = "evil"
        path.write_text(json.dumps(first, separators=(",", ":")) + "\n", encoding="utf-8")
        with ucs._CACHE_GUARD:
            ucs._STATE_CACHE.clear()
        with self.assertRaises(ucs.UserContinuityLedgerError) as raised:
            ucs.memory_compact_snapshot({"profile_id": "test-user"})
        self.assertEqual(raised.exception.error_code, "MEMORY_LEDGER_CORRUPT")

    def test_search_is_bounded_and_snapshot_current(self) -> None:
        self._add("alpha", "preferences.alpha", value="alpha connector discovery")
        self._add("beta", "preferences.beta", value="beta connector discovery")
        with patch.object(ucs, "read_events", side_effect=AssertionError("search must not fold ledger")):
            result = ucs.memory_search(
                {"profile_id": "test-user", "query": "connector discovery", "limit": 1}
            )
        self.assertEqual(result["count"], 1)
        self.assertTrue(result["bounded"])

    def test_concurrent_process_appends_serialize_and_preserve_hash_chain(self) -> None:
        shared_root = Path(self.tmp.name) / "cross-process-memory"
        python = sys.executable
        code = r'''
import json, os, sys
sys.path.insert(0, os.environ["PCMMAD_TEST_RUNTIME_ROOT"])
import user_continuity_store as u
idx=sys.argv[1]
r=u.memory_add({
 "profile_id":"race-user","actor":"assistant","source_instance":f"proc-{idx}",
 "idempotency_key":f"race-{idx}","target":f"race.fact.{idx}","section":"race",
 "class":"OBSERVED","value":f"value-{idx}","reason":"concurrent append",
 "export_class":"USER","confidence":"high"
})
print(json.dumps({"seq":r["event"]["event_seq"],"id":r["event"]["event_id"]}))
'''
        env = dict(os.environ)
        env["PCMMAD_USER_CONTINUITY_ROOT"] = str(shared_root)
        env["PCMMAD_TEST_RUNTIME_ROOT"] = str(RUNTIME_ROOT.parent)
        procs = [
            subprocess.Popen(
                [python, "-c", code, str(i)],
                cwd=PROJECT_ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for i in range(6)
        ]
        outputs = []
        try:
            for proc in procs:
                out, err = proc.communicate(timeout=30)
                self.assertEqual(proc.returncode, 0, err)
                outputs.append(json.loads(out.strip()))
        finally:
            for proc in procs:
                if proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=5)
        seqs = sorted(item["seq"] for item in outputs)
        self.assertEqual(seqs, [1, 2, 3, 4, 5, 6])
        with patch.object(ucs, "MEMORY_ROOT", shared_root):
            with ucs._CACHE_GUARD:
                ucs._STATE_CACHE.clear()
            verification = ucs.verify_events("race-user")
            self.assertTrue(verification["ok"], verification)
            self.assertEqual(verification["event_count"], 6)
            read = ucs.memory_read({"profile_id": "race-user", "sections": ["race"]})
            self.assertEqual(len(read["sections"]["race"]["facts"]), 6)
            self.assertEqual(read["snapshot_from_seq"], 6)


if __name__ == "__main__":
    unittest.main()
