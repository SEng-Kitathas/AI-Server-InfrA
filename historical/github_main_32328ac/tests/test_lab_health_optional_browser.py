from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT.parent))

from lab_tools_state import _lab_health_payload


class FakeLabToolError(Exception):
    def __init__(self, error_code: str, message: str, status: int = 500) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status = status


class FakeValidation:
    def to_dict(self):
        return {"api_valid": True, "connected": True, "validation_mode": "strict"}


class LabHealthOptionalBrowserTests(unittest.TestCase):
    def test_browser_bridge_failure_degrades_aggregate_health_instead_of_escaping(self) -> None:
        def bridge_call(*_args, **_kwargs):
            raise FakeLabToolError("BROWSER_BRIDGE_UNAVAILABLE", "bridge down", 502)

        dep = SimpleNamespace(
            error_cls=FakeLabToolError,
            tool_router_validation_state=lambda: FakeValidation(),
            policy_mode=lambda: "strict",
            plugin_loads=[],
            plugin_errors=[],
            beautiful_soup=object(),
            bridge_call=bridge_call,
            enabled_sources={"arxiv"},
            enabled_hunt_modes={"direct_hunt"},
            parser_version="test",
            get_cache_stats=lambda: {},
            get_index_cache_stats=lambda: {},
            execution_modes={"one_shot"},
            tool_registry={"lab.health": object()},
        )

        result = _lab_health_payload({}, dep)
        self.assertEqual(result["status"], "degraded")
        self.assertFalse(result["browser_bridge"]["ok"])
        self.assertEqual(result["browser_bridge"]["error_code"], "BROWSER_BRIDGE_UNAVAILABLE")
        self.assertEqual(result["browser_bridge"]["status"], 502)
        self.assertEqual(result["tools"], 1)


if __name__ == "__main__":
    unittest.main()
