"""Structural guardrails for the PCMMAD three-wing operator cockpit."""
from __future__ import annotations

from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HUD_ROOT = PROJECT_ROOT / "operator_hud"


class HudCockpitStructureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.html = (HUD_ROOT / "static" / "index.html").read_text(encoding="utf-8")
        self.css = (HUD_ROOT / "static" / "style.css").read_text(encoding="utf-8")
        self.js = (HUD_ROOT / "static" / "app.js").read_text(encoding="utf-8")

    def test_primary_ops_surface_is_three_wing_cockpit_with_corona_and_dock(self) -> None:
        for token in (
            'class="topbar corona"',
            'class="wing wing-left"',
            'class="wing wing-center"',
            'class="wing wing-right"',
            'class="command-dock"',
            'id="cockpitCommand"',
        ):
            self.assertIn(token, self.html)

    def test_existing_security_and_runtime_truth_hooks_survive_visual_recomposition(self) -> None:
        for token in (
            'id="globalState"',
            'id="approvalModal"',
            'id="approvalPayload"',
            'id="confirmApproval"',
            'id="toolAvailabilityState"',
            'id="resultBox"',
            'Exact Runtime Challenge + Payload',
            'single-use handle',
            'Browser Bridge · Optional',
        ):
            self.assertIn(token, self.html)
        self.assertIn("approval_challenge", self.js)
        self.assertIn("approval_handle:challenge.handle", self.js)

    def test_quick_browser_control_is_provider_neutral_and_capability_driven(self) -> None:
        combined = (self.html + "\n" + self.js).lower()
        self.assertNotIn("duckai", combined)
        self.assertNotIn("duck.ai", combined)
        self.assertIn('id="quickBrowserAction"', self.html)
        self.assertIn('data-preset="browser"', self.html)
        self.assertIn('value="about:blank"', self.html)
        self.assertIn("browser.session.start", self.js)
        self.assertIn("quickBrowser.classList.toggle('hidden',!browserStart)", self.js)

    def test_keyboard_first_navigation_and_presentation_only_tiers_exist(self) -> None:
        self.assertIn("focusCockpitCommand", self.js)
        self.assertIn("e.altKey&&['1','2','3','4'].includes(e.key)", self.js)
        self.assertIn("localStorage.setItem('pcmmad-hud-tier'", self.js)
        self.assertIn('body[data-ui-tier="minimal"]', self.css)
        self.assertIn('@media (prefers-reduced-motion: reduce)', self.css)
        self.assertIn('@media (prefers-contrast: more)', self.css)

    def test_runtime_and_project_context_are_first_class_cockpit_truth(self) -> None:
        for token in (
            'id="runtimeIdentity"',
            'id="projectFocus"',
            'id="runtimeGeneration"',
            'id="runtimeSource"',
            'id="projectContext"',
            'RUNTIME / PROJECT CONTEXT',
        ):
            self.assertIn(token, self.html)
        self.assertIn("r.runtime_identity||{}", self.js)
        self.assertIn("r.project_catalog||{}", self.js)
        self.assertIn("identity.source_head", self.js)
        self.assertIn("catalog.projects", self.js)

    def test_cockpit_summary_is_derived_from_live_status_and_tool_catalog(self) -> None:
        self.assertIn("renderCockpitStatus(data)", self.js)
        self.assertIn("renderCockpitTools()", self.js)
        self.assertIn("state.tools.filter(t=>t.mutating).length", self.js)
        self.assertIn("ready.optional_degraded", self.js)
        self.assertNotIn("cockpitRuntimeAuthority=", self.js)


if __name__ == "__main__":
    unittest.main()
