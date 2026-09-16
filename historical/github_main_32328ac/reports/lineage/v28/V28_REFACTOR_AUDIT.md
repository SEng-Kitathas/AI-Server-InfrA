
# PCMMAD Receiver V28 refactor audit

## Decision

**Sandbox promotion-clean.** The receiver preserves 49 routes, 75 registered tools, and 30 Custom GPT operations. Thirty-two regression tests pass, all route/resilience/security/schema/package/launcher reports are clean, and all CSC promotion surfaces are clean.

## Structural improvements

- typed machine-facing configuration and invalid-state rejection
- explicit required/optional route-family loading
- constant-time authentication comparison
- validated manual archive extraction rather than delegated extraction trust
- isolated verification roots and dynamic sidecar ports
- deterministic verification teardown
- one canonical Windows command surface
- v10.2 compact schema with no feature reduction
- immutable release-body manifest separated from mutable evidence
- lineage, migration, first-boot, invariant, and release-contract documentation

## Preserved authority surface

- Routes: **49**
- Server-native tools: **75**
- Imported GPT operations: **30**
- Regression tests: **25 → 32**

## Remaining host verification

- parse and execute PowerShell on Windows
- open a real ngrok tunnel and exercise a Custom GPT action callback
- mount and parity-check the surviving D:/E: project roots

These are explicitly deferred because the Linux sandbox cannot truthfully embody Windows/ngrok/user-drive reality.
