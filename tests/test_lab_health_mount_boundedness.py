"""Boundedness and non-mutation regressions for aggregate lab mount health."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

import lab_routes as lr


class LabHealthMountProbeTests(unittest.TestCase):
    def test_probe_timeout_fails_closed_without_blocking_parent(self) -> None:
        mount = {"name": "dead", "path": r"Z:\\dead"}
        with patch.object(
            lr.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(cmd=["python"], timeout=1.5),
        ):
            started = time.perf_counter()
            result = lr._probe_one_mount(mount)
            elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 0.5)
        self.assertFalse(result["exists"])
        self.assertFalse(result["writable"])
        self.assertIn("TimeoutError", result["error"])

    def test_probe_missing_mount_does_not_create_it(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "must-not-be-created"
            self.assertFalse(missing.exists())
            result = lr._probe_one_mount({"name": "missing", "path": str(missing)})
            self.assertFalse(missing.exists())
            self.assertFalse(result["exists"])
            self.assertFalse(result["writable"])

    def test_probe_decodes_successful_child_receipt(self) -> None:
        receipt = json.dumps({"exists": True, "writable": True, "error": None})
        completed = subprocess.CompletedProcess(
            args=["python"], returncode=0, stdout=receipt + "\n", stderr=""
        )
        with patch.object(lr.subprocess, "run", return_value=completed):
            result = lr._probe_one_mount({"name": "ok", "path": r"C:\\"})
        self.assertTrue(result["exists"])
        self.assertTrue(result["writable"])
        self.assertIsNone(result["error"])

    def test_aggregate_probes_mounts_concurrently_and_preserves_order(self) -> None:
        mounts = [{"name": f"m{i}", "path": f"P{i}:\\"} for i in range(8)]

        def slow_probe(mount):
            time.sleep(0.08)
            return {
                "name": mount["name"],
                "path": mount["path"],
                "exists": True,
                "writable": True,
                "error": None,
            }

        with patch.object(lr, "mount_summary", return_value=mounts), patch.object(
            lr, "_probe_one_mount", side_effect=slow_probe
        ):
            started = time.perf_counter()
            result = lr._probe_mounts()
            elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 0.35)
        self.assertEqual([row["name"] for row in result], [row["name"] for row in mounts])


if __name__ == "__main__":
    unittest.main()
