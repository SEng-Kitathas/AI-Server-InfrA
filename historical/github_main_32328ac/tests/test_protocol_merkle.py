from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import protocol_merkle as pm
import protocol_store as ps


def _hashes(n: int) -> list[str]:
    return [hashlib.sha256(f"event-{i}".encode()).hexdigest() for i in range(n)]


def _iterative_root(event_hashes: list[str]) -> str:
    if not event_hashes:
        return hashlib.sha256(b"").hexdigest()
    frontier: list[bytes | None] = []
    for event_hash in event_hashes:
        node = hashlib.sha256(b"\x00" + bytes.fromhex(event_hash)).digest()
        level = 0
        while True:
            if level >= len(frontier):
                frontier.append(node)
                break
            if frontier[level] is None:
                frontier[level] = node
                break
            node = hashlib.sha256(b"\x01" + frontier[level] + node).digest()
            frontier[level] = None
            level += 1
    root: bytes | None = None
    for node in frontier:
        if node is None:
            continue
        root = node if root is None else hashlib.sha256(b"\x01" + node + root).digest()
    assert root is not None
    return root.hex()


class ProtocolMerklePureTests(unittest.TestCase):
    def test_inclusion_proofs_verify_for_every_leaf_across_unbalanced_sizes(self) -> None:
        for n in range(1, 33):
            hashes = _hashes(n)
            root = pm.merkle_root_hex(hashes)
            for index, event_hash in enumerate(hashes):
                proof = pm.inclusion_proof_hex(index, hashes)
                self.assertTrue(
                    pm.verify_inclusion_proof(
                        event_hash=event_hash,
                        leaf_index=index,
                        tree_size=n,
                        proof=proof,
                        expected_root=root,
                    ),
                    (n, index, proof),
                )

    def test_inclusion_tampering_and_wrong_position_fail(self) -> None:
        hashes = _hashes(7)
        proof = pm.inclusion_proof_hex(3, hashes)
        root = pm.merkle_root_hex(hashes)
        self.assertFalse(
            pm.verify_inclusion_proof(
                event_hash=_hashes(1)[0],
                leaf_index=3,
                tree_size=7,
                proof=proof,
                expected_root=root,
            )
        )
        self.assertFalse(
            pm.verify_inclusion_proof(
                event_hash=hashes[3],
                leaf_index=2,
                tree_size=7,
                proof=proof,
                expected_root=root,
            )
        )
        damaged = list(proof)
        damaged[0] = ("00" if not damaged[0].startswith("00") else "ff") + damaged[0][2:]
        self.assertFalse(
            pm.verify_inclusion_proof(
                event_hash=hashes[3],
                leaf_index=3,
                tree_size=7,
                proof=damaged,
                expected_root=root,
            )
        )

    def test_consistency_proofs_verify_for_all_prefixes_across_small_trees(self) -> None:
        for new_size in range(1, 33):
            hashes = _hashes(new_size)
            new_root = pm.merkle_root_hex(hashes)
            for old_size in range(0, new_size + 1):
                old_root = pm.merkle_root_hex(hashes[:old_size])
                proof = pm.consistency_proof_hex(old_size, hashes)
                self.assertTrue(
                    pm.verify_consistency_proof(
                        old_size=old_size,
                        new_size=new_size,
                        old_root=old_root,
                        new_root=new_root,
                        proof=proof,
                    ),
                    (old_size, new_size, proof),
                )

    def test_rfc6962_seven_leaf_consistency_proof_shapes(self) -> None:
        hashes = _hashes(7)
        self.assertEqual(len(pm.consistency_proof_hex(3, hashes)), 4)
        self.assertEqual(len(pm.consistency_proof_hex(4, hashes)), 1)
        self.assertEqual(len(pm.consistency_proof_hex(6, hashes)), 3)

    def test_root_matches_independent_iterative_frontier_across_sizes(self) -> None:
        for n in range(0, 257):
            hashes = _hashes(n)
            self.assertEqual(pm.merkle_root_hex(hashes), _iterative_root(hashes), n)

    def test_zero_tree_consistency_requires_canonical_empty_root_and_valid_digest(self) -> None:
        empty = pm.EMPTY_ROOT.hex()
        nonempty = pm.merkle_root_hex(_hashes(3))
        self.assertTrue(
            pm.verify_consistency_proof(
                old_size=0, new_size=3, old_root=empty, new_root=nonempty, proof=[]
            )
        )
        self.assertFalse(
            pm.verify_consistency_proof(
                old_size=0, new_size=3, old_root="00" * 32, new_root=nonempty, proof=[]
            )
        )
        self.assertFalse(
            pm.verify_consistency_proof(
                old_size=0, new_size=3, old_root=empty, new_root="not-a-digest", proof=[]
            )
        )
        self.assertTrue(
            pm.verify_consistency_proof(
                old_size=0, new_size=0, old_root=empty, new_root=empty, proof=[]
            )
        )
        self.assertFalse(
            pm.verify_consistency_proof(
                old_size=0, new_size=0, old_root=empty, new_root="11" * 32, proof=[]
            )
        )

    def test_historical_inclusion_proof_stays_valid_only_for_its_bound_tree(self) -> None:
        old_hashes = _hashes(8)
        old_root = pm.merkle_root_hex(old_hashes)
        proof = pm.inclusion_proof_hex(3, old_hashes)
        self.assertTrue(
            pm.verify_inclusion_proof(
                event_hash=old_hashes[3],
                leaf_index=3,
                tree_size=8,
                proof=proof,
                expected_root=old_root,
            )
        )
        new_hashes = _hashes(12)
        new_root = pm.merkle_root_hex(new_hashes)
        self.assertFalse(
            pm.verify_inclusion_proof(
                event_hash=old_hashes[3],
                leaf_index=3,
                tree_size=12,
                proof=proof,
                expected_root=new_root,
            )
        )

    def test_large_tree_receipts_remain_logarithmic_in_proof_hash_count(self) -> None:
        n = 20_000
        hashes = _hashes(n)
        inclusion = pm.inclusion_proof_hex(12_345, hashes)
        consistency = pm.consistency_proof_hex(12_345, hashes)
        self.assertLessEqual(len(inclusion), 15)
        self.assertLessEqual(len(consistency), 16)
        self.assertTrue(
            pm.verify_inclusion_proof(
                event_hash=hashes[12_345],
                leaf_index=12_345,
                tree_size=n,
                proof=inclusion,
                expected_root=pm.merkle_root_hex(hashes),
            )
        )
        self.assertTrue(
            pm.verify_consistency_proof(
                old_size=12_345,
                new_size=n,
                old_root=pm.merkle_root_hex(hashes[:12_345]),
                new_root=pm.merkle_root_hex(hashes),
                proof=consistency,
            )
        )

    def test_consistency_rejects_wrong_old_root_new_root_and_proof(self) -> None:
        hashes = _hashes(13)
        proof = pm.consistency_proof_hex(5, hashes)
        old_root = pm.merkle_root_hex(hashes[:5])
        new_root = pm.merkle_root_hex(hashes)
        bad_root = hashlib.sha256(b"wrong").hexdigest()
        self.assertFalse(
            pm.verify_consistency_proof(
                old_size=5,
                new_size=13,
                old_root=bad_root,
                new_root=new_root,
                proof=proof,
            )
        )
        self.assertFalse(
            pm.verify_consistency_proof(
                old_size=5,
                new_size=13,
                old_root=old_root,
                new_root=bad_root,
                proof=proof,
            )
        )
        damaged = list(proof)
        damaged[-1] = ("11" if not damaged[-1].startswith("11") else "22") + damaged[-1][2:]
        self.assertFalse(
            pm.verify_consistency_proof(
                old_size=5,
                new_size=13,
                old_root=old_root,
                new_root=new_root,
                proof=damaged,
            )
        )


