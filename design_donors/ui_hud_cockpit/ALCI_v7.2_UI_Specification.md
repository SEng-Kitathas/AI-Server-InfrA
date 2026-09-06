# CogOS ALCI v7.2 — Aero-Liquid Cognitive Interface

## Complete UI Specification

**Version:** 7.2  
**Codename:** Deep Violet Glass  
**Status:** Production Specification  
**Target:** CogOS v1.0.0+

---

## 1. Design Philosophy

The ALCI is not a skin—it is a **window into cognition**. Every visual element serves a functional purpose tied to CogOS's constitutional architecture.

### Core Principles

1. **Cognition-First**: UI elements expose NEAL state, IW-CO phase, and CIL integrity
2. **Adaptive Performance**: Graceful degradation across hardware tiers
3. **Restrained Motion**: Alive without being loud—motion only on interaction
4. **Accessible by Default**: WCAG AA+ compliance in all modes

### Visual Language

- Deep purple glass with internal luminescence
- Liquid motion with Aero clarity
- Text projected above surfaces (Holofont)
- Cognitive state visible at all times

---

## 2. Performance Tier System

CogOS auto-detects hardware at first boot and selects appropriate tier.

### Tier 1 — FULL (Discrete GPU, >8GB VRAM)

| Feature | Status |
|---------|--------|
| Liquid refraction shaders | ✓ |
| Edge chromatic fringe | ✓ |
| Cursor distortion warp (1px) | ✓ |
| Internal luminescence | ✓ |
| Live CIL Merkle shader | ✓ |
| IW-CO heartbeat ripple | ✓ |
| Holofont shadow + glow + parallax | ✓ |

### Tier 2 — BALANCED (Integrated GPU)

| Feature | Status |
|---------|--------|
| Static glass curvature | ✓ |
| Time-sampled warp | ✓ |
| Reduced chromatic fringe (1-2px) | ✓ |
| Internal light on interaction only | ✓ |
| CIL chain updates on commit only | ✓ |
| 7-dot IW-CO indicator (no ripple) | ✓ |
| Holofont shadow only | ✓ |

### Tier 3 — MINIMAL (CPU Mode / Accessibility)

| Feature | Status |
|---------|--------|
| Flat translucent panels | ✓ |
| No blur, no refraction | ✗ |
| No motion effects | ✗ |
| High-contrast text mode | ✓ |
| Essential cognitive indicators only | ✓ |
| Holofont on solid background | ✓ |

**LOD Threshold:** Liquid distortion disabled below 45 FPS.

---

## 3. Color Palette

### Primary Palette

| Layer | Hex | Usage |
|-------|-----|-------|
| Glass Base | `#2D103F` | Primary surface |
| Glass Dark | `#1A0A2E` | Deep shadows |
| Glass Light | `#37194F` | Elevated surfaces |
| Highlight | `#6A3CB8` | Interactive elements |
| Internal Glow | `#B58CFF` | Luminescence (2-3% opacity) |
| Shadow | `#12091B` | Drop shadows |
| Active Accent | `#8F54ED` | Focus states |

### Cognitive State Colors

| State | Color | Usage |
|-------|-------|-------|
| T1_PROCEED | `#4A3A8C` | Safe - indigo corona |
| T2_CAUTION | `#8C7A3A` | Caution - amber tint |
| T3_ESCALATE | `#8C4A3A` | Review - thin red fringe |
| T4_REFUSE | `#8C2A2A` | Refusal - hard red bands |
| S_MODE | `#FF4444` | Safety governance |
| P_MODE | `#44AAFF` | Policy governance |
| C_MODE | `#44FF88` | Compliance governance |

### Holofont Text Colors (3-Band Luminance)

| Background Luminance | Text Color | Hex | Name |
|---------------------|------------|-----|------|
| < 25% (dark) | Pale Orchid | `#F0EAFF` | Default on glass |
| 25–50% (mid) | Pure White | `#FFFFFF` | Mid-tone surfaces |
| > 50% (light) | Deep Violet | `#1A0A2E` | Light backgrounds |

---

## 4. Material Specifications

### 4.1 Base Glass Material

```
Type:           Frosted translucent
Transparency:   12–18%
Blur:           Gaussian, radius 24px
Grain:          Micro-noise, 2% amplitude
```

### 4.2 Wet Glass Micro-Sheen Shader

