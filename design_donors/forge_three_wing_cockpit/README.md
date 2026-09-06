# Singularity Works Forge v1.0

**Autonomous bug bounty engine.** AST-level security analysis with directed taint chains, warrant graph, three-wing HUD cockpit, and structured HackerOne/Bugcrowd report output.

```
self_audit: 2791 pass / 42 warn / 0 fail
contrast:   30/30 paths
capsules:   79  |  strategies: 75  |  warrant_coverage: 1.0
```

---

## Quick Install

**Linux / macOS / WSL:**
```bash
curl -fsSL https://raw.githubusercontent.com/SEng-Kitathas/Singularity-works-/main/install.sh | bash
```
Or clone and run:
```bash
git clone https://github.com/SEng-Kitathas/Singularity-works-.git
cd Singularity-works-
bash install.sh
```

**Windows (PowerShell):**
```powershell
git clone https://github.com/SEng-Kitathas/Singularity-works-.git
cd Singularity-works-
.\install.ps1
```

The installer: clones the repo, creates a venv, installs dependencies, writes launcher scripts, and generates Claude Code MCP config.

---

## Requirements

| Component | Minimum | Notes |
|-----------|---------|-------|
| Python | 3.11+ | AST module required |
| git | any | for install + forge-commit-verified |
| LM Studio | 0.3.x+ | optional, for AI validation layer |
| Claude Code | any | optional, for MCP integration |

**LM Studio models (optional — forge runs standalone without them):**

| Role | Model | Size | Config |
|------|-------|------|--------|
| Reasoner | mradermacher/Qwen3.5-35B-A3B-Claude-4.6-Opus-Reasoning-Distilled | 21.2 GB | Q4_K_M |
| Coder | Melvin56/Qwen2.5-Coder-7B-Instruct-abliterated | 4.7 GB | Q4_K_M |

Both models load automatically via auto-detection from `/v1/models` — no manual model ID configuration needed.

---

## Usage

### Scan a file → bug bounty report

```bash
# Basic scan — prints findings to stdout
forge path/to/app.py

# Full report → HackerOne markdown + JSON
forge path/to/app.py --platform HackerOne --out ./reports --target "My Flask App"

# Bugcrowd format
forge path/to/app.py --platform Bugcrowd --out ./reports

# With scope note
forge path/to/app.py --scope "In scope: /api/* endpoints only" --out ./reports
```

Output files: `bounty_<target>_<timestamp>.md` and `bounty_<target>_<timestamp>.json`

### Python API

```python
from singularity_works.orchestration import Orchestrator
from singularity_works.models import Requirement, RunContext
from singularity_works.facts import FactBus
from singularity_works.bounty_reporter import build_report, save_report
from pathlib import Path

# Run the forge
orc = Orchestrator(Path(".forge/evidence.jsonl"))
orc.facts = FactBus()
result = orc.run(
    RunContext("bounty", "qa", "hud", {}),
    Requirement("REQ-1", "Security audit", tags=["security"]),
    open("app.py").read(),
)

# Build and save report
report = build_report(result, orc, target_name="app.py", platform="HackerOne")
paths  = save_report(report, "./reports")
print(f"Findings: {len(report.findings)}, Max CVSS: {report.cvss_score_max}")
```

### Live HUD cockpit

```bash
forge-hud          # run the demo
python3 -m singularity_works.hud   # same thing
```

The HUD renders a three-wing terminal cockpit (inspired by avionics glass cockpit principles):
- **LEFT**: gate matrix with EICAS-style FAIL/WARN/PASS status
- **CENTER**: verdict, warrant coverage meter, primary claim text, metrics
- **RIGHT**: directed taint chains (`USER_INPUT:L3 ──▶ NETWORK:L7`) + compound derivations

Modes: `full` (≥100 cols), `compact` (<100 cols), `status` (single line)

### Local inference integration

The historical `forge-health` / `local_model_adapter` surface is **not part of this qualified release candidate**.
The committed adapter was removed earlier, while newer local inference work remains machine-specific and unqualified for public release.
Portable local-inference support will return only after its adapter/config contract passes the same clean-release gate.

---

## Claude Code Integration (MCP)

The installer writes `~/.claude/mcp_singularity_works.json`. To activate:

