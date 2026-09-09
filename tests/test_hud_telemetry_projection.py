"""HUD contracts for receiver-owned telemetry projection and alert semantics."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HUD_ROOT = PROJECT_ROOT / "operator_hud"
HUD_SERVER = HUD_ROOT / "server.py"


def load_hud_module():
    name = "pcmmad_test_hud_telemetry_projection"
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, HUD_SERVER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    module.app.config.update(TESTING=True)
    return module


class HudTelemetryProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.hud = load_hud_module()

    def setUp(self) -> None:
        with self.hud.TELEMETRY_LOCK:
            self.hud.TELEMETRY_HISTORY.clear()

    def _health(self) -> dict:
        return {
            "ok": True,
            "tool_count": 116,
            "execution_readiness": {
                "status": "online",
                "global": {
                    "running": 10,
                    "queued": 2,
                    "global_limit": 12,
                    "global_queue_limit": 0,
                    "oldest_queued_age_seconds": 1.5,
                },
                "scheduler_thread_alive": True,
                "scheduler_telemetry": {
                    "watcher_alive": True,
                    "watcher_errors": 0,
                    "jobs_reconcile_errors": 0,
                    "last_tick_reconcile_errors": 0,
                    "last_error": None,
                },
                "unsupervised_jobs": [],
                "corrupt_job_files": [],
            },
            "background_batch_executor": {"configured_workers": 4, "alive": True},
        }

    def _observed(self) -> dict:
        return {
            "ok": True,
            "status": "available",
            "process": {
                "cpu_percent": 22.5,
                "rss_bytes": 64 * 1024 * 1024,
                "uss_bytes": 48 * 1024 * 1024,
                "handles": 420,
                "threads": 20,
                "connections": 4,
                "open_files": 3,
            },
            "system": {"memory_percent": 58.0, "storage": {"free_bytes": 200 * 1024 * 1024 * 1024, "percent": 50.0}},
            "http": {
                "request_count": 200,
                "requests_per_minute": 40.0,
                "client_error_count": 4,
                "server_error_count": 0,
                "server_error_rate": 0.0,
                "latency_ms": {"p50": 40.0, "p95": 450.0, "p99": 900.0},
            },
            "server": {
                "implementation": "waitress",
                "instrumented": True,
                "active_workers": 5,
                "worker_threads": 16,
                "queue_depth": 0,
                "queue_peak": 3,
                "active_peak": 12,
            },
            "dependencies": {
                "psutil": "7.2.2",
                "prometheus_client": "0.26.0",
                "waitress": "3.0.2",
                "py_spy": "0.4.2",
                "py_spy_available": True,
            },
        }

    def test_projection_preserves_loaded_capacity_and_resource_truth(self) -> None:
        telemetry = self.hud._telemetry_projection(self._health(), self._observed(), observed_ok=True)
        self.assertTrue(telemetry["ok"])
        self.assertEqual(telemetry["execution"]["global"]["global_limit"], 12)
        self.assertEqual(telemetry["process"]["handles"], 420)
        self.assertEqual(telemetry["server"]["worker_threads"], 16)
        self.assertEqual(telemetry["severity"], "warning")
        codes = {row["code"] for row in telemetry["alerts"]}
        self.assertIn("EXECUTION_QUEUE", codes)

    def test_integrity_failures_are_critical_not_generic_degradation(self) -> None:
        health = self._health()
        health["execution_readiness"]["unsupervised_jobs"] = ["orphan-1"]
        health["execution_readiness"]["scheduler_telemetry"]["watcher_errors"] = 1
        health["execution_readiness"]["scheduler_telemetry"]["last_watcher_error"] = "watcher exploded"
        observed = self._observed()
        observed["system"]["storage"]["percent"] = 95.0
        telemetry = self.hud._telemetry_projection(health, observed, observed_ok=True)
        self.assertEqual(telemetry["severity"], "critical")
        codes = {row["code"] for row in telemetry["alerts"]}
        self.assertIn("UNSUPERVISED_JOBS", codes)
        self.assertIn("WATCHER_ERROR", codes)
        self.assertIn("STORAGE_SPACE", codes)

    def test_history_is_bounded_for_browser_payload(self) -> None:
        health = self._health()
        observed = self._observed()
        for i in range(80):
            observed["process"]["rss_bytes"] += i
            result = self.hud._telemetry_projection(health, observed, observed_ok=True)
        self.assertEqual(len(result["history"]), 60)
        with self.hud.TELEMETRY_LOCK:
            self.assertEqual(len(self.hud.TELEMETRY_HISTORY), 80)

    def test_frontend_contains_active_telemetry_and_no_external_chart_dependency(self) -> None:
        html = (HUD_ROOT / "static" / "index.html").read_text(encoding="utf-8")
        js = (HUD_ROOT / "static" / "app.js").read_text(encoding="utf-8")
        for token in (
            "ACTIVE TELEMETRY · RED + USE + SCHEDULER",
            'id="telemetryWorkers"',
            'id="telemetryP95"',
            'id="telemetryRss"',
            'id="telemetryHostCpu"',
            'id="telemetryStorage"',
            'id="telemetryAlerts"',
            'id="telemetryDependencies"',
        ):
            self.assertIn(token, html)
        self.assertIn("function renderTelemetry(t)", js)
        self.assertIn("function sparkSvg(values)", js)
        self.assertIn("renderTelemetry(data.telemetry||{})", js)
        self.assertNotIn("chart.js", html.lower())
        self.assertNotIn("cdn.", html.lower())


if __name__ == "__main__":
    unittest.main()
