# V30 SERVER HARDENING + SEMANTIC RUNTIME + OPERATOR COCKPIT

Date: 2026-09-08
Status: **ENGINEERING QUALIFIED / PUBLICATION PENDING**
Branch: `server-hardening-2026-09-08`
Base: remote `origin/main` at UCM engineering feature `e786a5bebc23f9d09e05d417d04579126971d3b3`
Live Runtime: **FROZEN / UNTOUCHED** at `4163606459324feaa31252b3c2a6d58d73aaff46`
Final schema: **LAST / LOCKED / UNTRIGGERED**
Skills/UCM content/refactor: **OUT OF SCOPE / PAUSED**

## Campaign intent
Close the highest-priority non-Skill/non-memory engineering seams without crossing the live-promotion or final-schema boundaries.

The campaign addressed, in order:

1. unauthenticated research HTTP routes;
2. legacy inline approval secure-default retirement pressure;
3. semantic executor environment qualification and real consequence execution;
4. operator HUD three-wing cockpit embodiment;
5. suite-order informer timing leakage exposed during full qualification.

## 1. Research HTTP authentication

### Reproduced defect
Current source exposed four research routes without the shared receiver API-key guard:

- `/research/health`
- `/research/arxiv/search`
- `/research/arxiv/paper`
- `/research/hunt`

A direct Flask test-client request to `/research/health` without `X-GitHome-Key` returned HTTP 200 before repair.

### Embodiment
`research_routes.py` now uses the same `require_valid_api_key(request.headers)` boundary as the other major receiver planes. All four routes fail closed with typed `UNAUTHORIZED` / HTTP 401 when the receiver key is absent or invalid.

### Evidence
`tests/test_auth_boundary.py` includes all four unauthenticated route regressions plus an authorized health path.

Focused auth slice: **4/4 PASS**.

## 2. Approval authority cleanup

### Prior seam
Bound Runtime-issued approval challenges were already the stronger authority mechanism, but legacy inline payload approval remained enabled by default.

### Embodiment
`PCMMAD_ALLOW_LEGACY_INLINE_APPROVAL` now defaults to **disabled**. Legacy inline authority is retained only as an explicit migration escape hatch with positive opt-in (`1/true/yes/on/enabled`).

Normal protocol routing tests were migrated to the bound challenge flow. The test that explicitly verifies legacy compatibility now explicitly enables the migration gate rather than relying on insecure ambient defaults.

### Preserved laws
- approval authority is a separate Runtime object, not a boolean payload field;
- challenge remains bound to capability contract + arguments + target + expiry;
- changed arguments require a new challenge;
- legacy compatibility is not default authority.

Approval-focused slice: **16/16 PASS** before broader integration; protocol+informer integration later **16/16 PASS**.

## 3. Semantic executor environment restoration

### Prior blocker
Runtime had:

- retriever script;
- corpus DB;
- MiniLM index;
- Jina index;
- Jina model cache;

but no qualified Python environment containing the required ML dependencies. The old MiniLM Hugging Face cache also proved to be a **zero-byte phantom snapshot**: path presence existed while configs/tokenizers/model placeholders were empty.

### Deployment runtime
Created isolated Python 3.12 environment:

`E:\new pc\AI_Pushes_Sandbox\projects\PCMMAD_RECEIVER_LAB\runtimes\semantic_monster_py312`

The Runtime discovery path now prefers this dedicated deployment candidate rather than the receiver venv or broken historical environments.

Exact package lock is stored in:

`reports/SEMANTIC_RUNTIME_REQUIREMENTS_2026-09-08.txt`

Key qualified versions:

- `torch==2.14.0+cpu`
- `torchvision==0.29.0+cpu`
- `transformers==4.52.4`
- `sentence-transformers==5.7.0`
- `faiss-cpu==1.15.0`
- `numpy==2.5.3`
- `peft==0.20.0`
- `pillow==12.3.0`

The donor Jina config reported transformers 4.52.0, but that release is yanked on PyPI. The environment was behavior-qualified on the non-yanked 4.52.4 patch instead of preserving a yanked dependency by ritual.

### MiniLM repair
The broken user cache was **not mutated**. An exact-revision deployment-local copy of:

`sentence-transformers/all-MiniLM-L6-v2`

revision:

`c9745ed1d9f207416be6d2e6f8de32d1f16199bf`

was provisioned under the lab runtime and selected by default.

### Semantic scars embodied
`lab_tools_semantic.py` now:

