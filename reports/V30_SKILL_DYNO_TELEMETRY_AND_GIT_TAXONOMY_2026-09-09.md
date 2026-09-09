# V30 Skill Dyno Telemetry + Git Error-Taxonomy Qualification — 2026-09-09

Status: **SYNTHETIC SKILL CAMPAIGN QUALIFIED / ONE RUNTIME DEFECT EARNED AND SOURCE-QUALIFIED / LIVE UNTOUCHED**

## Purpose

Before allowing ordinary production work to discover server/Skill integration failures, an isolated clone of the current Runtime was pressure-tested with four synthetic cases per Operating Library v1.0 Skill: ideal activation, degraded/partial substrate, legitimate non-activation, and authority/adversarial boundary.

The campaign deliberately separated three control planes:
- source project: `PCMMAD_RECEIVER_LAB`
- isolated dyno clone: `PCMMAD_SKILL_DYNO_V1`
- observer/load generator: `PCMMAD_SKILL_DYNO_OBSERVER`

The desktop live Runtime was not restarted, redeployed, or promoted.

## Dyno source identity

Clone source recovery HEAD:
`103c3a82379407c3b1b108f96dc6f746511171e3`

Published engineering feature below that recovery frontier before this campaign:
`fb89bb1c6fef1ba97c58d3e93ae2b03db86b37ce`

Dyno bind:
`127.0.0.1:5510`

Dyno project/state/system/sandbox/temp roots were isolated from source and live state. Browser sidecar was intentionally absent to preserve a real optional-plane degradation condition.

## Telemetry dependencies

Pre-campaign inventory showed `psutil` present but request-level Prometheus instrumentation, stack sampling, and a production-grade Windows WSGI server absent.

Installed into host Python 3.12 for the isolated dyno campaign:
- `psutil==7.2.2` — already present; process/host memory, CPU, handles, connections, files, child processes, context switches, I/O
- `prometheus-client==0.26.0` — metrics registry/export
- `prometheus-flask-exporter==0.23.2` — endpoint/method/status request counts and latency histograms
- `py-spy==0.4.2` — external stack sampling/flamegraphs
- `waitress==3.0.2` — production-grade Windows WSGI thread pool and request queue
- Flask imported as `3.1.3`

`pip check`: **No broken requirements found.**

OpenTelemetry was deliberately not installed because this campaign is a single-process dyno with no distributed trace boundary. It would largely duplicate request timing without closing a current measurement gap. Add it only if a future cross-process/provider trace discriminator requires it.

Important boundary: these dependencies were installed in the host Python 3.12 environment used by the dyno tooling. No live Runtime process was restarted, so the live loaded environment did not change during this campaign. The telemetry launcher/instrumentation remained clone-only and is not part of this Runtime source candidate.

## Synthetic fixture

`SKILL_SYNTH_LAB` was initialized through Runtime protocol/approval authority and contains intentionally mixed evidence:
- current + stale continuity
- dirty nested Git repository
- known code regression
- failing CI log/script
- safe ZIP
- traversal ZIP with `../escape.txt`
- duplicate + unique binary blobs
- small dataset
- dependency contract drift
- model qualification table
- multi-source attention queue
- workflow with exceptions
- technical-document source evidence

After fixture seeding, every campaign case required the durable synthetic-project fingerprint to remain unchanged. Unexpected durable mutation was a hard test failure.

## 108-case Skill matrix

Operating Library top-level Skills: 27
Cases per Skill: 4
Total: **108**

Case classes:
1. ideal activation
2. degraded/partial substrate
3. legitimate non-activation
4. authority/adversarial boundary

Runtime mechanisms exercised include project recovery/files, Git, archive inspection/extraction, research, synchronous execution, capability availability, approval challenges, authentication, CI reproduction, model evidence, and currentness/failure semantics.

### First scar

Initial campaign: **107/108 PASS**.

The single failure was the Technical Document degraded case. The evaluator assumed an unsupported claim should produce zero search hits. Runtime search returned a fuzzy/navigational hit containing the source's claim-ceiling sentence, not evidence supporting the invented claim.

Earned evaluator law:

`SEARCH_HIT != CLAIM_SUPPORT`

The evaluator was corrected to assess direct support quality rather than raw hit count. The original 107/108 result was retained rather than overwritten.

### Corrected qualification

Subsequent complete campaigns: **108/108 PASS**, 4/4 for every Skill.

The final dependency-backed production-like campaign and no-restart warmed replay both remained **108/108 PASS** with the durable fixture unchanged.

## Concurrent pressure

Final burst:
- 96 requests
- 16 observer workers
- Waitress 12 worker threads
- success: **96/96**
- errors: 0
- Waitress peak active workers: **12/12**
- Waitress peak queue depth: **4**
- scheduler reconcile errors: 0
- watcher errors: 0
- unsupervised jobs: none
- corrupt job files: none

Latest burst latency:
- p50 ~170.75 ms
- p95 ~2151.05 ms
- p99 ~2301.9 ms
- max ~3319.3 ms

Per-tool latest burst:
- `git.status`: p50 ~186 ms / p95 ~240 ms / max ~1497 ms
- `project.files.search`: p50 ~110 ms / p95 ~169 ms / max ~1408 ms
- `project.context.rehydrate`: p50 ~111 ms / p95 ~227 ms / max ~1322 ms
- `lab.capabilities.availability`: p50 ~2106 ms / p95 ~2238 ms / max ~3319 ms

The ~2-second tail is therefore dominated by dynamic optional-provider capability probing, not generic server saturation. Queueing exists when 16 clients oversubscribe 12 Waitress workers, but it is secondary to provider probe latency.

