# LIQUID-AERO UI SYSTEM v2.0
## Windows 11 × Android Hybrid — Right-Handed QoL Dream

**Design Philosophy:** If Windows 11 and Android had a baby, raised by someone who actually uses their device right-handed and gives a shit about quality of life.

**Governing Principle:** Every interaction should feel *inevitable* — the control you need should be where your thumb already is.

**Technical Foundation:** See `LIQUID_AERO_DESIGN_SYSTEM.md` for glass shader specs, Holofont details, and color system definitions. This document focuses on UX patterns and layout.

---

## 1. CORE LAYOUT PHILOSOPHY

### 1.1 The Right-Handed Reality

Most UI designers are left-brain idiots who put everything on the left. We're fixing that.

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                      CONTENT AREA                           │
│                                                             │
│                   (Your actual work)                        │
│                                                             │
│                                                     ┌─────┐ │
│                                                     │ FAB │ │
│                                                     └─────┘ │
├─────────────────────────────────────────────────────────────┤
│ ◀ Back │        App Title        │ ⋮ │ Search │ ▼ Quick │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ○ ○ ○ ○ ○ ○ ○        [  HOME  ]        [ RECENT ] [ APPS ]│
│  Pinned Apps              ↑                   ↑        ↑   │
│                     Gesture Zone         Right Side    Far │
│                                          Thumb Zone   Right│
└─────────────────────────────────────────────────────────────┘

RIGHT-HANDED THUMB REACH ZONES:
┌─────────────────────────────────────┐
│ Hard    │  Stretch  │   Easy       │
│         │           │              │
│         │           │   ████████   │
│         │  ░░░░░░░  │   ████████   │
│         │  ░░░░░░░  │   ████████   │
│ ░░░░░░  │  ████████ │   ████████   │
│ ░░░░░░  │  ████████ │   ████████   │
│ ████████│  ████████ │   ████████   │
└─────────────────────────────────────┘
Primary actions go in the EASY zone (bottom-right quadrant)
```

### 1.2 The Hybrid DNA

| Feature | Windows 11 Parent | Android Parent | Our Child |
|---------|------------------|----------------|-----------|
| **Taskbar** | Centered, minimal | Hidden nav bar | Bottom bar, right-biased |
| **Start/Home** | Start menu | App drawer | Unified launcher |
| **Multitasking** | Snap layouts | Recent apps | Snap + gesture hybrid |
| **Notifications** | Action Center | Shade pull-down | Right-edge slide |
| **Quick Settings** | Action Center | Pull-down tiles | Persistent right panel |
| **Search** | Start menu + taskbar | Google bar | Semantic CIL search |
| **Widgets** | Widget board | Home screen | Glanceable right panel |

---

## 2. NAVIGATION SYSTEM

### 2.1 Bottom Bar (The Taskbar-NavBar Baby)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  [App1] [App2] [App3] [App4]      │█████████│      [Search] [Recent] [Apps]│
│     Pinned Apps                    Home Pill       Right-Hand Controls     │
│     (Left side, but)               (Center)        (Where your thumb is)   │
│     (still reachable)                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Behaviors:**
- **Tap Home Pill:** Go home
- **Swipe Up on Pill:** App drawer / Start
- **Swipe Up + Hold:** Recent apps (Windows 11 style cards)
- **Swipe from Right Edge:** Quick Settings panel
- **Swipe from Left Edge:** Back (or previous app)
- **Long Press Pinned App:** Jump list (Windows 11 style)

### 2.2 Gesture Navigation

```
GESTURE MAP (Right-Hand Optimized):

From Right Edge:
├── Short swipe: Quick Settings panel
├── Long swipe: Full Action Center
└── Swipe + hold: Clipboard manager

From Bottom:
├── Swipe up: Home
├── Swipe up + hold: Recent apps
└── Swipe up + right: Previous app (one-handed back)

From Left Edge:
├── Short swipe: Back
├── Long swipe: Previous app
└── (Less used - harder to reach)

From Top Right:
├── Swipe down: Notifications for current app
└── Swipe down + hold: All notifications