**Option A — Global (all projects):**

Add the contents to `~/.claude/settings.json`:
```json
{
  "mcpServers": {
    "singularity-works": {
      "command": "/path/to/.venv/bin/python3",
      "args": ["/path/to/singularity_works/forge_mcp_server.py"],
      "cwd": "/path/to/Singularity-works-"
    }
  }
}
```

**Option B — Per-project:**

Add to `.claude/settings.json` in your project root (same structure as above).

**Available MCP tools (9 total):**

| Tool | What it does |
|------|-------------|
| `forge_run_battery` | Run the current `verify_build.py` verification suite (legacy tool name retained) |
| `forge_get_assurance` | Security verdict for a code snippet |
| `forge_run_assurance_on_file` | Forge run on a file path |
| `forge_get_open_seams` | Open seams from the trace matrix |
| `forge_get_live_shadow` | Current Live Shadow state |
| `forge_get_escalation` | Escalation decision for a finding |
| `forge_get_blueprint` | Logic Blueprint Engine analysis |
| `forge_commit_verified` | Gate: require compile + self-verification; also require a battery if the verifier emits one |
| `forge_generate_bounty_report` | Full bug bounty report from code |

> Historical corpus-regression evidence remains in `tests/expectations.json` and `results/regression_summary.json`. The current `examples/verify_build.py` does **not** emit that corpus battery, so those historical counts are not treated as a live commit gate.

**Example Claude Code usage:**
```
@singularity-works forge_generate_bounty_report code="$(cat app.py)" target="My App" platform="HackerOne"
```

---

## What It Detects

30 verified vulnerability classes across Python, Rust, Go, Java, JavaScript, TypeScript, C#, Ruby:

| Category | Vulnerabilities |
|----------|----------------|
| **Injection** | SQLi (Python+Rust+Go), NoSQL injection ($where/$ne/$gt), SSTI, LDAP injection, CSV formula injection, Zip Slip, path traversal, XXE, CRLF |
| **Authentication** | JWT algorithm=none, JWT algorithm confusion, weak JWT secret, CSRF exempt, OAuth token in URL, account enumeration timing, Paramiko AutoAddPolicy |
| **Cryptography** | Hardcoded secrets (30+ patterns), DES/RC4/Blowfish, RSA < 2048 bits, cleartext protocols, urllib3 disable_warnings, pycrypto usage |
| **Execution** | eval/exec, Flask debug=True (RCE), SQLite enable_load_extension, subprocess shell=True, deserialization (pickle/yaml/marshal) |
| **Network** | SSRF, CORS wildcard + credentials, bind 0.0.0.0, GraphQL introspection, HTTP request smuggling (CL+TE) |
| **Access Control** | IDOR / missing object ownership, insecure cookies, secret serialization, file permissions 0o777 |
| **Resource** | Decompression bomb, tempfile TOCTOU, trojan source (CVE-2021-42574) |

**False positive rate: 0** (verified against 2791 self-audit gate checks)

---

## Detection Architecture

```
Source Code
    │
    ▼
Language Front Door (polyglot IR builder)
    │  Python: full AST  │  Rust/Go/Java: structural heuristic IR
    ▼
Genome-Gate Coupling (79 capsules → 75 strategies)
    │  Each capsule = pattern family + invariants + anti-patterns
    ▼
Fixed-Point Enforcement Loop (max 3 iterations)
    │  R1: injection+trust → compound_taint_injection
    │  R2: trust+network  → ssrf_confirmed
    │  R3: 3-hop chain    → critical_compound_hazard
    │  R4: memory+taint   → memory_corruption_via_taint
    ▼
Directed Taint Chain Publication (FactBus)
    │  source_line → transforms → sink_line (per finding)
    ▼
Assurance Warrant Graph
    │  Every claim warranted: WHY this gate discharge matters
    │  warrant_coverage = 1.0 (100%) on every run
    ▼
Bug Bounty Report Formatter
    │  CVSS v3.1 scores │ CWE references │ PoC steps │ Remediation
    └─► HackerOne .md │ Bugcrowd .md │ JSON export
```

---

## HUD Cockpit

