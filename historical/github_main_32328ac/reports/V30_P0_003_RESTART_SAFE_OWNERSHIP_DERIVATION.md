# V30 P0-003 — Restart-Safe Execution Ownership Derivation

Status: VERIFIED MECHANISM COMPOSITION / integration pending

## Intended outcome
A canonical async job remains truthful, governable, cancellable, and non-orphaning across receiver restart without creating a competing scheduler.

## Observed scars
1. V29 canonical scheduler stored live process control in in-memory `Popen` handles; restart destroys that ownership surface.
2. Initial durable runner/capsule branch fixed completion/cancel/timeout persistence but exposed:
   - fresh cancel request erased by worker startup stale-cleanup race
   - Windows `os.replace` heartbeat collision misclassified as job failure
3. Both runner races were isolated and fixed; 20 repeated lost-handle completions, all restart-survival tests, and full V30 suite passed afterward.
4. Naive named Windows Job Object persistence failed: after the last creator handle closes, `OpenJobObjectW` cannot reopen the object even while an assigned process remains alive.
5. Runner-held anchor handle succeeded: while the assigned runner held a second named Job Object handle, receiver-side handle loss still allowed a fresh reopen/query/terminate.
6. `KILL_ON_JOB_CLOSE` orphan discriminator succeeded: with receiver handle absent, killing the runner closed the final Job Object handle and Windows killed the runner-created descendant.

## Derived composition
### Canonical scheduler
Owns:
- submission/admission
- idempotency
- queueing
- lifecycle semantics
- result registration
- replay
- promotion/readback

### Durable runner
Owns only one admitted execution actuation:
- hold Job Object ownership-anchor handle
- write heartbeat/completion receipts
- enforce local timeout
- observe durable cancel request
- launch one command only after ownership handshake

It SHALL NOT admit, queue, replay, or define canonical job state.

### Windows Job Object
Owns OS-native process-tree containment:
- one named object per canonical execution job
- runner assigned before it may spawn descendants
- descendants inherit membership
- runner holds an anchor handle
- `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` enabled
- restarted receiver may reopen by name while runner remains alive
- if runner and receiver ownership both disappear, descendants are killed by the kernel rather than orphaned

### Process identity
PID is insufficient. Runtime identity should progressively bind:
- pid
- creation time
- executable identity
- command fingerprint
- canonical job/service identity
- node identity
- supervision generation/epoch

## Handshake invariant
1. scheduler creates named Job Object
2. scheduler enables kill-on-last-handle-close
3. scheduler writes worker request including Job Object name + ownership release path
4. scheduler spawns runner
5. scheduler assigns runner PID to Job Object
6. runner opens same Job Object and writes `OWNERSHIP_READY` heartbeat
7. scheduler verifies heartbeat token/job identity
8. scheduler writes ownership release receipt
9. only then may runner spawn user command
10. scheduler may close its creation handle; runner remains anchor

If the handshake fails, no user command may start.

## Termination policy
- normal cancellation: durable cancel request -> runner kills command/tree -> runner writes TERMINATED receipt
- receiver restart: runner remains anchor and continues receipt/cancel semantics
- runner unresponsive but Job Object reopenable: scheduler may use `TerminateJobObject` as bounded hard-stop fallback
- runner dies while receiver absent: final anchor closes and kernel kills descendants
- PID alone never grants ownership authority

## Claim ceiling
This is verified as a mechanism composition by isolated hostile tests. It is not yet promoted into the canonical V30 execution engine until integrated tests prove handshake, restart, cancellation, timeout, runner crash, malformed/stale Job Object state, and full regression behavior.
