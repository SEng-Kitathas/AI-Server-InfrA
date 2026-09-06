from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HUD_SERVER = PROJECT_ROOT / "operator_hud" / "server.py"


def load_hud_module():
    name = "pcmmad_test_operator_hud_host_guard"
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, HUD_SERVER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    module.app.config.update(TESTING=True)
    return module


class HudHostGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.hud = load_hud_module()
        cls.client = cls.hud.app.test_client()

    def test_bare_localhost_is_accepted(self) -> None:
        response = self.client.get("/api/meta", headers={"Host": "localhost"})
        self.assertNotEqual(response.status_code, 421)

    def test_bare_ipv4_loopback_is_accepted(self) -> None:
        response = self.client.get("/api/meta", headers={"Host": "127.0.0.1"})
        self.assertNotEqual(response.status_code, 421)

    def test_configured_port_loopback_is_accepted(self) -> None:
        response = self.client.get(
            "/api/meta", headers={"Host": f"localhost:{self.hud.HUD_PORT}"}
        )
        self.assertNotEqual(response.status_code, 421)

    def test_foreign_host_is_rejected(self) -> None:
        response = self.client.get("/api/meta", headers={"Host": "evil.example"})
        self.assertEqual(response.status_code, 421)
        self.assertEqual(response.get_json()["error_code"], "HUD_HOST_REJECTED")

    def test_loopback_with_wrong_explicit_port_is_rejected(self) -> None:
        wrong_port = self.hud.HUD_PORT + 1
        response = self.client.get(
            "/api/meta", headers={"Host": f"127.0.0.1:{wrong_port}"}
        )
        self.assertEqual(response.status_code, 421)
        self.assertEqual(response.get_json()["error_code"], "HUD_HOST_REJECTED")


if __name__ == "__main__":
    unittest.main()