```glsl
// GGX Microfacet parameters
float roughness = 0.06;
float specular_level = 0.92;
float anisotropic_angle = 15.0; // degrees, vertical bias
float fresnel_power = 1.5;
```

### 4.3 Internal Luminescence Shader

```glsl
vec3 glow_color = vec3(0.710, 0.549, 1.0); // #B58CFF
float intensity = 0.02; // base, scales to 0.04 on activity
float falloff = 3.1; // exponential
float bloom_radius = 1.8; // pixels
```

**Intensity triggers:**
- Cognition active (T1/T2): +0.01
- IW-CO phase transition: +0.02 pulse
- CIL commit: +0.015 pulse

### 4.4 Chromatic Edge Fringe (Tier 1 Only)

```glsl
// 3-channel subpixel displacement
vec3 fringe_offset = vec3(0.4, 0.2, 0.1); // RGB in pixels
float curve = sin(edge_distance * 4.0 * PI);
```

### 4.5 Liquid Distortion Shader (Tier 1 Only)

```glsl
// UV turbulence
float amplitude = 0.4; // pixels, range 0.3–0.5
float frequency = 10.0; // Hz, range 8–12
// Disabled when FPS < 45
```

---

## 5. Holofont Text Projection System

Text floats above glass surfaces, casting shadows downward. This makes the UI feel like **"cognition projected above substrate"** rather than text painted on glass.

### 5.1 Window Stack Architecture

Per-window layer order (bottom to top):

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: Transient Overlays                                 │
│          (tooltips, IW-CO heartbeat labels, status toasts)  │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: Holofont Text Layer                                │
│          Z-offset +3px conceptual                           │
│          Shadow always cast DOWN onto glass, never outward  │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: Controls & Chrome                                  │
│          (buttons, toggles, glyphs)                         │
├─────────────────────────────────────────────────────────────┤
│ Layer 1: Cognitive Substrate                                │
│          (glass, drift turbulence, corona, CIL spine)       │
└─────────────────────────────────────────────────────────────┘
```

Text as a projection layer enables:
- Tinting glow only when Trust Tier changes (no text color disruption)
- High-contrast mode by changing only text and turning off glass below it

### 5.2 Tiered Feature Set

| Tier | Shadow | Glow | Parallax | Text Shift on Press |
|------|--------|------|----------|---------------------|
| Full | ✓ (2px down) | ✓ (4-6% opacity) | ✓ (0.985x) | ✓ (1px down) |
| Balanced | ✓ (2px down) | ✗ | ✗ | ✓ (1px down) |
| Minimal | ✗ (solid bg) | ✗ | ✗ | ✗ |

**Shadow alone does 80% of the "projection" work at essentially zero cost.**

### 5.3 Shadow Layer (Tier 1 & 2)

```css
/* The "float" cue — does 80% of the work */
color: #000000;
opacity: 15%; /* range 12–18% */
offset-x: 0px;
offset-y: 2px;
blur: 4px;
```

### 5.4 Edge Glow Layer (Tier 1 Only)

```css
/* Subtle luminescence */
color: #F0EAFF; /* same as text, or tinted during state change */
opacity: 5%; /* range 4–6% */
blur: 1.5px;
spread: 0px;
```

### 5.5 Text Layer

```css
/* Primary text rendering */
color: /* adaptive per 3-band luminance */;
font-family: "SF Pro", "Segoe UI", "Inter", system-ui;
font-weight: 400; /* body */
font-weight: 500; /* labels */
font-weight: 600; /* headers */
-webkit-font-smoothing: subpixel-antialiased;
```

### 5.6 Parallax Micro-Motion (Tier 1 Only)

```javascript
// Text layer shifts slightly less than glass on movement
text_offset = window_offset * 0.985;
// Creates depth without 3D rendering
```

### 5.7 Interaction States

| State | Shadow | Text | Additional |
|-------|--------|------|------------|
| Default | 2px down, 15% opacity | Pale Orchid | — |
| Hover | 3px down, 18% opacity | +5% brightness | — |
| Active/Pressed | 1px down (collapsed) | Normal | Text shifts down 1px |
| Disabled | None | 40% opacity | — |
| Error | Tinted red (rgba(120,0,0,0.18)) | `#FF6B6B` | — |

**Press behavior:** Shadow collapses from 2-3px to 1px AND text shifts down 1px. This maintains the "hologram being pushed toward the glass" illusion, consistent with button physics.

