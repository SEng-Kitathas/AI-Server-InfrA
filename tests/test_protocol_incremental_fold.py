from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

import protocol_store as ps
from protocol_store import ProtocolLedgerError


class ProtocolIncrementalFoldTests(unittest.TestCase):
    def setUp(self) -> None:
        with ps._SNAPSHOT_CACHE_GUARD:
            ps._SNAPSHOT_CACHE.clear()

    def tearDown(self) -> None:
        with ps._SNAPSHOT_CACHE_GUARD:
            ps._SNAPSHOT_CACHE.clear()

    def _env(self, root: Path):
        return patch.multiple(
            ps,
            get_project_root=lambda project_id: root / project_id,
            init_project_layout=lambda project_id: (root / project_id).mkdir(
                parents=True, exist_ok=True
            ),
        )

    def test_warm_mutation_extends_one_fold_without_full_rebuild(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-protocol-warm-") as td:
            root = Path(td)
            with self._env(root):
                ps.ensure_protocol("p1", actor="test")
                original_apply = ps._apply_event
                counts = {"read": 0, "verify": 0, "build": 0, "apply": 0, "snapshot": 0}

                def forbidden_read(*args, **kwargs):
                    counts["read"] += 1
                    raise AssertionError("warm mutation must not reread full ledger")

                def forbidden_verify(*args, **kwargs):
                    counts["verify"] += 1
                    raise AssertionError("warm mutation must not reverify full ledger")

                def forbidden_build(*args, **kwargs):
                    counts["build"] += 1
                    raise AssertionError("warm mutation must not rebuild full snapshot")

                def apply_once(snapshot, event):
                    counts["apply"] += 1
                    return original_apply(snapshot, event)

                def unexpected_checkpoint(*args, **kwargs):
                    counts["snapshot"] += 1
                    raise AssertionError("sequence 2 must not rewrite periodic snapshot")

                with patch.object(ps, "read_events", side_effect=forbidden_read), patch.object(
                    ps, "verify_events", side_effect=forbidden_verify
                ), patch.object(ps, "build_snapshot", side_effect=forbidden_build), patch.object(
                    ps, "_apply_event", side_effect=apply_once
                ), patch.object(ps, "_write_snapshot", side_effect=unexpected_checkpoint):
                    event = ps.record_continuity(
                        "p1",
                        continuity_id="warm-2",
                        kind="MAINTENANCE",
                        summary="warm mutation",
                        actor="test",
                    )

                self.assertEqual(event.sequence, 2)
                self.assertEqual(counts, {"read": 0, "verify": 0, "build": 0, "apply": 1, "snapshot": 0})

    def test_external_ledger_tamper_invalidates_cache_and_refuses_append(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-protocol-tamper-") as td:
            root = Path(td)
            with self._env(root):
                ps.ensure_protocol("p1", actor="test")
                ps.record_continuity(
                    "p1",
                    continuity_id="before-tamper",
                    kind="MAINTENANCE",
                    summary="before",
                    actor="test",
                )
                paths = ps._paths("p1")
                lines = paths.events.read_text(encoding="utf-8").splitlines()
                first = json.loads(lines[0])
                original_actor = str(first["actor"])
                replacement = "x" * len(original_actor)
                if replacement == original_actor:
                    replacement = "y" * len(original_actor)
                first["actor"] = replacement
                lines[0] = json.dumps(first, sort_keys=True, separators=(",", ":"))
                paths.events.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
                size_before = paths.events.stat().st_size

                with self.assertRaises(ProtocolLedgerError):
                    ps.record_continuity(
                        "p1",
                        continuity_id="must-not-append",
                        kind="MAINTENANCE",
                        summary="must fail",
                        actor="test",
                    )

                self.assertEqual(paths.events.stat().st_size, size_before)
                verify = ps.verify_events("p1")
                self.assertFalse(verify["ok"])
                self.assertTrue(verify["failures"])

    def test_durable_append_projection_failure_forces_full_rebuild_on_next_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-protocol-recovery-") as td:
            root = Path(td)
            with self._env(root):
                ps.ensure_protocol("p1", actor="test")
                original_apply = ps._apply_event
                calls = {"apply": 0}

                def fail_first_apply(snapshot, event):
                    calls["apply"] += 1
                    if calls["apply"] == 1:
                        raise RuntimeError("injected projection failure after fsync")
                    return original_apply(snapshot, event)

                with self.assertRaisesRegex(RuntimeError, "injected projection failure"):
                    with patch.object(ps, "_apply_event", side_effect=fail_first_apply):
                        ps.record_continuity(
                            "p1",
                            continuity_id="durable-before-projection-fail",
                            kind="MAINTENANCE",
                            summary="durable",
                            actor="test",
                        )

                paths = ps._paths("p1")
                self.assertEqual(len(paths.events.read_text(encoding="utf-8").splitlines()), 2)
                self.assertIsNone(ps._cached_snapshot_if_current("p1"))

                original_build = ps.build_snapshot
                rebuilds = {"count": 0}

                def count_build(*args, **kwargs):
                    rebuilds["count"] += 1
                    return original_build(*args, **kwargs)

                with patch.object(ps, "build_snapshot", side_effect=count_build):
                    event = ps.record_continuity(
                        "p1",
                        continuity_id="after-recovery",
                        kind="MAINTENANCE",
                        summary="recovered",
                        actor="test",
                    )

                self.assertEqual(event.sequence, 3)
                self.assertEqual(rebuilds["count"], 1)
                verify = ps.verify_events("p1")
                self.assertTrue(verify["ok"])
                self.assertEqual(verify["event_count"], 3)

    def test_checkpoint_projection_is_periodic_not_per_event(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-protocol-checkpoint-") as td:
            root = Path(td)
            with self._env(root):
                writes: list[int] = []
                original_write = ps._write_snapshot

                def count_write(project_id, snapshot):
                    writes.append(snapshot.event_count)
                    return original_write(project_id, snapshot)

                with patch.object(ps, "_write_snapshot", side_effect=count_write):
                    ps.ensure_protocol("p1", actor="test")
                    for sequence in range(2, ps.PROTOCOL_SNAPSHOT_CHECKPOINT_INTERVAL + 1):
                        ps.record_continuity(
                            "p1",
                            continuity_id=f"c-{sequence}",
                            kind="MAINTENANCE",
                            summary="checkpoint cadence",
                            actor="test",
                        )

                self.assertEqual(writes, [1, ps.PROTOCOL_SNAPSHOT_CHECKPOINT_INTERVAL])
                paths = ps._paths("p1")
                self.assertTrue(paths.snapshot.is_file())
                verify = ps.verify_events("p1")
                self.assertTrue(verify["ok"])
                self.assertEqual(
                    verify["event_count"], ps.PROTOCOL_SNAPSHOT_CHECKPOINT_INTERVAL
                )

    def test_cache_miss_or_restart_uses_full_verify_fold_before_append(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-protocol-restart-") as td:
            root = Path(td)
            with self._env(root):
                ps.ensure_protocol("p1", actor="test")
                ps.record_continuity(
                    "p1",
                    continuity_id="before-restart",
                    kind="MAINTENANCE",
                    summary="warm",
                    actor="test",
                )
                with ps._SNAPSHOT_CACHE_GUARD:
                    ps._SNAPSHOT_CACHE.clear()

                original_build = ps.build_snapshot
                builds = {"count": 0}

                def count_build(*args, **kwargs):
                    builds["count"] += 1
                    return original_build(*args, **kwargs)

                with patch.object(ps, "build_snapshot", side_effect=count_build):
                    event = ps.record_continuity(
                        "p1",
                        continuity_id="after-restart",
                        kind="MAINTENANCE",
                        summary="must rebuild first",
                        actor="test",
                    )

                self.assertEqual(event.sequence, 3)
                self.assertEqual(builds["count"], 1)
                self.assertTrue(ps.verify_events("p1")["ok"])


if __name__ == "__main__":
    unittest.main()
