from __future__ import annotations

import json
import multiprocessing as mp
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baseline" / "pcmmad_receiver"))

import ucm_v1_runtime as ucm
import user_continuity_store as backend
from test_ucm_v1_runtime import collaboration, fact, source_provenance


def _proc_same_cas(memory_root: str, profile: str, payload: dict, start_event, queue) -> None:
    sys.path.insert(0, str(ROOT / "baseline" / "pcmmad_receiver"))
    import ucm_v1_runtime as child_ucm
    import user_continuity_store as child_backend
    child_backend.MEMORY_ROOT = Path(memory_root)
    with child_backend._CACHE_GUARD:
        child_backend._STATE_CACHE.clear()
    start_event.wait(10)
    try:
        out = child_ucm.add(payload)
        queue.put(("ok", out.get("replayed"), out.get("event_id"), out.get("event_hash")))
    except Exception as exc:
        queue.put(("error", getattr(exc, "error_code", type(exc).__name__), None, None))


class RecoveryFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pcmmad-warfort-recovery-")
        self.old_root = backend.MEMORY_ROOT
        backend.MEMORY_ROOT = Path(self.temp.name) / "memory"
        with backend._CACHE_GUARD:
            backend._STATE_CACHE.clear()
        with backend._LOCKS_GUARD:
            backend._PROFILE_LOCKS.clear()
        self.profile = "warfort-recovery"
        self.add("COLLABORATION_CONTRACT", collaboration(), idem="collab")

    def tearDown(self):
        backend.MEMORY_ROOT = self.old_root
        with backend._CACHE_GUARD:
            backend._STATE_CACHE.clear()
        with backend._LOCKS_GUARD:
            backend._PROFILE_LOCKS.clear()
        self.temp.cleanup()

    def payload(self, *, idem: str, **extra):
        h = ucm.head(self.profile)
        out = {
            "profile_id": self.profile,
            "actor": "assistant",
            "source_instance": "warfort",
            "provenance": source_provenance(idem),
            "idempotency_key": idem,
            "expected_head_seq": h["ledger_head_seq"],
            "expected_head_hash": h["ledger_head_hash"],
            "write_posture": "DIRECT_USER_AUTHORIZED",
        }
        out.update(extra)
        return out

    def add(self, record_type: str, record: dict, *, idem: str):
        if not hasattr(self, "profile"):
            self.profile = "warfort-recovery"
        return ucm.add(self.payload(idem=idem, record_type=record_type, record=record))

    def test_response_loss_after_ledger_append_recovers_by_idempotent_replay(self):
        payload = self.payload(idem="crash-after-ledger", record_type="FACT", record=fact("crash.fact"))
        original = backend._materialize_locked
        calls = {"count": 0}

        def explode_once(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 1:
                raise OSError("simulated snapshot write failure after authoritative ledger append")
            return original(*args, **kwargs)

        with patch.object(backend, "_materialize_locked", side_effect=explode_once):
            with self.assertRaises(OSError):
                ucm.add(payload)
        # The consequence exists in the authoritative ledger even though transport failed.
        after_failure = ucm.head(self.profile)
        self.assertEqual(after_failure["ledger_head_seq"], 2)
        replay = ucm.add(payload)
        self.assertTrue(replay["replayed"])
        self.assertTrue(replay["derived_snapshot_repaired"])
        self.assertEqual(replay["ledger_head_seq"], 2)
        self.assertEqual(ucm.get_fact(self.profile, "crash.fact")["fact_key"], "crash.fact")

    def test_truncated_ledger_cannot_use_newer_snapshot_as_current(self):
        self.add("FACT", fact("one"), idem="one")
        self.add("FACT", fact("two"), idem="two")
        paths = backend._paths(self.profile)
        lines = paths.ledger.read_bytes().splitlines(keepends=True)
        self.assertEqual(len(lines), 3)
        paths.ledger.write_bytes(b"".join(lines[:-1]))
        with backend._CACHE_GUARD:
            backend._STATE_CACHE.clear()
        with self.assertRaises(ucm.UcmError) as ctx:
            ucm.read_core(self.profile)
        self.assertEqual(ctx.exception.error_code, "UCM_CURRENTNESS_FAILURE")

    def test_corrupted_ledger_tail_fails_integrity_not_partial_success(self):
        self.add("FACT", fact("one"), idem="one")
        paths = backend._paths(self.profile)
        with paths.ledger.open("ab") as handle:
            handle.write(b'{"broken":')
        with backend._CACHE_GUARD:
            backend._STATE_CACHE.clear()
        with self.assertRaises(Exception) as ctx:
            ucm.head(self.profile)
        self.assertNotIn(type(ctx.exception).__name__, {"MemoryError", "RecursionError"})

    def test_corrupted_snapshot_object_is_not_silently_trusted(self):
        self.add("FACT", fact("one"), idem="one")
        paths = backend._paths(self.profile)
        manifest = json.loads(paths.current.read_text(encoding="utf-8"))
        object_rel = manifest["sections"]["ucm_facts"]["object"]
        object_path = paths.root / object_rel
        object_path.write_bytes(b"tampered")
        with self.assertRaises(backend.UserContinuityError) as ctx:
            backend.memory_read({"profile_id": self.profile, "sections": ["ucm_facts"]})
        self.assertEqual(ctx.exception.error_code, "MEMORY_SNAPSHOT_CORRUPT")

    def test_bounded_derived_cache_survives_high_churn(self):
        for i in range(120):
            self.add("FACT", fact(f"churn.{i}", groups=["historical"]), idem=f"churn-{i}")
        paths = backend._paths(self.profile)
        snapshots = list(paths.snapshots.glob("*.json"))
        objects = list(paths.objects.glob("*.json"))
        self.assertLessEqual(len(snapshots), 2)
        self.assertLessEqual(len(objects), 20)
        self.assertEqual(ucm.read_core(self.profile)["ingress_status"], "PASS")
        self.assertEqual(backend.verify_events(self.profile)["event_count"], 121)

    def test_cross_process_same_head_cas_allows_exactly_one_writer(self):
        h = ucm.head(self.profile)
        base = {
            "profile_id": self.profile,
            "actor": "assistant",
            "source_instance": "warfort",
            "expected_head_seq": h["ledger_head_seq"],
            "expected_head_hash": h["ledger_head_hash"],
            "write_posture": "DIRECT_USER_AUTHORIZED",
            "record_type": "FACT",
        }
        p1 = {**base, "provenance": source_provenance("p1"), "idempotency_key": "proc-1", "record": fact("proc.fact.1")}
        p2 = {**base, "provenance": source_provenance("p2"), "idempotency_key": "proc-2", "record": fact("proc.fact.2")}
        ctx = mp.get_context("spawn")
        start = ctx.Event(); queue = ctx.Queue()
        processes = [
            ctx.Process(target=_proc_same_cas, args=(str(backend.MEMORY_ROOT), self.profile, payload, start, queue))
            for payload in (p1, p2)
        ]
        for proc in processes: proc.start()
        start.set()
        results = [queue.get(timeout=15) for _ in processes]
        for proc in processes:
            proc.join(timeout=15)
            self.assertFalse(proc.is_alive())
            self.assertEqual(proc.exitcode, 0)
        self.assertEqual(sum(row[0] == "ok" for row in results), 1)
        self.assertEqual(sum(row[1] == "UCM_CURRENTNESS_FAILURE" for row in results if row[0] == "error"), 1)
        self.assertEqual(ucm.head(self.profile)["ledger_head_seq"], h["ledger_head_seq"] + 1)

    def test_cross_process_same_idempotency_is_commit_plus_replay(self):
        h = ucm.head(self.profile)
        payload = {
            "profile_id": self.profile,
            "actor": "assistant",
            "source_instance": "warfort",
            "provenance": source_provenance("same-process-replay"),
            "idempotency_key": "same-process-replay",
            "expected_head_seq": h["ledger_head_seq"],
            "expected_head_hash": h["ledger_head_hash"],
            "write_posture": "DIRECT_USER_AUTHORIZED",
            "record_type": "FACT",
            "record": fact("same.process.replay"),
        }
        ctx = mp.get_context("spawn")
        start = ctx.Event(); queue = ctx.Queue()
        processes = [ctx.Process(target=_proc_same_cas, args=(str(backend.MEMORY_ROOT), self.profile, payload, start, queue)) for _ in range(2)]
        for proc in processes: proc.start()
        start.set()
        results = [queue.get(timeout=15) for _ in processes]
        for proc in processes:
            proc.join(timeout=15)
            self.assertEqual(proc.exitcode, 0)
        oks = [row for row in results if row[0] == "ok"]
        self.assertEqual(len(oks), 2)
        self.assertEqual(sum(bool(row[1]) for row in oks), 1)
        self.assertEqual(len({row[2] for row in oks}), 1)
        self.assertEqual(ucm.head(self.profile)["ledger_head_seq"], h["ledger_head_seq"] + 1)


if __name__ == "__main__":
    unittest.main()
