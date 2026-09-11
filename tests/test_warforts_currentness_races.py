from __future__ import annotations

import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baseline"))

import icf_cs_v12_ingress as ingress
import protocol_store
import res_runtime as res
import shared_core
import ucm_v1_runtime as ucm
import user_continuity_store as memory_backend
from protocol_models import ContinuityKind
from test_res_runtime import valid_snapshot
from test_ucm_v1_runtime import collaboration, fact, source_provenance


class WarfortFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pcmmad-warfort-currentness-")
        self.base = Path(self.temp.name)
        self.old_projects = shared_core.PROJECTS_ROOT
        self.old_memory = memory_backend.MEMORY_ROOT
        shared_core.PROJECTS_ROOT = self.base / "projects"
        memory_backend.MEMORY_ROOT = self.base / "memory"
        with memory_backend._CACHE_GUARD:
            memory_backend._STATE_CACHE.clear()
        with memory_backend._LOCKS_GUARD:
            memory_backend._PROFILE_LOCKS.clear()
        self.project_id = "warfort-project"
        self.root = shared_core.init_project_layout(self.project_id)
        src = ROOT / "handoff/current/INTENT_CONSTRAINT_FRONTIER_CONTINUITY_STANDARD.md"
        target = self.root / ingress.ICF_CS_STANDARD_REL
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
        self.standard_path = target

    def tearDown(self):
        shared_core.PROJECTS_ROOT = self.old_projects
        memory_backend.MEMORY_ROOT = self.old_memory
        with memory_backend._CACHE_GUARD:
            memory_backend._STATE_CACHE.clear()
        with memory_backend._LOCKS_GUARD:
            memory_backend._PROFILE_LOCKS.clear()
        self.temp.cleanup()

    def write_res(self):
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

    def ucm_payload(self, profile: str, *, idem: str, **extra):
        h = ucm.head(profile)
        payload = {
            "profile_id": profile,
            "actor": "assistant",
            "source_instance": "warfort",
            "provenance": source_provenance(idem),
            "idempotency_key": idem,
            "expected_head_seq": h["ledger_head_seq"],
            "expected_head_hash": h["ledger_head_hash"],
            "write_posture": "DIRECT_USER_AUTHORIZED",
        }
        payload.update(extra)
        return payload

    def write_ucm(self, profile="warfort-user"):
        ucm.add(self.ucm_payload(profile, idem="collab", record_type="COLLABORATION_CONTRACT", record=collaboration()))
        return profile


class IcfIngressRaceTests(WarfortFixture):
    def test_icf_standard_change_mid_rehydrate_fails_closed(self):
        def mutate_standard(_request):
            self.standard_path.write_text("stale authority bytes\n", encoding="utf-8")
            return {"selected": [], "bytes_used": 0}

        with patch.object(ingress, "rehydrate_context", side_effect=mutate_standard):
            with self.assertRaises(ingress.IcfIngressError) as ctx:
                ingress.rehydrate_icf_v12(
                    project_id=self.project_id,
                    topic="frontier",
                    session_mode="NONUSER_NONRESEARCH_AUTOMATION",
                )
        self.assertEqual(ctx.exception.error_code, "ICF_CS_CURRENTNESS_FAILURE")

    def test_res_becomes_stale_mid_rehydrate_fails_closed(self):
        self.write_res()

        def mutate_res(_request):
            protocol_store.record_claim(
                self.project_id,
                claim_id="late-material-claim",
                kind="HYPOTHESIS",
                statement="late frontier movement",
                actor="test",
            )
            return {"selected": [], "bytes_used": 0}

        with patch.object(ingress, "rehydrate_context", side_effect=mutate_res):
            with self.assertRaises(ingress.IcfIngressError) as ctx:
                ingress.rehydrate_icf_v12(
                    project_id=self.project_id,
                    topic="research frontier",
                    session_mode="NONUSER_RESEARCH_AUTOMATION",
                )
        self.assertEqual(ctx.exception.error_code, "HANDOFF_EPISTEMIC_CONTINUITY_INCOMPLETE")

    def test_ucm_head_moves_mid_rehydrate_fails_closed(self):
        profile = self.write_ucm()

        def mutate_ucm(_request):
            ucm.add(self.ucm_payload(profile, idem="late-fact", record_type="FACT", record=fact("late.fact")))
            return {"selected": [], "bytes_used": 0}

        with patch.object(ingress, "rehydrate_context", side_effect=mutate_ucm):
            with self.assertRaises(ingress.IcfIngressError) as ctx:
                ingress.rehydrate_icf_v12(
                    project_id=self.project_id,
                    topic="frontier",
                    session_mode="INTERACTIVE_NONRESEARCH_USER_SESSION",
                    ucm_profile_id=profile,
                )
        self.assertEqual(ctx.exception.error_code, "UCM_CURRENTNESS_FAILURE")


