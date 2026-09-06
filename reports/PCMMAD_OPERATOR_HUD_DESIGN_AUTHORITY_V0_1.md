# PCMMAD Operator HUD — Design Authority v0.1

Status: WORKING DESIGN AUTHORITY / donor synthesis
Scope: presentation and operator-composition layer only; runtime truth remains governed by PCMMAD server contracts.

## Intended outcome
Build a receiver-native PCMMAD operator cockpit that is functionally truthful, AI-native, human-pleasant, visually distinctive, fast enough to leave open all day, and recognizably derived from the operator's own Aero/Yui/ALCI/CogTerm/three-wing cockpit lineage rather than generic dashboard fashion.

## Source authority / donor families

### A. Liquid-Aero / ALCI / HoloFont — material and visual language
Primary originals copied under `design_donors/ui_hud_cockpit/`:
- `LIQUID_AERO_DESIGN_SYSTEM.md`
- `LIQUID_AERO_UI_v2.md`
- `ALCI_v7.2_UI_Specification.md`
- `ALCI_v7.2_LiquidGlass_Complete.html`
- `YuiUI_Ultimate.html`
- `UI ingredients/YuiUI.html`
- `UI ingredients/CogOS UI/UI.html`

Earned reusable laws:
- Glass is a layered material system, not a single translucent rectangle.
- Visual richness must have explicit performance tiers and static/accessibility fallbacks.
- HoloFont is layered text projection: substrate separation, controlled shadow/glow, optional parallax/edge treatment, state-tinted emphasis, and a plain text fallback.
- True state semantics outrank decoration; cognitive/system state color must remain redundant with text/shape/position.
- Motion should be short, damped, state-driven, and suppressible.
- Material recipes must degrade gracefully on weak hardware and under reduced-motion/high-contrast modes.
- Important surfaces must remain legible over blur/glass.

### B. YuiUI-CP — glass cockpit semantics
Primary original:
- `YuiUI_CP_v1_0_OMEGA.md`

Reusable laws:
- "Glass cockpit" means integrated situational picture, not a collection of steam gauges.
- Primary operator state should be visible without drilling through menus.
- Panels are bounded functional units with explicit purpose and lifecycle.
- Safety/critical panels may have stronger visibility/persistence rules than ordinary panels.
- The UI is a projection of machine truth, never a parallel authority surface.

### C. CogTerm — dense terminal/operator language
Primary donor set includes:
- COGTERM v5.2 HOLONIC
- COGTERM unified/spec lineage located in the E:/new pc corpus

Reusable laws:
- Information density: no wasted permanent screen real estate.
- Temporal awareness: trends/history matter, not only current scalar values.
- Mode clarity: operator must know current runtime/mode/health state unambiguously.
- Graceful degradation: useful from narrow terminal width to large displays.
- Keyboard-first operation; mouse is additive, not mandatory.
- Accessibility: never use color as the only indicator.
- Panel priority is explicit; low-priority information yields before critical state.
- Every panel is conceptually a holon: purpose, owned state, inputs, outputs, invariants, hazards, health, and ability to fail/disable without killing the whole cockpit.

### D. Forge / Singularity Works — three-wing cockpit composition
Qualified donor copies under `design_donors/forge_three_wing_cockpit/`:
- `forge_hud.html`
- `forge_hud_server.py`
- `singularity_works/hud.py`
- `singularity_works/cockpit.py`
- `singularity_works/cockpit_runtime.py`

Recovered spatial law:
- THREE-WING COCKPIT rather than generic dashboard grid.
- Left wing = evidence/status/gates/alerts/inventory.
- Center = primary active work surface / integrated picture / live focus.
- Right wing = topology/history/obligations/secondary system intelligence.
- Bottom dock = direct command/input/action surface.
- Top band/corona = compact global assurance/health/mode identity.
- Mild perspective/wing geometry may express cockpit form, but geometry SHALL NOT reduce legibility or pointer accuracy.

## PCMMAD-native synthesis

### Top corona / command status strip
Always-visible compact global truth:
- receiver state/version/root identity
- overall readiness tier
- active/degraded planes
- async running/queued/failed counts
- current restart/recovery state
- capability count / policy mode
- critical alert count
- local time / session identity where useful

### Left wing — controls, gates, queues, alerts
Candidate surfaces:
- plane health matrix
- async queue/running jobs
- recent failures/scars
- approval-required actions
- transfer tickets/result handles
- project/session quick switcher
- restart/control receipts

