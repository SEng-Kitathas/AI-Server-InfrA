"""Contracts for authenticated receiver-owned RED/USE observability."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask, jsonify

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "baseline"))

import observability as obs


class RuntimeObservabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = patch.dict(
            os.environ,
            {
                "GITHOME_API_KEY": "observability-test-key",
                "PCMMAD_WORKLOAD_IDENTITY_MODE": "optional",
            },
            clear=False,
        )
        self.env.start()
        with obs._HTTP_SAMPLE_LOCK:
            obs._HTTP_SAMPLES.clear()
        self.app = Flask(__name__)
        self.app.register_blueprint(obs.observability_bp)

        @self.app.get("/probe/<value>")
        def probe(value: str):
            return jsonify({"ok": True, "value": value})

        @self.app.get("/client-reject")
        def client_reject():
            return jsonify({"ok": False, "error_code": "EXPECTED_REJECT"}), 409

        @self.app.get("/server-fail")
        def server_fail():
            return jsonify({"ok": False, "error_code": "SYNTHETIC_5XX"}), 503

        self.client = self.app.test_client()
        self.auth = {"X-GitHome-Key": "observability-test-key"}

    def tearDown(self) -> None:
        self.env.stop()

    def test_telemetry_is_authenticated_and_contains_red_use_fields(self) -> None:
        denied = self.client.get("/observability/telemetry")
        self.assertEqual(denied.status_code, 401)

        response = self.client.get("/observability/telemetry", headers=self.auth)
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["basis"], "receiver_owned_observability")
        self.assertEqual(body["process"]["pid"], os.getpid())
        self.assertGreater(body["process"]["rss_bytes"], 0)
        self.assertGreater(body["system"]["memory_total_bytes"], 0)
        self.assertGreater(body["system"]["storage"]["total_bytes"], 0)
        self.assertGreater(body["system"]["storage"]["free_bytes"], 0)
        self.assertIn("p95", body["http"]["latency_ms"])
        self.assertIn("queue_depth", body["server"])
        self.assertIsNotNone(body["dependencies"]["psutil"])
        self.assertIsNotNone(body["dependencies"]["prometheus_client"])

    def test_http_red_summary_distinguishes_4xx_from_5xx(self) -> None:
        self.client.get("/probe/a")
        self.client.get("/probe/b")
        self.client.get("/client-reject")
        self.client.get("/server-fail")
        body = self.client.get("/observability/telemetry", headers=self.auth).get_json()
        http = body["http"]
        self.assertGreaterEqual(http["request_count"], 4)
        self.assertEqual(http["client_error_count"], 1)
        self.assertEqual(http["server_error_count"], 1)
        self.assertGreater(http["client_error_rate"], 0)
        self.assertGreater(http["server_error_rate"], 0)

    def test_one_failed_collector_does_not_erase_red_or_use_sections(self) -> None:
        original = obs._process_snapshot
        try:
            obs._process_snapshot = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
            body = obs.telemetry_snapshot()
        finally:
            obs._process_snapshot = original
        self.assertFalse(body["ok"])
        self.assertEqual(body["status"], "degraded")
        self.assertIn("process", body["section_errors"])
        self.assertIn("http", body)
        self.assertIn("server", body)
        self.assertIn("execution", body)
        self.assertIn("request_count", body["http"])
        self.assertIn("latency_ms", body["http"])
        self.assertIn("queue_depth", body["server"])

    def test_http_collector_failure_preserves_process_system_and_server(self) -> None:
        original = obs._http_summary
        try:
            obs._http_summary = lambda: (_ for _ in ()).throw(RuntimeError("http boom"))
            body = obs.telemetry_snapshot()
        finally:
            obs._http_summary = original
        self.assertFalse(body["ok"])
        self.assertIn("http", body["section_errors"])
        self.assertIn("rss_bytes", body["process"])
        self.assertIn("memory_total_bytes", body["system"])
        self.assertIn("worker_threads", body["server"])
        self.assertEqual(body["http"]["request_count"], 0)
        self.assertIn("latency_ms", body["http"])

    def test_prometheus_scrape_is_authenticated_and_route_labels_are_bounded(self) -> None:
        self.client.get("/probe/alpha")
        self.client.get("/probe/beta")
        denied = self.client.get("/observability/metrics")
        self.assertEqual(denied.status_code, 401)
        response = self.client.get("/observability/metrics", headers=self.auth)
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.assertIn("pcmmad_http_requests_total", text)
        self.assertIn("pcmmad_process_rss_bytes", text)
        self.assertIn("pcmmad_execution_running", text)
        self.assertIn("pcmmad_execution_queued", text)
        self.assertIn("pcmmad_execution_worker_limit", text)
        self.assertIn('route="/probe/<value>"', text)
        self.assertNotIn('route="/probe/alpha"', text)
        self.assertNotIn('route="/probe/beta"', text)

    def test_dependency_surface_keeps_profiler_on_demand(self) -> None:
        deps = obs.dependency_snapshot()
        self.assertIn("py_spy_available", deps)
        self.assertIsInstance(deps["py_spy_available"], bool)
        self.assertIsNotNone(deps["waitress"])


if __name__ == "__main__":
    unittest.main()