class ProtocolMerkleIntegrationTests(unittest.TestCase):
    def _root(self, td: str) -> Path:
        return Path(td) / "projects"

    def test_receipts_rebuild_from_authoritative_ledger_and_bind_head(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-merkle-") as td:
            projects = self._root(td)
            with patch.object(ps, "get_project_root", side_effect=lambda pid: projects / pid), patch.object(
                pm, "read_events", side_effect=ps.read_events
            ), patch.object(pm, "verify_events", side_effect=ps.verify_events):
                ps.ensure_protocol("p1", actor="test")
                for i in range(1, 9):
                    ps.record_continuity(
                        "p1",
                        continuity_id=f"c{i}",
                        kind="MAINTENANCE",
                        summary=f"event {i}",
                        actor="test",
                    )

                events = ps.read_events("p1")
                root_receipt = pm.merkle_root_receipt("p1")
                inclusion = pm.merkle_inclusion_receipt("p1", 5)
                consistency = pm.merkle_consistency_receipt("p1", 4)

        self.assertEqual(root_receipt["receipt_type"], "protocol_merkle_root")
        self.assertEqual(root_receipt["tree_size"], len(events))
        self.assertEqual(root_receipt["ledger_head_hash"], events[-1].event_hash)
        self.assertTrue(root_receipt["verified_ledger_snapshot"])
        self.assertEqual(root_receipt["currentness_claim"], "not_asserted")
        self.assertTrue(root_receipt["currentness_requires_head_match"])
        self.assertEqual(inclusion["event_hash"], events[4].event_hash)
        self.assertEqual(inclusion["ledger_head_hash"], events[-1].event_hash)
        self.assertTrue(inclusion["verified"])
        self.assertTrue(inclusion["verified_ledger_snapshot"])
        self.assertEqual(inclusion["currentness_claim"], "not_asserted")
        self.assertTrue(inclusion["currentness_requires_head_match"])
        self.assertTrue(consistency["verified"])
        self.assertTrue(consistency["verified_ledger_snapshot"])
        self.assertEqual(consistency["currentness_claim"], "not_asserted")
        self.assertTrue(consistency["currentness_requires_head_match"])
        self.assertEqual(consistency["new_tree_size"], len(events))
        self.assertEqual(consistency["ledger_head_hash"], events[-1].event_hash)

    def test_receipt_does_not_claim_currentness_if_ledger_advances_after_verified_read(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-merkle-race-") as td:
            projects = self._root(td)
            with patch.object(ps, "get_project_root", side_effect=lambda pid: projects / pid), patch.object(
                pm, "read_events", side_effect=ps.read_events
            ):
                ps.ensure_protocol("p1", actor="test")
                ps.record_continuity(
                    "p1", continuity_id="c1", kind="MAINTENANCE", summary="before", actor="test"
                )
                fired = {"done": False}

                def verify_then_append(project_id: str, events=None):
                    result = ps.verify_events(project_id, events)
                    if not fired["done"]:
                        fired["done"] = True
                        ps.record_continuity(
                            "p1",
                            continuity_id="c2",
                            kind="MAINTENANCE",
                            summary="racing append",
                            actor="racer",
                        )
                    return result

                with patch.object(pm, "verify_events", side_effect=verify_then_append):
                    receipt = pm.merkle_root_receipt("p1")
                actual = ps.read_events("p1")

        self.assertTrue(receipt["verified_ledger_snapshot"])
        self.assertEqual(receipt["currentness_claim"], "not_asserted")
        self.assertTrue(receipt["currentness_requires_head_match"])
        self.assertNotEqual(receipt["ledger_head_hash"], actual[-1].event_hash)
        self.assertLess(receipt["tree_size"], len(actual))

    def test_tampered_authoritative_ledger_refuses_to_issue_proof(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-merkle-tamper-") as td:
            projects = self._root(td)
            with patch.object(ps, "get_project_root", side_effect=lambda pid: projects / pid), patch.object(
                pm, "read_events", side_effect=ps.read_events
            ), patch.object(pm, "verify_events", side_effect=ps.verify_events):
                ps.ensure_protocol("p1", actor="test")
                ps.record_continuity(
                    "p1",
                    continuity_id="c1",
                    kind="MAINTENANCE",
                    summary="event",
                    actor="test",
                )
                ledger = ps._paths("p1").events
                lines = ledger.read_text(encoding="utf-8").splitlines()
                first = json.loads(lines[0])
                first["actor"] = "evil"
                lines[0] = json.dumps(first, sort_keys=True, separators=(",", ":"))
                ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")
                with self.assertRaises(ps.ProtocolLedgerError):
                    pm.merkle_root_receipt("p1")


if __name__ == "__main__":
    unittest.main()