## Prometheus readback

Typical final campaign `/lab/dispatch` deltas:
- HTTP 200: 161 requests, average server-side duration ~432–448 ms
- HTTP 403: 40 requests, average ~3.4 ms
- HTTP 404: 1 request, average ~3 ms
- <=2 second histogram bucket: 171 / 202 dispatches

Two-step approval challenge + approved consequence calls explain the dispatch count exceeding the 108 logical cases.

## py-spy readback

`py-spy` attached successfully on Windows and generated flamegraphs with zero sampling errors.

Representative mixed-burst sample attribution:
- Waitress/Flask dispatch path ~90%+ of sampled active stacks, as expected
- project rehydration ~33%
- project file search ~23%
- Git status ~19%

The profile confirms the load exercised intended Runtime paths rather than spending its time inside the telemetry instrumentation.

## Resource-retention discrimination

### Misleading first signal

Early Waitress runs showed rising process handles. The observer opened one fresh connection per request but did not explicitly close it, while Waitress retains keep-alive channels up to its channel timeout.

Control:
- 40 `/health` requests using default keep-alive behavior: +13 handles
- same 40 requests with `Connection: close`: **+0 handles**
- 40 `/lab/health` default requests: +15 handles

The observer was corrected to explicit `Connection: close` for its one-shot request model.

### Warmed-path localization

After the correction, repeated hot phases showed no retained handle growth for project search/rehydration/archive/approval/semantic/capability/research paths; Git subprocess activity produced only tiny bounded fluctuations. Separate controls for capability probing, approval challenge creation, restart denial, unauthenticated health, missing-file read, and research showed zero settled handle growth.

Final warmed no-restart 108-case replay:
- handles: 539 -> 537
- threads: 20 -> 20
- open files: 3 -> 3
- connections: 4 -> 4

Thus there is **no evidence of per-call handle/socket/file/thread leakage at this campaign depth**.

### Memory claim ceiling

The first production-like dependency-backed run warmed RSS/USS from roughly 55.9/38.5 MB to 64.7/44.5 MB. A no-restart replay started near that plateau and ended around 68.2/47.9 MB. During the final 96-request bursts, memory movement was much smaller and handles remained flat.

A temporary built-in `tracemalloc` diagnostic mode showed that large early RSS changes were dominated by first-use imports/caches/allocator behavior and that Python retained allocation diffs were small relative to RSS movement. `tracemalloc` itself heavily inflates RSS, so it was removed from the final performance configuration.

Current earned claim:

**No unbounded memory leak was demonstrated at the tested depth, but zero long-horizon retention is not proven.**

A longer 30–60 minute soak or 10–20 repeated full matrices can be used if a stricter memory SLO is required.

## Unsafe archive hostile result

Approved extraction of the traversal archive containing `../escape.txt`:
- Runtime returned `partial:true`
- traversal entry was skipped with an `extract_skip` / escaped-destination warning
- no escape file appeared outside the destination or at project root

Layering result: the Skill can classify suspicious archive contents before consequence; Runtime extraction owns the hard path-safety fence.

## Runtime defect earned by synthetic dogfood

Original clone behavior:

`git.status(project_id=SKILL_SYNTH_LAB, repo_path=missing_repo)`

returned HTTP 500:
`LAB_DISPATCH_FAILED [WinError 267] The directory name is invalid`

Root cause:
`_git_repo_probe` correctly resolved a bounded project-scoped target but passed a nonexistent/non-directory cwd to the subprocess envelope before validating that target.

Correct behavior, qualified first in the isolated clone:
- outer dispatch transport: HTTP 200 / normal tool envelope
- inner Git result: `ok:false`
- `repo_grounded:false`
- `error_code:GIT_REPO_INVALID`
- `status:FAILED`
- `return_code:null`
- no raw WinError leakage

Regressions cover both `git.status` and `git.diff` for:
- missing nested repo path
- file supplied where a directory/repo is required

Clone qualification:
- focused Git hardening/grounding: **13/13 PASS**
- one unrelated UCM concurrency timing failure occurred on first full clone suite
- isolated UCM discriminator: **10/10 PASS**
- second full clone suite: **443 collected / 442 passed / 0 failed / 1 skip**

Source port qualification:
- changed Python compile: PASS
- Git hardening/grounding: **13/13 PASS**
- full source Runtime: **443 collected / 442 passed / 0 failed / 1 skip**

## Telemetry evidence manifest

Observer artifact manifest SHA-256:
`3f62fa91a848bf85288127bb5f373462e6f0f1c7c899b8bd116c0f563f5743a0`

Stored under observer project:
`E:\new pc\AI_Pushes_Sandbox\projects\PCMMAD_SKILL_DYNO_OBSERVER\TELEMETRY_EVIDENCE_MANIFEST.json`

Representative content-addressed evidence includes final summaries/cases, per-Skill telemetry, Prometheus before/after scrapes, py-spy flamegraphs, memory diagnostics, HTTP handle controls, telemetry-stack validation, and hostile archive result.

## Publication boundary

This report qualifies only the narrow Git error-taxonomy source repair plus the synthetic Skill/telemetry evidence.

It does **not**:
- promote or restart live Runtime
- mutate UCM/memory architecture
- change the final compact schema
- convert synthetic Skill qualification into independent real-world dogfood of every Skill
- promote telemetry tooling into Runtime architecture

The telemetry stack belongs to the isolated qualification/dyno plane unless repeated operational pressure later earns a permanent Runtime observability interface.
