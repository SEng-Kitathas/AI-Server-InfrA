# Domestic Adversarial Availability — Warfort Campaign

Standing laws: OPERATOR AVAILABILITY != SYSTEM AVAILABILITY. THE TECHNICAL OPERATOR IS A FAILURE DOMAIN. PROCESS STOP != DESIRED-STATE STOP. OUT-OF-PROCESS != OUT-OF-FAILURE-DOMAIN. Sharpest discriminator wins each branch.

## DA1 — Is HTTP 2xx sufficient readiness?
NO. Candidate supervisor now requires bounded JSON, `ok=true`, and core status in healthy/ok/degraded. Fake HTTP 200, HTML, explicit core-not-ok, and unknown status fail. `degraded` remains ready so optional browser failure cannot cause core restart. 6 hostile readiness cases PASS.

Earned: HTTP LIVENESS != RECEIVER READINESS. OPTIONAL DEGRADATION != CORE FAILURE.

## DA2 — Can recovery become a restart storm?
Initial daemon had no cross-iteration restart budget: YES. Added monotonic bounded restart window. Three attempts in window are allowed; fourth yields CRASH_LOOP_HOLD with receipt; old attempts age out. Crash-loop tests PASS.

Earned: DESIRED STATE RECONCILIATION != UNBOUNDED RESTART. Availability mechanisms require a bounded failure mode that preserves evidence instead of self-DoS.

## Current focused qualification
Supervisor base + HA + readiness + crash-loop: 16/16 PASS; py_compile PASS.

## Sharpest next discriminator
Current readiness still trusts `/api/health` self-report for receiver identity. A wrong/impostor PCMMAD-like service can return `{ok:true,status:healthy}`. Next: derive a minimum identity witness outside the mutable health claim—expected listener/process identity and/or a challenge endpoint bound to schema/catalog/source identity. Attack port impostor, stale receiver, candidate/current schema compatibility, and optional-degraded core. Do not require exact source HEAD for availability if a last-qualified compatible receiver is intentionally serving during deployment; separate SERVICE_READY from DEPLOYMENT_CURRENT.

## DA3 — Service identity vs deployment currentness
Added schema-family identity to minimum readiness. Impostor `{ok:true,status:healthy}` without schema identity fails; incompatible schema fails; compatible v11 degraded/healthy passes. Exact source HEAD is deliberately not required for SERVICE_READY, preserving a last-qualified compatible receiver during deployment. Supervisor focused suite now 20/20 before later additions.

Earned: SERVICE_READY != DEPLOYMENT_CURRENT. Availability may lawfully preserve a compatible last-qualified organism while deployment currentness is separately degraded.

## DA4 — Forgotten maintenance hold
An unbounded stop-file could strand unattended infrastructure indefinitely. Hold now has bounded age (default 2h); within bound desired STOPPED is respected, after bound stale hold is removed and RUNNING reconciliation resumes.

Earned: MAINTENANCE HOLD != PERMANENT AVAILABILITY DISABLE. Operator intent itself requires currentness.

## DA5 — Duplicate supervisor / stale singleton
Task Scheduler already requests IgnoreNew, but defense-in-depth singleton was added. First O_EXCL design exposed a new domestic failure: crash leaves stale lock and prevents future supervisor. Re-derived lock now records PID and only removes it when owner PID is dead.

Earned: SINGLETON FENCE != STALE SINGLETON DEADLOCK.

## DA6 — Interrupted execution after receiver restart
Inspection found existing scheduler startup in app_factory and durable reconciliation in execution_routes: SUBMITTED jobs are respawned/queued; worker-token active jobs finalize through durable worker state; legacy RUNNING records use process identity and become unsupervised or supervision-lost rather than silently duplicated. This is promising existing composition, not yet a new mechanism.

Sharpest next attack: process-level crash/restart emulation with a real durable execution record while receiver scheduler state is destroyed. Verify exactly-once/idempotency behavior, consequence-holder release, and final drain. Then attack an interrupted mutation where filesystem/Git consequence completed but response/registration did not. If execution recovery is already strong, do not add a boot recovery manager.

## DA7 — Restart recovery / response-loss composition
Existing mechanisms survived focused composition: worker restart recovery + ownership handshake + mutation authority + hostile response-loss/idempotency suite = 33/33 PASS. The Runtime already reconstructs idempotency from durable job records, rejects ambiguous/conflicting recovery, and starts scheduler reconciliation at app creation. No new boot recovery manager earned.

Earned: AVAILABILITY RECOVERY SHOULD COMPOSE EXISTING DURABLE CONSEQUENCE RECOVERY; DO NOT DUPLICATE IT IN SUPERVISOR. Supervisor restores service; receiver reconciles durable work.

## Sharpest next discriminator
The new singleton stale-lock recovery currently uses PID liveness only. PID reuse is a known PCMMAD scar: a different process can inherit the stale PID and permanently fence supervision. This is sharper than adding more availability features. Bind supervisor lock to process creation identity, not PID alone, using a dependency-light Windows witness. Then emulate same-PID/different-creation and malformed lock. After that, attack startup dependency failure (Python missing/corrupt) because supervisor and receiver still share Python as a failure domain.

