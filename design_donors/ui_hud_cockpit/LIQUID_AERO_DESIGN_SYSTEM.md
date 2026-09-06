# Liquid-Aero Design System

**A Unified Visual Language for Holonic Linux + Waydroid Android**

Version 1.0.0  
Author: Shane Thomas England

---

## Philosophy

This design system implements a cohesive visual language that spans the entire device—from native Linux applications to Android apps running in Waydroid. The user should never feel a "seam" between the two environments.

The aesthetic merges:
- **Apple's Liquid Glass**: Frosted translucent panels, soft glow, saturation boost, depth through blur
- **Windows Aero**: Glass borders, subtle bloom, lit edges, sense of floating layers
- **Holofont Projection**: Text that appears to hover above surfaces, casting soft shadows onto the glass beneath

**Core Principle:** The UI should feel like looking into a dark, luminous aquarium—depth, glow, and floating elements suspended in space.

---

## Design Tokens

### Colors (Dark Mode Base)

```
┌─────────────────────────────────────────────────────────────┐
│  COLOR TOKENS                                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Background Layer                                           │
│  ├─ bg_void         #030108    The deepest black            │
│  ├─ bg_solid        #05030A    Near-black base              │
│  └─ bg_elevated     #0A0612    Slightly lifted surfaces     │
│                                                             │
│  Glass Layer                                                │
│  ├─ glass_dark      #10081A    60% opacity - deep glass     │
│  ├─ glass_mid       #1A1028    50% opacity - standard       │
│  ├─ glass_light     #251838    40% opacity - elevated       │
│  └─ glass_border    #FFFFFF12  Edge highlight               │
│                                                             │
│  Accent (Purple/Violet Primary)                             │
│  ├─ accent_primary  #7C3AED    Main interactive             │
│  ├─ accent_glow     #A78BFA    Soft glow / hover            │
│  ├─ accent_dim      #5B21B6    Pressed / secondary          │
│  └─ accent_surface  #7C3AED20  Tinted glass for accents     │
│                                                             │
│  Text (Holofont Palette)                                    │
│  ├─ text_primary    #F0EAFF    Pale Orchid - main text      │
│  ├─ text_secondary  #C0B9E5    Muted - secondary            │
│  ├─ text_tertiary   #8B7FA8    Dim - hints, disabled        │
│  └─ text_inverse    #1A0A2E    On light surfaces            │
│                                                             │
│  Semantic                                                   │
│  ├─ success         #10B981    Green                        │
│  ├─ warning         #F59E0B    Amber                        │
│  ├─ error           #EF4444    Red                          │
│  └─ info            #3B82F6    Blue                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Spatial Tokens

```
┌─────────────────────────────────────────────────────────────┐
│  SPATIAL TOKENS                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Border Radius                                              │
│  ├─ radius_xs       4dp        Chips, tags                  │
│  ├─ radius_sm       8dp        Buttons, inputs              │
│  ├─ radius_md       12dp       Cards, tiles                 │
│  ├─ radius_lg       16dp       Panels, dialogs              │
│  ├─ radius_xl       20dp       Major containers             │
│  └─ radius_full     9999dp     Pills, avatars               │
│                                                             │
│  Spacing (4dp grid)                                         │
│  ├─ space_xs        4dp                                     │
│  ├─ space_sm        8dp                                     │
│  ├─ space_md        12dp                                    │
│  ├─ space_lg        16dp                                    │
│  ├─ space_xl        24dp                                    │
│  └─ space_2xl       32dp                                    │
│                                                             │
│  Elevation (for shadows)                                    │
│  ├─ elevation_none  0dp        Flat                         │
│  ├─ elevation_low   2dp        Subtle lift                  │
│  ├─ elevation_mid   4dp        Cards                        │
│  ├─ elevation_high  8dp        Dialogs, menus               │
│  └─ elevation_glass 16dp       Floating glass panels        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Effect Tokens