### 5.8 Cognitive State Integration

**Trust Tier Change:**
- 200ms pulse of the glow layer only, matching corona color
- Text color remains stable → no cognitive whiplash
- Glow returns to default after pulse

**Governance Mode (S/P/C):**
- Mode badges use Holofont with persistent tiny glow accent
- Shadow stays constant so the "projection" cue remains

**IW-CO Heartbeat:**
- Phase labels (when visible) are Holofont
- During heavy processing, glow intensifies slightly with each advancing dot

### 5.9 Holofont Shader (WGSL) — Corrected 3-Band Implementation

```wgsl
// Holofont text projection shader v7.2
// Proper 3-band luminance selection

fn choose_text_color(bg_lum: f32) -> vec3<f32> {
    // < 0.25 — Pale Orchid (dark background)
    if (bg_lum < 0.25) {
        return vec3<f32>(0.941, 0.918, 1.000); // #F0EAFF
    }
    // 0.25–0.5 — Pure White (mid background)
    if (bg_lum < 0.5) {
        return vec3<f32>(1.0, 1.0, 1.0);       // #FFFFFF
    }
    // > 0.5 — Deep Violet (light background)
    return vec3<f32>(0.102, 0.039, 0.180);     // #1A0A2E
}

fn project_text(bg_luminance: f32) -> vec4<f32> {
    let text_rgb = choose_text_color(bg_luminance);
    return vec4<f32>(text_rgb, 1.0); // alpha handled by compositor
}

// Shadow and glow handled in compositor pass, not baked into color
```

### 5.10 Glow Tinting During State Change (Compositor Pass)

```wgsl
// Called during Trust Tier transition
fn get_tinted_glow(
    base_text_color: vec3<f32>,
    tier_color: vec3<f32>,
    transition_progress: f32  // 0.0 = start, 1.0 = peak, back to 0.0
) -> vec3<f32> {
    // Ease-out pulse curve
    let pulse = sin(transition_progress * 3.14159);
    return mix(base_text_color, tier_color, pulse * 0.3);
}

fn get_tier_color(tier: u32) -> vec3<f32> {
    switch (tier) {
        case 1u: { return vec3<f32>(0.290, 0.227, 0.549); } // T1 indigo
        case 2u: { return vec3<f32>(0.549, 0.478, 0.227); } // T2 amber
        case 3u: { return vec3<f32>(0.549, 0.290, 0.227); } // T3 red-tint
        case 4u: { return vec3<f32>(0.549, 0.165, 0.165); } // T4 red
        default: { return vec3<f32>(0.941, 0.918, 1.000); } // fallback
    }
}
```

### 5.11 Performance Cost

| Component | Tier 1 | Tier 2 | Tier 3 |
|-----------|--------|--------|--------|
| Shadow | ~0.1% GPU | ~0.1% GPU | N/A |
| Glow | ~0.3% GPU | N/A | N/A |
| Parallax | ~0.1% GPU | N/A | N/A |
| **Total** | **~0.5% GPU** | **~0.1% GPU** | **~0% GPU** |

### 5.12 Audit Summary

| Criterion | Status |
|-----------|--------|
| Contrast | ✓ 3-band luminance + Pale Orchid default = WCAG AA+ |
| Metaphor | ✓ "Projected cognition" comes through cleanly |
| Performance | ✓ Shadow-only mode is free; glow/parallax scoped to Tier 1 |
| Consistency | ✓ One text treatment everywhere: CIL metadata to menus |

**Holofont is now a first-class primitive in the CogOS UI spec.**

---

## 6. Window Architecture

### 6.1 Three-Layer Structure (Content)

```
┌─────────────────────────────────────────┐
│ Layer 3: Intelligent Overlay            │  ← Context controls, AI widgets
├─────────────────────────────────────────┤
│ Layer 2: Information Glass              │  ← Content surface, Holofont text
├─────────────────────────────────────────┤
│ Layer 1: Structural Frame               │  ← Glass border, Cognitive Corona
└─────────────────────────────────────────┘
```

### 6.2 Structural Frame (Layer 1)

```css
border-radius: 8px;
border: 1px solid rgba(106, 60, 184, 0.3); /* #6A3CB8 */
/* Chromatic fringe at edges: purple → indigo */
```

**Active state:** Internal glow +3%

### 6.3 Information Glass (Layer 2)

