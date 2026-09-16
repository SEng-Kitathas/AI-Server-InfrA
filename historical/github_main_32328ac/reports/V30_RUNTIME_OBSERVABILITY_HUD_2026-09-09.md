# V30 Runtime Observability + HUD Projection — 2026-09-09

Status: **ENGINEERING QUALIFIED / LIVE PROCESS UNCHANGED**

## Trigger

The isolated Skill dyno campaign installed `psutil`, Prometheus instrumentation, `py-spy`, and Waitress to obtain real process/request/server-pressure telemetry. The operator asked whether those dependencies could become active telemetry in the normal server HUD and requested the most complete practical server/laboratory monitoring choices rather than a minimal CPU widget.

## Architecture choice

The closest operational analogue is an SRE/laboratory control plane:

- **RED** for the HTTP service surface: request Rate, Errors, Duration;
- **USE** for process/host resources: Utilization, Saturation, Errors;
- explicit scheduler/queue integrity telemetry for PCMMAD-specific execution truth;
- bounded history/sparklines for trend context;
- expensive profiler (`py-spy`) kept on-demand rather than continuously attached.

Load-bearing boundary:

`HUD PRESENTATION != TELEMETRY AUTHORITY`

The receiver owns observability truth. The HUD projects the receiver-owned authenticated telemetry and must not rediscover receiver state by PID scraping or parallel heuristics.

Additional boundary:

`MONITORING_FAILURE != CORE_RUNTIME_FAILURE`

Observability is an optional route family. Missing telemetry may degrade the HUD's optional-plane readback but does not falsely mark the receiver authority plane down.

## Canonical runtime dependencies

Added to `baseline/pcmmad_receiver/requirements.txt` and `pyproject.toml`:

- `psutil>=7.2,<8`
- `prometheus-client>=0.26,<1`
- `waitress>=3.0,<4`

`py-spy>=0.4,<1` is recorded as an optional `diagnostics` dependency rather than a continuously loaded production dependency.

`SETUP_PCMMAD_RUNTIME.ps1` now verifies imports for Flask/requests/BeautifulSoup plus psutil/Prometheus/Waitress.

### Fresh-environment discriminator

A brand-new Python 3.12 venv was created using only the canonical receiver requirements.

Installed successfully:
- Flask 3.1.3
- requests 2.34.2
- beautifulsoup4 4.15.0
- psutil 7.2.2
- prometheus-client 0.26.0
- Waitress 3.0.2

`pip check`: **No broken requirements found.**

A direct fresh-venv `telemetry_snapshot()` returned `ok:true`, process RSS, host/storage metrics, and exact dependency readback.

Important scar: the currently loaded/live receiver venv did **not** contain psutil during this campaign. No package was installed into that live environment. Live dependency embodiment remains part of the separately gated reload/promotion step.

## Receiver observability surface

New optional blueprint:

- `GET /observability/telemetry` — authenticated compact JSON for the HUD/operator plane
- `GET /observability/metrics` — authenticated Prometheus exposition for machine scraping

Both require the receiver API key.

### RED metrics

Bounded Flask route labels are derived from `request.url_rule.rule`, never raw user paths, preventing route-label cardinality explosion.

Prometheus metrics include:
- `pcmmad_http_requests_total{route,method,status}`
- `pcmmad_http_request_duration_seconds{route,method}` histogram
- canonical scheduler gauges for running, queued, loaded worker limit, unsupervised jobs, corrupt job records, reconcile errors, and watcher errors

The JSON telemetry carries a five-minute window:
- request count
- requests/minute
- 4xx count/rate
- 5xx count/rate
- p50 / p95 / p99 / max latency

4xx and 5xx remain distinct because expected authority/validation rejection is not equivalent to internal server failure.

### Process USE metrics

Receiver process telemetry includes:
- PID and process uptime
- CPU percent + user/system CPU time
- RSS / USS / VMS
- threads
- Windows handles when available
- open files
- inet connections
- direct child processes
- voluntary/involuntary context switches
- process IO bytes/operation counts

### Host/resource USE metrics

Host telemetry includes:
- CPU percent + logical/physical CPU counts
- physical memory total/available/percent
- swap total/used/percent
- disk IO counters
- network bytes/packets
- storage volume total/used/free/percent for `PCMMAD_ROOT`

Storage was added deliberately because this Runtime writes jobs, journals, artifacts, archives, checkpoints, and result handles; CPU/RAM health alone cannot detect a full-volume failure.

### HTTP server saturation

The receiver entrypoint now prefers Waitress over Flask's development server.

Default independent HTTP pool:
- `PCMMAD_HTTP_THREADS=16`
- minimum accepted value: 4
- finite value required

This pool is deliberately separate from the 12-job async execution capacity. Control/readback/cancel/health requests must retain HTTP headroom when execution is saturated.