The forge ships a live terminal HUD based on avionics glass cockpit principles (ALCI v7.2, YuiUI-CP v1.0 OMEGA design specs):

```
■ Singularity Works v1.37 │ VERDICT: ■ RED │ WC: 43/43 │ ✗4 ~2 ✓24 r3 │ chains:3 │ COMPOUND: R1 R3
═══════════════════════════════════════════════════════════════════════════════════════════════════════
        GATE MATRIX          │         VERDICT  ·  WARRANT          │      CHAINS  &  COMPOUND
─────────────────────────────┼──────────────────────────────────────┼─────────────────────────────────
PHASE    qa-synthesis         │   ■ RED                              │   TAINT CHAINS
REQ      Security audit       │                                      │   USER_INPUT:L14 ──▶ NOSQL:L17 ✓
RADICAL  TRUST+PARSE          │   WARRANT COVERAGE                   │   USER_INPUT:L18 ──▶ TEMPLATE:L20 ✓
PROGRESS analysis             │   [▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░]  43/43  │
[████████████████████] 100%  │                                      │   COMPOUND DERIVATION
                              │   PRIMARY CLAIM:                     │   [R1] injection + trust
─ GATES ─────────────────────┤   FALSIFIED: 4 gate families         │   [R3] 3-hop critical chain
  ✗ injection   NoSQL...      │   falsified. Runtime unobserved.     │
  ✗ injection   SSTI ren...   │                                      │   ─ META ─────────────────────
  ✗ exec_safety Flask debug   │   ─ METRICS ─────────────────────   │   branch   main
  ~ serialize   yaml.load     │   CAPSULES    79                     │   session  bounty-01
  ~ network     0.0.0.0 bind  │   STRATEGIES  75                     │   provider qwen2.5-coder-7b
  ✓ 24 gates pass             │   ELAPSED_MS  112                    │
═══════════════════════════════════════════════════════════════════════════════════════════════════════
EVENTS
 · genome bundle: 14 capsules active
 · fixed-point iter 1: 18 new facts → iter 2: converged
 · R1 compound_taint_injection: fired │ assurance rollup: warrant_coverage=1.0
```

Color key: `✗` RED = fail (security violation), `~` AMBER = warn, `✓` GREEN = pass

---

## Project Structure

```
Singularity-works-/
├── install.sh                    # One-touch Linux/macOS/WSL installer
├── install.ps1                   # One-touch Windows installer
├── pyproject.toml                # Package manifest v1.0
├── configs/
│   └── seed_genome.json          # 79 capsules (2,973 lines)
└── singularity_works/
    ├── orchestration.py          # Forge run loop + fixed-point wiring
    ├── genome_gate_factory.py    # 75 detection strategies (5,040 lines)
    ├── enforcement.py            # Fixed-point propagation + R1-R4 rules
    ├── assurance.py              # Warrant graph + 100% claim coverage
    ├── language_front_door.py    # Polyglot IR builder + taint tracker
    ├── hud.py                    # Three-wing ANSI cockpit (781 lines)
    ├── bounty_reporter.py        # Bug bounty report formatter (749 lines)
    ├── forge_mcp_server.py       # Claude Code MCP server (9 tools)
    ├── forge_hud_server.py       # WebSocket HUD backend
    ├── cil_council.py            # REASONER/CODER adversarial loop
    ├── facts.py                  # Typed FactBus (taint_chain publisher)
    ├── models.py                 # RunResult, AssuranceClaim, GateResult
    └── ...                       # 35 modules total
```

---

## Laws Active

| Law | Statement |
|-----|-----------|
| **Law 0** | Discourse ≠ implementation — iterate freely in discourse |
| **Law 1** | 0-Day Not Someday — no stubs, no TODOs in build mode |
| **Law Ω** | Every artifact at theoretical maximum — Platonic ideal |
| **Law Σ** | Voice speculative ideas, map isomorphisms, challenge assumptions |

---

## License

MIT — see LICENSE file.

Research sources used in detector implementations:
gosec (Apache-2.0), eslint-plugin-security (Apache-2.0), njsscan (MIT),
graudit (MIT), PayloadsAllTheThings (MIT), detect-secrets (MIT/Apache-2.0)

---

*"The glass box that shows what the black box hides."*
