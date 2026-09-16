# Unattended Recovery Credential / Remote Ingress Warfort

## UR1 — Recurrent mutation authority scar
Generation 43 again persisted ACTIVE with lease_id=null after expiry. Live 160-cap server has no maintenance.* capabilities because the local maintenance plane is not deployed. Normal acquire lawfully advanced to generation 44 after expiry. Recurrence strengthens P0 requirement for immediate impossible-state reconciliation after deployment.

## UR2 — Machine recovery credential carrier
Candidate uses Windows DPAPI LocalMachine with fixed purpose entropy and removes ACL inheritance, granting only SYSTEM and Administrators. API key and ngrok authtoken are separate protected blobs. Secret CLI no longer accepts a secret argument; protection input is stdin. Shared RecoverySecret.psm1 prevents crypto-semantics duplication between installer/runtime.

Hostile observation: after ACL restriction the current non-elevated ancal process cannot read the protected blob at all (AccessDenied), which is the desired boundary.

Earned: USER ENVIRONMENT != RECOVERY SECRET STORE. MACHINE RECOVERY SECRET MUST BE AVAILABLE TO THE RECOVERY IDENTITY WITHOUT BECOMING MACHINE-WIDE PLAINTEXT. SECRET PROTECTION != SECRET COMMAND-LINE EXPOSURE.

## UR3 — Separate receiver/tunnel SYSTEM recovery design
Candidate one-time elevated installer captures non-secret runtime configuration, protects GITHOME_API_KEY + ngrok authtoken, copies the real ngrok binary, and registers independent SYSTEM/AtStartup receiver and tunnel tasks. Runtime launchers read no User environment. Tunnel materializes config only in an ACL-restricted temporary file and deletes it in finally. Tunnel launcher contains no receiver restart/kill path.

Focused static/dependency/domestic warfort: 17/17 PASS. Non-elevated installer attempt correctly refuses before mutation with ELEVATED_ADMIN_REQUIRED_FOR_ONE_TIME_RECOVERY_INSTALL.

## UR4 — SYSTEM-context proof attempt
BLOCKED by the actual execution identity: current PCMMAD execution runs as SOVEREIGN-1\ancal with IS_ADMIN=False. Creating a temporary SYSTEM scheduled task returns Access Denied. Therefore DPAPI LocalMachine semantics are implemented, but SYSTEM decryption + no-login receiver/tunnel execution cannot be honestly marked verified from this control surface.

## Substantive blocker / reopen condition
One-time OS elevation is now the precise external boundary. A local administrator must install the recovery root once (or PCMMAD must gain a separately authorized elevated maintenance bootstrap). After that, Warfort must immediately perform an actual SYSTEM-context test: decrypt test credential without exposing it, start isolated receiver with User env absent, authenticated /health + v11 orient, start independent tunnel, remote readback, kill/restart each independently, then reboot/no-login qualification. Do not promote/install live tasks before this proof.

Candidate law: AUTONOMOUS RECOVERY MAY REQUIRE ONE-TIME PRIVILEGED EMBODIMENT; IT MUST NOT REQUIRE REPEATED OPERATOR AVAILABILITY AFTER EMBODIMENT.
