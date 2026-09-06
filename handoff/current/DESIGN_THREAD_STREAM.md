# PCMMAD Receiver V30 — Design Thread Stream

Started/reconstructed: 2026-09-05 07:27 ET
Purpose: chronological recovery spine for the V29→V30 Receiver/Laboratory Runtime modernization.

## Reconstruction note

This stream was created late because the required project continuity directory existed but had not been populated. Earlier turns in this long thread are therefore reconstructed from:
- the active conversation context;
- the verified local V30 reports;
- current working-tree state;
- live server readbacks;
- explicit user instructions retained in-thread.

Where exact raw wording is available and load-bearing, it is preserved. Where the thread had already compacted/skipped turns, this uses the highest-fidelity practical chronological paraphrase. This is a recovery artifact, not a claim that every omitted conversational filler turn has been recreated verbatim.

---

## Phase 01 — Receiver ancestry / modernization trigger

### USER
Requested that the current PCMMAD receiver be treated as ancestry, copied, and then aggressively improved under the SOP/hostile-engineering method rather than incrementally polished. Desired a “multi-million-dollar server dream” level result and explicitly invited strip-for-parts research from external architectures/science.

State effect:
- V29 became immutable baseline ancestry, not the work surface.
- modernization target became V30 working body.

### ASSISTANT / SERVER ACTION
Initialized project `PCMMAD_RECEIVER_LAB` under `E:\new pc\AI_Pushes_Sandbox\projects\PCMMAD_RECEIVER_LAB`.
Copied V29 RC1 archive into `V29_BASELINE` and extracted only the copy.
Created `V30_WORKING\PCMMAD_receiver`.
Verified baseline archive:
- bytes: 711638
- SHA-256: `5baf9b66a9137d950aeabac2ea76fbbb919e177f90788e5341ee6e15a80b89d8`.

---

## Phase 02 — SOP deep read and corrected build metabolism

### USER
Required a linear deep read of the entire SOP package, not a skim or summary substitute.

### ASSISTANT / SERVER ACTION
Traversed the R4.4 SOP archive and five distinct sealed ancestry ZIP identities, deduplicating byte-identical readable members only by exact SHA while still inspecting all distinct archive contents.
Reported coverage included:
- 6 archive identities total
- 249 archive-member occurrences inspected
- 234 readable text occurrences
- 151 distinct readable byte identities
- ~759 KB unique readable source
- ~14.4k lines.

Derived that earlier work strongly used PDVER/hostile engineering and some CSC but had not explicitly exercised the full R4.4 supporting metabolism, especially Attention Reservoir, Helix, OARR recurrence, Loop+, Global Scar Ledger, and live state instruments.

### USER
Corrected the actual build loop and made the BUILD vs EMBODY distinction explicit:

FIX THE INTENDED OUTCOME
→ inspect reality / ancestry / constraints
→ try composition before invention
→ PROBE
→ DERIVE
→ VERIFY
→ BUILD smallest justified change
→ ATTACK IT
→ ISOLATE FAILURE
→ STRIP / MUTATE
→ EMBODY
→ RECURSE
→ CSC / semantic gate / release qualification.

Supporting machinery must feed this loop rather than become ceremonial parallel modules.

State effect:
- exact user-supplied loop became canonical V30 engineering metabolism.
- worker-capsule architecture was demoted from assumed solution to candidate needing replay through composition-before-invention.

---

## Phase 03 — Async authority split discovered

### USER
Asked for full pass over all planes/tools, especially async, stating “there’s definitely Something wrong in there somewhere.”

### ASSISTANT / SERVER ACTION
Found two async engines:
1. large canonical `execution_routes.py` durable queue/scheduler/lifecycle;
2. smaller `lab_tools_execution.py` in-memory direct Popen path.

### USER
Explicitly locked that the “big intended async module must win” when fixing the double-version Popen bug.

### ASSISTANT / SERVER ACTION
P0-001:
- `execution.submit` delegated to canonical scheduler.
- terminate/status/output/wait moved to canonical state.
- regression forbade adapter-side lifecycle ownership markers.
- targeted tests passed.

P0-002:
- reproduced global `_ADMISSION_LOCK` contention where slow all-project reconciliation blocked unrelated project admission.
- moved readiness scans/whole-tree discovery/file reads outside global lock.
- hostile cross-project test went FAIL before → PASS after.

State effect:
- canonical scheduler established as sole async admission/lifecycle authority.

---

## Phase 04 — Restart-safe ownership derivation

### ASSISTANT / SERVER ACTION
Investigated P0-003: after receiver restart the child process can survive while the in-memory Popen object is gone, making timeout/terminate/governance uncertain.

Initial candidate: durable one-job worker capsule with request/heartbeat/completion/cancel sidecars, subordinate to scheduler.

The first integration attempt exposed instability and was not promoted.

### ASSISTANT / SOP REPLAY
After deeper R4.4 review, replayed the intended outcome and external/native composition options rather than assuming the capsule architecture.

Windows Job Objects were explored.

A key failed hypothesis was preserved:
- a named Job Object is NOT durable merely because it has a name;
- when the last handle closes, the object disappears even if an assigned child continues.

Surviving composition:
- canonical scheduler = sole lifecycle/admission authority
- one-job runner = durable outcome/cancel/timeout receipts
- Windows Job Object = kernel process-tree containment
- runner-held Job Object handle = ownership anchor across receiver restart.

Handshake:
1. scheduler creates containment
2. launches/assigns worker
3. worker proves it holds containment object
4. scheduler verifies worker identity
5. scheduler issues token-bound release
6. only then may user command execute.

Additional Windows scar:
- venv `python.exe` PID may be launcher, not actual worker;
- launcher PID and real heartbeat worker PID were separated.

Hostile tests covered restart completion, cancellation, timeout, wrong token, handshake failure, cancel-before-release, duplicate Job Object names, lost receiver handle, orphan cleanup after runner crash.

State effect:
- restart-safe ownership became a strong V30 integrated candidate, still not live-promoted.

---

## Phase 05 — Live restart lifecycle / BAT repair

### USER
Pointed out the Desktop restart BAT was supposed to kill live ngrok/server instances but never properly did; requested a proper restart path and inline server restart capability.

### ASSISTANT / SERVER ACTION
Audited live install:
`C:\Users\ancal\Desktop\PCMMAD_RECEIVER_V29_NATIVE_PROTOCOL_RC1\PCMMAD_receiver`.

Found defects:
1. process identity was too broad and could kill RAHL-HUD because HUD used receiver venv Python;
2. `PowerShell -NoExit` wrappers could survive child shutdown;
3. an initial regex still matched HUD because receiver venv appeared earlier in command line;
4. DETACHED_PROCESS launch did not produce expected restart receipt;
5. Desktop BAT poisoned `PCMMAD_ROOT` by reusing it for install directory;
6. strict dispatcher mutation approval required payload approval but Custom GPT action wrapper exposed only tool name.

Repaired architecture:
- canonical controller: `RESTART_RECEIVER_AND_NGROK.ps1`
- thin Desktop BAT: `restart_pcmmad_receiver.bat`
- exact receiver script suffix identity
- all ngrok processes converged to one
- only provable wrappers killed
- port 5000/listener convergence before start
- direct receiver/ngrok launch, no `-NoExit`
- health + ngrok API + public URL verification
- environment rehydrated from User-level canonical variables at restart boundary
- structured restart receipt.

Inline tools:
- `control.receiver.restart`
- `control.receiver.restart.status`

They schedule/delegate to the same controller rather than create another restart lifecycle.

Real BAT and inline approved restart were exercised. RAHL-HUD survived process cleanup.

State effect:
- restart became a tested service-control mechanism and a key process-ownership scar.

---

## Phase 06 — Transfer plane parity

### ASSISTANT / LIVE WORK
Added transfer family before V30 modernization:
- 6 tools
- short-lived 256-bit tickets
- resumable bounded chunks
- per-chunk SHA256 + whole-file SHA256
- staged imports
- same-volume atomic promotion
- HTTP streaming
- no anonymous filesystem exposure.

Cross-volume atomic move defect was found and repaired by staging on destination volume.

### ASSISTANT / V30 AUDIT
Later found V30 static body had regressed all six transfer tools plus `browser.upload` that existed live.
Recovered those capabilities into V30.

State effect:
- live/V30 parity became a formal audit concern.

---

## Phase 07 — RAHL-HUD recognized as server UI lineage

### USER
Clarified that RAHL-HUD is the UI for the server “iirc,” said it was thrown together, and wanted TLC/improvement.

### USER
Added a specific presentation requirement: search all of `E:\new pc` for Aero-Glass design plans, HoloFont ideas, and the three-wing cockpit idea including Ui/YuiUi/CogTerm; since the server was growing up, presentation should become as “sexy” as originally intended.

### ASSISTANT / SERVER RESEARCH
Recovered presentation donor material and created `PCMMAD_OPERATOR_HUD_DESIGN_AUTHORITY_V0_1.md`.
Recovered requirements include:
- Aero-Glass / Liquid-Aero
- HoloFont
- YuiUI / Ui
- CogTerm
- Forge / Singularity Works
- responsive three-wing cockpit
- top corona
- bottom command dock
- keyboard-first operation
- runtime topology/jobs/queue/progress views.

State effect:
- RAHL-HUD became operator-presentation ancestry, but Runtime remains truth authority.

---

## Phase 08 — Commander’s intent / unfinished work interruption check

### USER
Asked to circle back to all stated Commander’s Intent and identify what had not been touched because user kept interrupting.

State effect:
- all-plane modernization worklist became explicit rather than a sequence of isolated fixes.
- async, HUD, schema, adapters, continuity, transfer, semantic, security, resource, and final promotion seams remained visible.

---

## Phase 09 — PCMMAD Runtime + MCP + Skills architecture converges

### USER
Proposed architecture:
- ordinary Project Chat
- PCMMAD Skill = operating doctrine
- PCMMAD MCP/App = actual machine hands
- PCMMAD server/runtime = execution substrate
- Custom GPT becomes optional compatibility/preset rather than architecture authority.

Further emphasized:
- server-native core
- MCP as thin projection
- Skills as AI-side operating intelligence
- do not make Runtime “an MCP implementation.”

Proposed compressed MCP control plane around identity/status/capability discovery/invoke/projects/jobs/results/batch rather than projecting 100 tools or one opaque god-tool.

### ASSISTANT
Converged on:
PCMMAD = methodology
Laboratory Runtime = truth/state/durable capability
Adapters = MCP/OpenAPI/CLI/HUD/etc.
OBE/Skills = operating intelligence
Model = replaceable co-processor
Project Chat = replaceable mission surface.

State effect:
- Custom GPT Action bridge demoted to compatibility frontend.
- transport-not-architecture authority became explicit.

---

## Phase 10 — Skill-thread cross-thread contract refinement

### USER / SKILL THREAD ADDENDUM
Skill thread accepted the split and refined it:
- `capabilities.invoke` must not become disguised god-tool;
- lazy invocation depends on typed discoverable contracts and bounded namespaces;
- capability_version/schema_version/schema_hash/contract_digest required to detect stale client assumptions;
- approval should be a target-bound envelope/handle, not boolean;
- process identity must exceed PID;
- projection matrix should capture native authority, adapters, lossiness, lifecycle, approval, idempotency, result/readback, currentness, and adapter-only state;
- adapter-local durable job/project/artifact/process/approval truths are architecture smell.

State effect:
- `PCMMAD_RUNTIME_ADAPTER_COMPATIBILITY_CONTRACT_V0_1.md` became cross-thread contract authority.
- projection matrix became next shared artifact.

---

## Phase 11 — Whole-plane audit: health, semantic, bounded results

### ASSISTANT / SERVER ACTION
A-002:
- aggregate `lab.health` hard-failed when optional browser bridge was unavailable.
- repaired to report degraded optional state rather than global failure.

A-003:
- foreground `lab.batch` could overflow constrained action response.
- reused existing result store for oversized foreground batch.
- `atomic=false` made explicit.

Semantic audit:
- stale C: script/DB paths
- malformed dependency probe
- receiver Python lacked faiss/numpy/torch/sentence_transformers/transformers
- old D: semantic venv pointed to removed C:\Program Files\Python312\python.exe
- data/index/model assets still survived.

Recovered evolved retriever donor:
`E:\new pc\AI_Pushes_Sandbox\projects\cto-chat-thread-organizer\tools\db_helper\monster_dual_retriever.py`
SHA-256 `0c0841230d33e427892ca83520f0845ab12c38290d4d9511f1cadce44c564dac`.

New semantic truth:
- assets present
- no qualified executor
- `available=false`
- `status=unavailable`
- blocker `no_qualified_python_runtime`.

State effect:
- fake-ish semantic health replaced by explicit dependency/currentness truth.

---

