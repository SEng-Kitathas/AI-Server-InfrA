"""Contract tests for machine-facing runtime configuration invariants."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "baseline" / "pcmmad_receiver"))

from runtime_config import (
    BrowserBridgeRuntimeConfig,
    RuntimeConfigurationError,
    ServerRuntimeConfig,
    parse_http_base_url,
    parse_port,
)


class RuntimeConfigTests(unittest.TestCase):
    def test_port_boundary_is_explicit(self) -> None:
        self.assertEqual(parse_port("5000", 1), 5000)
        for value in ("0", "65536", "abc"):
            with self.subTest(value=value), self.assertRaises(RuntimeConfigurationError):
                parse_port(value, 5000)

    def test_browser_url_boundary_rejects_opaque_or_decorated_values(self) -> None:
        self.assertEqual(parse_http_base_url("http://127.0.0.1:4471/", "x"), "http://127.0.0.1:4471")
        for value in ("file:///tmp/bridge", "bridge", "http://host/path?secret=x"):
            with self.subTest(value=value), self.assertRaises(RuntimeConfigurationError):
                parse_http_base_url(value, "http://127.0.0.1:4471")

    def test_configs_are_derived_from_environment_at_the_boundary(self) -> None:
        with patch.dict(
            os.environ,
            {
                "PCMMAD_BIND_HOST": "0.0.0.0",
                "PCMMAD_BIND_PORT": "5050",
                "PCMMAD_BROWSER_BRIDGE_URL": "http://127.0.0.1:9000/",
            },
            clear=False,
        ):
            self.assertEqual(ServerRuntimeConfig.from_env().port, 5050)
            self.assertEqual(ServerRuntimeConfig.from_env().host, "0.0.0.0")
            self.assertEqual(
                BrowserBridgeRuntimeConfig.from_env().base_url,
                "http://127.0.0.1:9000",
            )


if __name__ == "__main__":
    unittest.main()