Priority law: failures, dangerous pending actions, and degraded required planes rise to the top automatically.

### Center wing — integrated operator picture
Default center content should be useful without selecting a tool first:
- current project/control state
- live chronological event stream
- active job detail when a job is selected
- current tool/action form when an operation is invoked
- browser/research/semantic results when those planes are active
- unified human-readable machine-truth receipts

The center SHALL NOT devolve into a giant raw JSON panel. Raw representations remain one click/key away.

### Right wing — topology, history, context
Candidate surfaces:
- capability-family topology / degraded services
- project root + mounts
- Git/current lineage state
- recent control receipts
- continuity/live-shadow indicators
- resource/host telemetry summary
- compact temporal trends/sparklines
- contextual help/schema for current operation

### Bottom dock — command bar
A first-class operator command surface:
- searchable tools/actions/projects
- keyboard-first palette
- quick command aliases
- safe free-text filter/search
- schema-aware action invocation
- explicit approval interaction when required

The dock is not a shell pretending to understand everything. It dispatches typed server operations and makes their lifecycle visible.

## Material system

### Base palette
Use the recovered Liquid-Aero dark system as donor, translated to PCMMAD semantic roles rather than copied literally.

Suggested semantic material classes:
- `glass-base` — ordinary surfaces
- `glass-raised` — active/selected surfaces
- `glass-critical` — critical/approval surfaces
- `glass-degraded` — optional-plane degradation
- `glass-terminal` — dense text/code surfaces with reduced blur

### HoloFont adaptation
Use HoloFont selectively:
- title/corona labels
- selected semantic state
- compact major readouts
- critical transition emphasis

Do NOT apply glow to long body text, logs, code, dense tables, or every label.

Mandatory fallback:
- no glow/parallax dependency for comprehension
- high-contrast text mode
- reduced-motion/static mode

### Performance tiers
Tier A / FULL:
- backdrop blur where useful
- layered borders/highlights
- restrained animated sheen/parallax
- richer charts

Tier B / BALANCED (default target for this laptop/server):
- limited blur to major structural surfaces
- no expensive continuous full-screen shader effects
- CSS transforms/opacity preferred over layout animation
- HoloFont limited to high-value text

Tier C / MINIMAL:
- opaque/translucent flat panels
- no blur/parallax
- no decorative continuous animation
- full semantic/layout parity retained

Operator can force tier. Automatic downgrade MAY occur only if observable performance thresholds are crossed and SHALL be visible.

## Interaction laws
- Keyboard-first navigation across wings and command dock.
- Pointer/touch remain fully supported.
- Focus state is always obvious.
- No critical action via hover-only control.
- Dangerous/mutating actions show approval requirement and expected lifecycle before dispatch.
- Submitted / queued / running / completed / durable / registered / promoted remain visually distinct where applicable.
- Optional-plane failure degrades that panel; it does not paint the whole cockpit red.
- Required-plane failure escalates globally.
- Panels may collapse, isolate, or disable without taking down the rest of the HUD.

## Accessibility laws
- Text/shape/icon + color redundancy.
- Reduced motion.
- Static mode.
- High-contrast mode.
- Scalable type.
- Dense/compact/full display modes.
- Glass transparency SHALL never reduce core text contrast below acceptable readability.

## Anti-patterns forbidden
- Generic admin-dashboard card soup.
- Glassmorphism for its own sake.
- Neon-everything cyberpunk noise.
- Continuous expensive shader effects on a workstation that is also doing real compute.
- One giant raw tool list as primary navigation.
- Hidden lifecycle stages.
- Color-only health semantics.
- Animations that obscure state change timing.
- Vendor-specific OpenAI/Anthropic/Google visual or protocol assumptions.
- UI-owned state that can disagree with server machine truth.

## Current implementation consequence
The existing RAHL-HUD security/journal/tool-dispatch behavior is the incumbent behavioral baseline. Presentation should be rebuilt around it incrementally while preserving its working security and approval semantics.

The first visual embodiment SHOULD prove:
1. three-wing responsive layout,
2. corona + bottom command dock,
3. Liquid-Aero tokens and balanced performance tier,
4. HoloFont applied only to selected title/state surfaces,
5. truthful core/degraded/optional plane health,
6. keyboard navigation,
7. same underlying dispatch/journal/security behavior as current HUD.

Only after that slice survives hostile UI/security/performance testing should richer motion/shader effects be admitted.