## Phase 12 — User introduces AI-attention law and final-schema sequencing

### USER
Explicitly instructed that routing/waiting/job queues/anything likely to make the model hang in tool state should send **small reports to the AI**, enough to make decisions and tell the user what is happening rather than sit “45 mins of thinking.”

Also instructed that the final thing, only once the whole server is truly done, should be a radical redesign of the dated schema; maxim: just because something was not envisioned or intended does not mean it cannot be done.

### ASSISTANT
Derived:
**LONG-RUNNING WORK SHALL NOT REQUIRE LONG-RUNNING MODEL ATTENTION.**
**EXECUTION MAY BLOCK; THE OPERATOR CONTROL LOOP SHOULD NOT.**
**RETURN DECISION INFORMATION EARLY; STORE BULK WORK LOCALLY.**

Final schema redesign explicitly deferred until whole-runtime convergence.

---

## Phase 13 — AXIOM-01 becomes foundational

### USER
Preferred “Intent is a constraint, not a ceiling” as the foundational line, comparing it to a recurring boot inscription and suggesting it be injected through boring guaranteed touchpoints such as health so it always reaches context without needing to be said.

### ASSISTANT / SERVER ACTION
Promoted:
**AXIOM-01 — INTENT IS A CONSTRAINT, NOT A CEILING.**

Implemented compact `constitutional_seed` through both ordinary `/health` and native `lab.health`, from one source module with digest/version.

State effect:
- foundational permission/search-space law became ambient runtime metadata.

---

## Phase 14 — User rejects static-schema blind spot

### USER
Clarified the original schema was the user’s introduction to JSON via earlier models; it may be clever but is stiff/static/brittle and reflects a first-principles blind spot. Requested help exploiting what the schema *could* be, not merely polishing the inherited contract.

### ASSISTANT
Initially described a reflective capability language/IR with objects, traits, effects, pre/postconditions, affordances, composition, and projection generation.

### USER
Corrected framing: the point was **Holonic and ECS-ish**; that is why those concepts fit so readily because the bones were already in the original server design.

### ASSISTANT
Re-grounded:
- do not invent foreign meta-ontology;
- surface/regularize existing entity/component/system/holon bones;
- capability traits can be components rather than new taxonomy;
- final schema becomes serialized projection of a living native model.

State effect:
- final schema campaign direction locked as holonic/ECS-ish projection, no ECS framework rewrite.

---

## Phase 15 — Worklist fold and capability contract embodiment

### USER
“Fold all this into the work list and then proceed as you see fit.”

### ASSISTANT / SERVER ACTION
Created/expanded `V30_COMMANDERS_INTENT_AND_WORKLIST.md` with:
- AXIOM-01
- long-running AI attention law
- holonic/ECS direction
- deferred final schema campaign
- cross-thread OBE handshake.

Verified ToolSpec enhancements:
- effective approval requirement
- capability/schema version
- schema hash
- contract digest
- output schema
- side-effect class.

Added effect traits after proving one-dimensional `mutating` insufficient.

State effect:
- native capability contract began converging toward typed reflective/runtime-current semantics.

---

## Phase 16 — Bounded execution/result control surfaces

### ASSISTANT / SERVER ACTION
Found `execution.wait` defaulted to `timeout_seconds=None` and looped forever for active jobs; terminal output could also be unbounded.

Implemented:
- default bounded wait
- server cap
- bounded terminal excerpts
- `execution.progress`
- evidence-based progress classes such as PROGRESSING/QUIESCENT/POSSIBLY_STALLED/SUPERVISION_UNCERTAIN/TERMINAL
- suggested recheck interval
- explicit bulk-output pointer.

Result store hardening:
- large default result read → preview
- metadata-only mode
- bounded range mode
- explicit full opt-in.

MCP manifest enriched with native contract hashes/currentness/authority/effects and stable manifest digest.

State effect:
- constrained-client/tool-state hanging reduced structurally.

---

## Phase 17 — Bound approval authority derived from real smuggling failure

### ASSISTANT / DIAGNOSTIC
Demonstrated current approval weakness:
- same `approval:{permit:true}` authorized service A
- service B
- changed args
- unrelated capability.

### ASSISTANT / DONOR QUARRY
Inspected CTO signed-promotion machinery and extracted reusable mechanism:
- identity-bound evidence
- canonical integrity hash
- provenance/operator identity
- issue/freshness/expiry
- auditable certificate/decision lineage.

Did NOT import CTO promotion ontology.

### ASSISTANT / SERVER ACTION
Built `approval_authority.py`:
- challenge bound to capability/version/schema/contract
- canonical arguments digest
- target summary
- danger/effect traits
- issue/expiry
- single-use
- integrity hash
- consumer provenance.

Dispatcher changed so authority envelope is separate from capability payload.

Schema/protocol eligibility checked before consuming single-use authority.
Legacy inline approval retained only as warned compatibility path with disable switch.

Focused tests passed at introduction.

State effect:
- approval became a real Runtime authority object rather than a boolean argument.

---

## Phase 18 — Context/file plane hostile audit

### ASSISTANT / SERVER ACTION
Observed project file-read control-plane 500 while direct local file read worked.

Source isolated undefined variable `s` in line-window logic.
Fixed exact bug rather than widening exception swallowing.

Then found three “bounded” context consumers were only response-bounded, not execution-bounded:
- file read
- search indexing
- recent rehydration fallback
all called whole-file `read_text()` before slicing.

Unified on bounded reader:
- bounded prefix raw bytes
- streaming line-window reads
- output and line caps.

Found project-scope authority flaw:
- scoped candidate validated against ANY globally allowed root, allowing cross-project escape on allowed drive.

Fixed exact base-root confinement after path resolution.
Hostile checks:
- relative escape rejected
- absolute escape rejected
- real Windows directory junction into sibling project rejected.

Found rehydration first-selection budget could exceed declared budget.
Fixed remaining-byte clipping including multibyte UTF-8.

State effect:
- context plane earned stronger resource and project-scope invariants.

---

## Phase 19 — Architectural Mechanism Quarry imported from Skill thread

### USER / SKILL THREAD
Supplied explicit research framing:
- not researching architectures to choose an architecture
- researching mechanisms that sharpen PCMMAD structures already earned.

Donor families:
ECS, holonic, entity/component relations, capability security, effect systems, blackboards, actor/supervisor, self-describing, hypermedia affordances, dynamic service composition, reflective systems, typed-state planning, resource queries, graph/query systems.

Important historical principle from user work:
- higher-order composition does not automatically inherit authority/currentness/warrant/resources/guarantees from parts.

### ASSISTANT
Persisted laws:
**MECHANISM FIRST. REPRESENTATION SECOND.**
**DONOR != AUTHORITY.**
**EMERGENT CAPABILITY IS ALLOWED; EMERGENT AUTHORITY IS NOT.**

Added hostile admission template and REJECT/DEFER/QUARRY/CANDIDATE/EARNED disposition.

State effect:
- architecture research became governed quarry, not architecture shopping.

---

## Phase 20 — Git plane hostile audit

### ASSISTANT / SERVER ACTION
Identified repo-authority flaw:
- Git walks upward from cwd to ancestor repo;
- project directory ≠ exact repository ownership.

Implemented exact `git rev-parse --show-toplevel` grounding for mutations.

Preserved unborn repositories with `head=null`, `unborn=true`.

Mutation postconditions:
- commit: staging must succeed; staged changes must exist; HEAD must advance.
- reset-hard: user target resolved to exact commit before mutation using `--end-of-options`; final HEAD + tracked tree must converge.
- clean: dry-run preview before; execute; dry-run again; no candidates may remain.

Compatibility tension:
- first strict read implementation broke old non-repo `git.status` expectation.
- resolved by keeping read operations as grounded negative envelopes (`repo_grounded=false`) while mutations fail closed.

Focused hostile + historical tests passed at the time.

State effect:
- Git became exact-root scoped with postcondition verification.

---

## Phase 21 — Continuity failure discovered

### USER
Asked:
“Have you kept the SOP REQUIRED continuity planes and docs etc up to date for this project? If not I need a FULL AND COMPLETE update- the threads full so I need this to survive 1:1 for a new thread”

### ASSISTANT / AUDIT
Switched mode to CHECKPOINT / RECOVERY.

Project inspection found:
- `state/current`, `state/next_steps`, `state/doctrine_snapshot`, `state/revisit_ledger`, `state/trace_matrix` existed only as empty directories.
- `continuity/live_shadow` and `continuity/design_thread_stream` also existed only as empty directories.
- project store reported no manifest and no ledger.

This means detailed ad-hoc reports had been kept current but SOP-required continuity instruments had NOT been maintained.

State effect:
- continuity noncompliance explicitly acknowledged; broad build work halted.

---

## Phase 22 — Fresh checkpoint reveals stale green claim

### ASSISTANT / SERVER ACTION
Ran current V30 suite as part of recovery rather than trusting previous reports.

Fresh truth:
- 182 tests collected
- V30 registry: 99 native tools / 16 families
- full suite currently RED
- 7 failures, all `tests/test_hud_bound_approval.py`
- one intentional/conditional Windows symlink-privilege skip.

Seven failing tests:
1. `test_authority_must_be_object`
2. `test_batch_unknown_tool_fails_closed`
3. `test_batch_uses_effective_approval_and_strips_nested_authority`
4. `test_exact_explicit_authority_envelope_is_forwarded_separately`
5. `test_initial_dispatch_forwards_no_synthetic_authority_and_strips_embedded_smuggling`
6. `test_legacy_approve_bit_is_rejected_before_receiver_call`
7. `test_meta_advertises_runtime_bound_challenge_model`

Observed common symptom:
- HUD test client gets HTTP 421 where expected status is 200/400/403/409.

This supersedes earlier full-suite-green statements.

Live health snapshot separately showed:
- server online
- scheduler alive
- E:\new pc roots
- 16 families
- live family counts summing to 96 tools
- 30 imported actions are explicitly only compact frontend ceiling.

State effect:
- HUD bound-approval integration became immediate blocker.
- live vs V30 divergence now explicitly captured.

---

## Phase 23 — Continuity reconstruction / checkpoint

### ASSISTANT / SERVER ACTION
Created registered state artifacts through project artifact store:
- Current State
- Next Steps
- Doctrine Snapshot
- Revisit Ledger
- Trace Matrix
- Live Shadow
- Design Thread Stream (this file)

Also preparing a dedicated checkpoint and maintenance note.

Key handoff law:
A future thread SHALL rehydrate from these artifacts before widening, and SHALL NOT trust old “green” reports over the fresh current-state blocker.

---

## Recovery-ready immediate resume instruction

When a new thread starts:
1. identify project `PCMMAD_RECEIVER_LAB`.
2. read registered Current State.
3. read Next Steps.
4. read Doctrine Snapshot.
5. read Revisit Ledger.
6. read Trace Matrix.
7. read Live Shadow.
8. read the tail of this Design Thread Stream.
9. verify current tree with focused `tests/test_hud_bound_approval.py` if no newer checkpoint exists.
10. isolate HTTP 421 source before any new architecture work.
11. after focused fix, run entire 182-test suite.
12. update continuity before resuming verification/web/research audit.

Do not start the final schema redesign. Do not live-promote V30. Do not create a new scheduler. Do not treat the Skill/MCP candidate interface as frozen. Do not auto-install the semantic stack as an unrelated side effect.

---

## Append discipline from this point forward

After each meaningful future exchange:
- append user intent/state changes to this stream;
- append assistant action/result;
- update Live Shadow if load-bearing state changes;
- update Current/Next/Doctrine/Revisit/Trace when their semantics change;
- preserve failures and reversals rather than rewriting them away.

---

## Phase 24 — Continuity repair verification completed

### ASSISTANT / SERVER READBACK
After writing the registered continuity set, project readback changed from:
- `manifest_exists=false`
- `ledger_exists=false`

to:
- `manifest_exists=true`
- `ledger_exists=true`.

Manifest now registers:
- Current State
- Next Steps
- Doctrine Snapshot
- Revisit Ledger
- Trace Matrix
- Live Shadow
- Design Thread Stream
- Thread Handoff Checkpoint
- Continuity Repair maintenance note.

A generic project-root rehydration test still failed to prefer continuity and instead selected `.pcmmad_sync_runs`, reporting:
- “No live shadow selected”
- “No design-thread chronology selected.”

This was NOT hidden.

An explicit rehydration test scoped to `path="continuity"` then returned exactly two selected artifacts:
- `continuity.live_shadow`
- `continuity.design_thread_stream`
with `open_seams=[]` and `partial=false`.

### State consequence
- continuity data is durable and registered;
- deterministic new-thread recovery is verified through manifest/checkpoint + explicit continuity subtree rehydration;
- generic root rehydration ranking remains an open tooling defect to fix later;
- Current State and Live Shadow were updated again so they no longer say recovery is still in progress.