class UcmPacketRaceTests(WarfortFixture):
    def test_ucm_read_core_rejects_head_change_during_packet_assembly(self):
        profile = self.write_ucm()
        original_core = ucm._core_fact_records

        def mutate_after_head(pid):
            ucm.add(self.ucm_payload(profile, idem="racing-fact", record_type="FACT", record=fact("racing.fact")))
            return original_core(pid)

        with patch.object(ucm, "_core_fact_records", side_effect=mutate_after_head):
            with self.assertRaises(ucm.UcmError) as ctx:
                ucm.read_core(profile)
        self.assertEqual(ctx.exception.error_code, "UCM_CURRENTNESS_FAILURE")

    def test_two_writers_same_cas_exactly_one_commits(self):
        profile = self.write_ucm()
        h = ucm.head(profile)
        barrier = threading.Barrier(2)
        outcomes: list[tuple[str, str]] = []
        lock = threading.Lock()

        def worker(index: int):
            payload = {
                "profile_id": profile,
                "actor": "assistant",
                "source_instance": "warfort",
                "provenance": source_provenance(f"race-{index}"),
                "idempotency_key": f"race-{index}",
                "expected_head_seq": h["ledger_head_seq"],
                "expected_head_hash": h["ledger_head_hash"],
                "write_posture": "DIRECT_USER_AUTHORIZED",
                "record_type": "FACT",
                "record": fact(f"race.fact.{index}"),
            }
            barrier.wait(timeout=5)
            try:
                ucm.add(payload)
                result = ("ok", "")
            except ucm.UcmError as exc:
                result = ("error", exc.error_code)
            with lock:
                outcomes.append(result)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(sum(kind == "ok" for kind, _ in outcomes), 1)
        self.assertEqual(sum(code == "UCM_CURRENTNESS_FAILURE" for _, code in outcomes), 1)
        self.assertEqual(ucm.head(profile)["ledger_head_seq"], h["ledger_head_seq"] + 1)

    def test_same_idempotent_write_concurrently_becomes_commit_plus_replay(self):
        profile = self.write_ucm()
        h = ucm.head(profile)
        barrier = threading.Barrier(2)
        outcomes: list[dict] = []
        lock = threading.Lock()
        payload = {
            "profile_id": profile,
            "actor": "assistant",
            "source_instance": "warfort",
            "provenance": source_provenance("same-replay"),
            "idempotency_key": "same-replay",
            "expected_head_seq": h["ledger_head_seq"],
            "expected_head_hash": h["ledger_head_hash"],
            "write_posture": "DIRECT_USER_AUTHORIZED",
            "record_type": "FACT",
            "record": fact("same.replay.fact"),
        }

        def worker():
            barrier.wait(timeout=5)
            out = ucm.add(dict(payload))
            with lock:
                outcomes.append(out)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(len(outcomes), 2)
        self.assertEqual(sum(bool(x.get("replayed")) for x in outcomes), 1)
        self.assertEqual(len({x["event_id"] for x in outcomes}), 1)
        self.assertEqual(ucm.head(profile)["ledger_head_seq"], h["ledger_head_seq"] + 1)


if __name__ == "__main__":
    unittest.main()