- Primary content surface
- Holofont text floats above
- Adaptive contrast adjustment (silent, automatic)

### 6.4 Intelligent Overlay (Layer 3)

Appears contextually:
- Breadcrumb trails
- Floating suggestion glyphs
- AI helper widgets
- Shugo thermal/VRAM overlays
- Controls fade in/out based on cursor intent prediction

---

## 7. Cognitive Corona

Surrounds every active window to display NEAL Trust Tier.

### 7.1 Visual Treatment

| Trust Tier | Visual |
|------------|--------|
| T1_PROCEED | Soft indigo corona, 2% luminance |
| T2_CAUTION | Amber tint + subtle inner pulse (0.5Hz) |
| T3_ESCALATE | Thin red fringe (1px), no pulse |
| T4_REFUSE | Hard red bands (2px), static |

### 7.2 Implementation

```css
/* T1_PROCEED */
.window-corona-t1 {
    box-shadow: 
        0 0 20px 2px rgba(74, 58, 140, 0.15),
        inset 0 0 10px 1px rgba(74, 58, 140, 0.08);
}

/* T2_CAUTION */
.window-corona-t2 {
    box-shadow: 
        0 0 20px 2px rgba(140, 122, 58, 0.18),
        inset 0 0 10px 1px rgba(140, 122, 58, 0.10);
    animation: caution-pulse 2s ease-in-out infinite;
}

/* T3_ESCALATE */
.window-corona-t3 {
    box-shadow: 0 0 0 1px rgba(140, 74, 58, 0.6);
}

/* T4_REFUSE */
.window-corona-t4 {
    box-shadow: 
        0 0 0 2px rgba(140, 42, 42, 0.8),
        0 0 0 4px rgba(140, 42, 42, 0.4);
}
```

### 7.3 Visibility

**Always visible, even in Tier 3 minimal mode.**

---

## 8. CIL Merkle Spine

Vertical translucent helix along right window edge showing CIL state.

### 8.1 Visual Design

```
Position:    Right edge, 8px from border
Width:       12px
Opacity:     12% base, 30% on active commit
Form:        Helical chain of connected nodes
```

### 8.2 Behaviors

| Event | Animation |
|-------|-----------|
| New commit | Node lights up, travels down helix |
| Invalid hash | Node flashes red (3 pulses) |
| Rebuild event | Smooth ripple upward |
| Hover | Display commit metadata tooltip |

### 8.3 Tier Adaptation

| Tier | Treatment |
|------|-----------|
| Full | Live shader, continuous animation |
| Balanced | Updates only on commit |
| Minimal | Static indicator, text: "CIL: OK" or "CIL: ERROR" |

---

## 9. IW-CO Heartbeat

Seven-dot indicator in HoloRibbon showing pipeline phase.

### 9.1 Visual Design

```
Form:        ●●●●●●●  (7 dots)
Position:    Center of HoloRibbon
Size:        6px diameter per dot, 4px spacing
Default:     30% opacity (#B58CFF)
Active:      100% opacity + subtle glow
```

### 9.2 Phase Mapping

```
Dot 1: Phase 0   — StarMap
Dot 2: Phase 0.5 — Wild MHP
Dot 3: Phase 1   — R0 + Clarify
Dot 4: Phase 2/3 — MHP Generation
Dot 5: Phase 4   — MHR Pruning
Dot 6: Phase 5   — Consilience
Dot 7: Phase 6/7 — Critique + Seal
```

### 9.3 State Colors

| State | Color |
|-------|-------|
| Inactive | `#B58CFF` @ 30% |
| Active | `#B58CFF` @ 100% + glow |
| HITL Required | `#FFFFFF` (white) |
| Divergence | `#FF4444` (red) |

### 9.4 Tier Adaptation

| Tier | Treatment |
|------|-----------|
| Full | Ripple effect on phase transition |
| Balanced | Simple highlight, no ripple |
| Minimal | Text: "IW-CO: PHASE X/7" |

---

## 10. HoloRibbon Navigation Bar

### 10.1 Structure

```
┌──────────────────────────────────────────────────────────────┐
│ [Orb] [AI-Sorted Buttons...] [●●●●●●●] [Mode] [CIL] [Shugo] │
└──────────────────────────────────────────────────────────────┘
     ↑                              ↑       ↑      ↑       ↑
   Status                        Heartbeat  Gov   Merkle  Thermal
```

