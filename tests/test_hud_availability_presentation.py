from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HUD_ROOT = PROJECT_ROOT / "operator_hud"
HUD_SERVER = HUD_ROOT / "server.py"


def load_hud_module():
    name = "pcmmad_test_hud_availability_presentation"
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, HUD_SERVER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    module.app.config.update(TESTING=True)
    return module


class HudAvailabilityPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.hud = load_hud_module()
        cls.client = cls.hud.app.test_client()

    def test_optional_browser_down_keeps_core_ready(self) -> None:
        def receiver_request(path, method="GET", payload=None, timeout=5.0):
            if path == "/lab/health":
                return 200, {"ok": True, "status": "ok", "tool_count": 100, "execution_readiness": {}}
            if path == "/observability/telemetry":
                return 200, {"ok": True, "status": "available", "process": {}, "system": {}, "http": {}, "server": {}, "dependencies": {}}
            self.fail(f"unexpected receiver status path: {path}")

        with patch.object(self.hud, "receiver_request", side_effect=receiver_request), patch.object(
            self.hud,
            "bridge_request",
            return_value=(502, {"ok": False, "error": "bridge unavailable"}),
        ), patch.dict(
            self.hud.JOURNAL_STATE,
            {"ok": True, "load_integrity_ok": True, "write_ok": True},
        ):
            response = self.client.get("/api/status", headers={"Host": "localhost"})

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["receiver"]["ok"])
        self.assertFalse(body["browser_bridge"]["ok"])
        self.assertFalse(body["browser_bridge"]["required_for_core"])
        self.assertTrue(body["readiness"]["core_ready"])
        self.assertEqual(body["readiness"]["status"], "ready_optional_degraded")
        self.assertEqual(body["readiness"]["optional_degraded"], ["browser_bridge"])
        self.assertTrue(body["readiness"]["required"]["receiver"])
        self.assertFalse(body["readiness"]["optional"]["browser_bridge"])

    def test_receiver_down_means_core_not_ready_even_if_browser_is_up(self) -> None:
        with patch.object(
            self.hud,
            "receiver_request",
            return_value=(502, {"ok": False, "error_code": "receiver_down"}),
        ), patch.object(
            self.hud,
            "bridge_request",
            return_value=(200, {"ok": True}),
        ), patch.dict(
            self.hud.JOURNAL_STATE,
            {"ok": True, "load_integrity_ok": True, "write_ok": True},
        ):
            response = self.client.get("/api/status", headers={"Host": "localhost"})

        body = response.get_json()
        self.assertFalse(body["readiness"]["core_ready"])
        self.assertFalse(body["readiness"]["required"]["receiver"])
        self.assertEqual(body["readiness"]["optional_degraded"], ["observability"])
        self.assertEqual(body["readiness"]["status"], "degraded")

    def test_observability_down_is_optional_not_core_failure(self) -> None:
        def receiver_request(path, method="GET", payload=None, timeout=5.0):
            if path == "/lab/health":
                return 200, {"ok": True, "status": "ok", "tool_count": 100, "execution_readiness": {}}
            if path == "/observability/telemetry":
                return 503, {"ok": False, "error_code": "OBS_DOWN"}
            self.fail(f"unexpected receiver status path: {path}")

        with patch.object(self.hud, "receiver_request", side_effect=receiver_request), patch.object(
            self.hud, "bridge_request", return_value=(502, {"ok": False, "error": "bridge unavailable"})
        ), patch.dict(
            self.hud.JOURNAL_STATE, {"ok": True, "load_integrity_ok": True, "write_ok": True}
        ):
            response = self.client.get("/api/status", headers={"Host": "localhost"})

        body = response.get_json()
        self.assertTrue(body["readiness"]["core_ready"])
        self.assertEqual(set(body["readiness"]["optional_degraded"]), {"browser_bridge", "observability"})
        self.assertFalse(body["observability"]["required_for_core"])
        self.assertFalse(body["telemetry"]["ok"])

    def test_api_tools_preserves_native_availability_verbatim(self) -> None:
        availability = {
            "registered": True,
            "mode": "dynamic",
            "scope": "browser_bridge",
            "status": "unknown",
            "available": None,
            "probe_supported": True,
            "provider_id": "browser_bridge",
            "basis": "explicit_probe_required",
        }
        upstream = {
            "ok": True,
            "count": 1,
            "tools": [{"name": "browser.health", "availability": availability}],
        }
        with patch.object(self.hud, "receiver_request", return_value=(200, upstream)):
            response = self.client.get("/api/tools", headers={"Host": "localhost"})
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["tools"][0]["availability"], availability)

    def test_frontend_uses_selected_tool_explicit_native_probe_only(self) -> None:
        js = (HUD_ROOT / "static" / "app.js").read_text(encoding="utf-8")
        html = (HUD_ROOT / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn("availabilityChecks:{}", js)
        self.assertIn("lab.capabilities.availability", js)
        self.assertIn("tool_names:[t.name]", js)
        self.assertIn("checkSelectedAvailability", js)
        self.assertIn("a.mode==='dynamic'&&a.probe_supported", js)
        self.assertNotIn("tool_names:state.tools.map", js)
        self.assertNotIn("tool_names:state.filtered.map", js)
        self.assertIn("Check current availability", html)
        self.assertIn("NATIVE AVAILABILITY", html)

    def test_frontend_labels_optional_degradation_without_core_failure(self) -> None:
        js = (HUD_ROOT / "static" / "app.js").read_text(encoding="utf-8")
        html = (HUD_ROOT / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn("CORE READY · OPTIONAL DEGRADED", js)
        self.assertIn("core_ready", js)
        self.assertIn("optional_degraded", js)
        self.assertIn("Browser Bridge", html)
        self.assertIn("OPTIONAL", html)


    def test_frontend_rejects_stale_availability_probe_when_contract_digest_changes(self) -> None:
        js = (HUD_ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("function currentAvailabilityCheck(t)", js)
        self.assertIn("cardDigest!==checkedDigest", js)
        self.assertIn("delete state.availabilityChecks[t?.name]", js)
        self.assertIn("const checked=currentAvailabilityCheck(t)", js)

    def test_catalog_refresh_rebinds_selected_tool_to_fresh_native_card(self) -> None:
        js = (HUD_ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("const selectedName=state.selected?.name||null", js)
        self.assertIn("const fresh=state.tools.find(t=>t.name===selectedName)||null", js)
        self.assertIn("state.selected=fresh", js)
        self.assertIn("renderAvailability(fresh)", js)
        self.assertIn("delete state.availabilityChecks[selectedName]", js)

    def test_dynamic_probe_result_is_ephemeral_ui_state_not_native_card_rewrite(self) -> None:
        js = (HUD_ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("state.availabilityChecks[t.name]=row", js)
        self.assertNotIn("t.availability=row", js)
        self.assertNotIn("state.tools[t.name].availability=row", js)


if __name__ == "__main__":
    unittest.main()