### Exact next engineering action
Do not widen work. Reproduce/isolate the HUD bound-approval HTTP 421 failure cluster, repair it, run the focused seven tests, then run the full 182-test suite and immediately update continuity.


---

## Phase 25 — Commander’s Intent transfer hardening

### USER
Asked whether the Commander’s Intent listing would properly transfer, noting that this is historically the continuity element most likely to become spotty or incomplete after thread rollover.

### ASSISTANT / AUDIT
Compared `V30_COMMANDERS_INTENT_AND_WORKLIST.md` against Current State, Doctrine Snapshot, Trace Matrix, Revisit Ledger, and handoff checkpoint.

Finding:
- load-bearing architecture direction was present and redundantly represented;
- however the Commander’s Intent file mixed strong current architecture prose with stale historical status checkboxes.
- examples: an old “full V30 tests green after P0-003 integration” line remained checked even though the current suite is red from seven HUD approval tests; several mechanisms now completed (bounded progress/result retrieval, capability currentness fields, target-bound approval, context audit, Git audit) remained unchecked.

Interpretation:
- direction transfer was stronger than ordinary task continuity, but not yet 1:1-safe because a fresh model could overweight stale checklist state and accidentally reopen or repeat settled engineering choices.

### ASSISTANT / NORMALIZATION
Preserved pre-normalization file at:
`V30_WORKING\PCMMAD_receiver\reports\_history\V30_COMMANDERS_INTENT_AND_WORKLIST_PRE_2026-09-05_CONTINUITY_NORMALIZATION.md`
SHA-256:
`3340c9fbe75e1dc9a765e00752a381cca925f4f34c731d8d034401aa7faabb92`

Rewrote the active Commander’s Intent into a current three-layer authority:
1. desired end-state / engineering direction;
2. locked architecture constraints, placement laws, anti-regressions, sequencing locks, scars;
3. current verified campaign frontier and exact blocker.

Added/strengthened load-bearing direction that had previously been scattered or implicit:
- local-first/thread-life doctrine;
- full R4.4 supporting machinery (Attention Reservoir, Semantic Helix, OARR, Loop+, CSC) as functional obligations;
- Runtime/adapter/OBE/model/project-chat placement law;
- “same machine truth, different ergonomics” for HUD and AI;
- skinny/lazy typed MCP projection hypothesis without freezing vocabulary;
- capability currentness/effect/authority contract direction;
- composite requalification and emergent-capability-vs-authority law;
- exact async/process ownership anti-regressions;
- continuity as an engineering plane;
- final schema redesign sequencing lock;
- fresh-thread anti-regression list;
- exact current HUD HTTP 421 blocker and resume path.

Active normalized file:
`V30_WORKING\PCMMAD_receiver\reports\V30_COMMANDERS_INTENT_AND_WORKLIST.md`
SHA-256:
`b88604bc23a0ec2b523a4cf98640f3470c970d409dc7e1fa287dcca905a0d345`

Registered manifest checkpoint:
`checkpoints\COMMANDERS_INTENT_CURRENT.md`
with the same SHA-256.

Current State was updated so fresh-thread ingress explicitly reads Commander’s Intent immediately after Current State and before Next Steps/Doctrine.
Trace Matrix now marks Commander’s Intent as load-bearing architecture-direction authority.
Live Shadow fresh-thread ingress now includes the same ordering.

### State consequence
Commander’s Intent is no longer merely a useful report. It is a registered handoff authority with current status, explicit anti-regressions, and direct fresh-thread ingress ordering.

Any future change to architecture direction, mechanism placement, sequencing lock, or major anti-regression requires explicit Commander’s Intent update/supersession rather than silent drift.


---

## Phase 26 — HUD HTTP 421 blocker isolated and closed

### ASSISTANT / RE-ENTRY
Re-entered from registered Current State → Commander’s Intent → explicit continuity shadow pair as required by the repaired handoff.

Focused reproduction:
- `tests/test_hud_bound_approval.py`
- 8 collected
- 7 failures / 1 pass
- every failing route returned HTTP 421 before expected approval/meta behavior.

### PROBE / FAILURE ISOLATION
Searched all HUD 421 emitters and found a single source:
`operator_hud/server.py` DNS-rebinding Host guard.

Direct Flask test-client probe showed:
- effective Host: `localhost`
- no explicit port
- HUD trusted set contained only `localhost:5090`, `127.0.0.1:5090`, `[::1]:5090`.

Therefore the bound-approval tests were never reaching bound-approval logic.

Classification:
**pre-route Host-guard representation mismatch**, not Runtime approval-authority defect.

### DERIVATION
Security invariant to preserve:
- only exact loopback host identities are lawful for the local HUD;
- foreign/rebinding hostnames must fail closed;
- explicitly wrong ports must fail closed;
- omitted port on an otherwise exact loopback identity is a representation variant, not a different trust identity.

### BUILD / EMBODIMENT
Changed HUD trusted-host set to accept exact:
- `localhost`
- `127.0.0.1`
- `[::1]`
- plus those same identities with configured HUD port.

Did NOT add wildcard/pattern hostname trust.
Did NOT change Runtime approval semantics.

Added `tests/test_hud_host_guard.py` covering:
- bare localhost accepted
- bare IPv4 loopback accepted
- configured-port loopback accepted
- foreign hostname rejected 421
- loopback with wrong explicit port rejected 421.

Code identities after repair:
- `operator_hud/server.py` SHA-256 `82d9a12961bcede6986002dfd11a80a2910c6bafb1675fe5a10e20fb74b72a42`
- `tests/test_hud_host_guard.py` SHA-256 `4bc76af3d9e8d5052b060a6b8f31e881d40463d52e3b6f0392071dc4bb7734b7`.

### VERIFY
Focused hostile/compatibility cluster:
- `test_hud_host_guard.py`: 5/5 PASS
- `test_hud_bound_approval.py`: 8/8 PASS
- combined: **13/13 PASS**.

Full V30 suite:
- **187 tests collected**
- full suite **GREEN**
- only existing conditional Windows symlink-privilege skip remains.

### STATE CONSEQUENCE
- HUD bound-approval Runtime model remains intact and qualified.
- HTTP 421 blocker is closed.
- Current State / Next Steps / Revisit / Trace / Live Shadow / Commander’s Intent were advanced to the next frontier.
- current ordered audit frontier is now:
  1. verification command plane
  2. web/network boundary
  3. research plane.


---

## Phase 27 — Verification plane and shared sync subprocess boundedness qualified

### AUDIT
`verify.gates` was already correctly classified as high-risk, approval-required arbitrary execution and was proven capable of mutating project state. Its cwd uses canonical `safe_project_cwd()` → resolved-root `scope_check()`, so project scope was already structurally sound.

Two remaining defects were found:
1. shared `run_subprocess_envelope()` used `capture_output=True`, materializing all child output in Python memory before slicing to configured response limits;
2. `verify.gates` had a generic object schema, no hard gate-count ceiling, and did not explicitly state that `passed` meant declared command exit success rather than arbitrary semantic truth.

### EMBODIMENT — shared subprocess
Replaced heap-first capture with local temporary stdout/stderr spooling:
- child writes directly to temp files;
- only requested bounded prefix is read into response;
- truncation derived from capture file size;
- shell remains disabled;
- stdin is DEVNULL;
- timeout kills/waits child and returns typed TIMEOUT;
- temp capture directory cleaned after receipt.

Hostile test generated multi-megabyte stdout/stderr while returning only 4 KiB/3 KiB.

### EMBODIMENT — verify.gates
- max synchronous gates: 32;
- timeout_each remains capped at 600s;
- typed nested input/output schema;
- per-gate `evidence_scope=declared_gate_command_exit`;
- aggregate `evidence_scope=declared_gate_command_exit_only`;
- aggregate `semantic_claim_verified=false`;
- requested/attempted/stopped-early/duration/timeout fields;
- effect traits now advertise project scope, bounded output, bounded gate count, and command-exit-only evidence semantics.

### VERIFY
- shared subprocess hostile tests: 3/3 PASS;
- cross-plane subprocess/Git/verifier/env regression cluster: 14/14 PASS;
- verification contract/effect/subprocess cluster: 10/10 PASS;
- full V30 suite GREEN across **195 collected tests**, with only existing conditional Windows symlink-privilege skip.

### CLAIM CEILING
`verify.gates` proves the exit/result behavior of the declared gate commands. A zero exit code is evidence for that gate execution; it does not automatically prove an arbitrary higher-order semantic claim unless the caller/workflow separately defines and qualifies that claim.

### STATE CONSEQUENCE
Verification plane is qualified on current scope.
Current frontier advances to web/network target authority and SSRF/redirect/DNS/bounded-response semantics, then research.


---

## Phase 28 — Continuity/tree reconciliation recovered already-earned A-019..A-023 planes

### DISCOVERY
While resuming the web frontier, bounded audit-ledger read showed that `V30_ALL_PLANE_TOOL_AUDIT.md` already contained later verified slices that registered Current/Next still described as open:
- A-019 research bounded control/cache/type currentness
- A-020 protocol non-initializing observation/current GENESIS doctrine
- A-021 SOP ingestion integrity/currentness/concurrency/resource slice
- A-022 transfer authority/scope/currentness/integrity slice
- A-023 plugin transactional reload/currentness slice.

This was treated as a continuity/state-promotion discrepancy, not as proof that the reports were automatically authoritative.

### VERIFY CURRENT TREE
Ran the exact focused suites against the current V30 working tree:
- `test_research_bounded_control.py` — 6/6
- `test_protocol_read_nonmutating.py` — 5/5
- `test_protocol_runtime.py` — 8/8
- `test_sop_ingest_integrity.py` — 6/6
- `test_sop_effect_contract.py` — 3/3
- `test_transfer_plane_hostile.py` — 10/10
- `test_plugin_transactional_reload.py` — 7/7

Combined reconciliation: **45/45 PASS**.

### PROMOTED CURRENT SURVIVORS
Research:
- bounded/thread-safe cache, streamed HTTP cap, wall-budgeted hunt, structured partial/query errors, typed result/starmap fixes.

Protocol:
- status/guard reads do not initialize protocol state; absent remains absent; current future GENESIS carries AXIOM-01 + full build metabolism without rewriting historical ledgers.

SOP ingestion:
- source-currentness and exact chunk SHA/token semantics, idempotent unacked replay, per-corpus in-process lock, package preflight ceilings, streaming archive hash, final proceed guard with explicit registered/verified/current/started/complete/proceed distinctions.

Transfer:
- exact project scope, API-key protected HTTP routes, mutating adapter delegates to native authority dispatch, ticket-manifest integrity, destination identity binding, exact chunk SHA, full-hash/atomic finalize, hostile concurrency/expiry/tamper checks.

Plugin:
- isolated transactional candidate registry, rollback, collision rejection, stale-tool cleanup, source SHA/currentness, stable bookkeeping references, reload/registry locks, generation/contract digest/changed receipts.

### CLAIM CEILINGS PRESERVED
- SOP does not yet claim true streaming member/chunk inspection or multi-process locking.
- transfer export tickets do not claim immutable source snapshots.
- plugin transaction does not sandbox trusted in-process plugin Python.

### CONTINUITY SCAR
This was a different continuity failure mode from the earlier empty-state problem: the continuity instruments existed and were updated, but a detailed audit ledger had advanced farther than the registered Current/Next promotion state.

New rule reinforced:
After an audit slice is verified, promote its status into Current/Next/Trace immediately. At re-entry, compare the audit tail against continuity before reopening a plane.

### STATE CONSEQUENCE
Current/Next/Revisit/Trace/Live Shadow/Commander’s Intent were reconciled. Active frontier is now only the **remaining web.fetch contract/currentness gaps**, not basic SSRF or already-qualified research/protocol/SOP/transfer/plugin work.


---

## Phase 29 — Web public-read contract/currentness slice qualified

### BASELINE
A-018 had already earned the public-network security boundary:
- http/https only;
- pre-request DNS validation;
- all resolved addresses must be globally routable;
- mixed public/private answers rejected;
- redirect target revalidated before follow;
- final URL revalidated;
- body physically bounded with `max_bytes + 1` probe;
- explicit DNS rebinding residual.

### REMAINING GAPS
- URL credentials/userinfo were not explicitly rejected;
- URL/User-Agent lengths and control/header-injection characters were not Runtime-contract bounded;
- redirect ceiling was implicit urllib behavior;
- machine input/output schema remained generic;
- response status and DNS validation timestamp were absent;
- raw body could be complete while 200k text distillation silently truncated without separate evidence.