```
┌─────────────────────────────────────────────────────────────┐
│  EFFECT TOKENS                                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Blur (for glass effect)                                    │
│  ├─ blur_subtle     8px        Light frosting               │
│  ├─ blur_standard   16px       Standard glass               │
│  ├─ blur_heavy      24px       Deep frosting                │
│  └─ blur_max        32px       Maximum (use sparingly)      │
│                                                             │
│  Glow (for accent elements)                                 │
│  ├─ glow_radius     12px       Spread of glow               │
│  ├─ glow_color      accent_glow @ 40% opacity               │
│  └─ glow_active     accent_primary @ 60% opacity            │
│                                                             │
│  Holofont Shadow (text projection)                          │
│  ├─ shadow_radius   4px                                     │
│  ├─ shadow_offset_x 0px                                     │
│  ├─ shadow_offset_y 2px                                     │
│  └─ shadow_color    (sampled from surface @ 70% opacity)    │
│                                                             │
│  Aero Edge                                                  │
│  ├─ edge_highlight  #FFFFFF18  Top/left inner stroke        │
│  ├─ edge_shadow     #00000033  Bottom/right inner stroke    │
│  └─ edge_width      1px                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Glass Surface

The fundamental building block—a translucent panel with blur and edge treatment.

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│    ┌───────────────────────────────────────────────────┐    │
│    │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│◄── Highlight edge (top/left)
│    │░                                               ░░│    │
│    │░          GLASS SURFACE                        ░░│◄── Blurred background shows through
│    │░                                               ░░│    │
│    │░░                                             ░░░│    │
│    │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│◄── Shadow edge (bottom/right)
│    └───────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Properties:
├─ background: glass_mid @ 50% opacity
├─ border-radius: radius_lg (16dp)
├─ backdrop-filter: blur(blur_standard) [16px]
├─ border-top: 1px solid edge_highlight
├─ border-left: 1px solid edge_highlight  
├─ border-bottom: 1px solid edge_shadow
├─ border-right: 1px solid edge_shadow
└─ box-shadow: 0 4px 16px rgba(0,0,0,0.4)
```

### 2. Glass Card

A Glass Surface with structured content layout.

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│    ┌───────────────────────────────────────────────────┐    │
│    │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│    │
│    │░                                               ░░│    │
│    │░   ┌──────┐                                    ░░│    │
│    │░   │ ICON │   Title Text                       ░░│◄── Holofont projection
│    │░   └──────┘   Secondary text                   ░░│    │
│    │░              ─────────────────────────        ░░│    │
│    │░                                               ░░│    │
│    │░              [ Action ]  [ Action ]           ░░│    │
│    │░░                                             ░░░│    │
│    │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│    │
│    └───────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3. Holofont Text

