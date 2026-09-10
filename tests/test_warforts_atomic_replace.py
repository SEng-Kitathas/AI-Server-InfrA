from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baseline"))

import shared_core


class AtomicReplaceWarfortTests(unittest.TestCase):
    def test_transient_windows_sharing_violation_retries_then_commits(self):
        with tempfile.TemporaryDirectory(prefix="pcmmad-warfort-atomic-") as td:
            root = Path(td)
            target = root / "state.json"
            target.write_text('{"old":true}\n', encoding="utf-8")
            original_replace = Path.replace
            calls = {"count": 0}

            def flaky_replace(self: Path, destination):
                calls["count"] += 1
                if calls["count"] <= 2:
                    raise PermissionError(13, "simulated Windows sharing violation")
                return original_replace(self, destination)

            with patch.object(Path, "replace", new=flaky_replace), patch.object(
                shared_core, "_atomic_replace_transient", return_value=True
            ), patch.object(shared_core.time, "sleep", return_value=None):
                shared_core.save_json_atomic(target, {"new": True})

            self.assertEqual(calls["count"], 3)
            self.assertEqual(shared_core.load_json(target, {}), {"new": True})
            self.assertEqual([p for p in root.iterdir() if p.name.startswith("tmp")], [])

    def test_persistent_lock_fails_visible_and_cleans_temp(self):
        with tempfile.TemporaryDirectory(prefix="pcmmad-warfort-atomic-") as td:
            root = Path(td)
            target = root / "state.json"
            target.write_text('{"old":true}\n', encoding="utf-8")

            def always_locked(self: Path, destination):
                raise PermissionError(13, "persistent lock")

            with patch.object(Path, "replace", new=always_locked), patch.object(
                shared_core, "_atomic_replace_transient", return_value=True
            ), patch.object(shared_core, "_ATOMIC_REPLACE_RETRY_SECONDS", 0.0):
                with self.assertRaises(PermissionError):
                    shared_core.save_json_atomic(target, {"new": True})

            self.assertEqual(shared_core.load_json(target, {}), {"old": True})
            leftovers = [p for p in root.iterdir() if p != target]
            self.assertEqual(leftovers, [])

    def test_nontransient_replace_error_is_not_retried(self):
        with tempfile.TemporaryDirectory(prefix="pcmmad-warfort-atomic-") as td:
            root = Path(td)
            target = root / "state.json"
            calls = {"count": 0}

            def bad_replace(self: Path, destination):
                calls["count"] += 1
                raise OSError(22, "invalid argument")

            with patch.object(Path, "replace", new=bad_replace), patch.object(
                shared_core, "_atomic_replace_transient", return_value=False
            ):
                with self.assertRaises(OSError):
                    shared_core.save_json_atomic(target, {"new": True})

            self.assertEqual(calls["count"], 1)
            self.assertFalse(target.exists())
            self.assertEqual(list(root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