### EMBODIMENT
- URL max 8192 chars; URL control chars rejected.
- embedded userinfo/credentials rejected before DNS/follow with `WEB_CREDENTIALS_FORBIDDEN`.
- User-Agent max 512 chars; control/newline chars rejected.
- redirect ceiling explicit at 5.
- DNS receipts include validation timestamp.
- successful HTTP status exposed.
- separate `truncated` vs `text_truncated` and explicit text limit.
- typed input/output schema and effect traits for these guarantees.
- DNS rebinding TOCTOU residual retained; no socket-pinning claim.

### VERIFY
- prior web SSRF/network suite: 6/6 PASS.
- new web contract/currentness suite: 8/8 PASS.
- combined: **14/14 PASS**.
- full V30 suite GREEN across **203 collected tests** with only existing conditional Windows symlink-privilege skip.

### STATE CONSEQUENCE
Web public-read scope is qualified. Active frontier advances to the continuity/context rehydration defects already observed during this thread rollover: root-level internal-noise ranking and stale index-cache excerpts.


---

## Phase 30 — ICF-CS v1.0 adopted and embodied in V30 rehydration

### USER
Provided the generic **Intent–Constraint–Frontier Continuity Standard — ICF-CS v1.0** and explicitly instructed this project to use the solution while ignoring unrelated project-specific details.

Core laws imported:
- `DIRECTION != CONSTRAINTS != FRONTIER != HISTORY`
- `HISTORICAL_HANDOFF != CURRENT_INGRESS`
- `DONOR != AUTHORITY`
- `RECENT_TIMESTAMP != CURRENT_AUTHORITY`
- `STALE_GREEN != CURRENT_EVIDENCE`
- conflict grammar: `CONFLICT → RECOVERY/AUDIT → LOCALIZE → REPAIR/SUPERSEDE → READBACK → RESUME`.

### PRE-MUTATION INSPECTION
Verified the previously interrupted `context_engine.py` mutation had not landed.
Registered continuity manifest was intact.

Persisted generic doctrine:
- `state/doctrine_snapshot/INTENT_CONSTRAINT_FRONTIER_CONTINUITY_STANDARD.md`
- SHA-256 `0bd3bf72203dbf65d93dd68b66cf1502b64e304ec7298ae27068afb7eb7e06f0`.

Persisted deterministic project ingress:
- `checkpoints/ICF_CS_CURRENT.md`
- SHA-256 `b2206342e04d7d6185f8b804b6be5ecb505b3675e4958decd39eda37899e03cc`.

### DERIVATION
Source inspection proved four continuity defects:
1. recursive search treated `.pcmmad_sync_runs` and other transient/internal trees as normal evidence;
2. index cache validity was TTL-only and could return stale excerpts after a source artifact changed;
3. Doctrine/Revisit/Trace were classified but omitted from rehydration priority;
4. Current/Intent/continuity anchors were selected only when lexical topic matching happened to find them.

### EMBODIMENT
V30 `context_engine.py` now:
- distinguishes authority classes for Current, ICF Standard, Intent, Next, Doctrine, Revisit, Trace, Live Shadow, DTS;
- seeds those roles in ICF cold-start order before topic evidence;
- reserves only a bounded share of the caller budget for authority anchors;
- filters seeded paths out of topic selection so authority files are not duplicated;
- excludes transient/internal recursive search noise by default, including `.pcmmad_sync_runs`, VCS internals, caches, venvs, `node_modules`, `_v30_backups`, `.pcmmad_tmp_*`, and generic `.tmp` files;
- keeps explicit targeting of internal paths available;
- binds index-cache validity to canonical resolved path + size + `mtime_ns`, with cache state under an RLock;
- exposes cache `source_currentness` in the typed wire model;
- returns ICF-CS version/selected authority classes/cold-start law in rehydration receipts.

### HOSTILE TESTS
New `test_icf_cs_rehydration.py` covers:
- transient sync-log exclusion;
- explicit internal-path access preserved;
- same-size file rewrite invalidates cache when `mtime_ns` changes;
- all nine ICF authority roles seeded before transient-topic noise;
- Live Shadow update visible on immediate next rehydrate;
- Doctrine/Revisit/Trace are first-class priorities;
- no duplicate paths and no `.pcmmad_tmp_*` scratch selection.

Focused ICF/context cluster:
- 20 PASS / 1 conditional Windows symlink-privilege skip.

Complete V30 suite:
- **209 collected tests**
- GREEN
- only the existing conditional Windows symlink-privilege skip.

### ACTUAL PROJECT READBACK
Direct V30 root rehydration against `PCMMAD_RECEIVER_LAB` returned, in order:
1. `state.current`
2. `continuity.icf_standard`
3. `continuity.intent`
4. `state.next_steps`
5. `state.doctrine_snapshot`
6. `state.revisit_ledger`
7. `state.trace_matrix`
8. `continuity.live_shadow`
9. `continuity.design_thread_stream`
then topic-specific evidence.

Receipt facts:
- all nine classes selected;
- `unique_paths=true`;
- `open_seams=[]`;
- no sync/scratch noise;
- cache currentness = `canonical_path+size+mtime_ns`.

Twenty stale root-level `.pcmmad_tmp_*` staging files from earlier artifact updates were found and deleted.

### CLAIM CEILING
- this behavior is V30-working-tree truth, not live-receiver promotion;
- path+size+mtime_ns is practical source-currentness, not cryptographic content identity.

### STATE CONSEQUENCE
Current State / Next Steps / Doctrine / Revisit / Trace / Live Shadow / Commander’s Intent were updated to ICF-CS semantics.
The old HUD-421 “active challenge” text was explicitly removed from Doctrine as stale.

Active Frontier is now **remaining Commander’s Intent/tree/audit reconciliation before selecting another implementation plane**.


---

## Phase 31 — Native capability effect contracts completed across current 99-tool registry

### RECONCILIATION / CENSUS
After ICF-CS adoption, the remaining Commander checklist was compared against current Runtime evidence rather than trusted as a blind queue.

Fresh registry census found:
- 99 native tools / 16 families;
- 28 capabilities still had `side_effect_class="unknown"` and empty `effect_traits`;
- 67 generic input schemas / 97 generic output schemas;
- 52 effective approval-required capabilities;
- 47 `mutating=true` capabilities.

The generic schema counts were explicitly separated from effect truth and **did not trigger final schema redesign**, which remains locked deferred.

### SOURCE-DERIVED CLASSIFICATION
The 28 ambiguous cards were inspected by implementation mechanism rather than tool name.

Key distinctions:
- browser health/sessions/pages/content = `external_read` via browser bridge/network;
- browser screenshot = `external_interaction`, retaining possible external artifact creation;
- `lab.health` = `read_probe`, because it reads Runtime/plugin/cache state and probes browser bridge health over network;
- `semantic.monster.health` = `read_probe`, because it reads/hashes resources and spawns bounded Python dependency probes;
- project search/rehydration = `read_cache`, because they read project state and write only ephemeral index cache; rehydrate also advertises ICF authority awareness;
- filesystem/doctrine/project/model/archive/session/reflexion observation = explicit local `read` with scope/boundedness traits;
- HUD status = process/service `read_probe`;
- receiver restart status = persisted receipt/service-state `read`.

Eight registration modules were updated; behavior/policy was not intentionally widened.
Backups live under:
`baseline/pcmmad_receiver/_v30_backups/AUDIT_EFFECT_CLASSIFICATION_V1`.

### HOSTILE INVARIANT
Added `tests/test_capability_effect_completion.py` enforcing:
- zero unknown/empty native effect contracts;
- external browser reads remain distinct from pure reads;
- screenshot preserves external-artifact claim ceiling;
- context search/rehydrate admit ephemeral cache effects;
- health/dependency probes are not mislabeled reads;
- local read families remain explicit.

Focused classification/regression cluster: **34/34 PASS**.

Full V30 suite after mutation:
- **216 collected tests**
- GREEN
- only the existing conditional Windows symlink-privilege skip.

Fresh registry readback:
- unknown_side_effect_count = 0
- empty_effect_traits_count = 0
- side-effect classes now cover read / read_cache / read_probe / read_reconcile / external_read / external_interaction / execution / mutation / ephemeral_mutation / runtime_mutation.

### CLAIM CEILING
Effect classification is complete for the current 99-tool registry.
Automatic effect-trait → policy inference remains unearned.
The 67 generic input / 97 generic output schemas are separate projection/schema evidence and do not authorize premature final schema redesign.

### STATE CONSEQUENCE
Commander’s Intent effect-classification item is now earned-current.
Active Frontier advances to **capability availability/currentness vs schema/runtime/policy/imported-adapter parity**.


---

## Phase 32 — Qualified ICF-CS additive overlay merged; stale Frontier conflict repaired

### USER / SOURCE PACKAGE
Uploaded:
`RAHL_ENGINEERING_CANONICAL_SOP_R4_4_ICF_CS_V1_0_ADDENDUM_2026-09-05.zip`.

The package self-demotes unless exact qualification passes, so it was audited before doctrine promotion.

### EXACT-BYTE QUALIFICATION
Qualified source package facts:
- outer ZIP SHA-256 `51ed7f424dff7c67534f7e53e8a7c10ebd93bf33ea575eea49dc3f05c24a92a9`
- package bytes `2,546,098`
- manifest SHA `953ca5683d16876dac573f3ad5c367c5b9c31af5726d7f92c676719c609a36b8`
- semantic-read ledger SHA `38eca2fa3d8cfae563bfa5d8225156e61fb4413d5600f52fc4e1db3852271c2b`
- exact sealed R4.4 parent SHA `04f3e94efe8c901cc83a12a9c8531be8a9bb350728b8f9eba53db0fd082b3bbc`.

Qualification evidence:
- outer ZIP CRC PASS;
- exact parent hash + parent CRC PASS;
- manifest membership/hash/size PASS;
- project-agnostic active surface PASS;
- semantic bindings/anti-bindings PASS;
- machine contract PASS;
- semantic-read ledger PASS;
- all load-bearing readable members linearly read on exact candidate bytes during this merge session;
- hostile suite **22/22 mutants rejected**, zero unexpected passes;
- clean-extraction verifier PASS;
- deterministic rebuild produced a byte-for-byte identical ZIP with the same outer SHA.

Disposition:
**ACTIVE_BINDING_ADDITIVE_DOCTRINE_ABOVE_SEALED_R4_4**, within continuity/process-control scope only.

### EXACT LOCAL REGISTRATION
The first normal text-store update normalized Windows line endings and therefore changed the standard hash. That normalized projection was immediately superseded rather than misrepresented as exact source bytes.

Byte-exact package members are now registered locally:
- human standard SHA `b22b6ba65992bf8e235df9acfb044da772282ae3820a1359af3b5309d1e1051b`
- machine contract SHA `527e4fa0926449155a8aa548656b3debc5292262f8cfaab0ca3f0470e7771f5a`
- claim ceiling SHA `079a523d017438cfd9057d5bfe78b4bf47e4550c20fc9bbd3840cbf6d66f245a`.

Registered navigation/qualification surfaces:
- `state/doctrine_snapshot/CURRENT_CANONICAL_SOP_POINTER.md`
- `checkpoints/ICF_CS_ADDENDUM_QUALIFICATION_RECEIPT.md`
- updated `checkpoints/ICF_CS_CURRENT.md`.

### DOCTRINE DELTAS FROM QUALIFIED OVERLAY
The qualified overlay is stricter than the earlier local draft:
- cold start is version-agnostic and uses `CURRENT CANONICAL SOP`, not a frozen R4.x identifier;
- `CURRENT_INGRESS_POINTER != CURRENT_STATE_PROOF` is binding;
- continuity-adjacent evaluation/steering data gets provenance/currentness/authority hygiene;
- binding laws include expected-label separation, benchmark authority ceiling, format-vs-semantic failure separation, agreement-vs-authority-fidelity separation, intent-vs-factual-truth, continuity-map-vs-live-evidence, remembered-summary-vs-source-contact, and summary-fidelity-vs-source-completeness.

### ICF CONFLICT FOUND
Immediately applying the qualified standard exposed a stale Frontier:
- Current/Next/Live/Commander still pointed toward capability availability/currentness work;
- but the V30 working tree already contained a later compact OpenAPI authority-envelope mutation made after the last full-suite run.

The 216-test green result therefore applied to the immediately preceding bytes, not the current compact-schema bytes.

Classification:
`STALE_GREEN != CURRENT_EVIDENCE`.

### REPAIR
Current State, Next Steps, Doctrine, Revisit, Trace, Live Shadow, and Commander’s Intent were repaired to the same current truth:
- compact 30-operation OpenAPI template has been edited to project separate bound authority instead of legacy inline boolean approval;
- that edit is **BUILD / UNVERIFIED**;
- availability/currentness work is paused;
- exact immediate action is focused adapter parity/security qualification, then fresh full suite, then promote/demote.

