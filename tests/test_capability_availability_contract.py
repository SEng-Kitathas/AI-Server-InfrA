from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PROJECT_ROOT / "baseline" / "pcmmad_receiver"
sys.path.insert(0, str(RUNTIME_ROOT))

import lab_tools
import lab_tools_semantic
from control_plane_models import ToolSpec


class CapabilityAvailabilityContractTests(unittest.TestCase):
    def test_card_describes_dynamic_availability_without_executing_provider(self) -> None:
        calls = []

        def provider():
            calls.append(True)
            return {"status": "available", "available": True}

        spec = ToolSpec(
            name="x.dynamic",
            description="dynamic",
            availability_mode="dynamic",
            availability_scope="external_provider",
            availability_provider_id="provider.x",
            availability_provider=provider,
            handler=lambda payload: {},
        )
        card = spec.to_card()
        self.assertEqual(calls, [])
        self.assertEqual(card["availability"]["mode"], "dynamic")
        self.assertEqual(card["availability"]["status"], "unknown")
        self.assertIsNone(card["availability"]["available"])
        self.assertTrue(card["availability"]["probe_supported"])
        self.assertEqual(card["availability"]["provider_id"], "provider.x")

    def test_resident_card_means_handler_dispatchability_not_target_health(self) -> None:
        spec = ToolSpec(name="x.resident", description="resident", handler=lambda payload: {})
        availability = spec.to_card()["availability"]
        self.assertEqual(availability["mode"], "resident")
        self.assertTrue(availability["registered"])
        self.assertEqual(availability["status"], "available")
        self.assertTrue(availability["available"])
        self.assertEqual(availability["basis"], "registered_handler")

    def test_availability_semantics_participate_in_contract_digest(self) -> None:
        base = dict(name="x", description="x", handler=lambda payload: {})
        resident = ToolSpec(**base)
        dynamic = ToolSpec(
            **base,
            availability_mode="dynamic",
            availability_scope="provider",
            availability_provider_id="p",
            availability_provider=lambda: {"available": True},
        )
        self.assertNotEqual(resident.contract_digest, dynamic.contract_digest)

    def test_explicit_probe_deduplicates_shared_provider(self) -> None:
        calls = []

        def provider():
            calls.append(True)
            return {"status": "available", "available": True, "basis": "shared"}

        registry = {
            name: ToolSpec(
                name=name,
                description=name,
                handler=lambda payload: {},
                availability_mode="dynamic",
                availability_scope="bridge",
                availability_provider_id="shared.bridge",
                availability_provider=provider,
            )
            for name in ("x.one", "x.two", "x.three")
        }
        result = lab_tools._capability_availability_payload(
            {"tool_names": list(registry)}, registry
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["provider_probe_count"], 1)
        self.assertEqual(result["count"], 3)
        self.assertTrue(all(row["available"] for row in result["rows"]))

    def test_provider_exception_fails_unknown_not_green(self) -> None:
        def bad_provider():
            raise RuntimeError("provider exploded")

        registry = {
            "x.bad": ToolSpec(
                name="x.bad",
                description="bad",
                handler=lambda payload: {},
                availability_mode="dynamic",
                availability_scope="provider",
                availability_provider_id="bad.provider",
                availability_provider=bad_provider,
            )
        }
        row = lab_tools._capability_availability_payload(
            {"tool_names": ["x.bad"]}, registry
        )["rows"][0]
        self.assertEqual(row["status"], "unknown")
        self.assertIsNone(row["available"])
        self.assertIn("availability_probe_failed", row["blockers"])
        self.assertIn("provider exploded", row["error"])

    def test_request_is_bounded_and_unknown_tools_fail_closed(self) -> None:
        with self.assertRaises(lab_tools.LabToolError) as too_many:
            lab_tools._capability_availability_payload(
                {"tool_names": [f"x.{i}" for i in range(lab_tools.AVAILABILITY_MAX_TOOLS + 1)]},
                {},
            )
        self.assertEqual(
            too_many.exception.error_code, "CAPABILITY_AVAILABILITY_LIMIT_EXCEEDED"
        )

        with self.assertRaises(lab_tools.LabToolError) as missing:
            lab_tools._capability_availability_payload(
                {"tool_names": ["not.registered"]}, {}
            )
        self.assertEqual(missing.exception.error_code, "TOOL_NOT_FOUND")

    def test_actual_registry_exposes_provider_contracts_without_probing(self) -> None:
        cards = {row["name"]: row for row in lab_tools.list_tools()}
        self.assertIn("lab.capabilities.availability", cards)
        self.assertEqual(
            cards["lab.capabilities.availability"]["availability"]["mode"], "resident"
        )

        for name in (
            "browser.health",
            "browser.sessions.list",
            "browser.navigate",
            "browser.screenshot",
            "procedure.browser.prompt_capture",
        ):
            availability = cards[name]["availability"]
            self.assertEqual(availability["mode"], "dynamic", name)
            self.assertEqual(availability["scope"], "browser_bridge", name)
            self.assertEqual(availability["provider_id"], "browser_bridge", name)
            self.assertEqual(availability["status"], "unknown", name)

        semantic_search = cards["semantic.monster.search"]["availability"]
        self.assertEqual(semantic_search["mode"], "dynamic")
        self.assertEqual(
            semantic_search["provider_id"], "semantic.monster.default_runtime"
        )
        self.assertIn("per-call explicit", semantic_search["scope"])

        semantic_health = cards["semantic.monster.health"]["availability"]
        self.assertEqual(semantic_health["mode"], "resident")
        self.assertTrue(semantic_health["available"])

        lab_health = cards["lab.health"]["availability"]
        self.assertEqual(lab_health["mode"], "resident")

    def test_semantic_default_probe_does_not_overclaim_explicit_overrides(self) -> None:
        with patch.object(
            lab_tools_semantic,
            "_semantic_resolution",
            return_value={
                "available": False,
                "blockers": ["no_qualified_python_runtime"],
                "python": {"selected": None},
            },
        ):
            result = lab_tools_semantic._semantic_default_search_availability()
        self.assertFalse(result["available"])
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["basis"], "semantic_default_runtime_probe")
        card = {row["name"]: row for row in lab_tools.list_tools()}[
            "semantic.monster.search"
        ]
        self.assertIn("per-call explicit", card["availability"]["scope"])

    def test_resident_availability_probe_does_not_invoke_target_handler(self) -> None:
        calls = []
        registry = {
            "x.resident": ToolSpec(
                name="x.resident",
                description="resident",
                handler=lambda payload: calls.append(payload) or {},
            )
        }
        row = lab_tools._capability_availability_payload(
            {"tool_names": ["x.resident"]}, registry
        )["rows"][0]
        self.assertEqual(calls, [])
        self.assertTrue(row["available"])
        self.assertEqual(row["basis"], "registered_handler")


if __name__ == "__main__":
    unittest.main()
