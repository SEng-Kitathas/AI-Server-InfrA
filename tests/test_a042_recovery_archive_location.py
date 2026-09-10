from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CURRENT = PROJECT_ROOT / "handoff" / "current"
ARCHIVE = PROJECT_ROOT / "handoff" / "archive" / "a042_wip_recovery_2026-09-07"


class A042RecoveryArchiveLocationTests(unittest.TestCase):
    def test_current_handoff_contains_locator_not_shadow_source_files(self) -> None:
        self.assertFalse((CURRENT / "wip").exists())
        locator = CURRENT / "A042_HISTORICAL_WIP_RECOVERY_POINTER.md"
        self.assertTrue(locator.is_file())
        text = locator.read_text(encoding="utf-8")
        self.assertIn("historical recovery evidence", text.lower())
        self.assertIn("handoff/archive/a042_wip_recovery_2026-09-07", text.replace("\\", "/"))

    def test_archived_inventory_and_all_thirteen_payload_hashes_are_preserved(self) -> None:
        inventory_path = ARCHIVE / "A042_WIP_INVENTORY.json"
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        self.assertEqual(inventory["schema"], "pcmmad.a042-wip-recovery.v2")
        self.assertEqual(inventory["file_count"], 13)
        self.assertEqual(len(inventory["files"]), 13)
        for row in inventory["files"]:
            archived_name = Path(row["recovery_path"]).name
            path = ARCHIVE / archived_name
            self.assertTrue(path.is_file(), archived_name)
            data = path.read_bytes()
            self.assertEqual(len(data), row["bytes"], archived_name)
            self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"], archived_name)

    def test_project_mutation_authority_historical_identity_is_unchanged(self) -> None:
        path = ARCHIVE / "A042_PROJECT_MUTATION_AUTHORITY_WIP.py"
        self.assertEqual(path.stat().st_size, 20926)
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            "5e294d1ae20601d9a5404f5b4712d82c676ca6acc55c9530a5787dc6239ed04e",
        )


if __name__ == "__main__":
    unittest.main()