### STATE CONSEQUENCE
Qualified ICF-CS is now controlling continuity doctrine above sealed R4.4.
The material disagreement was localized and repaired before further implementation work, exactly following:
`CONFLICT -> RECOVERY/AUDIT -> LOCALIZE -> REPAIR/SUPERSEDE -> READBACK -> RESUME`.


---

## Phase 33 — Compact OpenAPI bound-authority projection qualified and promoted

### FRONTIER ENTRY
Qualified ICF-CS had demoted the previous 216-test green because the compact OpenAPI template was edited afterward. No further implementation work was allowed until the adapter patch was qualified or rolled back.

### CURRENT TEMPLATE READBACK
Template:
`baseline/pcmmad_receiver/pcmmad_lab_action_schema_v10_3_pcmmad_native_protocol_compact_30_router.json`

Pre-test current SHA:
`ae1459582f515395ca58905133d643875ef1ebfd168ce5b36bcc665077c1433e`.

Readback confirmed:
- exactly 30 operations;
- dispatch top-level `authority` references `BoundApprovalAuthority`;
- batch step carries separate per-step `authority`;
- payload descriptions state arguments only and reject authority metadata placement;
- `BoundApprovalAuthority` requires `approval_handle` + `permit`, supports optional operator/provenance labels, and rejects extra fields.

### HOSTILE / PARITY REGRESSION
Added:
`tests/test_compact_schema_authority_parity.py`
SHA `6d54a90aa020e8c958beb0e1356705544849f2dae94d13ed1b25a27802806f51`.

It proves:
- compact surface remains exactly 30 operations with unique operation IDs;
- dispatch and batch authority are separate from capability arguments;
- no compact schema description/example teaches legacy inline boolean approval;
- authority schema matches Runtime retry shape;
- endpoint descriptions preserve bound-authority and non-atomic batch semantics;
- restart controller still publishes this exact compact template to `pcmmad_lab_action_schema_ACTIVE.json`.

Focused cluster included:
- compact parity test;
- native bound approval dispatch;
- approval authority integrity/replay/currentness;
- HUD approval forwarding/smuggling rejection;
- transfer HTTP→native authority delegation;
- protocol compact-surface non-expansion;
- schema-authority constraint pipeline.

Result: **59/59 PASS**.

### FULL VERIFY
Complete V30 suite on current schema bytes:
- **223 collected tests**
- GREEN
- only the existing conditional Windows symlink-privilege skip.

Schema SHA remained:
`ae1459582f515395ca58905133d643875ef1ebfd168ce5b36bcc665077c1433e`.

### PROMOTION
The compact adapter authority patch moved from BUILD/UNVERIFIED to **EARNED V30 CURRENT SCOPE**.

The prior 216-test green is retained as historical evidence for preceding bytes and is superseded as current evidence by the 223-test green.

### CLAIM CEILING
- this is a compatibility/security correction to the inherited 30-operation adapter, not final schema redesign;
- V30 working-tree schema is not live imported schema until explicit V30 promotion/restart;
- Runtime legacy inline approval remains transitional when explicitly enabled, but the compact adapter no longer advertises or depends on it.

### STATE CONSEQUENCE
Current/Next/Doctrine/Revisit/Trace/Live Shadow/Commander/ICF current ingress were advanced to the 223-test green state.
Active Frontier returns to **native capability availability/currentness**.


---

## Phase 34 — Native capability availability/currentness qualified and promoted

### SOP RE-ENTRY
User explicitly instructed continuation from the prior boundary under the SOP.

Re-entry followed Current → ICF-CS → current canonical SOP surfaces → Live Shadow/DTS → fresh local readback.

The live/root `rehydrateProjectContext` path reproduced the older known defect by selecting `.pcmmad_sync_runs` noise and reporting missing shadow surfaces. This was **not** treated as current V30 truth. Explicit `path="continuity"` rehydration selected both Live Shadow and DTS with no seams. This confirms live receiver context tooling remains behind the qualified V30 working tree.

### STARTING BUILD STATE
Availability/currentness mechanism existed in source but was unqualified.
Previous 223-test green applied to the immediately preceding bytes only.

Touched modules:
- `control_plane_models.py`
- `lab_tools.py`
- `lab_tools_browser.py`
- `lab_tools_semantic.py`
- new `tests/test_capability_availability_contract.py`.

### CORE DERIVATION
Binding distinction:
`REGISTRATION != CAPABILITY_AVAILABILITY != TARGET_HEALTH`

Rejected design:
- hidden provider/health probes during ordinary capability listing/discovery.

Earned design:
- static probe-free availability contract on cards;
- resident vs dynamic modes;
- explicit bounded currentness reads only when requested;
- dynamic provider identity/scope;
- shared provider probes deduplicated once per request;
- provider exceptions fail to UNKNOWN, never fake green;
- availability semantics affect contract digest; transient probe results do not.

### PROVIDERS
Browser:
- all browser/procedure capabilities share dynamic provider `browser_bridge`;
- one bounded bridge `/health` probe serves all requested browser capabilities in a single availability call.

Semantic:
- `semantic.monster.search` uses dynamic provider `semantic.monster.default_runtime`;
- claim scope is explicitly default runtime only; per-call runtime/path overrides may change outcome;
- `semantic.monster.health` remains resident/callable as the diagnostic surface.

New native capability:
`lab.capabilities.availability`
- max 32 requested tool names;
- unknown tools fail closed;
- does not invoke target capabilities;
- returns bounded provider/currentness evidence.

### HOSTILE QUALIFICATION
Compile + dedicated suite:
- 9/9 PASS.

One attempted adjacent regression command used a nonexistent guessed filename `tests/test_browser_contracts.py` and failed before collecting tests (pytest return code 4). No implementation failure occurred. Test names were then read from the actual tree before retry.

Correct adjacent currentness/authority cluster:
- effect completion/traits
- semantic runtime/doctrine
- plugin transactional reload
- approval authority/bound dispatch
- HUD bound approval
- MCP manifest contract
- lab health optional browser
- availability contract

Result: **60/60 PASS**.

### DIRECT CURRENT PROVIDER READBACK
Fresh V30 registry:
- **100 tools / 16 families**.

Availability request for:
- `browser.health`
- `browser.pages.list`
- `browser.content`
- `semantic.monster.search`
- `lab.health`

Result:
- exactly **2 provider probes** for 5 capabilities;
- three browser tools shared one `browser_bridge` probe;
- semantic search used one default-runtime probe;
- resident `lab.health` used no provider probe;
- browser bridge current status `unavailable`, blocker `browser_bridge_unavailable`;
- semantic default runtime current status `unavailable`, blocker `no_qualified_python_runtime`;
- resident `lab.health` current availability `available`, basis `registered_handler`.

This directly proves provider/target health is not collapsed into resident capability callability.

### FULL VERIFY
Complete V30 suite on current availability bytes:
- **232 collected tests**
- GREEN
- only the existing conditional Windows symlink-privilege skip.

Current identities:
- `control_plane_models.py` SHA `5644bd4e821bdf5ebaa3f102aff580f70c9d09ac396434eeb35690b96c2a28ce`
- `lab_tools.py` SHA `f27b4029ae9377217f479f4888dc570eca06cea60c5251b3f918fee107497fbf`
- `lab_tools_browser.py` SHA `9a592a039e780ff78a6e882aa222b17fb6dce83fd2e549fc9e56b2480171ca71`
- `lab_tools_semantic.py` SHA `205a21b30373a78f62ea2872c03d4dc9bf429ea83b8d99ecb8e62933da6fe6f0`
- availability regression SHA `e37711ad26d7264e1d9efa44742909e71a8ff9c19cdb57fdb0e1f1552ef1a92a`.

### PROMOTION / CLAIM CEILINGS
A-028 promoted for current V30 scope.

Claim ceilings:
- current dynamic provider coverage is evidence-backed and narrow: browser bridge + semantic default search runtime;
- resident availability proves handler dispatchability, not arbitrary argument success or managed-target health;
- semantic result is default-runtime scoped;
- plugin capabilities remain resident unless future evidence earns dynamic providers;
- automatic availability/effect → policy inference remains unearned;
- live receiver remains unpromoted and does not expose this V30 contract.

### STATE CONSEQUENCE
Current / Next / Doctrine / Revisit / Trace / Live Shadow / Commander / ICF Current were promoted to 100 tools / 232-test green.

Active Frontier moves to **adapter/projection parity against native effect + availability + authority + currentness contracts**, while final schema redesign remains locked deferred.


---

## Phase 35 — First durable Git publication established and remotely verified

### USER
Supplied new repository:
`https://github.com/SEng-Kitathas/AI-Server-InfrA.git`

Instruction: after completing the current qualified step, push pursuant to SOP.

### PRE-PUBLICATION AUTHORITY CHECK
Neither project root nor `V30_WORKING/PCMMAD_receiver` had an existing Git repository.
Remote `git ls-remote` succeeded with no refs, consistent with an empty repository.

Exact selected Git root:
`V30_WORKING/PCMMAD_receiver`

Reason:
that directory is the V30 publishable Runtime body; project-store continuity/checkpoint machinery remains outside it and must not be conflated with source publication.

### PUBLICATION HYGIENE
Preflight:
- no source file >10 MiB;
- no obvious secret-like filenames;
- bounded credential-pattern scan returned no matches;
- `.worker_selftest/` identified as ephemeral;
- `.pcmmad_sync_runs/` identified as execution scratch;
- `baseline/pcmmad_receiver/_v30_backups/` and other `**/_v30_backups/` identified as local mutation backups;
- `*.bak.*` identified as local historical copies;
- `operator_hud/runtime/` identified as runtime journal state.

These were excluded from publication.

Git emitted Windows line-ending normalization warnings during the first staging attempt. Because the project carries byte hashes/manifests, automatic text normalization was treated as a lineage defect risk.

Added `.gitattributes`:
`* -text`

This preserves exact project bytes rather than silently normalizing LF/CRLF on commit/checkout.

Final staged tree after reset/re-stage:
- 312 source/evidence files;
- zero forbidden local backup/selftest/sync/runtime-journal paths;
- byte policy `text: unset` confirmed on representative source/manifests.

### LOCAL COMMIT
Branch:
`main`

Root commit:
`2d6549f01327c7b3250cc863d64cc3eca18417e3`

Tree:
`fb0ef53683feeb02210b86c9ae84f5d56600fd81`

Subject:
`Promote PCMMAD Receiver V30 through A-028 availability currentness`

Commit message records the 100-tool/16-family, availability/currentness, 9/9 + 60/60 + 232-test qualification basis.

### PUSH / REMOTE READBACK
Push:
`main -> origin/main`

Independent remote readback:
`git ls-remote origin refs/heads/main`
returned:
`2d6549f01327c7b3250cc863d64cc3eca18417e3 refs/heads/main`.

Local HEAD after push:
`2d6549f01327c7b3250cc863d64cc3eca18417e3`.

Upstream:
`origin/main`.

Working tree:
clean (`## main...origin/main`).

### AUTHORITY LAW
**GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION.**

The repository is durable source/publication lineage. It does not prove the Desktop live receiver has been replaced, restarted, or brought to V30 parity.

### CONTINUITY
Registered `checkpoints/GIT_PUBLICATION_CURRENT.md` with exact root/remote/commit/tree/hygiene/readback proof.
Current/Next/Doctrine/Revisit/Trace/Live/ICF were updated to the new publication boundary.

Future earned V30 source deltas should follow: verify root → hygiene/secret preflight → appropriate qualification → commit → push → remote-head readback → continuity receipt.


---

## Phase 36 — MCP availability projection parity qualified with live ICF conflict recovery

### FRONTIER ENTRY
After A-028 publication, parity inspection showed one real semantic loss:
- native `/lab/tools` cards carried availability;
- HUD `/api/tools` forwarded those cards unchanged;
- compact OpenAPI `/lab/tools` permitted arbitrary tool-card fields;
- `_mcp_manifest_tool_card()` manually selected fields and omitted `availability`.

### BUILD
`lab_routes.py` was changed so MCP manifest cards preserve native `availability` verbatim.
`tests/test_mcp_manifest_contract.py` was expanded to verify browser/semantic dynamic availability contract preservation and HTTP manifest behavior.

Projection-contract documents were reconciled to current earned Runtime truth: 100 tools, effect classification complete, bound approval embodied, bounded result preview/range embodied, plugin lifecycle/currentness earned, native availability core earned. Final schema redesign remains deferred.

### VERIFY
Focused MCP/availability/effect/compact-schema cluster:
- **27/27 PASS**.

Complete V30 suite:
- **233 collected tests GREEN**
- existing conditional Windows symlink-privilege skip only.

