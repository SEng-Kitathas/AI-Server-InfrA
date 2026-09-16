# DAEMON NON-INFERENCE RUNTIME CAMPAIGN — 2026-09-15

## Scope
Inference/generative conversation and HUD UI were explicitly deferred by operator. This campaign completed the highest-value remaining non-inference Daemon work in clone only. No live install/promotion occurred.

## Qualified runtime/service
- `mvf_resident/daemon_service.py`: persistent non-conversational Daemon service with proactive initiative loop, no prompt requirement.
- Fresh service cycles run `default_receiver_lab_duties` on cadence and persist through qualified Daemon plane.
- Local read-only HTTP surfaces: `/health`, `/status`, `/events`.
- Health requires CURRENT plane + initiative thread alive + no cycle error/currentness timeout; process existence alone is insufficient.
- Status/events report `mutation_authority=false`.
- Durable status files added to Daemon plane: `status/current.json`, `status/timeline.jsonl`, `status/alerts.jsonl` path reserved.
- Service lifecycle/SQLite ownership is initiative-thread-local; HEaT found and fixed cross-thread SQLite misuse rather than disabling SQLite thread safety.

## Receiver native integration
- Added native low-danger read-only capabilities: `daemon.health`, `daemon.status`, `daemon.events`.
- Capabilities proxy local Daemon service via `PCMMAD_DAEMON_URL`, default `http://127.0.0.1:5015`.
- Real clone smoke against port 5016 returned health/status/events through `lab_tools.dispatch_tool`.
- Installer now exports `PCMMAD_DAEMON_URL` from configured Daemon port so body->brain observation follows deployment config.

## Proactive cognition / body HA duty
- Default `receiver-currentness-ha` duty now observes both Python Receiver processes and `ngrok` processes plus PCMMAD scheduled tasks.
- Daemon remains read-only for body recovery effects; diagnosis/observation does not grant restart authority.

## Unattended recovery / HA embodiment in clone
Extended `supervisor/install_unattended_recovery.ps1` clone-only design:
- copies full `mvf_resident` runtime into recovery install root;
- configures explicit `DAEMON_PROJECT_ROOT`, `DAEMON_PORT`, `PCMMAD_DAEMON_URL`;
- adds `PCMMAD_V30_Daemon_SYSTEM` workload task;
- adds independent `PCMMAD_V30_DaemonSupervisor_SYSTEM` task;
- Daemon supervisor reuses existing hardened `receiver_supervisor.py` with `mvf.daemon-health.` schema family;
- independent `daemon_supervisor_receipt.json`, maintenance hold, singleton lock, restart budget/window;
- original Receiver/ngrok/Supervisor SYSTEM tasks remain intact;
- Daemon workload does not receive RecoverySecret/GITHOME key merely because supervisor infrastructure has it.

## Real clone-only recovery experiments
Temporary Daemon service on port 5016 ran autonomously with surfaces CURRENT and no mutation authority. Independent temporary supervisor was started using the existing supervisor primitive.

Exact-identity recovery proof:
- first clean exact-identity run: PID `36804`, creation `2026-09-15T21:39:34.9493119Z` -> PID `15756`, creation `2026-09-15T21:39:53.3496423Z`; health `healthy`; live Receiver port 5000 PID remained `12788`.
- maintenance-hold run: PID `15756` killed under bounded STOPPED hold; no 5016 listener while hold active; supervisor receipt action `MAINTENANCE_HOLD`; clearing hold recovered Daemon as PID `26940`; health `healthy`; live Receiver unchanged.
- an earlier recovery `10264 -> 36804` demonstrated recovery but creation-time conversion in the probe was invalid, so it is retained only as partial evidence and not promoted to exact-identity proof.

## Cleanup
Campaign temp scheduled tasks were stopped/unregistered. A child Daemon process survived task removal and was then reaped with exact port+command-line guard. Final port 5016 absent; live port 5000 still PID 12788.

## Qualification
- focused service/HA/native/installer/plane/bootstrap/Interaction Integrity: 34/34 PASS before final native status additions; final focused status/config slice 11/11 PASS.
- broad regression after full non-inference integration: 48 test files, compile rc 0, pytest rc 0, diff-check rc 0.
- PowerShell unattended recovery installer parse: clean.

## Current boundary
Clone non-inference Daemon runtime, persistence/bootstrap, proactive initiative, body observation, native status surfaces, and independent OOP recovery are qualified. Remaining major work:
1. **deferred by operator:** generative inference/conversation bridge;
2. **deferred by operator:** HUD communication/status UI;
3. **not performed:** live/project-control Daemon root creation, SYSTEM task installation, or live promotion. This remains a promotion/safe-window decision, not a clone engineering gap.