Text that appears to float above the surface, casting a soft shadow.

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  HOLOFONT RENDERING                                         │
│                                                             │
│  Layer Stack (bottom to top):                               │
│                                                             │
│  1. Glass Surface (blur applied)                            │
│           │                                                 │
│  2. Text Shadow ─────────────────────────┐                  │
│     │   color: surface_color @ 70%       │                  │
│     │   blur: 4px                        │ ← Creates the    │
│     │   offset: (0px, 2px)               │   "projection"   │
│           │                              │   onto glass     │
│  3. Primary Text ────────────────────────┘                  │
│         color: text_primary (#F0EAFF)                       │
│         font-weight: 500                                    │
│                                                             │
│  Visual Result:                                             │
│                                                             │
│     ░░░░░░░░░░░░░░░░░░░░░░░░░░░░    ← Glass surface        │
│     ░░░░░░░░░░░░░░░░░░░░░░░░░░░░                            │
│     ░░░░░░░░░████████░░░░░░░░░░░    ← Shadow (blurred)     │
│     ░░░░░░░░████████████░░░░░░░░                            │
│            ▀▀▀▀▀▀▀▀▀▀▀▀          ← Text (crisp)            │
│            Hello World                                      │
│                                                             │
│  The shadow color is SAMPLED from the glass beneath,        │
│  creating a cohesive "cast shadow" effect unique to         │
│  each surface's tint.                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4. Glow Button / Active State

Interactive elements get a soft radial glow when active/focused.

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  BUTTON STATES                                              │
│                                                             │
│  Default:                                                   │
│  ┌──────────────────────┐                                   │
│  │     Button Label     │  glass_mid, no glow               │
│  └──────────────────────┘                                   │
│                                                             │
│  Hover:                                                     │
│  ┌──────────────────────┐                                   │
│  │     Button Label     │  glass_light, subtle glow         │
│  └──────────────────────┘                                   │
│    ╰── soft purple halo ──╯                                 │
│                                                             │
│  Active/Pressed:                                            │
│  ╭┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈╮                                   │
│  ┊  ┌──────────────────┐ ┊  accent_surface, strong glow     │
│  ┊  │  Button Label    │ ┊                                  │
│  ┊  └──────────────────┘ ┊                                  │
│  ╰┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈╯                                   │
│    ╰── intense purple aura ──╯                              │
│                                                             │
│  Glow Implementation:                                       │
│  ├─ box-shadow: 0 0 12px accent_glow @ 40%                  │
│  └─ For strong: 0 0 20px accent_primary @ 60%               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Platform Implementations

### Linux (GTK4 + Adwaita)

```css
/* /usr/share/themes/LiquidAero/gtk-4.0/gtk.css */

@define-color bg_void #030108;
@define-color bg_solid #05030A;
@define-color glass_mid rgba(26, 16, 40, 0.5);
@define-color accent_primary #7C3AED;
@define-color text_primary #F0EAFF;

/* Glass Surface */
.glass-surface {
  background-color: @glass_mid;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.07);
  box-shadow: 
    inset 1px 1px 0 rgba(255, 255, 255, 0.09),
    inset -1px -1px 0 rgba(0, 0, 0, 0.2),
    0 4px 16px rgba(0, 0, 0, 0.4);
}

/* Note: GTK4 blur requires compositor support (Mutter/KWin) */
/* Use background-blend-mode or pre-blurred wallpaper regions */

/* Holofont Text */
.holofont {
  color: @text_primary;
  text-shadow: 0 2px 4px rgba(26, 16, 40, 0.7);
}

/* Glow Button */
.glow-button:hover {
  box-shadow: 0 0 12px rgba(167, 139, 250, 0.4);
}

.glow-button:active {
  background-color: rgba(124, 58, 237, 0.2);
  box-shadow: 0 0 20px rgba(124, 58, 237, 0.6);
}
```

### Linux (Qt/QML)

```qml
// GlassSurface.qml
import QtQuick 2.15
import QtGraphicalEffects 1.15

Rectangle {
    id: glassSurface
    
    color: "#1A1028"  // glass_mid
    opacity: 0.5
    radius: 16
    
    border.width: 1
    border.color: "#FFFFFF12"
    
    // Blur effect (requires source behind)
    layer.enabled: true
    layer.effect: GaussianBlur {
        radius: 16
        samples: 33
    }
    
    // Aero edge highlights
    Rectangle {
        anchors.fill: parent
        color: "transparent"
        radius: parent.radius
        border.width: 1
        border.color: "#FFFFFF18"
        anchors.margins: -1
    }
}

// HolofontText.qml
Text {
    id: holofontText
    color: "#F0EAFF"
    font.weight: Font.Medium
    
    layer.enabled: true
    layer.effect: DropShadow {
        radius: 4
        samples: 9
        verticalOffset: 2
        color: "#B31A1028"  // glass_mid @ 70%
    }
}
```

### Android (Jetpack Compose)

```kotlin
// theme/LiquidAeroTheme.kt
package com.holonic.liquidaero

import androidx.compose.ui.graphics.Color

object LiquidAeroColors {
    val bgVoid = Color(0xFF030108)
    val bgSolid = Color(0xFF05030A)
    val glassMid = Color(0x801A1028)  // 50% opacity
    val glassLight = Color(0x66251838) // 40% opacity
    val accentPrimary = Color(0xFF7C3AED)
    val accentGlow = Color(0xFFA78BFA)
    val textPrimary = Color(0xFFF0EAFF)
    val textSecondary = Color(0xFFC0B9E5)
}

// components/GlassSurface.kt
@Composable
fun GlassSurface(
    modifier: Modifier = Modifier,
    blurRadius: Float = 16f,
    content: @Composable () -> Unit
) {
    Box(
        modifier = modifier
            .graphicsLayer {
                // Hardware blur (Android 12+)
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                    renderEffect = RenderEffect.createBlurEffect(
                        blurRadius, blurRadius,
                        Shader.TileMode.CLAMP
                    )
                }
            }
            .background(
                color = LiquidAeroColors.glassMid,
                shape = RoundedCornerShape(16.dp)
            )
            .border(
                width = 1.dp,
                brush = Brush.linearGradient(
                    colors = listOf(
                        Color.White.copy(alpha = 0.09f),
                        Color.Black.copy(alpha = 0.2f)
                    ),
                    start = Offset.Zero,
                    end = Offset.Infinite
                ),
                shape = RoundedCornerShape(16.dp)
            )
            .padding(16.dp)
    ) {
        content()
    }
}

// components/HolofontText.kt
@Composable
fun HolofontText(
    text: String,
    modifier: Modifier = Modifier,
    style: TextStyle = MaterialTheme.typography.bodyLarge,
    shadowColor: Color = LiquidAeroColors.glassMid.copy(alpha = 0.7f)
) {
    Text(
        text = text,
        modifier = modifier,
        style = style.copy(
            color = LiquidAeroColors.textPrimary,
            shadow = Shadow(
                color = shadowColor,
                offset = Offset(0f, 2f),
                blurRadius = 4f
            )
        )
    )
}

// components/GlowButton.kt
@Composable
fun GlowButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit
) {
    var isPressed by remember { mutableStateOf(false) }
    
    val glowAlpha by animateFloatAsState(
        targetValue = if (isPressed) 0.6f else 0f
    )
    
    Box(
        modifier = modifier
            .pointerInput(Unit) {
                detectTapGestures(
                    onPress = {
                        isPressed = true
                        tryAwaitRelease()
                        isPressed = false
                    },
                    onTap = { onClick() }
                )
            }
            .drawBehind {
                if (glowAlpha > 0f) {
                    drawCircle(
                        color = LiquidAeroColors.accentPrimary.copy(alpha = glowAlpha),
                        radius = size.maxDimension * 0.6f,
                        style = Fill,
                        blendMode = BlendMode.Screen
                    )
                }
            }
            .background(
                color = if (isPressed) 
                    LiquidAeroColors.accentPrimary.copy(alpha = 0.2f)
                else 
                    LiquidAeroColors.glassMid,
                shape = RoundedCornerShape(12.dp)
            )
            .padding(horizontal = 24.dp, vertical = 12.dp)
    ) {
        content()
    }
}
```

### Android SystemUI Integration

```xml
<!-- frameworks/base/packages/SystemUI/res/values/colors_liquidaero.xml -->
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="qs_background_dark">#05030A</color>
    <color name="qs_tile_background">#801A1028</color>
    <color name="notification_background">#801A1028</color>
    <color name="accent_primary">#7C3AED</color>
    <color name="text_primary_dark">#F0EAFF</color>
    <color name="text_secondary_dark">#C0B9E5</color>
</resources>

<!-- frameworks/base/packages/SystemUI/res/values/styles_liquidaero.xml -->
<style name="Theme.SystemUI.LiquidAero" parent="Theme.SystemUI">
    <item name="android:colorBackground">@color/qs_background_dark</item>
    <item name="android:textColorPrimary">@color/text_primary_dark</item>
    <item name="android:textColorSecondary">@color/text_secondary_dark</item>
    <item name="colorAccent">@color/accent_primary</item>
</style>
```

---

## Performance Budget (ONN Tablet)

### GPU Constraints

| Resource | Budget | Notes |
|----------|--------|-------|
| Blur surfaces (simultaneous) | ≤3 | More causes frame drops |
| Blur radius | ≤20px | Higher = exponential cost |
| Transparency layers (stacked) | ≤2 | Avoid nesting glass |
| Glow effects (active) | ≤2 | Expensive blend modes |

### Where to Apply Blur

**YES (blur these):**
- Notification shade background (1 surface)
- Quick Settings panel background (1 surface)
- App drawer background (1 surface)
- Lock screen controls (when visible)

**NO (skip blur):**
- Individual QS tiles
- Individual notification cards
- Every button and chip
- Nested dialogs

### Performance Mode Toggle

Implement a toggle in Developer Options:

```kotlin
// When Performance Mode enabled:
object LiquidAeroConfig {
    var performanceMode: Boolean = false
    
    val blurEnabled: Boolean
        get() = !performanceMode
    
    val glowEnabled: Boolean
        get() = !performanceMode
    
    val glassOpacity: Float
        get() = if (performanceMode) 0.9f else 0.5f
}
```

In Performance Mode:
- Disable all blur effects
- Increase glass opacity (less transparency)
- Disable glow animations
- Keep shapes and layout intact

---

## Cross-Platform Consistency

### The Waydroid Boundary

When Android runs inside Waydroid on Holonic Linux, users should not perceive a visual "break" between environments.

**Consistency Rules:**

1. **Same color palette** - Both use identical hex values
2. **Same border radii** - 16dp panels everywhere
3. **Same text colors** - #F0EAFF primary on both sides
4. **Same shadow treatment** - Holofont projection on all text
5. **Same accent color** - #7C3AED purple throughout

**Shared Wallpaper Blur:**

The blur effect should sample from the *actual* wallpaper, which is shared between Linux and Android. This creates visual continuity—the same wallpaper shows through glass panels on both sides.

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                    SHARED WALLPAPER                         │
│                  (deep purple nebula)                       │
│                                                             │
│   ┌──────────────────┐         ┌──────────────────┐        │
│   │░░ Linux App ░░░░░│         │░░ Android App ░░░│        │
│   │░░░░░░░░░░░░░░░░░░│         │░░░░░░░░░░░░░░░░░░│        │
│   │░░░░░░░░░░░░░░░░░░│         │░░░░░░░░░░░░░░░░░░│        │
│   └──────────────────┘         └──────────────────┘        │
│         ↑                              ↑                   │
│         └──── Same blur, same tint ────┘                   │
│                                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Typography

### Font Stack

**Primary:** Inter (or system sans-serif)  
**Monospace:** JetBrains Mono (or system monospace)

### Scale

| Token | Size | Weight | Use |
|-------|------|--------|-----|
| display_lg | 32sp | 600 | Hero text, splash |
| display_md | 24sp | 600 | Page titles |
| title_lg | 20sp | 500 | Section headers |
| title_md | 16sp | 500 | Card titles |
| body_lg | 16sp | 400 | Primary content |
| body_md | 14sp | 400 | Secondary content |
| label_lg | 14sp | 500 | Buttons, labels |
| label_md | 12sp | 500 | Chips, tags |
| caption | 12sp | 400 | Hints, timestamps |

### Holofont Application

Apply Holofont shadow to:
- All text on glass surfaces
- Titles and headers
- Button labels
- Status bar text
- Notification titles

Skip Holofont on:
- Body text in scrolling lists (performance)
- Input field content
- Very small captions (shadow gets muddy)

---

## Animation Guidelines

### Timing

| Type | Duration | Easing |
|------|----------|--------|
| Micro (ripple, press) | 100ms | ease-out |
| Standard (expand, slide) | 200ms | ease-in-out |
| Emphasis (dialogs, panels) | 300ms | cubic-bezier(0.4, 0, 0.2, 1) |
| Complex (page transitions) | 400ms | spring(damping=0.8) |

### Glass Animations

When glass panels appear:
1. Fade in opacity (0 → 50%)
2. Scale up slightly (0.95 → 1.0)
3. Blur intensity ramps up (0 → 16px)

Duration: 200-300ms with ease-out

### Glow Animations

Interactive glow should:
- Fade in on hover/focus (150ms)
- Intensify on press (100ms)
- Fade out on release (200ms)

---

## Iconography

### Style

- Outlined (not filled) for most UI
- 2px stroke weight
- Rounded caps and joins
- Consistent 24x24dp size

### Glow Treatment

Active/selected icons get:
- Fill: accent_primary
- Drop shadow: 0 0 8px accent_glow @ 50%

### Recommended Icon Sets

- **Lucide** (MIT license, consistent style)
- **Phosphor** (MIT license, multiple weights)
- **Material Symbols** (outlined variant)

---

## Appendix: Jules Instruction Block

Copy this directly to Jules:

```
INSTRUCTION: Implement Liquid-Aero Design System

This design system must be implemented TWICE, with visual consistency:

1. LINUX SIDE (Holonic Linux)
   - GTK4 theme: /usr/share/themes/LiquidAero/
   - Qt/QML components for any Qt apps
   - Apply to: file manager, settings, terminal, system dialogs

2. ANDROID SIDE (Waydroid)
   - SystemUI modifications in frameworks/base/packages/SystemUI/
   - Custom Launcher3 fork or new launcher
   - Theme: Theme.SystemUI.LiquidAero
   - Apply to: status bar, notification shade, quick settings, 
     volume panel, power menu, lock screen, app drawer

CORE COMPONENTS TO IMPLEMENT:
- GlassSurface: Translucent panel with blur and Aero edges
- GlassCard: Structured content container
- HolofontText: Text with projected shadow effect
- GlowButton: Interactive element with radial glow

DESIGN TOKENS:
- See color palette in specification
- Border radius: 16dp for panels, 12dp for cards, 8dp for buttons
- Blur radius: 16px standard (cap at 20px for performance)

PERFORMANCE REQUIREMENTS:
- Maximum 3 simultaneous blur surfaces
- Implement Performance Mode toggle (disables blur/glow)
- Test on Mali-G52 GPU (ONN tablet)

CROSS-PLATFORM CONSISTENCY:
- Identical colors between Linux and Android
- Same Holofont shadow treatment everywhere
- Shared wallpaper blur (both sides sample same wallpaper)
- User should not perceive a "seam" between environments

REFERENCE:
- Apple liquid glass (iOS 18 control center)
- Windows Vista/7 Aero (glass borders, bloom)
- Holofont = text that appears to hover above glass
```

---

*End of Liquid-Aero Design System Specification*