Waitress telemetry includes:
- configured/created worker threads
- active workers
- current task queue depth
- peak active workers
- peak queue depth

A low-overhead daemon sampler records queue/active peaks. If Waitress is unavailable, the receiver falls back to the Flask server with an explicit console degradation message; observability never becomes a boot-killing dependency.

The HUD itself also prefers Waitress with an independent default 8-thread local HTTP pool.

## Prometheus collectors

The receiver-owned registry also includes Prometheus process/platform/GC collectors in addition to PCMMAD-specific metrics.

Machine scrape and HUD JSON are driven from the same request/process instrumentation rather than separate truth planes.

## HUD projection

`/api/status` now grounds receiver health from `/lab/health` and telemetry from `/observability/telemetry` in parallel, rather than using `/lab/tools` as a health proxy.

Telemetry is marked optional in HUD readiness:
- receiver authority failure -> core degradation
- observability failure -> optional degradation
- browser bridge failure -> optional degradation

The HUD keeps a bounded 180-sample server-side ring and sends the most recent 60 compact points to the browser for sparklines.

### Active HUD gauges

Primary operator metrics:
- execution workers `running / loaded_capacity`
- execution queue + oldest queue age
- HTTP p95
- receiver RSS + USS

Resource/integrity strip:
- receiver CPU
- host CPU
- host memory
- storage free
- handles
- threads
- sockets/open files
- HTTP active/configured workers
- HTTP queue peak
- requests/minute
- HTTP 5xx rate
- scheduler/watcher state

Short native SVG sparklines are generated without Chart.js/CDN/external dependencies for worker utilization, queue depth, p95 latency, and RSS.

### Active alert rules

Critical:
- unsupervised execution jobs
- corrupt job records
- scheduler error / reconcile error
- watcher errors
- nonzero HTTP 5xx rate
- storage >=97% used or <10 GiB free

Warning:
- execution utilization >=90%
- execution queue >0
- HTTP server queue >0
- host CPU >=90%
- host memory >=90%
- storage >=90% used or <25 GiB free (critical at >=97% or <10 GiB free)
- HTTP p95 >=2000 ms

These are operator attention indicators, not replacement authority for the underlying Runtime records.

## Real Waitress integration smoke

An isolated source-tree receiver instance was started on `127.0.0.1:5512` with:
- Waitress threads: 16
- isolated PCMMAD roots
- isolated API key
- browser sidecar intentionally absent

72 concurrent authenticated requests were issued with 24 clients across `/lab/health` and `/observability/telemetry`.

Result:
- all 72 requests: HTTP 200
- Waitress active peak: **16/16**
- Waitress queue peak: **8**
- final queue depth: 0
- `/observability/metrics`: HTTP 200
- Prometheus request metric present: yes
- Prometheus RSS gauge present: yes
- `/lab/health`: HTTP 200
- execution readback: running 0 / queued 0 / loaded engineering limit 12
- process RSS during sample: ~64.4 MB
- process USS: ~45.2 MB
- dependency readback: psutil 7.2.2 / Prometheus 0.26.0 / Waitress 3.0.2 / py-spy 0.4.2 available externally

The deliberately heavy 24-client health/telemetry burst produced HTTP p95 ~3.4 s and queue depth 8, demonstrating that the saturation metrics are real rather than decorative. Normal HUD polling is one status request every five seconds, not this synthetic health-scan storm.

Raw smoke result:
`reports/V30_OBSERVABILITY_SMOKE_RESULT.json`

## Tests

Focused Runtime config + observability + HUD suite:
- **40/40 PASS**

Added/updated contracts cover:
- authenticated telemetry and metrics
- process/host/storage fields
- RED 4xx vs 5xx separation
- bounded Prometheus route labels
- profiler remains on-demand
- independent 16-thread HTTP default
- observability degradation does not become core receiver failure
- loaded execution capacity survives HUD projection
- critical scheduler/watcher/orphan/storage alert taxonomy
- bounded HUD history
- no external chart/CDN dependency

Full Runtime after final storage-pressure addition:
- collected: **456**
- passed: **455**
- failed: **0**
- conditional skip: **1**

Python compile: PASS.
Node `--check` on HUD JS: PASS.

## Claim ceiling

This engineering candidate proves the observability dependencies can be made first-class, receiver-owned active telemetry and projected into the HUD without creating a second authority plane.

It does **not** claim live embodiment yet.

The currently loaded live process/environment remains separate:

`PUBLISHED_CONFIGURATION != LOADED_PROCESS_CONFIGURATION`

`ENGINEERING_TRUTH != LIVE_PROCESS_TRUTH UNTIL DEPENDENCIES + CODE ARE EMBODIED AND READ BACK`

A later explicitly authorized live reload must install the canonical dependencies into the target Runtime environment, restart/reload the receiver/HUD, read back Waitress/telemetry dependency versions, loaded execution capacity, and then perform the already-locked >=10 async live acceptance campaign.