Current code/report identities:
- `lab_routes.py` SHA `f7a499bf62205cf8e001c044b028cd8bbf38aa5873c6cac7e0ae66d3e9263720`
- `test_mcp_manifest_contract.py` SHA `4444bd610ffcfc6f3464905ab254e769fa6d5169f2db199e4aa81bd41e1f4842`
- projection matrix MD SHA `ffe6ad179303290f64d72c921c0bc3b21f015a95bdacf07f99d46788ddf7177a`
- projection matrix JSON SHA `599c336dfa441243d6c6968b750b0f2631cabc3e63102040b66a03e5048d182a`
- compatibility contract SHA `c3f45ec3d57ab46eefffb6bcce937659227ac59a6b8ac75932e9886179b13dfb`.

### INTENTIONAL LOSSINESS CLASSIFICATION
- HUD transport: zero-loss for availability fields; presentation still open.
- Compact OpenAPI `/lab/tools`: permissive validation carries availability but does not strongly enumerate it. Classified as validation/documentation lossiness, not wire truncation; not a trigger for final schema redesign.
- MCP manifest: availability omission was a real semantic loss and is now fixed.

### ICF CONFLICT EVENT
While promoting A-029 continuity, `registerProjectExecutionArtifact` rejected the Current State update because the expected previous SHA no longer matched.

Expected previous SHA:
`351054714e7ac6d23b50bbf18687e531856bfc97f19c032db544d8514b53ece0`

Observed current SHA:
`44d9ddc13b9eb01cd257299dd9b905f78dbd5b266e4fb47bc1cc7af29ad885e4`.

The write was NOT forced.

Manifest/readback showed Current, Next, Live Shadow, and ICF Current had been updated around 20:28 ET to correctly mark the post-publication MCP two-file delta as BUILD / UNVERIFIED. Doctrine/Revisit/Trace/Commander/DTS were unchanged.

This was treated as legitimate currentness repair, not corruption.

Applied qualified conflict grammar:
`CONFLICT -> RECOVERY/AUDIT -> LOCALIZE -> REPAIR/SUPERSEDE -> READBACK -> RESUME`.

A-029 continuity was regenerated from those newer surfaces, preserving the BUILD/UNVERIFIED chronology and superseding it only after the 27/27 + 233-test evidence.

### PROMOTION
A-029 is now EARNED V30 CURRENT SCOPE.

Active Frontier:
- HUD presentation parity for dynamic availability/core-vs-optional health;
- remaining permissive adapter lossiness classification;
- then evidence-ranked next Runtime seam.

Git publication of the A-029 source delta remains the immediate final action for this phase.


---

## Phase 37 — A-029 Git publication closed with remote readback

A-029 source delta was staged as exactly seven tracked files:
- `baseline/pcmmad_receiver/lab_routes.py`
- `tests/test_mcp_manifest_contract.py`
- projection matrix MD/JSON
- adapter compatibility contract
- all-plane audit ledger
- Commander’s Intent source.

No unstaged publishable changes remained.

Commit:
`e777bd4fdcd2ec942f2269903bf8129b53cf33cd`

Tree:
`a9ca60adce87274bc4d02d2017a37b4189755c3f`

Subject:
`Preserve native availability in MCP manifest (A-029)`

Push:
`2d6549f..e777bd4 main -> main`.

Independent remote readback:
`e777bd4fdcd2ec942f2269903bf8129b53cf33cd refs/heads/main`.

Local HEAD matched remote; working tree clean.

`checkpoints/GIT_PUBLICATION_CURRENT.md` was updated to make A-029 the current source publication while retaining A-028 history.

Final authority ceiling remains:
`GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION`.

Current Frontier after publication:
HUD presentation parity for dynamic capability availability and core-vs-optional health, while HUD remains a pure consumer of Runtime truth.


---

## Phase 38 — HUD availability/core-vs-optional presentation qualified

### FRONTIER ENTRY
After A-029 publication, HUD presentation parity was the active Frontier.

Inspection found a concurrent uncommitted HUD candidate already present:
- `operator_hud/server.py`
- `operator_hud/static/app.js`
- `operator_hud/static/index.html`
- `operator_hud/static/style.css`
- new `tests/test_hud_availability_presentation.py`.

The candidate was treated as controlled evidence, not duplicated.

### CONCURRENT CANDIDATE BASELINE
Candidate behavior:
- `/api/status` added explicit `readiness` with core HUD/Receiver/journal and optional browser bridge;
- browser bridge labeled optional;
- global UI could display `CORE READY · OPTIONAL DEGRADED`;
- native tool availability shown in badges/detail;
- explicit `Check current availability` used native `lab.capabilities.availability` for the selected tool only;
- ephemeral UI availability rows stored in `state.availabilityChecks`;
- no catalog-wide hidden availability scan.

Candidate + existing HUD security/process baseline:
**26/26 PASS**.

### HOSTILE CURRENTNESS FINDING
Source inspection found a stale-evidence seam:
- ephemeral availability rows were keyed only by tool name;
- after a native capability contract changed, an old probe row could remain displayed against a new card;
- catalog refresh also left `state.selected` referencing the old card object.

### HARDENING
Added `currentAvailabilityCheck(t)`:
- compares checked-row `contract_digest` with current native card `contract_digest`;
- missing/mismatched digest discards ephemeral evidence;
- stale provider evidence never masquerades as current.

Catalog refresh now:
- rebinds selected capability by name to the fresh card;
- refreshes selected category/name/description/badges/availability;
- clears selected detail and ephemeral evidence if capability disappears.

No Runtime capability/availability semantics were changed.
No background availability polling was added.
No unavailable scoped/default probe was turned into an unconditional dispatch gate.

### QUALIFICATION
Strengthened HUD/native-currentness cluster:
- HUD availability presentation
- bound approval
- Host guard
- HUD process ownership
- native availability contract
- MCP manifest contract

Result: **41/41 PASS**.

Complete V30 suite:
- **241 collected tests GREEN**
- existing conditional Windows symlink-privilege skip only.

Current identities:
- `operator_hud/server.py` SHA `a0dadde4418c23eb24477103038069e7332ec28da54400cad2c1e079f2ee6301`
- `operator_hud/static/app.js` SHA `c5775e0869ec3867929c3a7fdacadb2604ae87b64acefb84e117b02bc7fd5213`
- `operator_hud/static/index.html` SHA `edc4b4d27867a65fb2451ccba3321c296de4c4fbd90d5441583f35236cc52965`
- `operator_hud/static/style.css` SHA `baa0948a220d3889ece508be9d24bb9eacc538128b919259b1b5554779beb9d0`
- `tests/test_hud_availability_presentation.py` SHA `c9fd6fd4a1301c8d8e391ec2c712912024f7589420e7590e667d58765faaadab`.

### AUTHORITY / CLAIM CEILING
`HUD_PRESENTATION != RUNTIME_AVAILABILITY_AUTHORITY`.

HUD readiness is a live operator presentation aggregate; native capability availability remains Runtime-owned. Browser bridge direct health is an operator diagnostic surface, not persisted authority. Availability checks remain explicit, bounded, ephemeral, and capability-contract bound.

### STATE CONSEQUENCE
A-030 promoted across Current/Next/Doctrine/Revisit/Trace/Live/Commander/ICF.
Active Frontier moves to remaining adapter-lossiness classification, then evidence-ranked next Runtime seam selection.
Git publication is the final action for this phase.


### PHASE 38 QUALIFICATION ADDENDUM — Projection-currentness regression and final publication evidence

The Phase 38 41/41 + 241-test checkpoint remains valid historical evidence for the HUD/native-currentness code slice at that moment.

A subsequent load-bearing projection-contract reconciliation added `tests/test_runtime_adapter_projection_currentness.py` and updated the shared Runtime/adapter compatibility + projection matrix through A-030.

The first combined HUD+projection run correctly FAILED 1/32 because the machine projection matrix still carried a stale umbrella open item: `remaining MCP/OpenAPI/HUD/imported-action parity` after MCP and HUD availability slices had already been earned.

The test was not weakened. The machine matrix was repaired to the actual unresolved seam: `remaining OpenAPI/imported-action/runtime-surface parity`.

Final focused qualification on the resulting bytes:
- complete HUD family + projection-currentness regression: **32/32 PASS**.
- JavaScript syntax: PASS.

Final complete V30 qualification on the publication candidate:
- **245 collected tests GREEN**;
- existing conditional Windows symlink-privilege skip only.

Final A-030 currentness therefore supersedes the intermediate 241 count as Frontier evidence while preserving the earlier checkpoint in chronology.

Commander’s Intent was also reconciled so core-vs-optional readiness is checked/earned, capability availability is marked earned-core/extensible, and plugin transactional currentness is no longer left as a generic unchecked item.

Active Frontier after publication: remaining OpenAPI/imported-action/runtime-surface currentness classification, then evidence-ranked next Runtime hardening seam. Final schema redesign remains locked/deferred.


---

## Phase 40 — Thread-saturation recovery, Git reality reconciliation, and repo-contained handoff campaign

### USER
Provided the GitHub repository URL `https://github.com/SEng-Kitathas/AI-Server-InfrA.git`, reported that the prior thread inference had failed because the thread was full, supplied a copied tail claiming A-028 was closed and Git promotion was beginning, and required:
- verify what actually happened rather than trusting the copied tail;
- push to Git as soon as possible;
- ensure the entire project state survives for a fresh thread;
- especially preserve the Laboratory Runtime ↔ OBE/Skills duality and current SOP/ICF-CS handoff obligations.

### RECOVERY / REALITY READBACK
The copied tail was treated as recovery evidence, not current authority.

Direct project search proved the project had advanced significantly beyond the copied tail:
- A-028 availability/currentness was already qualified and promoted;
- A-029 MCP availability projection was qualified;
- A-030 HUD availability/core-vs-optional readiness presentation was qualified;
- projection-currentness reconciliation also existed;
- current V30 registry = 100 tools / 16 families.

Exact Git root was confirmed as:
`E:\new pc\AI_Pushes_Sandbox\projects\PCMMAD_RECEIVER_LAB\V30_WORKING\PCMMAD_receiver`

Remote:
`https://github.com/SEng-Kitathas/AI-Server-InfrA.git`

Branch/upstream:
`main` / `origin/main`.

Fresh pre-handoff Git readback:
- local HEAD `f63f31f7f2ae89f9253d21609a1d431df29e0a69`
- remote `refs/heads/main` exact same SHA
- tree `6dbdc6fa9a42531ae0252b634cfd3f8e0d749ba3`
- working tree clean before the current handoff mutation.

Fresh complete V30 suite on those published bytes:
- 245 collected tests
- GREEN
- one existing conditional Windows symlink-privilege skip.

### ICF-CS CONFLICT FOUND
Outer project continuity had lagged Git reality:
- Current State still described A-029 as the current published head;
- Next Steps still said “publish A-030”;
- Live Shadow still called A-030 publication pending;
- `GIT_PUBLICATION_CURRENT.md` still described `7aee592` as current and a later projection candidate as uncommitted;
- `ICF_CS_CURRENT.md` still said publication was pending.

This was a material Frontier/currentness disagreement.

Applied qualified ICF-CS conflict grammar:
`CONFLICT -> RECOVERY/AUDIT -> LOCALIZE -> REPAIR/SUPERSEDE -> READBACK -> RESUME`.

### CONTINUITY REPAIR
Registered updates repaired Current State, Next Steps, Doctrine, Revisit, Trace, Live Shadow, ICF Current, Commander’s Intent, and Git Publication checkpoint to the actual pre-handoff Git state.

New explicit doctrine:
- Git may carry a commit-bound continuity recovery mirror for thread-loss/local-store-loss recovery;
- that mirror is navigation/recovery evidence, not a second live truth plane;
- canonical local/runtime consequence-bearing readback still controls when available;
- `CURRENT_INGRESS_POINTER != CURRENT_STATE_PROOF`;
- `GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION`.

### RUNTIME ↔ OBE/SKILLS DUALITY PRESERVED
Current architecture authority remains:
- PCMMAD = methodology;
- Laboratory Runtime = canonical durable machine truth/state/capability;
- adapters (MCP/OpenAPI/CLI/HUD/future transports) = projections only;
- OBE/Skills = reusable AI/operator operating intelligence and composition judgment;
- model = replaceable co-processor;
- Project Chat = replaceable mission interaction surface.

Runtime owns capability contracts/currentness, projects/repos/mounts/nodes, jobs/queues/lifecycle/process ownership, services, results/artifacts, continuity, authority/approval/policy, verification/readback, transfer, and earned resource/telemetry state.

OBE/Skills own workflow intelligence such as discovery grammar, rehydration, evidence/currentness reasoning, hostile campaign routing, artifact sealing judgment, mission control, capability scouting, and composition logic. They SHALL NOT duplicate durable Runtime state/lifecycle semantics.

Placement law remains:
`MECHANISM LIVES WHERE STATE LIVES; COMPOSITION JUDGMENT USUALLY LIVES IN SKILL/MODEL SPACE UNTIL AN INVARIANT IS EARNED FOR RUNTIME ENFORCEMENT.`

