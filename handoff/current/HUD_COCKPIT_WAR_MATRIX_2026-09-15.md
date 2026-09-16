# HUD COCKPIT / INSTRUMENT-PANEL WAR MATRIX — 2026-09-15

## Evidence from current HUD screenshot
HUD is visually coherent but operationally still a card dashboard. During Receiver outage it showed Receiver DOWN/HTTP 502, yet primary center authority remained dominated by generic repeated runtime-pulse rows. Causal evidence, recovery state, security/events, restart budget, task/process identity, and operator action were not promoted into the primary scan field.

## Design target
Strip aviation/spacecraft/cockpit patterns for information architecture, not cosplay: primary operating display, warning/caution/advisory annunciation, mode awareness, system synoptics, fault isolation, trends, redundancy, drill-down. Fictional interfaces are donor material only; retain only mechanisms that improve scan speed, comprehension, action quality, or parity of representation.

## Matrix
- Receiver down/ngrok up; ngrok down/Receiver up; Daemon degraded; multiple simultaneous failures; Defender severe detection; maintenance hold; crash-loop budget exhausted; stale continuity; approval required; mutation running; background campaign normal; no alerts; noisy telemetry flood; tiny screen; operator away; color-blind/low-contrast; keyboard-only; latency; stale UI response; contradictory status; hidden mode; false green; master-warning acknowledgment; old alarm persists after repair; 100+ events without center takeover; causal chain vs raw event list.

## Candidate cockpit decomposition
Primary operating field: organism state + causal chain + recovery mode/action.
Annunciator strip: WARN / CAUT / ADV / NORMAL with deduplication and acknowledgment semantics.
Mode/status line: authority, project, Daemon initiative, maintenance hold, approval/mutation modes.
System synoptic: Receiver/ngrok/Daemon/OOP HA/HUD/continuity/security relationships.
Trend instruments: restart attempts/window, queue/load, process churn, evidence staleness.
Secondary pages: evidence, security, continuity, topology, tools, research.

`PRETTY DASHBOARD != COCKPIT`
`MORE CARDS != MORE SITUATIONAL AWARENESS`
`PRIMARY FAILURE != SECONDARY TAB CONTENT`