## DA8 — Singleton PID-reuse attack
PID-only stale-lock recovery was rejected as naive. Lock now binds PID + Windows process creation FILETIME. Same PID/same creation fences duplicate; same PID/different creation is recognized as reuse and stale lock recovers; dead owner recovers; malformed/unverifiable lock fails safe and preserves evidence. Full supervisor family 26/26 PASS after repair.

Earned: PID != PROCESS IDENTITY. This reuses an existing PCMMAD scar rather than rediscovering it in production.

## DA9 — Recovery-root dependency attack
SUBSTANTIAL BLOCKER. Startup installer executes the supervisor with the same user Python 3.12 installation class that the receiver depends on. If Windows/Python update/removal/corruption breaks that interpreter, the always-on supervisor cannot start, so it cannot restore the receiver. There is also no verified last-qualified runtime rollback surface in the supervisor. Task Scheduler/SYSTEM does not solve interpreter failure-domain coupling.

This is now sharper than further Python-level warforts. Continuing to add daemon logic would decorate a recovery root that shares a critical dependency with the organism it must recover.

Earned: STARTUP INDEPENDENCE != RECOVERY-ROOT INDEPENDENCE. THE RECOVERY ROOT MUST HAVE A SMALLER FAILURE DOMAIN THAN THE SERVICE IT RESTORES.

Reopen condition: package the supervisor as an independently deployable sealed executable/runtime (or Windows-native service) whose launch does not depend on the receiver Python installation; bind its identity/hash at install; give it a known-good receiver launch artifact/manifest and bounded rollback ladder. Then rerun package-loss, Python-loss, port-impostor, crash-loop, reboot/startup, interrupted-execution, and agent-ingress warforts.

## DA3 — Service identity vs deployment currentness
PASS, narrow. Added a second bounded identity challenge: compatible schema family, capability floor, catalog identity. Fake health-only service and schema-incompatible service fail; compatible older 160-cap receiver remains SERVICE_READY; catalog equality separately determines DEPLOYMENT_CURRENT.

Earned: SERVICE_READY != DEPLOYMENT_CURRENT. AVAILABILITY MUST NOT REQUIRE THE NEWEST DEPLOYMENT WHEN A QUALIFIED COMPATIBLE MINIMUM CAN KEEP INGRESS ALIVE.

## DA4 — Reboot during interrupted governed work
PASS at classification layer. Restarting service no longer implies control-state recovery: ACTIVE+null lease => RECONCILIATION_REQUIRED; active consequence => INTERRUPTED_CONSEQUENCE_REVIEW; unknown interruption remains UNKNOWN. Service may come up while continuity/control readiness remains false.

Earned: SERVICE RECOVERY != CONSEQUENCE RECOVERY. BOOT GREEN != CONTROL STATE RECONCILED.

## DA5 — Stale maintenance hold
PASS. Old implementation treated existence of a stop file as indefinite desired STOPPED and could strand the lab after reboot. Hold is now structured, operator+reason required, expiry required, maximum duration bounded; expired/corrupt/overlong hold fails toward desired RUNNING.

Earned: MAINTENANCE HOLD != PERMANENT AVAILABILITY DISABLE. A RECOVERY OVERRIDE MUST ITSELF EXPIRE OR BE REQUALIFIED.

## Current campaign pressure
Identity/currentness 9/9; boot recovery + hold + identity/currentness 18/18. Earlier readiness/crash-loop 13/13.

## Attention Reservoir breadth check
Still open: supervisor failure-domain independence; canonical receiver task missing/corrupt; Python runtime removal; duplicate supervisors; disk pressure/receipt write failure; clock jumps (hold uses wall time while restart window uses monotonic); sleep/wake; network/ngrok independent convergence; interrupted deployment/known-good rollback.

## Sharpest next discriminator / blocker candidate
The supervisor is still Python and source-tree dependent. Windows can boot perfectly while Python/package/source is missing or broken, making the supposed recovery root unavailable. This is more load-bearing than ngrok/sleep polish. Attack startup with missing Python and missing receiver tree, then determine the minimum independently deployable recovery artifact. If solving it requires a separately packaged/native/service host or sealed embedded Python bundle, stop and treat that packaging/deployment boundary as the substantive blocker rather than pretending source-level HA is operator-independent.

## DA6 — Recovery-root dependency attack
SUBSTANTIVE BLOCKER CONFIRMED. Startup task directly executes an external Python installation and resolves `supervisor/receiver_supervisor.py` from the mutable source tree. No embedded/independently packaged runtime exists. Therefore a Windows/Python update, Python removal, source-tree deletion/corruption, or path move can kill the supervisor before it can repair the receiver.

Disposition: HARD STOP at source-level HA. Do not claim operator-independent recoverability or install this candidate as highest-assurance startup root yet.

Earned: A RECOVERY ROOT CANNOT SHARE A MUTABLE RUNTIME/DEPLOYMENT DEPENDENCY WITH THE SERVICE IT MUST RECOVER. STARTUP REGISTRATION != BOOTSTRAP INDEPENDENCE.

Reopen condition: produce an independently deployable, identity-bound supervisor artifact (e.g. Windows service/native executable or sealed self-contained runtime bundle) installed outside mutable receiver source, with known-good receiver recovery material. Prove it survives receiver tree loss and normal Python removal, then attack service registration loss, binary corruption, rollback, disk pressure, and interrupted deployment.