Pill Gestures:
├── Tap: Home
├── Swipe left/right: Switch recent apps
└── Long press: Assistant / CIL Search
```

### 2.3 The Home Pill

Borrowed from Android but made better:

```
Normal State:
    ────────────────────
         │███████│
    ────────────────────

Contextual States:
    Playing Media:        Downloading:          Timer Running:
    │▶ advancement bar│   │████░░░░ 67%│        │⏱ 3:42│
```

---

## 3. WINDOW MANAGEMENT

### 3.1 Snap Layouts (Windows 11 Style, Touch Optimized)

When you drag a window to screen edge or long-press the maximize button:

```
SNAP LAYOUT OPTIONS (8" Tablet):

┌─────────┬─────────┐  ┌─────────────────────┐  ┌───────┬───────────────┐
│         │         │  │                     │  │       │               │
│   50%   │   50%   │  │        100%         │  │  33%  │      67%      │
│         │         │  │                     │  │       │               │
└─────────┴─────────┘  └─────────────────────┘  └───────┴───────────────┘

┌─────────────────────┐  ┌─────────┬─────────┐
│                     │  │         │         │
│        67%          │  ├─────────┤   50%   │
├─────────────────────┤  │         │         │
│        33%          │  │   50%   ├─────────┤
└─────────────────────┘  │         │         │
                         └─────────┴─────────┘
```

**Snap Triggers:**
- Drag window to edge
- Long-press maximize button → layout picker
- Three-finger pinch → overview with snap zones
- Keyboard: `Super + Arrow keys`

### 3.2 Recent Apps (Android Cards + Windows Timeline)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         RECENT APPS                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  ┌───────┐  │  │  ┌───────┐  │  │  ┌───────┐  │  │  ┌───────┐  │    │
│  │  │       │  │  │  │       │  │  │  │       │  │  │  │       │  │    │
│  │  │ App 1 │  │  │  │ App 2 │  │  │  │ App 3 │  │  │  │ App 4 │  │    │
│  │  │       │  │  │  │       │  │  │  │       │  │  │  │       │  │    │
│  │  └───────┘  │  │  └───────┘  │  │  └───────┘  │  │  └───────┘  │    │
│  │   Chrome    │  │   Files     │  │   Notes     │  │  Terminal   │    │
│  │  10min ago  │  │  25min ago  │  │   1hr ago   │  │  Yesterday  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
│                                                                         │
│  ────────────── Yesterday ──────────────                               │
│  ┌─────────────┐  ┌─────────────┐                                      │
│  │  Session 1  │  │  Session 2  │   ← Windows Timeline style           │
│  └─────────────┘  └─────────────┘     grouped by time                  │
│                                                                         │
│                    [Clear All]                    [Screenshot] [Split] │
│                                                   (Right side actions) │
└─────────────────────────────────────────────────────────────────────────┘
```

**Recent Apps Features:**
- Swipe card up: Close app
- Swipe card right: Pin to split screen
- Tap card: Switch to app
- Long-press card: App info, force stop, split options
- Screenshots embedded in cards (like Android 12+)

### 3.3 Picture-in-Picture (Android Style)

```
┌────────────────────────────────────────────────────────────┐
│                                                            │
│                     MAIN APP                               │
│                                                    ┌──────┐│
│                                                    │ PiP  ││
│                                                    │Video ││
│                                                    └──────┘│
│                                                            │
└────────────────────────────────────────────────────────────┘

PiP Behaviors:
- Drag to any corner
- Double-tap: Expand to full
- Swipe off edge: Dismiss
- Auto-docks to bottom-right (right-handed default)
```

---

## 4. ACTION CENTER & QUICK SETTINGS

### 4.1 The Right Edge Panel

Swipe from right edge reveals the Action Center. This is Windows 11 + Android unified:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                    │████████████│
│                                                    │            │
│                                                    │  QUICK     │
│                   MAIN CONTENT                     │  SETTINGS  │
│                                                    │            │
│                   (Dimmed)                         │ ┌────┬────┐│
│                                                    │ │WiFi│ BT ││
│                                                    │ ├────┼────┤│
│                                                    │ │DND │ 🔦 ││
│                                                    │ ├────┼────┤│
│                                                    │ │Auto│Dark││
│                                                    │ └────┴────┘│
│                                                    │            │
│                                                    │ 🔆━━━━━━━━ │
│                                                    │ Brightness │
│                                                    │            │
│                                                    │ 🔊━━━━━━━━ │
│                                                    │  Volume    │
│                                                    │            │
│                                                    │ ▶ Now      │
│                                                    │   Playing  │
│                                                    │            │
│                                                    │ [Edit] [⚙]│
│                                                    │████████████│
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Quick Toggles Grid

```
QUICK TOGGLES (Customizable, 2x4 default):

┌────────────┬────────────┬────────────┬────────────┐
│    WiFi    │ Bluetooth  │  Airplane  │  Hotspot   │
│     ✓      │     ✓      │            │            │
├────────────┼────────────┼────────────┼────────────┤
│    DND     │ Flashlight │   Auto-    │    Dark    │
│            │            │  Rotate    │    Mode    │
├────────────┼────────────┼────────────┼────────────┤
│  Location  │   NFC      │  Battery   │  Cast      │
│            │            │   Saver    │            │
├────────────┼────────────┼────────────┼────────────┤
│  Screen    │  Night     │ [Custom]   │ [Custom]   │
│  Record    │  Light     │            │            │
└────────────┴────────────┴────────────┴────────────┘

Toggle Behaviors:
- Tap: Toggle on/off
- Long press: Open settings for that feature
- Drag: Reorder (in edit mode)
```

### 4.3 Notifications (Android Style in Right Panel)

```
NOTIFICATIONS (Below Quick Settings):

┌─────────────────────────────────────────┐
│  NOW                                    │
│  ┌───────────────────────────────────┐  │
│  │ 📧 Email - John Doe               │  │
│  │    Meeting tomorrow at 3pm        │  │
│  │    [Reply] [Archive]      2m ago  │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │ 💬 Messages - Mom                 │  │
│  │    Call me when you can           │  │
│  │    [Reply] [Mark Read]    15m ago │  │
│  └───────────────────────────────────┘  │
│                                         │
│  EARLIER                                │
│  ┌───────────────────────────────────┐  │
│  │ 📱 System Update                  │  │
│  │    Ready to install               │  │
│  └───────────────────────────────────┘  │
│                                         │
│              [Clear All]                │
└─────────────────────────────────────────┘

Notification Actions:
- Swipe right: Dismiss
- Swipe left: Snooze options
- Expand: See full content + actions
- Long press: Notification settings
```

---

## 5. APP LAUNCHER / START MENU

### 5.1 The Unified Launcher

Swipe up from Home Pill or tap Start. This is Windows 11 Start + Android App Drawer:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 🔍  Search apps, files, settings, web...                   ⌨️  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  PINNED                                                    [All Apps >]│
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐      │
│  │      │ │      │ │      │ │      │ │      │ │      │ │      │      │
│  │ 📁   │ │ 🌐   │ │ ⚙️   │ │ 📝   │ │ 🎵   │ │ 📷   │ │ 📧   │      │
│  │      │ │      │ │      │ │      │ │      │ │      │ │      │      │
│  │Files │ │Chrome│ │Settin│ │Notes │ │Music │ │Camera│ │Email │      │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘      │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐      │
│  │      │ │      │ │      │ │      │ │      │ │      │ │  +   │      │
│  │ 💻   │ │ 📅   │ │ 📊   │ │ 🎮   │ │ 📖   │ │ 🔧   │ │ Add  │      │
│  │      │ │      │ │      │ │      │ │      │ │      │ │      │      │
│  │ Term │ │ Cal  │ │Sheets│ │Games │ │Reader│ │Tools │ │      │      │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘      │
│                                                                         │
│  RECOMMENDED                                          [More >]         │
│  ┌──────────────────────┐ ┌──────────────────────┐                     │
│  │ 📄 Project_v2.docx   │ │ 📁 Downloads         │                     │
│  │    Modified 2hr ago  │ │    3 new files       │                     │
│  └──────────────────────┘ └──────────────────────┘                     │
│  ┌──────────────────────┐ ┌──────────────────────┐                     │
│  │ 🖼️ Screenshot_123    │ │ 🌐 github.com/...    │                     │
│  │    Just now          │ │    Visited today     │                     │
│  └──────────────────────┘ └──────────────────────┘                     │
│                                                                         │
│  ─────────────────────────────────────────────────────────────────     │
│  [👤 Shane]                              [⏻ Power]  [⚙️ Settings]     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 All Apps View (Android Drawer Style)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ← Back                    All Apps                      🔍 Search     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  A ─────────────────────────────────────────────────────────────────   │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                                   │
│  │ App  │ │ App  │ │ App  │ │ App  │     Alphabetical                  │
│  │Store │ │ 2    │ │ 3    │ │ 4    │     with section                  │
│  └──────┘ └──────┘ └──────┘ └──────┘     headers                       │
│                                                                         │
│  B ─────────────────────────────────────────────────────────────────   │
│  ┌──────┐ ┌──────┐                                                     │
│  │Brows │ │ App  │                                                     │
│  │ er   │ │      │            ┌─────┐                                  │
│  └──────┘ └──────┘            │  A  │  ← Fast scroll                   │
│                               │  B  │     (right edge)                 │
│  C ─────────────────────────  │  C  │                                  │
│  ┌──────┐ ┌──────┐ ┌──────┐   │  ⋮  │                                  │
│  │Calc  │ │Calen │ │Camera│   │  Z  │                                  │
│  │      │ │ dar  │ │      │   └─────┘                                  │
│  └──────┘ └──────┘ └──────┘                                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

Long-press app for context menu:
┌────────────────────┐
│ 📌 Pin to Start    │
│ 📌 Pin to Taskbar  │
│ ℹ️  App Info       │
│ 🗑️  Uninstall      │
│ ══════════════════ │
│ [App shortcuts...] │
└────────────────────┘
```

---

## 6. SEMANTIC SEARCH (CIL-Powered)

### 6.1 Universal Search

This is where CIL makes us better than everyone. Search isn't just text matching—it's semantic.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 🔍  that document about the tablet project             [Voice]  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  TOP RESULTS                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 📄 HARDWARE_FEASIBILITY.md                           98% match  │   │
│  │    "onn.8 Tablet 2024...research synthesis...GO confirmed"      │   │
│  │    Modified: Today                          ~/holonic-linux/    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 📄 MISSION_BRIEF.md                                  94% match  │   │
│  │    "Project Holonic Linux...tablet...CIL filesystem"            │   │
│  │    Modified: Today                          ~/holonic-linux/    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ALSO FOUND IN                                                         │
│  ├─ 📁 Files (3 results)                                               │
│  ├─ 📧 Email (1 conversation)                                          │
│  ├─ 🌐 Web History (2 pages)                                           │
│  └─ ⚙️ Settings (1 option)                                             │
│                                                                         │
│  ─────────────────────────────────────────────────────────────────     │
│  💡 Try: "show me files I edited yesterday about linux"                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Natural Language Queries

CIL enables queries like:
- "that spreadsheet from last month with the budget numbers"
- "photos from when I was in Charlotte"  
- "code I wrote that handles authentication"
- "documents I shared with John"
- "stuff I was working on before the meeting"

This is the killer feature no other OS has.

---

## 7. FILE MANAGER (Windows Explorer + Android Files)

### 7.1 Dual-Pane with Semantic Navigation

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ← ○ ↑  │ /home/shane/Documents                    🔍│ ≡ │ ⊞ │ ⋮ │   │
├─────────┼───────────────────────────────────────────────────────────────┤
│         │                                                               │
│ ⭐ Quick│  Name              Size      Modified       Type             │
│  Access │  ────────────────────────────────────────────────────        │
│ ────────│  📁 Projects       —         Today          Folder           │
│ 🏠 Home │  📁 Work           —         Yesterday      Folder           │
│ 📁 Docs │  📄 notes.md       2.3 KB    2 hours ago    Markdown         │
│ 📥 Down │  📄 report.pdf     1.2 MB    Last week      PDF              │
│ 🖼️ Pics │  📊 data.xlsx      456 KB    Last month     Spreadsheet      │
│ 🎵 Music│                                                               │
│ 🎬 Video│  ─── Semantic Groups (CIL-powered) ──────────────────────    │
│         │                                                               │
│ ────────│  📚 "Holonic Project"                        [12 files]      │
│ 💾 Drives│     Related files across folders                            │
│ ├─ 32GB │                                                               │
│ └─ SD   │  🔧 "Configuration Files"                    [8 files]       │
│         │     .config, .toml, .yaml files                              │
│ ────────│                                                               │
│ 🏷️ Tags │                                                               │
│ • work  │                                                               │
│ • proj  │                                                               │
│ • code  │                                                               │
│         │                                                               │
├─────────┴───────────────────────────────────────────────────────────────┤
│  12 items │ 2 selected │ 3.4 MB                   [Properties] [Share] │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Context Menu (Right-Click / Long-Press)

```
┌─────────────────────────┐
│ 📂 Open                 │
│ 📂 Open with...         │
│ ─────────────────────── │
│ ✂️ Cut           Ctrl+X │
│ 📋 Copy          Ctrl+C │
│ 📋 Paste         Ctrl+V │
│ ─────────────────────── │
│ 🔗 Share               →│───┐
│ 📤 Send to             →│   │ Nearby Share
│ ─────────────────────── │   │ Email
│ 🗑️ Delete              │   │ Bluetooth
│ 📝 Rename              │   │ Copy to clipboard
│ ─────────────────────── │   └─────────────────
│ 🏷️ Add Tag             →│
│ ⭐ Add to Quick Access  │
│ 🔍 Find similar (CIL)   │  ← Semantic search for related files
│ ─────────────────────── │
│ ℹ️ Properties          │
└─────────────────────────┘
```

---

## 8. SETTINGS APP (Windows 11 Style)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ⚙️ Settings                                               🔍 Search   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 👤 Shane England                                                │   │
│  │    shane@example.com                                            │   │
│  │    [Manage Account]                                             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌──────────────┬──────────────────────────────────────────────────┐   │
│  │              │                                                   │   │
│  │ 📡 Network   │  WiFi                                            │   │
│  │              │  ────────────────────────────────────────────    │   │
│  │ 🔗 Connected │  Connected to: HomeNetwork                       │   │
│  │    Devices   │                                                   │   │
│  │              │  ┌────────────────────────────────────────────┐  │   │
│  │ 🎨 Personal- │  │ 📶 HomeNetwork          Connected    [i]  │  │   │
│  │    ization   │  │ 📶 Neighbor_5G          Secured       ─    │  │   │
│  │              │  │ 📶 CoffeeShop           Open          ─    │  │   │
│  │ 📱 Apps      │  │ 📶 Guest                Secured       ─    │  │   │
│  │              │  └────────────────────────────────────────────┘  │   │
│  │ 🔋 Battery   │                                                   │   │
│  │              │  [+ Add Network]         [WiFi Preferences]      │   │
│  │ 🔒 Privacy   │                                                   │   │
│  │              │  ────────────────────────────────────────────    │   │
│  │ ♿ Access-   │  Bluetooth                              [On ●]   │   │
│  │    ibility   │  Mobile Hotspot                        [Off ○]  │   │
│  │              │  Airplane Mode                         [Off ○]  │   │
│  │ 🔧 System    │                                                   │   │
│  │              │                                                   │   │
│  │ ℹ️ About     │                                                   │   │
│  │              │                                                   │   │
│  └──────────────┴──────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 9. QUALITY OF LIFE FEATURES

### 9.1 Clipboard Manager (Windows 11 Style)

`Win + V` or long-press paste:

```
┌─────────────────────────────────────────┐
│  📋 Clipboard History                   │
├─────────────────────────────────────────┤
│  ┌───────────────────────────────────┐  │
│  │ "The quick brown fox..."         │  │
│  │ Text · Just now            [📌]  │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │ [Image Preview]                   │  │
│  │ Screenshot · 5 min ago     [📌]  │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │ https://github.com/...           │  │
│  │ Link · 1 hour ago          [📌]  │  │
│  └───────────────────────────────────┘  │
│                                         │
│  📌 Pinned                              │
│  ┌───────────────────────────────────┐  │
│  │ shane@email.com                   │  │
│  │ Pinned · Email              [✕]  │  │
│  └───────────────────────────────────┘  │
│                                         │
│  [Clear All]              [Settings ⚙️] │
└─────────────────────────────────────────┘
```

### 9.2 Screenshot Tools (Snipping Tool + Android)

`Power + Vol Down` or `Win + Shift + S`:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│         ┌─────────────────────────────────────────────────┐            │
│         │                                                 │            │
│         │         SELECTION AREA                          │            │
│         │         (Drag to adjust)                        │            │
│         │                                                 │            │
│         └─────────────────────────────────────────────────┘            │
│                                                                         │
│  ─────────────────────────────────────────────────────────────────     │
│  [□ Rectangle] [○ Freeform] [▭ Window] [⊡ Full Screen] [✕ Cancel]     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

After capture:
┌─────────────────────────────────────┐
│ Screenshot saved                    │
│ [Edit] [Share] [Delete]   [Copy ✓] │
└─────────────────────────────────────┘
```

### 9.3 Quick Note (Edge Panel or Widget)

```
┌──────────────────────────┐
│ 📝 Quick Note            │
├──────────────────────────┤
│                          │
│ Buy milk                 │
│ Call dentist             │
│ Meeting @ 3pm            │
│ █                        │
│                          │
├──────────────────────────┤
│ [Save to Notes] [Share]  │
└──────────────────────────┘
```

### 9.4 Focus Modes (Android + iOS hybrid)

```
Focus Modes:
┌────────────────────────────────────────────┐
│  🎯 Focus                                  │
├────────────────────────────────────────────┤
│                                            │
│  ┌────────────────────────────────────┐   │
│  │ 💼 Work                      [On]  │   │
│  │    Silence except: Slack, Email    │   │
│  │    Schedule: M-F 9am-5pm           │   │
│  └────────────────────────────────────┘   │
│                                            │
│  ┌────────────────────────────────────┐   │
│  │ 🌙 Sleep                     [Off] │   │
│  │    Silence all                     │   │
│  │    Schedule: Daily 11pm-7am        │   │
│  └────────────────────────────────────┘   │
│                                            │
│  ┌────────────────────────────────────┐   │
│  │ 🎮 Gaming                    [Off] │   │
│  │    Silence except: Discord         │   │
│  │    Trigger: When game running      │   │
│  └────────────────────────────────────┘   │
│                                            │
│  [+ Create New Focus]                      │
└────────────────────────────────────────────┘
```

### 9.5 Split Screen Quick Launch

From any app, swipe up + hold, then:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│           Which app to open in split screen?                           │
│                                                                         │
│  SUGGESTED (based on current app)                                      │
│  ┌──────┐ ┌──────┐ ┌──────┐                                           │
│  │Notes │ │ Web  │ │ Term │  ← CIL knows you often use these together │
│  └──────┘ └──────┘ └──────┘                                           │
│                                                                         │
│  RECENT                                                                │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                        │
│  │      │ │      │ │      │ │      │ │      │                        │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘                        │
│                                                                         │
│                                              [All Apps]                │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 10. VISUAL DESIGN SYSTEM

### 10.1 Liquid-Aero Core (Unchanged)

All the glass, blur, and depth from the original spec remains:

```css
/* Holofont remains primary */
@font-face {
  font-family: 'Holofont';
  /* Custom variable font */
}

/* Glass layers */
--glass-primary: rgba(255, 255, 255, 0.7);     /* Light mode */
--glass-primary-dark: rgba(30, 30, 30, 0.8);   /* Dark mode */
--blur-radius: 20px;

/* Accent derived from wallpaper (Material You style) */
--accent-primary: /* extracted from wallpaper */;
--accent-secondary: /* complementary */;
```

### 10.2 Motion Design

```
ANIMATION PRINCIPLES:

App Launch:      Scale up (0.95 → 1.0) + fade in, 200ms ease-out
App Close:       Scale down (1.0 → 0.95) + fade out, 150ms ease-in
Panel Slide:     Slide from edge, 250ms spring(1, 80, 10)
Window Snap:     Position tween, 200ms ease-out
Button Press:    Scale (1.0 → 0.97 → 1.0), 100ms
Toggle:          Background slide, 200ms ease-in-out
List Item:       Staggered fade-in, 50ms delay per item

All animations respect system "reduce motion" preference.
```

### 10.3 Dark Mode (True OLED Black Option)

```
DARK MODE LEVELS:

Standard Dark:
  --background: #1a1a1a
  --surface: #2d2d2d
  --glass: rgba(45, 45, 45, 0.8)

OLED Black (battery saver):
  --background: #000000
  --surface: #121212
  --glass: rgba(18, 18, 18, 0.9)
```

### 10.4 Color Extraction (Material You)

```
WALLPAPER → COLOR PALETTE:

1. Analyze wallpaper for dominant colors
2. Generate primary, secondary, tertiary accents
3. Apply to:
   - Quick Settings toggles (active state)
   - Selection highlights
   - Progress indicators
   - FAB (Floating Action Button)
   - Notification accents
4. Ensure WCAG AA contrast compliance
5. Provide manual override in settings
```

---

## 11. ACCESSIBILITY (Baked In, Not Bolted On)

### 11.1 Right-Handed One-Hand Mode

```
ONE-HAND MODE (Activated by swipe down on home pill):

┌─────────────────────────────────────────┐
│░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
│░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
│░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
│                    ┌───────────────────┐│
│                    │                   ││
│                    │   SHRUNKEN UI     ││
│                    │   (Right-biased)  ││
│                    │                   ││
│                    │                   ││
│                    │         [●]       ││
│                    └───────────────────┘│
└─────────────────────────────────────────┘

Swipe on dead zone to exit.
```

### 11.2 Font Scaling

```
TEXT SIZE OPTIONS:
├── Tiny      (0.85x)
├── Small     (0.92x)
├── Default   (1.0x)
├── Large     (1.15x)
├── Larger    (1.30x)
└── Largest   (1.50x)

All UI scales, not just text.
```

---

## 12. CODEX PRIME COMPLIANCE

### 12.1 Human-Centric Verification

Per Codex Prime Article 3:

| Requirement | Implementation |
|-------------|----------------|
| **Human agency** | All actions reversible, no destructive defaults |
| **Transparency** | CIL audit log accessible via settings |
| **Graceful degradation** | Works offline, works without account |
| **Privacy by design** | Local-first processing, sync is opt-in |

### 12.2 Holonic Architecture in UI

The UI reflects the holonic principle—each component is both whole and part:

```
HOLONIC UI STRUCTURE:

System (whole)
├── Shell (part of system, whole containing...)
│   ├── Panels (parts of shell, wholes containing...)
│   │   ├── Widgets (autonomous wholes)
│   │   └── Notifications (autonomous wholes)
│   ├── Launcher (part of shell, whole containing...)
│   │   ├── Apps (autonomous wholes)
│   │   └── Search (autonomous whole)
│   └── Window Manager (part of shell, whole containing...)
│       └── Windows (autonomous wholes, containing...)
│           └── App content (fractal continues)
```

Each level can function independently. Shell can run without panels. Launcher can run without shell. The architecture is resilient.

---

## 13. IMPLEMENTATION PRIORITY

### Phase 4: Liquid-Aero UI (6-8 weeks)

**Week 1-2:**
- Bottom bar with gesture navigation
- Basic window management (no snap layouts yet)
- App launcher (grid only)

**Week 3-4:**
- Quick Settings panel (right edge)
- Notification system
- Snap layouts

**Week 5-6:**
- Settings app
- File manager with CIL integration
- Clipboard manager

**Week 7-8:**
- Polish, animations, transitions
- Accessibility features
- Theme engine (Material You extraction)

---

## 14. TECH STACK

| Component | Technology |
|-----------|------------|
| **Compositor** | wlroots (Wayland) |
| **Shell** | Custom (GTK4 + Rust bindings) |
| **Launcher** | GTK4 + libadwaita base, custom styling |
| **Animations** | GTK4 + CSS transitions + custom interpolators |
| **Blur** | GPU shader via wlroots |
| **Theming** | CSS variables + runtime color extraction |
| **Search** | CIL semantic index (local) |
| **Gestures** | libinput + custom gesture recognizer |

---

*This is the Windows 11 × Android baby, raised right-handed, spoiled with QoL, and blessed by the Holonic Bible. Build this.*