Cross-thread meeting surfaces remain:
- `reports/PCMMAD_RUNTIME_ADAPTER_COMPATIBILITY_CONTRACT_V0_1.md`
- `reports/PCMMAD_RUNTIME_ADAPTER_PROJECTION_MATRIX_V0_1.md`
- machine-readable projection companion.

Final OBE↔Runtime interface vocabulary SHALL NOT freeze before audited-successor reconciliation.

### AI ATTENTION / ASYNC LAW PRESERVED
`LONG-RUNNING WORK SHALL NOT REQUIRE LONG-RUNNING MODEL ATTENTION.`

Queues/jobs/research/browser/build/download/archive work must provide bounded, decision-grade progress receipts while bulk output stays behind handles/ranges. The AI must not remain trapped in an open-ended tool call simply to learn whether work is progressing.

### CURRENT BUILD/PROMOTION ACTION
Create a Git-contained `handoff/current/` snapshot with exact current ICF/state/shadow/Commander surfaces, source-hash manifest, a repo-root `CURRENT_INGRESS.md`, and an explicit Runtime↔OBE/Skills architecture handoff. Then commit, push, remote-read the new head, and update outer Git publication receipt.

The Git handoff snapshot is commit-bound recovery evidence. It does not become a second durable Runtime/project-store authority.


---

## Phase 41 — Git-contained ICF/Runtime↔Skills handoff sealed, pushed, and remotely verified

### HANDOFF QUALIFICATION
Repository handoff artifacts were materialized under:
- root `CURRENT_INGRESS.md`
- `handoff/current/`
- hostile regression `tests/test_git_handoff_current.py`.

The first hostile regression rejected one wording mismatch in the placement-law witness. The document was strengthened to carry the explicit canonical short form `MECHANISM LIVES WHERE STATE LIVES`; the test was not weakened.

Final handoff qualification on exact candidate bytes:
- focused handoff regression **6/6 PASS**;
- complete V30 suite **251 collected tests GREEN**;
- one existing conditional Windows symlink-privilege skip;
- basic secret-like scan over new ingress/handoff/Commander delta: no hits;
- byte-wise real trailing-space/tab scan: zero issues;
- snapshot manifest hashes declared members.

### GIT COMMIT / PUSH
Staged delta was restricted to:
- updated `reports/V30_COMMANDERS_INTENT_AND_WORKLIST.md`;
- new repo-root `CURRENT_INGRESS.md`;
- new `handoff/current/*` recovery bundle;
- new `tests/test_git_handoff_current.py`.

No unintended code/runtime/cache files were staged.

Committed:
`cc2802f6d0a0ea24fe036aad9bdb6abfde925566`

Subject:
`Seal ICF-CS Git handoff and Runtime-Skills boundary`

Commit delta:
- 21 files
- 4,997 insertions
- 4 deletions.

Pushed successfully:
`f63f31f..cc2802f  main -> main`.

### REMOTE READBACK
Independent readback after push:
- local HEAD `cc2802f6d0a0ea24fe036aad9bdb6abfde925566`
- remote `refs/heads/main` exact same SHA
- tree `b93f7973a3c29c6f6ddfcbc88df9405e0c61d095`
- branch/upstream clean
- remote `origin/main:CURRENT_INGRESS.md` opened successfully and carried expected recovery-pointer authority ceiling / `INTENT IS A CONSTRAINT, NOT A CEILING` ingress.

Disposition:
**GIT HANDOFF PUBLICATION COMPLETE / REMOTE-VERIFIED.**

### HANDOFF CONTENT
The repository now carries a commit-bound cold-start recovery surface containing:
- Current State
- Next Steps
- Doctrine Snapshot
- Revisit Ledger
- Trace Matrix
- Live Shadow
- complete current Design Thread Stream snapshot
- ICF current ingress
- Commander’s Intent
- canonical SOP pointer
- exact qualified ICF-CS standard/machine contract/claim ceiling
- ICF qualification receipt
- source-hash snapshot manifest
- Git publication base receipt
- explicit Runtime↔OBE/Skills duality handoff
- handoff qualification receipt.

The root ingress directs a fresh thread to perform dynamic Git/local/runtime readback before mutation.

### RUNTIME↔OBE/SKILLS DUALITY
Git handoff explicitly preserves:
- PCMMAD = methodology
- Runtime = durable truth/state/capability
- adapters = projections only
- OBE/Skills = reusable AI/operator intelligence/composition judgment
- model = replaceable co-processor
- Project Chat = replaceable interaction surface
- no second Skill-side PCMMAD ontology
- final OBE↔Runtime vocabulary waits for audited-successor reconciliation
- `TRANSPORT IS NOT ARCHITECTURE AUTHORITY`
- `MECHANISM LIVES WHERE STATE LIVES`
- `EMERGENT CAPABILITY IS ALLOWED. EMERGENT AUTHORITY IS NOT`
- `LONG-RUNNING WORK SHALL NOT REQUIRE LONG-RUNNING MODEL ATTENTION`.

Candidate Skill portfolio/mechanism-quarry sections are explicitly marked research/candidate rather than Runtime authority.

### AUTHORITY CEILING
`GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION`.

`GIT_HANDOFF_SNAPSHOT != LIVE_PROJECT_STATE_PROOF`.

The handoff is durable recovery evidence. Fresh canonical local/runtime/Git readback remains required before consequential mutation.

### FRONTIER AFTER PUBLICATION
Resume remaining adapter-lossiness classification (especially OpenAPI/imported-action/runtime-surface currentness/typing), classify mismatches ACCEPTABLE / DEFERRED / FIX-NOW, then select the next genuinely-open Runtime seam by evidence.

Final schema redesign remains locked until whole-runtime convergence / explicit final trigger.


---

## Phase 42 — A-031 compact capability-family effective-approval parity

### USER CADENCE
User explicitly required continuous work until thread saturation with Git push after **every earned step**.

Operational cadence now binding for this thread:
`EARN STEP -> UPDATE CONTINUITY -> QUALIFY -> COMMIT -> PUSH -> REMOTE READBACK -> NEXT STEP`.

### REHYDRATION SCAR
Generic root rehydrate selected stale `.pcmmad_sync_runs` excerpts and reported no Live Shadow/DTS in that call.
Those excerpts were rejected as current authority. Fresh direct reads of Current/Next/Live/ICF/Commander/projection surfaces restored the qualified current state.

### ADAPTER LOSSINESS CENSUS
Native tool cards expose 17 top-level fields. Current compact OpenAPI intentionally keeps `/lab/tools.tools[]` permissive (`additionalProperties=true`) so evolving native cards cross the wire without truncation.

A stronger contradiction was found in the closed `CapabilityFamilyCard` response schema:
- native family cards serialize `effective_approval_required_tools`;
- compact schema used `additionalProperties=false` but omitted that field;
- all 16 families emit it;
- browser family proved semantic significance: 6 declared approval-required tools versus 12 effective approval-required tools.

Classification:
**FIX-NOW**. This was not acceptable compression because the schema contradicted actual emitted response shape and hid authority-significant policy truth.

### EMBODIMENT
Compact `CapabilityFamilyCard` now declares/requires:
`effective_approval_required_tools: integer >= 0`.

Description states that effective policy can derive approval from mutation/danger rules beyond declared `approval_required` metadata.

No Runtime behavior/policy changed.
Compact compatibility surface remains exactly 30 operations.

Backup:
`baseline/pcmmad_receiver/_v30_backups/AUDIT_A031_FAMILY_AUTHORITY_PARITY/pcmmad_lab_action_schema_v10_3_pcmmad_native_protocol_compact_30_router.json`.

### HOSTILE REGRESSION
Added:
`tests/test_compact_schema_family_authority_parity.py`.

It proves:
- closed family schema key set exactly equals native serialized family-card keys across all 16 families;
- effective approval count is required/non-negative;
- effective count is never below declared count;
- at least one real family differs;
- compact operation count remains 30.

### VERIFICATION
Focused compact schema/effect/bound-authority cluster:
**32/32 PASS**.

Complete V30 suite:
**254 collected tests GREEN** with the existing conditional Windows symlink-privilege skip only.

Current schema SHA:
`b069f594eec05a85331cb8b551625de430fb43b30820c580a19317751270db20`.

A-031 test SHA:
`b8f80b96a8dd3e0ceeefb591bd6fcf0542cd2bde99f0b456a46e63c9aa5f6942`.

### LOSSINESS DISPOSITION
- closed family-card effective-approval omission: **FIX-NOW -> EARNED**;
- permissive `/lab/tools.tools[]` capability cards: **ACCEPTABLE CURRENT COMPATIBILITY** — wire semantics preserved; strong validation/docs deferred unless concrete client failure or final schema campaign justifies it.

### NEXT DISCRIMINATOR — NOT YET MUTATED
Compact Action `/lab/results/get` advertises only historical `summary_only` while native Runtime supports:
`auto | full | metadata | preview | range`
plus byte offset/length and preview sizing.

This is isolated as the next adapter-lossiness step because it may violate bounded-result / bounded-model-attention law.

No result-handle adapter mutation begins until A-031 is committed, pushed, and remote-read back.


### A-031 final qualification scar — stale projection-currentness regression

During the final exact-candidate gate, handoff regression passed 6/6 but the complete suite rejected the candidate because `test_runtime_adapter_projection_currentness.py` still hard-coded `reconciled_through == A-030` and expected the human matrix phrase `reconciled through A-030`.

Failure classification:
**EVALUATOR/CURRENTNESS STALENESS**, not A-031 Runtime/schema failure.

The projection matrix had lawfully advanced to A-031, while the regression remained pinned to the prior A-030 frontier.

Repair discipline:
- did **not** roll the matrix back;
- did **not** weaken/remove A-030 HUD currentness assertions;
- updated the regression to require `reconciled_through == A-031`;
- retained A-030 availability/HUD authority checks;
- added explicit A-031 witnesses for `effective_approval_required_tools` and `FIX-NOW / EARNED` classification.

Post-repair focused currentness/A-031/handoff cluster:
**20/20 PASS**.

Post-repair complete V30 suite:
**254 collected tests GREEN**, existing conditional Windows symlink-privilege skip only.

Projection-currentness test SHA:
`7149a057715d7a15feb761cdd60fb1369f8140afbf7a730fb34ac9850783e5e9`.

This scar reinforces:
`STALE_GREEN != CURRENT_EVIDENCE` and `EVALUATOR_EXPECTATION != CURRENT_AUTHORITY`.

A-031 remains pending only Git commit/push/remote-readback before the next adapter seam begins.


### A-031 byte-preservation correction — schema hash lineage

The initial A-031 schema mutation was semantically correct but had been written with LF line endings, causing a noisy 9,214-line Git diff under the repository's deliberate `* -text` byte-preservation policy.

The exact-delta audit rejected that publication candidate before Git.

Repair:
- restored the compact schema from exact `HEAD` bytes;
- re-applied only the A-031 `effective_approval_required_tools` property + required-token against the original CRLF formatting;
- preserved the existing 30-operation surface;
- no Runtime semantics changed.

Historical LF-normalized candidate SHA:
`b069f594eec05a85331cb8b551625de430fb43b30820c580a19317751270db20`.

Current byte-preserved publishable schema SHA:
`2d845dce9312a1a86a1217059a5dc046d435fb4f66540f703a92d4609b37a4ce`.

The earlier hash remains in chronology as a rejected pre-publication candidate; current authority surfaces were corrected to the CRLF-preserved hash rather than rewriting history.

This reinforces the source-lineage law: semantic equivalence does not erase byte identity when manifests/Git lineage are intentionally byte-sensitive.


### A-031 Git publication complete

Final publishable A-031 candidate used the CRLF-preserved schema bytes.

Final qualification before commit:
- focused projection/A-031/handoff cluster **20/20 PASS**;
- complete V30 suite **254 collected tests GREEN**;
- compact operation count 30;
- schema SHA `2d845dce9312a1a86a1217059a5dc046d435fb4f66540f703a92d4609b37a4ce`.

Git commit:
`02b6ef1224a7ced2abab3cbd3e61235727842249`

Tree:
`6720a4ac13c41fe90c6ca70cb5a85e07fd612f0c`.

Subject:
`Fix compact capability-family effective approval parity`.

Push:
`cc2802f..02b6ef1  main -> main`.

Independent readback:
- local HEAD = remote `refs/heads/main` = `02b6ef1224a7ced2abab3cbd3e61235727842249`;
- branch clean against `origin/main`.

Disposition:
**A-031 EARNED + GIT REMOTE-VERIFIED.**

Next isolated adapter-lossiness discriminator:
A-032 compact `/lab/results/get` request projection versus native bounded `auto|full|metadata|preview|range` modes.


