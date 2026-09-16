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
            'Browser · optional',
        ):
            self.assertIn(token, self.html)
        self.assertIn("approval_challenge", self.js)
        self.assertIn("continuation.authority_template", self.js)
        self.assertIn("permit:true", self.js)
        self.assertIn("sendDispatch(continuationTool,continuation.arguments,authority,continuation.expected_contract_digest)", self.js)
        self.assertIn("challenge?.handle", self.js)

    def test_keyboard_first_navigation_and_presentation_only_tiers_exist(self) -> None:
        self.assertIn("focusCockpitCommand", self.js)
        self.assertIn("e.altKey&&['1','2','3','4'].includes(e.key)", self.js)
        self.assertIn("localStorage.setItem('pcmmad-hud-tier'", self.js)
        self.assertIn('body[data-ui-tier="minimal"]', self.css)
        self.assertIn('@media (prefers-reduced-motion: reduce)', self.css)
        self.assertIn('@media (prefers-contrast: more)', self.css)

    def test_cockpit_summary_is_derived_from_live_status_and_tool_catalog(self) -> None:
        self.assertIn("renderCockpitStatus(data)", self.js)
        self.assertIn("renderCockpitTools()", self.js)
        self.assertIn("state.tools.filter(t=>t.mutating).length", self.js)
        self.assertIn("ready.optional_degraded", self.js)
        self.assertNotIn("cockpitRuntimeAuthority=", self.js)

    def test_primary_operating_display_prioritizes_state_causality_and_recovery_over_dispatch_history(self) -> None:
        for token in (
            'id="masterAnnunciator"', 'id="masterAnnunciatorLabel"', 'id="cockpitFaultTitle"',
            'id="cockpitCausalChain"', 'id="cockpitRecoveryCue"', 'id="synHud"',
            'id="synNgrok"', 'id="synReceiver"', 'id="synDaemon"', 'id="synJournal"', 'id="synBrowser"',
            'id="cockpitScar"',
        ):
            self.assertIn(token, self.html)
        self.assertIn("label='WARNING'", self.js)
        self.assertIn("label='CAUTION'", self.js)
        self.assertIn("label='NORMAL'", self.js)
        self.assertIn("Receiver unavailable", self.js)
        self.assertIn("Windows / Defender evidence", self.js)
        self.assertIn("Security signal present; causation is NOT established.", self.js)
        self.assertIn("transport ${n.ok?'ONLINE':'UNKNOWN/DOWN'}", self.js)
        self.assertIn("data.scar_intelligence", self.js)
        self.assertIn("completed.slice(0,4)", self.js)
        self.assertIn(".master-annunciator.warning", self.css)
        self.assertIn(".system-synoptic", self.css)
        self.assertIn(".scar-callout", self.css)

    def test_daemon_is_neutral_until_configured_and_scar_packet_is_optional(self) -> None:
        self.assertIn("d.configured?(d.ok?'ONLINE':'DEGRADED'):'STANDBY'", self.js)
        self.assertIn("!d.configured", self.js)
        self.assertIn("scarBox.hidden=true", self.js)

    def test_side_wings_are_compressed_into_instrument_banks_without_losing_controls(self) -> None:
        self.assertIn('class="instrument-bank systems-rack"', self.html)
        self.assertIn('class="instrument-bank context-bank"', self.html)
        self.assertIn('class="operating-law-strip"', self.html)
        for token in ('id="hudCard"','id="receiverCard"','id="journalCard"','id="bridgeCard"','id="openToolExplorer"','id="openBrowserView"','id="openActivityView"','id="openRawTools"'):
            self.assertIn(token,self.html)
        for token in ('.instrument-bank', '.instrument-row', '.operating-law-strip', '.law-chip'):
            self.assertIn(token,self.css)
        self.assertNotIn('class="guidance-grid"', self.html)

    def test_annunciation_lifecycle_and_condition_tape_are_first_class_instruments(self) -> None:
        for token in ('id="masterAnnunciatorMeta"','id="trendStatusAge"','id="trendLatency"','id="trendFailures"','id="trendTransport"','id="trendDaemon"'):
            self.assertIn(token,self.html)
        self.assertIn('advanceAnnunciation',self.js)
        self.assertIn('trendDirection',self.js)
        self.assertIn('.condition-tape',self.css)
        self.assertIn('.annunciator-meta',self.css)

    def test_cognitive_diagnostic_inspector_exposes_truth_layers_topology_sources_and_scars(self) -> None:
        for token in ('id="diagnosticModal"','id="diagnosticFacts"','id="diagnosticInferences"','id="diagnosticUnknowns"','id="diagnosticSources"','id="diagnosticTopology"','id="diagnosticScars"','id="diagnosticNext"','id="cockpitDiagnosticBtn"'):
            self.assertIn(token,self.html)
        for token in ('deriveDiagnosticPacket','INFERENCE BLOCKED','windows.failure_evidence.inspect','continuity:${item.surface}','scar:${scar.best_occurrence.source}','openDiagnostic','closeDiagnostic'):
            self.assertIn(token,self.js)
        for token in ('.diagnostic-modal-card','.truth-tag.fact','.truth-tag.inference-blocked','.diagnostic-map','.diagnostic-chip'):
            self.assertIn(token,self.css)
        self.assertIn('title="Open cognitive diagnostic"',self.html)
        self.assertIn('▲ Expand diagnostic',self.html)

    def test_browser_security_gate_is_integrated_as_cockpit_instrument_not_legacy_card(self) -> None:
        for token in ('id="browserGateState"','id="browserGateToggle"','id="trendBrowser"','BROWSER · SECURITY'):
            self.assertIn(token,self.html)
        for token in ('toggleBrowserGate','/api/browser/gate','ARMED / NOT READY','Browser armed but automation not ready'):
            self.assertIn(token,self.js)
        for token in ('.gate-control.blocked','.gate-control.armed','.synoptic-node.blocked'):
            self.assertIn(token,self.css)
        self.assertIn('browser-gate-instrument',self.html)
        self.assertNotIn('Browser Gate Settings',self.html)

    def test_ha_restart_budget_is_cockpit_instrument_and_diagnostic_input(self) -> None:
        self.assertIn('id="trendHaBudget"',self.html)
        for token in ('supervisor_budgets','restart budget corrupt-hold','restart budget exhausted','maintenance hold active'):
            self.assertIn(token,self.js)
        self.assertIn('HA BUDGET',self.html)


if __name__ == "__main__":
    unittest.main()