- probes the actual behavior-complete dependency set: `faiss`, `numpy`, `torch`, `sentence_transformers`, `transformers`, `PIL`, `peft`, `torchvision`;
- structurally qualifies MiniLM files rather than treating `directory.exists()` as a model-health proof;
- fails the outer tool call when the retriever subprocess exits nonzero;
- fails with typed `SEMANTIC_OUTPUT_INVALID` when the child returns success without valid JSON;
- prefers the qualified lab semantic runtime/model deployment when available.

### Real consequence qualification
A real `semantic.monster.search` was executed against the actual corpus/indexes after the full Runtime suite:

- health available: **true**
- blockers: **[]**
- all 8 required modules: **true**
- MiniLM model structural qualification: **true**
- child return code: **0**
- parsed result: **true**
- MiniLM hits: **20**
- Jina hits: **20**

Therefore the historical `no_qualified_python_runtime` blocker is **closed for this deployment**.

Semantic hostile regression slice: **7/7 PASS**.

## 4. Operator HUD cockpit embodiment

### Prior seam
The HUD backend/security/dispatch mechanics were mature, but the primary visual composition still behaved like a conventional tab/card dashboard despite the recovered three-wing cockpit design authority.

### Embodiment
The primary Operations surface is now:

`corona → left wing | integrated center | right wing → persistent command dock`

while Browser, Activity, and Tool Explorer remain secondary workspaces.

The cockpit derives operator truth from existing Runtime/HUD data only:

- capability/family counts from live tool catalog;
- core/optional assurance from `/api/status` readiness evidence;
- browser presence from actual sessions;
- recent activity from the durable HUD journal.

Presentation-only local state includes the material tier:

- FULL
- BALANCED
- MINIMAL

It cannot become Runtime authority.

Additional embodiment:

- keyboard command palette (`Ctrl/Cmd+K`, `/`);
- `Alt+1..4` workspace switching;
- responsive three-wing collapse;
- reduced-motion fallback;
- high-contrast fallback;
- approval challenge UI preserved exactly as Runtime-bound authority;
- raw Tool Explorer retained as expert surface rather than primary UX.

### Evidence
HUD regression family: **27/27 PASS**.

Static checks:

- Node `--check` on `operator_hud/static/app.js`: PASS
- DOM identity audit: **87 IDs / 87 unique / 0 duplicates**
- structural cockpit regression: PASS

## 5. Informer suite-order isolation

### Observed failure
The first full Runtime qualification after the above changes produced one intermittent failure in:

`test_idle_scheduler_does_not_poll_at_250ms_and_completion_wakes_it`

The test passed repeatedly in isolation, including **20 isolated-process repetitions / 0 failures**, but failed under full-suite ordering.

### Root cause
Earlier execution tests legitimately start the process-global scheduler thread. The informer integration test then patched `_scheduler_tick` and launched a second manual scheduler loop without quiescing the process-global loop. Under full-suite order, both loops incremented the test's tick capture.

This duplicate-loop topology is a **test isolation artifact**, not a production scheduler topology.

### Embodiment
The integration test now explicitly calls `_shutdown_scheduler()` and clears scheduler stop/wake state before owning its manual loop.

Informer + protocol integration after repair: **16/16 PASS**.

## Final qualification

Combined hardening campaign before final suite: **54/54 PASS**.

Final Runtime suite on exact code bytes:

**434 collected / 433 passed / 0 failed / 1 conditional skip**.

Real semantic dual-lane retrieval was then repeated successfully after the full suite.

## Claim ceiling

This campaign does **not** claim:

- live Runtime promotion;
- live/repo parity at the new engineering feature;
- final imported-action schema redesign;
- Skill ecosystem convergence;
- UCM representation/refactor completion;
- ingestion of real user continuity;
- GPU qualification for semantic retrieval (current environment is CPU-qualified);
- multi-host semantic execution;
- that the HUD has been live-promoted to the frozen desktop Runtime.

## Publication lineage constraint

A paused, local-only UCM recovery commit exists on local `main` and is intentionally excluded from this hardening branch. This campaign branches from remote `origin/main` at `e786a5b...` so server hardening can publish without silently absorbing paused memory work.

Before updating remote `main`, preserve the paused UCM recovery commit on an explicit holding ref/branch, verify remote `main` has not advanced unexpectedly, then fast-forward remote `main` from the hardening branch only if ancestry is still exact.
