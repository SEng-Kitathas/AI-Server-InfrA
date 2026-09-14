# Break-Glass Functional Dependency Campaign

Definition locked: immutable dependency = a function without which correct server operation is impossible unless that function is lawfully replaced. Implementation/version is not immutable merely because the function is.

## BG1 — Can hard requirements be expressed by function rather than current implementation?
PASS, provisional. Manifest separates five core functions from guarantee/optional dependencies: boot recovery host, independent recovery runtime, known-good receiver material, persistent governed state, loopback API. Remote ingress/HUD/browser are explicit guarantee degradations rather than core killers.

Earned: FUNCTIONAL REQUIREMENT != CURRENT PROVIDER. CORE OPERABILITY != EVERY GUARANTEE AVAILABLE.

## BG2 — Does the evaluator fail closed on missing hard functions without flattening optional failures?
PASS. Missing/unknown core dependency blocks core_operational. Browser/remote absence preserves local core while reporting the lost guarantee. Known-good material hash mismatch fails. 7/7 breakglass tests; combined dependency/supervisor pressure 25/25 PASS.

Scar: first dependency-isolation test grepped source text and falsely failed because the docstring said `no pcmmad_receiver imports`. Replaced naive text assertion with AST import inspection. Harness scar, not product defect.

## BG3 — Can the dependency evaluator itself leave the receiver source tree?
NARROW PASS. breakglass_core.py + manifest copied alone to an isolated temp directory and imported under Python `-I`; no receiver package or project path required. This removes receiver-package dependency but NOT Python-runtime dependency.

## Sharpest discriminator / substantive blocker
The remaining bootstrap circularity is now precise: the recovery evaluator can survive receiver-tree loss, but still requires a Python interpreter. The functional manifest correctly names an independent recovery runtime, and no such self-contained provider exists yet. Do not pretend stdlib-only Python is runtime independence.

Reopen: package the tiny break-glass core as a self-contained independently installed artifact (native/service executable or embedded runtime bundle), bind its identity and manifest, and include/locate sealed known-good receiver recovery material. Then physically emulate normal-Python absence and receiver-tree absence together. Only after that should we install it as SYSTEM startup root.

## BG4 — Self-contained provider attack: normal Python path + receiver tree absent
PASS in sacrificial recovery root. Built a local sealed-by-manifest bundle from last published qualified head `30c4826`: receiver archive 2,512,340 bytes; recovery Python archive 135,025,340 bytes; PowerShell restore script. Restore executed through Windows PowerShell with PATH reduced to Windows/System32 only, reconstructed independent Python + receiver source, and imported 171 capabilities.

Two real scars were found: (1) PowerShell Compress-Archive over `Python312\*` silently omitted root-level python.exe/DLL files; replaced by OS tar of the directory root. (2) Expand-Archive was so slow the governing mutation lease expired mid-extraction and left a partial runtime; restore now uses OS tar and completes in ~43s in this sandbox.

Earned: ARCHIVE EXISTS != RECOVERY RUNTIME COMPLETE. RECOVERY MUST FUNCTIONALLY BOOT THE RESTORED PROVIDER AFTER EXTRACTION. INTERRUPTED RECOVERY MUST BE ASSUMED PARTIAL UNTIL READBACK.

## BG5 — Minimum receiver boot and agent ingress
PASS. Restored runtime/source launched an isolated Flask receiver on port 5199 with isolated PCMMAD roots. Authenticated `/health` returned full receiver health. A fresh HTTP POST to `/lab/vnext/orient` returned schema `11.0.0-candidate`, count 2/2 requested (`fs.glob`, `project.mutation.inspect`). This is actual restored agent<->server protocol evidence, not import-only evidence.

## BG6 — Supervisor target warfort
MAJOR DEFECT FOUND. Candidate supervisor defaults targeted `127.0.0.1:5090/api/health`; actual receiver is port 5000 and exposes `/health`. Port 5090 is HUD. Therefore the proposed always-on supervisor was probing the wrong component and nonexistent route. Local candidate corrected to `http://127.0.0.1:5000/health`; regression added.

Earned: SUPERVISION LABEL != SUPERVISED COMPONENT. READINESS TARGET IDENTITY MUST BE DERIVED FROM THE SERVICE CONTRACT, NOT COPIED BY CONVENTION.

## BG7 — Unattended credential/session failure domain
SUBSTANTIVE BLOCKER. `/health` is correctly API-key protected. The current live `PCMMAD_V30_Receiver` scheduled task runs as user `ancal`, LogonType Interactive, RunLevel Limited. GITHOME_API_KEY exists in Process/User scope but not Machine scope. Therefore after reboot with nobody logged in, the canonical receiver task and its credential acquisition are not qualified to start unattended. A SYSTEM supervisor cannot simply inherit the user's credential.

This means source/runtime recovery is now proven, but operator-independent REMOTE_INGRESS_READY is not.

Earned: BOOT STARTUP REGISTRATION != UNATTENDED STARTUP. USER-SESSION CREDENTIAL != MACHINE RECOVERY CREDENTIAL. CREDENTIAL AVAILABILITY IS A FUNCTIONAL DEPENDENCY OF AUTHENTICATED REMOTE INGRESS.

## Hard stop / reopen
Do not install the SYSTEM HA/break-glass tasks yet. Reopen by deriving a machine recovery credential carrier with explicit local security boundary (prefer OS-protected secret + restrictive ACL, not plaintext environment promotion), and separate local core startup from tunnel recovery. Then run a no-interactive-user boot emulation: SYSTEM-context recovery must restore/start receiver, authenticate its functional probe, and independently converge ngrok/remote ingress without relying on ancal's interactive environment.