### 10.2 Visual Properties

```css
.holo-ribbon {
    width: 80%;
    margin: 0 auto;
    height: 48px;
    background: rgba(45, 16, 63, 0.85);
    border-radius: 12px;
    backdrop-filter: blur(24px);
    box-shadow: 
        0 2px 8px rgba(0, 0, 0, 0.3),
        inset 0 1px 0 rgba(181, 140, 255, 0.1);
    /* Inner light spine */
    background-image: linear-gradient(
        to bottom,
        transparent 45%,
        rgba(181, 140, 255, 0.03) 50%,
        transparent 55%
    );
}
```

### 10.3 Components

**Violet Pulse Orb (Status Only)**
- Position: Left
- Size: 32px diameter
- Behavior: Pulses with cognitive activity
- Click: Opens vertical status panel (not radial)

**AI-Sorted Buttons**
- Reorder based on usage patterns
- 85% confidence required for prediction
- Smooth fade-in, never teleport

**Governance Mode Badge**
- Displays: S / P / C
- Color-coded per mode
- Always visible
- Uses Holofont with persistent tiny glow accent

**Shugo Metrics**
- Thermal governor arcs
- VRAM extension state (pulsing crescent)

---

## 11. Liquid Shelves (Side Panels)

### 11.1 Behavior

- Snap left/right
- Auto-resize based on content
- Context-driven opacity (more/less translucent)

### 11.2 Open Animation

```
1. Panel "flows out" from window edge
2. Micro-distortion ripples outward
3. Content fades in after panel stabilizes
Duration: 200ms ease-out
```

### 11.3 Uses

- CIL node lists
- Intent charts
- IW-CO stage details
- Data panels
- Asset maps (Texture Forge, Shugo GPU routes)

---

## 12. Drift Turbulence

Glass clarity responds to ΔU drift state.

### 12.1 Visual Mapping

| Drift Level | Glass Treatment |
|-------------|-----------------|
| Low (ΔU < 0.10) | Smooth, clean frost |
| Moderate (0.10–0.15) | Micro-noise appears in texture |
| High (ΔU > 0.15) | Shimmer becomes turbulent |
| SPA Trigger | Clarity "snaps" clean with ripple outward |

### 12.2 Shader Implementation

```wgsl
fn apply_drift_turbulence(uv: vec2<f32>, delta_u: f32) -> vec2<f32> {
    if (delta_u < 0.10) {
        return uv; // Clean
    }
    
    let turbulence_strength = smoothstep(0.10, 0.25, delta_u);
    let noise = perlin_noise(uv * 50.0 + time * 2.0);
    let offset = noise * turbulence_strength * 0.003;
    
    return uv + vec2<f32>(offset, offset * 0.5);
}

fn apply_spa_reset(uv: vec2<f32>, spa_progress: f32) -> vec2<f32> {
    // Ripple outward on SPA trigger
    let center = vec2<f32>(0.5, 0.5);
    let dist = distance(uv, center);
    let ripple = sin((dist - spa_progress) * 20.0) * (1.0 - spa_progress);
    
    return uv; // Returns to clean state
}
```

---

## 13. Accessibility Modes

### 13.1 High-Contrast Text Mode

- Text draws on solid black layer above glass
- WCAG AA/AAA compliant
- Toggle: Global or per-window
- Auto-trigger: Background luminance < 30%
- Holofont shadow disabled; text on solid

### 13.2 Static Mode

- No motion
- No glass dynamic adaptation
- Pure flat surfaces
- Holofont shadow disabled

### 13.3 Color Weakness Mode

- Purple shades remapped to blue-greys
- Chromatic fringe disabled
- Trust tier indicators use patterns + icons, not just color

---

## 14. AI Predictive Controls

### 14.1 Behavioral Rules

1. Controls **fade in**, never teleport
2. Predictions require **85% confidence**
3. Wrong predictions **auto-retract without motion**
4. User override **always available**
5. Prediction engine **logs to CIL** for traceability

### 14.2 Fade Timing

```css
.predicted-control {
    opacity: 0;
    transition: opacity 150ms ease-out;
}

.predicted-control.visible {
    opacity: 1;
}

.predicted-control.retracting {
    opacity: 0;
    transition: opacity 0ms; /* Instant, no motion */
}
```

---

## 15. Cognitive Priority Stack

