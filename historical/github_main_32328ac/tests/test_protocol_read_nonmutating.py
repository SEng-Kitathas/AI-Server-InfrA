from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

import lab_tools
import protocol_store
import shared_core


class ProtocolReadNonMutatingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.projects = Path(self.temp.name) / "projects"
        self.projects.mkdir(parents=True)
        self.patches = [
            patch.object(protocol_store, "get_project_root", lambda project_id: self.projects / project_id),
            patch.object(protocol_store, "init_project_layout", lambda project_id: (self.projects / project_id).mkdir(parents=True, exist_ok=True)),
            patch.object(shared_core, "PROJECTS_ROOT", self.projects),
        ]
        for item in self.patches:
            item.start()
        (self.projects / "alpha").mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def _events(self) -> Path:
        return self.projects / "alpha" / "system" / "protocol" / "events.jsonl"

    def test_status_on_absent_protocol_is_truthful_and_nonmutating(self) -> None:
        before = list((self.projects / "alpha").rglob("*"))
        result = protocol_store.protocol_status("alpha", initialize=False)
        after = list((self.projects / "alpha").rglob("*"))
        self.assertTrue(result["ok"])
        self.assertFalse(result["initialized"])
        self.assertIsNone(result["state"])
        self.assertFalse(result["ledger"]["present"])
        self.assertEqual(result["ledger"]["event_count"], 0)
        self.assertEqual(before, after)
        self.assertFalse(self._events().exists())

    def test_guard_on_absent_protocol_preserves_legacy_without_genesis(self) -> None:
        result = protocol_store.evaluate_mode_gate("alpha", "SPECIMEN", actor="test")
        self.assertTrue(result["ok"])
        self.assertTrue(result["allowed"])
        self.assertFalse(result["initialized"])
        self.assertIsNone(result["current_mode"])
        self.assertIn("not active", result["reason"])
        self.assertFalse(self._events().exists())

    def test_initialized_status_remains_verified_read(self) -> None:
        protocol_store.ensure_protocol("alpha", actor="test", initial_mode="AUDIT")
        before = self._events().read_bytes()
        result = protocol_store.protocol_status("alpha", initialize=False)
        after = self._events().read_bytes()
        self.assertTrue(result["initialized"])
        self.assertTrue(result["ledger"]["present"])
        self.assertTrue(result["ledger"]["ok"])
        self.assertEqual(result["state"]["current_mode"], "AUDIT")
        self.assertEqual(before, after)

    def test_new_genesis_carries_current_metabolism_and_axiom(self) -> None:
        protocol_store.ensure_protocol("alpha", actor="test")
        first = json.loads(self._events().read_text(encoding="utf-8").splitlines()[0])
        payload = first["payload"]
        self.assertEqual(payload["protocol_version"], "1.1")
        self.assertEqual(payload["method_version"], protocol_store.PROTOCOL_METHOD_VERSION)
        self.assertEqual(payload["method"], protocol_store.PROTOCOL_BUILD_METABOLISM)
        self.assertEqual(payload["primary_axiom"], "INTENT IS A CONSTRAINT, NOT A CEILING.")
        self.assertIn("BUILD_SMALLEST_JUSTIFIED_CHANGE", payload["method"])
        self.assertIn("ATTACK", payload["method"])
        self.assertIn("STRIP_MUTATE", payload["method"])

    def test_protocol_read_cards_are_explicitly_non_initializing_reads(self) -> None:
        tools = {row["name"]: row for row in lab_tools.list_tools()}
        for name in ("protocol.status", "protocol.guard.check", "protocol.ledger.verify"):
            with self.subTest(name=name):
                self.assertEqual(tools[name]["side_effect_class"], "read")
                self.assertIn("non_initializing", tools[name]["effect_traits"])


if __name__ == "__main__":
    unittest.main()
