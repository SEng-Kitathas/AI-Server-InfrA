from __future__ import annotations

import sys
import tempfile
import json
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baseline"))

from pcmmad_receiver import lab_routes, lab_tools


class RuntimeIdentityProjectionTests(unittest.TestCase):
    def test_runtime_identity_is_v30_engineering_truth_not_v29_package_label(self) -> None:
        lab_routes._RUNTIME_IDENTITY_CACHE = None
        identity = lab_routes._runtime_identity()
        self.assertEqual(identity["product"], "PCMMAD Laboratory Runtime")
        self.assertEqual(identity["generation"], "V30")
        self.assertEqual(identity["release_state"], "engineering_current")
        self.assertEqual(identity["schema_primary"], "v11.0 capability microkernel")
        self.assertIn("RUNTIME_ENGINEERING_IDENTITY", identity["identity_law"])
        head = identity.get("source_head")
        if head is not None:
            self.assertEqual(len(head), 40)

    def test_native_lab_health_projects_online_status_explicitly(self) -> None:
        health = lab_tools.tool_lab_health()
        self.assertTrue(health["ok"])
        self.assertEqual(health["status"], "online")
        self.assertGreaterEqual(health["tool_count"], 1)

    def test_project_catalog_is_bounded_and_uses_authoritative_projects_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pcmmad-project-catalog-") as td:
            root = Path(td)
            for name in ("CFE", "FORGE", "PCMMAD_RECEIVER_LAB"):
                (root / name).mkdir()
            (root / ".hidden").mkdir()
            with patch.object(lab_routes, "PROJECTS_ROOT", root):
                catalog = lab_routes._project_catalog()
        self.assertEqual(catalog["root"], str(root))
        self.assertEqual(catalog["projects"], ["CFE", "FORGE", "PCMMAD_RECEIVER_LAB"])
        self.assertEqual(catalog["count"], 3)
        self.assertFalse(catalog["partial"])
        self.assertIsNone(catalog["error"])




class ReleaseIdentityTests(unittest.TestCase):
    def test_active_package_identity_is_v30_laboratory_runtime(self) -> None:
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        release = json.loads((ROOT / "RELEASE.json").read_text(encoding="utf-8"))
        current = (ROOT / "baseline" / "pcmmad_receiver" / "README_CURRENT.txt").read_text(encoding="utf-8")
        self.assertTrue(version.startswith("30."), version)
        self.assertEqual(release["runtime_generation"], "V30")
        self.assertIn("Laboratory Runtime", release["name"])
        self.assertIn("V30", current)
        self.assertNotIn("V29 Native Protocol Release Candidate 1\n", current)

if __name__ == "__main__":
    unittest.main()