---

## Phase 43 — A-032 compact Actions bounded result-handle parity

### FRONTIER ENTRY
A-031 was already remote-verified at `02b6ef1224a7ced2abab3cbd3e61235727842249` before this seam began.

### EXACT LOSSINESS READBACK
Native `/lab/results/get` supports:
- `mode=auto|full|metadata|preview|range`;
- historical `summary_only=true` as preview alias;
- `offset_bytes` for range reads;
- `length_bytes` default 32768, capped by `RESULT_RANGE_MAX_BYTES=65536`;
- `preview_chars` default 1200, clamped 200..`RESULT_PREVIEW_MAX_CHARS=4000`;
- auto mode returns preview for stored results larger than `RESULT_INLINE_SAFE_BYTES=12000`;
- metadata mode avoids payload materialization;
- explicit full mode is caller opt-in.

Compact Actions `ResultHandleRequest` was closed (`additionalProperties=false`) and exposed only:
- project_id;
- handle;
- summary_only.

A constrained Action client therefore could not lawfully request metadata-only identity, exact byte slices, preview size, or explicit full-vs-auto behavior even though the Runtime already supported them.

Classification:
**FIX-NOW** — semantic adapter loss intersecting bounded model context/result doctrine.

### EMBODIMENT
Surgically updated the existing CRLF compact schema:
- added exact mode enum `auto|full|metadata|preview|range`, default `auto`;
- added `offset_bytes` min/default 0;
- added `length_bytes` min 1 / default 32768 / max 65536;
- added `preview_chars` min 200 / default 1200 / max 4000;
- retained `summary_only` and documented it as historical preview alias;
- operation description now tells constrained clients to prefer bounded modes and treats full as explicit opt-in;
- operation count remains exactly 30.

No native route/result behavior changed.

Current schema SHA:
`25be4cbd0ab4b5a0be10e1e087857537656a712f33308de12e3a462a7186bf6c`.

### HOSTILE REGRESSION
Added:
`tests/test_compact_schema_result_bounded_parity.py`
SHA `00056925c09ad0aa6b3c526e69d119964d2b13d79cf9680c678b59154d406d92`.

The regression binds Action mode/range/preview controls to current native constants and protects the historical alias plus 30-operation ceiling.

### VERIFICATION
Focused native result + compact adapter + currentness + handoff cluster:
**36/36 PASS**.

Complete V30 suite:
**260 collected tests GREEN**, existing conditional Windows symlink-privilege skip only.

Projection matrix and compatibility contract advanced through A-032.

### LOSSINESS CEILING
Mode-dependent 200 response remains permissively typed as object.
Disposition: **ACCEPTABLE CURRENT COMPATIBILITY / DEFERRED STRONG TYPING** because request bounded choice and native result identity/hash/mode truth are preserved while no concrete client requires a frozen polymorphic response hierarchy.

### CURRENT STATE
A-032 is technically/continuity-earned and awaiting this step's mandatory Git commit/push/remote-readback before any A-033 implementation begins.


### A-032 Git publication complete / execution hostile campaign admitted

A-032 final publication was independently read back after push.

Git commit:
`a3d84199e2673b87c4d7d246bf591bb3dbefdd63`

Tree:
`7055df4da7200121207734cf36bb703441ae1b6d`.

Subject:
`Expose bounded result retrieval in compact Actions`.

Verification carried into publication:
- focused result/adapter/currentness cluster 36/36 PASS;
- refreshed handoff 6/6 PASS;
- complete V30 suite 260 GREEN;
- compact schema SHA `25be4cbd0ab4b5a0be10e1e087857537656a712f33308de12e3a462a7186bf6c`;
- 30 operations.

Remote/local `main` were exact and branch clean after push.

Immediately afterward the user supplied a hostile execution-plane teardown with measured claims about:
- repeated full-tree capacity scans under the process-global admission lock;
- poison execution records permanently starving queue drain;
- scheduler duty cycle scaling with lifetime job count;
- no retention and a flat execution directory;
- active/terminal partition as structural fix;
- Werkzeug dev-server exposure;
- legacy bare-PID reuse risk;
- process-local admission lock under double receiver start.

Campaign disposition:
The teardown is admitted as **PROVISIONAL HOSTILE EVIDENCE**, not automatic architecture authority. Failure classes are separated into independently reproduced/qualified/pushed steps.

Ordered frontier:
1. A-033 admission hotpath reproduction/fix;
2. A-034 poison-record isolation/read-path failure excerpt separation;
3. A-035 active/terminal execution-store partition;
4. A-036 retention/bounded drain;
5. separate serving-model / PID-reuse / multi-receiver ownership audits.

Per-step Git publication/readback remains mandatory.


---

## Phase 44 — A-033 execution admission hotpath read-amplification repair

### HOSTILE INPUT
User supplied an execution-plane teardown with measured claims about saturation-time admission lock amplification, poison-record starvation, lifetime-tree scheduler cost, active/terminal partitioning, retention, serving model, PID reuse, and multi-receiver admission ownership.

Exact attachment identities and campaign split are persisted in:
`reports/hostile_inputs/EXECUTION_PLANE_TEARDOWN_2026-09-05_RECEIPT.md`.

The donor patch was **not** applied wholesale because it bundled admission hotpath and poison-record isolation.

### CURRENT-V30 REPRODUCTION BEFORE MUTATION
Synthetic store:
- 40 terminal history records
- 8 RUNNING records at global limit
- 12 QUEUED records.

One `_drain_queue('p1')` produced:
- 0 starts;
- 12 `_capacity_snapshot` calls;
- 12 `_can_start_now` calls;
- **49 job-tree walks** = 1 candidate discovery + 4×12 capacity scans;
- **2,940 job-file loads**;
- 0.554 s on operator Windows host, already greater than the configured 0.25 s scheduler interval.

The external mechanism was independently reproduced on current V30.

### DERIVATION
Current `_effective_running_count()` semantics include live managed `_RUNNING` processes before durable RUNNING records. The donor's simpler file-only census would narrow that behavior.

Derived A-033 `_running_census()` therefore:
- snapshots live managed process IDs under `_RUNNING_LOCK`;
- counts them globally even if durable status is transiently stale;
- walks durable records once;
- globally deduplicates job IDs while maintaining independent per-project seen sets;
- counts non-managed durable RUNNING records only when PID liveness succeeds.

Lock-order audit confirmed existing admission→running ordering and no reverse nested path in current module.

### EMBODIMENT
`_drain_queue_locked()` now:
- establishes global/per-project running capacity once under admission;
- uses local budgets for the pass;
- increments budgets only after successful spawn+write;
- breaks immediately when global capacity is exhausted;
- continues past a full project so another project may still start;
- no longer calls `_can_start_now()` per candidate.

`_capacity_snapshot()` and `_can_start_now()` remain for observational/other callers.

Backup:
`baseline/pcmmad_receiver/_v30_backups/AUDIT_A033_ADMISSION_HOTPATH/execution_routes.py`.

### HOSTILE REGRESSION
Added `tests/test_execution_admission_hotpath.py`.

It proves:
- same saturated 60-record case is exactly 2 walks / 120 loads;
- saturation causes zero queued-record reads and zero per-candidate capacity calls;
- one remaining global slot admits only one candidate without re-census;
- a full project does not block another project;
- live managed-process semantics survive transiently stale durable status.

### POST-FIX MEASUREMENT
Same 60-record case:
- 2 tree walks;
- 120 loads;
- 0 `_can_start_now` / 0 `_capacity_snapshot`;
- 0 queued `_read_job` at global saturation;
- 0.231 s;
- 0 starts.

500 terminal + 8 RUNNING + 50 QUEUED Windows case:
- candidate discovery: 2.226 s outside `_ADMISSION_LOCK`;
- admission-lock hold: **0.049 s**;
- 0 starts.

The remaining off-lock flat-tree scan is not claimed fixed; it is direct current-host evidence for A-035 active/terminal partitioning.

### VERIFICATION
- current execution cluster: **19/19 PASS**;
- complete V30 suite: **264 collected tests GREEN**;
- one existing conditional Windows symlink-privilege skip.

Current identities:
- `execution_routes.py` SHA `2cea76cd1b24291f1ef5d929fedbf02f6102b3bc0e2927cedc5db2a367d0a02e`;
- A-033 test SHA `fd2ed0b73c413d88dc8083797d623504da5bca435b7a0063c9d1d8b1ba56efb8`.

### CLAIM CEILING / NEXT
A-033 fixes repeated capacity scans under the global admission lock only.

Still open:
- A-034 poison-record scheduler isolation / critical-path failure excerpt I/O;
- A-035 active/terminal partition and lifetime-scan cost;
- A-036 retention/bounded drain;
- serving model, legacy PID identity, multi-receiver admission ownership.

A-034 mutation is blocked until A-033 Git commit/push/remote-readback completes.


### A-033 Git publication complete

A-033 admission read-amplification repair was committed and remotely verified before A-034 began.

Commit:
`2eeebd9182fdbf8e02241f4edd1b482a6862caa7`

Tree:
`9a2b9009fe5f645f83375b5bdd06e09d0d474577`.

Subject:
`Fix execution admission read amplification`.

Push:
`a3d8419..2eeebd9  main -> main`.

Remote/local `main` matched exactly and the branch was clean after push.

Publication qualification:
- final handoff + execution focused gate 25/25 PASS;
- complete V30 suite 264 GREEN;
- execution SHA `2cea76cd1b24291f1ef5d929fedbf02f6102b3bc0e2927cedc5db2a367d0a02e`.

Disposition:
**A-033 EARNED + GIT REMOTE-VERIFIED.**

Active Frontier advances to A-034 poison-record scheduler starvation / critical-path failure excerpt I/O.


---

## Phase 45 — A-034 poison-record scheduler isolation / deferred output reads

### CURRENT-V30 REPRODUCTION
One dead RUNNING record with empty stdout/stderr paths and three healthy QUEUED records was placed first in a real temp execution store.

Five consecutive scheduler ticks before repair:
- 5/5 aborted on Windows `PermissionError` for `.`;
- queue drain reached 0/5;
- poison record persisted RUNNING;
- queued records remained queued.

This independently reproduced the user's Linux starvation mechanism with the Windows-specific filesystem exception.

### ROOT CAUSE
`_mark_supervision_lost` changed the in-memory record to FAILED, then called `_job_failure_excerpt` before persistence. Empty output path became `Path("") == "."`; arbitrary filesystem read failed; durable FAILED transition never happened. `_scheduler_tick` had no record-local isolation, so the outer scheduler loop retried the same poison every tick before queue drain.

### DERIVATION / EMBODIMENT
- supervision-loss reconciliation is now filesystem-independent;
- failure digest persists with empty stdout/stderr excerpts and `excerpt_capture=deferred_to_output_read`;
- explicit bounded `/project/execution/output` remains the output-read surface;
- `_scheduler_tick` isolates record-local reconciliation exceptions, continues, and always reaches drain;
- SchedulerTelemetry adds cumulative `jobs_reconcile_errors`, current `last_tick_reconcile_errors`, bounded `last_reconcile_error`, and timestamp;
- readiness degrades on current-tick reconcile errors and recovers after later clean ticks while retaining historical diagnostic text.

No fake quarantine claim is made because records are not moved to a quarantine store.

### HOSTILE REGRESSION
Added `tests/test_execution_scheduler_poison_isolation.py`.

First focused run: 23/24 PASS. The failing fixture wrote `aaa_poison.json` containing job_id `poison`; Runtime correctly persisted canonical `poison.json` while the test reread the stale alias filename. Fixture identity was corrected; Runtime code was not weakened.

Post-correction execution cluster: 24/24 PASS.

### POST-FIX EXACT REPRO
Five ticks:
- 5/5 completed cleanly;
- drain reached 5/5;
- poison persisted FAILED / supervision_lost;
- failure digest carries `excerpt_capture=deferred_to_output_read`.

Queued records remained QUEUED only because the hostile repro intentionally used a no-op drain sentinel.

### VERIFICATION
Complete V30 suite: **269 collected tests GREEN** with the existing conditional Windows symlink-privilege skip only.

Current hashes:
- execution_routes.py `6c3dda46a004ca88f24839b6ad769c12e235b1f679ae0654c1ba9ae5c95c058c`
- control_plane_models.py `1ac32417682c6638728c1a9c5523f0781a81256c13cc55810a68b7af0ebded0e`
- A-034 test `ced3b110ad52c56b2f58ea611cd79230440d5e0d2fc7eeadd7945950ff144484`.

### CLAIM CEILING / NEXT
A-034 fixes poison-record starvation and supervision-loss critical-path output I/O only.
A-035 active/terminal partition remains next after A-034 Git remote readback. Retention/bounded drain/serving/PID/multi-receiver remain separate.