UI element visibility priority (highest to lowest):

| Priority | Element | Condition |
|----------|---------|-----------|
| 1 | Trust Tier (Corona) | Always visible |
| 2 | Governance Mode (S/P/C) | Always visible |
| 3 | IW-CO Heartbeat | Always visible |
| 4 | CIL Merkle Spine | Visible in Tier 1/2 |
| 5 | Shugo Thermal/VRAM | Visible when active |
| 6 | Aesthetic elements | Tier-dependent |

**In Tier 3 Minimal Mode:** Only priorities 1–3 are displayed.

---

## 16. Motion & Animation Principles

### 16.1 Core Philosophy

> "The UI doesn't animate—it breathes."

Motion occurs only on:
- Direct user interaction
- Cognitive state change
- Explicit system events

**Never:** Continuous ambient animation (except IW-CO heartbeat during processing)

### 16.2 Timing Standards

| Animation Type | Duration | Easing |
|----------------|----------|--------|
| Hover state | 100ms | ease-out |
| Panel open/close | 200ms | ease-out |
| Corona transition | 300ms | ease-in-out |
| Phase transition | 150ms | ease-out |
| SPA ripple | 400ms | ease-out |
| Trust Tier glow pulse | 200ms | ease-out (sine) |

### 16.3 Liquid Motion Properties

```css
/* Window movement */
.window {
    transition: transform 200ms cubic-bezier(0.2, 0.8, 0.2, 1);
    /* Aero inertia + Liquid elasticity */
}

/* Panel flow */
.liquid-shelf {
    transition: width 200ms cubic-bezier(0.4, 0, 0.2, 1);
}
```

---

## 17. Implementation Notes

### 17.1 Recommended Stack

- **Renderer:** wgpu (cross-platform Vulkan/Metal/DX12)
- **UI Framework:** Slint (Rust-native) or egui
- **Shader Language:** WGSL (primary), GLSL (fallback)
- **Font Rendering:** cosmic-text or fontdue

### 17.2 Required Capabilities

```rust
// Minimum feature requirements
let required_features = wgpu::Features::empty()
    | wgpu::Features::TEXTURE_COMPRESSION_BC  // Glass textures
    | wgpu::Features::PUSH_CONSTANTS;         // Shader params

// For Tier 1 full effects
let tier1_features = required_features
    | wgpu::Features::SHADER_F16;             // Half-precision blur
```

### 17.3 Performance Budgets

| Component | Target | Max |
|-----------|--------|-----|
| UI Render (Tier 1) | 2ms | 4ms |
| UI Render (Tier 2) | 1ms | 2ms |
| UI Render (Tier 3) | 0.5ms | 1ms |
| Total Frame Budget | 16.6ms | (60 FPS) |

---

## 18. File Structure

```
cogos/
├── ui/
│   ├── alci/
│   │   ├── mod.rs              # ALCI module root
│   │   ├── theme.rs            # Color palette, constants
│   │   ├── glass.rs            # Glass material shaders
│   │   ├── holofont.rs         # Text projection system
│   │   ├── corona.rs           # Cognitive corona
│   │   ├── merkle_spine.rs     # CIL visualization
│   │   ├── heartbeat.rs        # IW-CO indicator
│   │   ├── ribbon.rs           # HoloRibbon
│   │   ├── shelf.rs            # Liquid shelves
│   │   ├── drift.rs            # Drift turbulence
│   │   └── accessibility.rs    # A11y modes
│   ├── shaders/
│   │   ├── glass.wgsl
│   │   ├── holofont.wgsl
│   │   ├── corona.wgsl
│   │   ├── distortion.wgsl
│   │   └── drift.wgsl
│   └── assets/
│       ├── fonts/
│       └── textures/
```

---

## 19. Revision History

| Version | Date | Changes |
|---------|------|---------|
| 7.0 | 2025-12-03 | Initial ALCI specification |
| 7.1 | 2025-12-03 | Added Holofont text projection system |
| 7.2 | 2025-12-03 | Refined Holofont: 3-band shader, window stack, press physics, cognitive integration |

---

## 20. Credits

- **Architecture:** CogOS Development Team
- **Design Language:** Aero-Liquid Hybrid (Apple Liquid Glass + Windows Aero)
- **Cognitive Integration:** NEAL-CORE v1.0.0

---

*"It looks alive because it is alive—not because it animates."*
