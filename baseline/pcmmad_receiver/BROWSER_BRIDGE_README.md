# PCMMAD Browser Bridge

The browser bridge is a standard local PCMMAD runtime plane on `127.0.0.1:4471`.

## Production / unattended behavior

The unattended recovery installer registers two SYSTEM Scheduled Tasks:

- `PCMMAD_V30_BrowserBridge_SYSTEM` — canonical browser-bridge workload, starts at boot.
- `PCMMAD_V30_BrowserBridgeSupervisor_SYSTEM` — out-of-process health supervisor with restart budget, maintenance hold, receipt, singleton lock, and durable failure state.

The workload task does **not** own its own restart loop; the supervisor does. This preserves the same restart-budget/HA discipline as Receiver and ngrok.

## Manual controls

Use the repository helpers:

- `START_BROWSER_BRIDGE.cmd` — starts the canonical managed task when installed, waits for identity-bound `/health`, and falls back to a direct development launch only when the managed task does not exist.
- `CHECK_BROWSER_BRIDGE.cmd` — verifies `/health`, `service=pcmmad_browser_bridge`, PID/session/Playwright state, and reports whether the managed task exists.
- `STOP_BROWSER_BRIDGE.cmd` — stops the canonical task when installed; development fallback refuses to kill a non-bridge process on port 4471.

Health endpoint: `http://127.0.0.1:4471/health`.

`PROCESS LISTENING != BROWSER BRIDGE HEALTHY`
`OPTIONAL FOR A GIVEN TASK != MANUALLY STARTED INFRASTRUCTURE`
