# PCMMAD Receiver V30 — All-Plane / All-Tool Hostile Audit

Status: ACTIVE
Mode: AUDIT inside BUILD-COMMIT

## Baseline
- live receiver at audit start: 96 native tools / 16 families / 30 imported operations
- V30 working tree after preserving live deltas: 98 native tools / 16 families / 57 HTTP routes
- V30 full pytest suite: PASS after each earned patch recorded below

## A-001 — V30 static body regressed live capabilities
Severity: P0 release blocker
Status: FIXED in V30 working tree

Observed:
- V30 initially omitted all six live transfer tools and live `browser.upload`.
- exact live-only set was seven capabilities.

Embodiment:
- preserved `transfer_plane.py`
- preserved `lab_plugins/transfer.py`
- restored transfer blueprint registration
- restored `browser.upload` spec

Verification:
- V30 registry now 98 tools / 16 families
- route count 57
- full suite PASS

## A-002 — aggregate `lab.health` hard-failed on optional browser outage
Severity: P1 health/truth defect
Status: FIXED in V30 working tree

Observed:
- browser bridge localhost:4471 is down.
- `browser.health` correctly returned `BROWSER_BRIDGE_UNAVAILABLE`.
- `lab.health` returned the same browser exception instead of aggregate degraded state.

Mechanism:
- `_bridge_call()` converts connection error to native `LabToolError`.
- `_browser_bridge_status()` did not catch `dep.error_cls`.
- optional browser-plane failure therefore escaped aggregate health.

Embodiment:
- aggregate health now catches native bridge error and converts it to `BridgeStatus`.
- regression: `tests/test_lab_health_optional_browser.py`.

Verification:
- focused regression PASS
- full V30 suite PASS

## A-003 — `lab.batch` aggregate output can exceed action gateway ceiling
Severity: P1 agent/transport robustness
Status: OPEN

Observed:
- batch of five simple health/status tools produced `ResponseTooLargeError` at the action gateway.

Derived requirement:
- batch execution must budget aggregate response size.
- large/overflowing batch outputs should be stored server-side under a result handle rather than materialized through constrained clients.
- batch semantics must preserve per-step ordering/status/partial failure and MUST NOT imply transaction.

## A-004 — questionable `mutating` metadata on executable capabilities
Severity: P1 capability-contract/authority semantics
Status: OPEN / requires semantic inspection

Flagged descriptors:
- `browser.evaluate`
- `execution.run`
- `execution.submit`
- `lab.tools.reload`
- `python.run`
- `verify.gates`

Do not patch by label alone. Determine whether `mutating` means server-state mutation only or externally observable side effect. V30/MCP contract requires a less ambiguous side-effect model regardless.

## A-005 — Monster/Chimera semantic health was false/misleading
Severity: P1 capability-currentness
Status: FIXED to truthful unavailability; executor restoration deferred

Observed live defects:
- hardcoded stale C: retriever path
- hardcoded stale C: corpus DB path
- retriever script reported missing despite surviving E: copies
- dependency probe generated malformed `python -c` and failed with SyntaxError
- receiver Python lacked all five required modules
- migrated project semantic venvs were absent/broken
- D: semantic venv existed but referenced removed C:\Program Files\Python312\python.exe
- dispatcher outer `ok=true` could be misread as semantic operationality

Reality/ancestry:
- evolved retriever: `E:\new pc\AI_Pushes_Sandbox\projects\cto-chat-thread-organizer\tools\db_helper\monster_dual_retriever.py`
  SHA-256 `0c0841230d33e427892ca83520f0845ab12c38290d4d9511f1cadce44c564dac`
- older Monster ancestry retriever remains available separately.
- corpus DB exists at `E:\new pc\AI_Pushes_Sandbox\projects\pcmmad_ingress\pcmmad_corpus_analysis.sqlite` (~3.67 GB)
- D: MiniLM and Jina indexes exist.
- MiniLM model cache path exists.
- no discovered Python runtime currently provides faiss + numpy + torch + sentence_transformers + transformers together.

Embodiment:
- one shared semantic resolver used by health and search
- explicit payload/env/canonical-project discovery with provenance source labels
- evolved CTO donor preferred only as discovered implementation; runtime does not promote CTO project path into architecture authority
- dependency probe rewritten as safe one-line `python -c`
- Python execution environment is now a qualified resource, not assumed `sys.executable`
- search receives resolved DB/index/model paths through a child-only environment
- shared subprocess envelope gained optional `env` support without mutating parent environment
- semantic health returns `status`, `available`, `blockers`, resource paths/existence/source/hash, Python candidates/modules/currentness
- old top-level health fields remain compatibility projections over the new resolution
- unavailable search raises typed `SEMANTIC_UNAVAILABLE` before execution

Current semantic truth:
- data/index/model/script assets: present
- qualified executor: absent
- capability status: `unavailable`
- blocker: `no_qualified_python_runtime`

Verification:
- `tests/test_semantic_runtime_resolution.py`: PASS
- `tests/test_subprocess_env_isolation.py`: PASS
- legacy semantic compatibility tests: PASS
- full V30 suite: PASS

## Current next audit frontier
1. result/batch bounded-output semantics
2. native capability metadata / effective authority model
3. research plane
4. project/filesystem/git/state planes
5. SOP/protocol planes
6. transfer hostile pressure
7. plugin lifecycle/isolation
8. control/HUD plane
9. schema/runtime/MCP projection parity

## A-006 — indefinite AI wait/tool-state trap
Severity: P0 operator/control-loop defect
Status: FIXED in V30 working tree

Observed:
- `execution.wait` defaulted `timeout_seconds=None` and `_wait_until_done()` looped indefinitely while a job remained active.
- wait output also defaulted `max_bytes=None`, allowing potentially large terminal stdout/stderr materialization.

Embodiment:
- bounded wait default 8s; server cap 30s;
- terminal wait excerpt default 4096 bytes; server cap 16384 bytes;
- new `execution.progress` returns compact decision-grade status without bulk logs;
- active wait timeout returns compact progress rather than blank/indefinite state;
- progress receipt includes lifecycle/stage, actually-started, elapsed, queue position, supervision, heartbeat/output age, output availability/size, failure digest, artifact links, recommended recheck interval, and explicit bulk-output tool;
- progress classification: TERMINAL / QUEUED / STARTING / PROGRESSING / QUIESCENT / POSSIBLY_STALLED / SUPERVISION_UNCERTAIN / TERMINATING.

Verification:
- `tests/test_execution_bounded_progress.py`: 5/5 PASS
- full V30 pytest suite PASS

Law embodied:
`LONG-RUNNING WORK SHALL NOT REQUIRE LONG-RUNNING MODEL ATTENTION.`
`RETURN DECISION INFORMATION EARLY; STORE BULK WORK LOCALLY.`

## A-007 — foundational intent axiom was conversational, not ambient
Severity: architecture/continuity
Status: FIXED in V30 working tree

Embodiment:
- new `runtime_axioms.py` single authority surface;
- AXIOM-01 = `INTENT IS A CONSTRAINT, NOT A CEILING.`;
- compact constitutional seed includes stable version + digest;
- projected through ordinary `/health` and native `lab.health`.

Verification:
- `tests/test_runtime_axiom_seed.py`: 3/3 PASS
- full V30 pytest suite PASS

## A-008 — result handles could still re-materialize oversized payload by default
Severity: P1 constrained-client robustness
Status: FIXED in V30 working tree

Observed:
- large results were stored server-side but `/lab/results/get` default path returned the entire JSON body.

Embodiment:
- `mode=auto`: small result full; large result compact preview;
- `mode=metadata`: identity/hash/size/provenance/payload summary only;
- `mode=preview`: bounded semantic preview;
- `mode=range`: exact bounded raw-byte slice, base64 encoded, with offset/length/total/eof/sha256;
- `mode=full`: explicit opt-in to whole-result materialization;
- range cap 65536 bytes; preview cap 4000 chars; default inline safety ceiling 12000 bytes;
- range hashing uses streaming file hash rather than loading whole file merely to verify identity.

Verification:
- `tests/test_result_bounded_retrieval.py`: 6/6 PASS
- full V30 pytest suite PASS

## A-009 — MCP-ready manifest discarded native contract currentness/authority metadata
Severity: P1 adapter-currentness
Status: FIXED in V30 working tree

Embodiment:
- MCP-ready manifest now projects category/tags, danger, declared/effective approval, mutation, side-effect class, effect traits, capability/schema versions, schema hash, contract digest, input schema and output schema;
- manifest carries a stable digest over capability identity + contract digest.

Verification:
- `tests/test_mcp_manifest_contract.py`: 3/3 PASS
- full V30 pytest suite PASS

## A-010 — one-dimensional `mutating` field cannot express real runtime effects
Severity: P1 capability-contract semantics
Status: PARTIALLY EMBODIED / audit continues

Observed examples:
- `execution.progress/status/wait/output` are observational but may reconcile lifecycle and advance queue state;
- `execution.run/python.run` execute arbitrary code/processes;
- `browser.evaluate` can mutate external/browser state despite `mutating=false`;
- `transfer.export.create` creates ephemeral ticket state;
- research operations perform network IO and may write caches;
- plugin reload changes the live capability surface.

Embodiment:
- ToolSpec now supports composable `effect_traits` in addition to coarse `side_effect_class`;
- effect traits participate in `contract_digest` and MCP projection;
- declared mutation tools receive a default `durable_mutation` trait;
- high-risk ambiguous tools explicitly classified:
  - execution/run/python/submit;
  - execution observational reconciliation surfaces;
  - browser.evaluate;
  - research arXiv/search/hunt;
  - semantic Monster search;
  - lab.tools.reload;
  - transfer.export.create.

Verification:
- `tests/test_capability_effect_traits.py`: 3/3 PASS
- full V30 pytest suite PASS

Open:
- complete effect/authority classification across the remaining native tool registry;
- determine which effect traits should influence policy automatically vs remain descriptive evidence.

## Shared runtime↔OBE projection artifacts
Created:
- `reports/PCMMAD_RUNTIME_ADAPTER_PROJECTION_MATRIX_V0_1.md`
- `reports/PCMMAD_RUNTIME_ADAPTER_PROJECTION_MATRIX_V0_1.json`

These are candidate shared contracts grounded in the current V30 audit. They do not freeze final MCP vocabulary or final schema design.

## A-011 — approval boolean allowed authority smuggling across target/tool/arguments
Severity: P0/P1 authority defect
Status: FIXED in V30 working tree; legacy compatibility path remains transitional

Observed pre-fix behavior:
- the same `approval:{permit:true}` was accepted for service A, service B, changed arguments, and an entirely different capability;
- approval was not bound to capability identity, contract digest, target, argument digest, freshness, provenance, or single-use consumption;
- approval also lived inside tool arguments, mixing policy authority with capability input schemas.

Composition donor:
- CTO signed-promotion machinery contributed the reusable mechanism, not its domain ontology:
  - identity-bound certificate evidence;
  - canonicalized SHA-256 integrity digest;
  - operator/provenance fields;
  - issued/freshness/expiry semantics;
  - auditable decision/certificate lineage.

Embodiment:
- new `approval_authority.py` runtime subsystem;
- strict unapproved call creates a short-lived challenge bound to:
  - capability id/version;
  - schema hash;
  - contract digest;
  - exact canonical argument digest;
  - target summary;
  - danger/effect traits;
  - issue/expiry time;
- challenge is single-use by default and durable under `SYSTEM_ROOT/lab/approvals`;
- exact resubmission uses a separate authority envelope: approval handle + explicit permit + optional operator/provenance;
- changed args/target, different capability, contract drift, expiry, replay, or record tamper fail with distinct typed errors;
- challenge is consumed atomically before handler execution but only after schema and protocol/mode gates pass;
- approval fields are stripped before input-schema validation and never reach capability handlers;
- dispatch and batch both accept separate authority envelopes;
- ToolResultEnvelope reports approval mode/handle when bound authority was used;
- legacy inline `approval:{permit:true}` remains temporarily available under `PCMMAD_ALLOW_LEGACY_INLINE_APPROVAL`, but response warning explicitly labels it unbound/transitional; it can be disabled without affecting bound challenge flow.

Verification:
- `tests/test_approval_authority.py`: 8/8 PASS
- `tests/test_bound_approval_dispatch.py`: 7/7 PASS
- focused approval cluster: 15/15 PASS
- full V30 pytest suite PASS

Open hardening:
- challenge expiry/garbage collection policy;
- keyed integrity/signature decision after broader threat-model pass;
- adapter/HUD UX for user confirmation and provenance;
- eventual default disable/removal of legacy inline approval after client migration;
- optional revocation/list/introspection projection if operationally justified.

## A-012 — project/context file read control-plane endpoint returned HTTP 500 on tiny bounded read
Severity: P1 context/control reliability
Status: OPEN

Observed during audit:
- project `readProjectFile` action for `baseline/pcmmad_receiver/lab_policy.py` lines 1-120 returned generic HTTP 500;
- same file was immediately readable through local execution plane (`Get-Content`), proving underlying file/path existed and was healthy.

Interpretation:
- context/file plane failure != file failure;
- investigate route/action adapter/error-envelope path later; do not silently reroute and call the context plane healthy.

## A-012 update — project/context bounded line read HTTP 500
Status: FIXED in V30 working tree

Failure isolated:
- `context_engine.read_file()` computed `start_line` but referenced undefined variable `s` when deriving end line and slicing content.
- line-window requests therefore raised `NameError`, which was outside the route's typed context exception set and surfaced as generic Flask HTTP 500.
- the underlying file was healthy; context plane failed while execution-plane direct read succeeded.

Embodiment:
- replaced undefined alias with explicit `start_line` / `end_line` variables.
- did NOT broaden the route to swallow arbitrary programmer exceptions.

Verification:
- `tests/test_context_line_window.py`: 2/2 PASS
- direct engine exact line-window PASS
- HTTP route line-window PASS
- full V30 pytest suite PASS

## A-013 — bounded context read still materializes entire text file before slicing
Severity: P1 resource/control-plane defect
Status: OPEN / active next seam

Observed:
- `context_engine.read_file()` currently executes `target.read_text(...)` before applying `MAX_READ_BYTES` or requested line bounds.
- response is bounded, but server memory/materialization is not.

Required invariant:
`BOUNDED_RESPONSE != BOUNDED_EXECUTION` unless the implementation also avoids unnecessary whole-file materialization.

## A-013 update — bounded context materialization
Status: FIXED in V30 working tree

Embodiment:
- `read_file()` no longer calls whole-file `Path.read_text()` before slicing;
- prefix reads consume at most `max_bytes + 1` raw bytes;
- line-window reads stream bounded line fragments and never accumulate skipped lines;
- explicit end_line is capped by `MAX_READ_LINES`;
- search indexing and recent rehydration fallback now reuse the same bounded prefix reader instead of their own whole-file `read_text()[:N]` implementations.

Verification:
- `tests/test_context_bounded_materialization.py`: 4/4 PASS
- `tests/test_context_search_rehydrate_bounded.py`: 2/2 PASS
- existing context line-window tests PASS
- full V30 pytest suite PASS

## A-014 — project-scoped context paths could escape into other globally allowed roots
Severity: P0/P1 authority/path-scope defect
Status: FIXED in V30 working tree

Observed:
- `resolve_user_path(..., base_root=project_root)` validated the base root, but validated the requested candidate against ANY globally allowed root;
- with broad allowed roots, `../other-project/...` or absolute paths into another allowed root could escape project scope while still being globally allowed.

Embodiment:
- scoped calls now require the fully resolved candidate to remain under the exact resolved base root;
- unscoped/general context calls retain global mount allowlist semantics;
- `Path.resolve()` places symlink/junction destinations under the same final scope check.

Verification:
- `tests/test_context_project_scope.py`: 4 PASS / 1 symlink test skipped because symlink creation privilege unavailable;
- relative cross-project escape rejected;
- absolute cross-project escape rejected;
- in-scope path accepted;
- unscoped globally allowed access preserved;
- full V30 pytest suite PASS.

## A-015 — rehydration content budget can be exceeded by first selected excerpt
Severity: P1 bounded-context defect
Status: OPEN / active next seam

Observed:
- `_select_hit()` and recent fallback only reject an oversize excerpt when a prior selection exists;
- first selection can exceed caller's requested `budget_bytes`.

Required invariant:
- selected excerpt bytes must not exceed the declared rehydration content budget; if useful evidence is larger, clip it to remaining budget rather than silently violating the budget.

## A-016 — Git project/repository identity could collapse into ancestor repo authority
Severity: P0/P1 repo-authority defect
Status: FIXED in V30 working tree

Observed risk:
- running `git` from a project directory does not prove that directory is a repository root;
- Git walks upward to an ancestor `.git`, so a mis-grounded project could read or mutate an ancestor repository while subprocess calls still succeed.

Embodiment:
- exact repo grounding now resolves `git rev-parse --show-toplevel` and requires equality with the resolved project root;
- repo identity reports project_id, exact repo_root, HEAD, branch, unborn state, and grounding status;
- unborn repositories remain valid (`head=null`, `unborn=true`);
- read operations (`git.status`, `git.diff`) preserve historical envelope behavior on non-repos but return `repo_grounded=false` with typed failure instead of traversing/reading an ancestor repo;
- mutating operations require strict exact repo grounding and refuse to proceed on mismatch.

Mutation postconditions:
- `git.commit`:
  - exact repo identity before mutation;
  - staging failure stops before commit;
  - verifies staged changes exist;
  - commit failure is typed;
  - verifies HEAD advances;
  - returns before/after identity + status snapshots.
- `git.reset_hard`:
  - resolves requested target to exact commit with `--end-of-options` before mutation;
  - resets to resolved SHA, not ambiguous user token;
  - verifies final HEAD equals resolved target;
  - verifies tracked worktree/index are clean relative to target.
- `git.clean`:
  - dry-run deletion preview before mutation;
  - executes requested clean semantics;
  - repeats dry-run and requires no candidates remain;
  - returns preview-before / clean / preview-after + verified=true.

Capability effects:
- git status/diff marked read + exact-repo-identity traits;
- commit/reset/clean carry explicit mutation/destructive/postcondition traits.

Compatibility scar:
- first strict read implementation raised on non-repos and broke historical `git.status` envelope expectations;
- corrected split: reads return grounded negative envelope, mutations remain strict.

Verification:
- `tests/test_git_grounding_postconditions.py`: 6/6 PASS
- `tests/test_git_ops_hardening.py`: PASS
- combined Git compatibility + hostile suite: 8/8 PASS
- full V30 pytest suite PASS.

## A-017 — `verify.gates` effect semantics understated arbitrary execution + state mutation
Severity: P1 capability-contract truth
Status: FIXED in V30 working tree

Observed:
- custom verification gates accept arbitrary argv arrays and execute subprocesses;
- a gate can therefore write files, spawn processes, access network, etc.;
- failed gates also append a reflexion into project state.

Embodiment:
- `verify.gates` now declares `mutating=true`;
- side_effect_class=`execution`;
- effect traits include executes_code, spawns_process, arbitrary_process_side_effects, may_write_project_state, records_failure_reflexion.

Verification:
- hostile test proves a custom verification command can mutate the project;
- failed-gate test proves reflexion state write;
- focused web/verify cluster 8/8 PASS;
- full V30 pytest suite PASS.

## A-018 — `web.fetch` SSRF/internal-network authority gap
Severity: P0/P1 network authority defect
Status: FIXED in V30 working tree for public-web capability

Observed pre-fix:
- only URL scheme (`http|https`) was validated;
- localhost, loopback, private RFC1918, link-local/cloud metadata, unspecified/reserved addresses were not rejected;
- redirects were followed without target-scope revalidation;
- mixed DNS answers containing both public and private addresses were not rejected;
- read used exactly `max_bytes`, so truncation/current output completeness could not be known.

Embodiment:
- `web.fetch` is explicitly public-network-only;
- hostname required and current DNS answers resolved before request;
- every resolved address must be globally routable;
- loopback/private/link-local/reserved/unspecified/multicast/non-global targets rejected;
- mixed public+private DNS answers rejected;
- each redirect target revalidated before follow;
- final response URL revalidated;
- reads `max_bytes + 1`, clips to `max_bytes`, returns truthful truncation flag;
- response carries initial/final resolved target evidence, redirect chain, scope, byte budget;
- contract effect traits now include network_io, reads_external_state, public_network_only, redirects_revalidated, bounded_output;
- no `allow_private=true` escape hatch added: intentional internal service access should be a separate capability/authority surface.

Residual explicitly reported:
- stdlib urllib performs its own connection-time DNS resolution; pre-request/redirect/final validation reduces but does not cryptographically eliminate DNS rebinding TOCTOU.

Verification:
- public target accepted;
- loopback/private/link-local/unspecified IPv4/IPv6 rejected;
- mixed public+private DNS answer rejected;
- redirect to private target rejected before superclass follow;
- bounded physical read/truncation verified;
- focused web/verify cluster 8/8 PASS;
- full V30 pytest suite PASS.

## A-019 — research plane bounds/cache/type-currentness defects
Severity: P1 control-loop/resource/correctness
Status: FIXED in V30 working tree

Observed:
- cache eviction branch referenced undefined variable `v` once the cache exceeded its cap;
- cache dictionary/byte accounting had no lock despite threaded server execution;
- default in-memory research cache cap was 512 MiB;
- requests materialized whole HTTP response via `.text` before parsing;
- `research.hunt` could issue up to five sequential queries with 20s timeout each (~100s worst-case model occupation);
- one failed later query discarded the whole hunt rather than preserving earlier successful evidence;
- typed zero-result response incorrectly fell through to dict indexing because empty `results=[]` was falsey;
- starmap expected mapping `.get()` while dedupe/rank produced typed `RankedResearchHit`, so a non-empty real hunt could crash during topology build.

Embodiment:
- cache now protected by `RLock` and byte accounting is corrected;
- cache cap reduced to 64 MiB default; oversized single entries are not cached;
- arXiv HTTP uses streamed body with 2 MiB hard response cap and bounded per-request timeout;
- individual arXiv search clamps max_results to 1..PER_QUERY_MAX_RESULTS and validates sort vocabulary;
- hunt wall budget defaults 20s, server-capped 30s;
- each query receives only current remaining wall budget (capped by request timeout);
- no new query starts after budget exhaustion;
- per-query arXiv failures become structured `query_errors`; earlier successful evidence is retained;
- hunt reports partial/budget_exhausted/queries_attempted/queries_planned/elapsed_ms/decision_note;
- typed empty results are handled without falsey fallback;
- starmap now accepts mapping or typed objects exposing `to_dict()`.

Verification:
- cache-over-cap regression PASS;
- concurrent cache put/get stress PASS;
- oversized streamed body rejection PASS;
- partial-result preservation PASS;
- wall-budget admission PASS;
- effect-trait/currentness contract PASS;
- `tests/test_research_bounded_control.py`: 6/6 PASS;
- full V30 pytest suite PASS.

## A-020 — protocol observation could silently initialize governance state
Severity: P0/P1 truth/continuity defect
Status: FIXED in V30 working tree

Observed:
- `protocol.status()` defaulted `initialize=True`;
- `evaluate_mode_gate()` called `ensure_protocol()` despite claiming to evaluate without mutating state;
- therefore status/guard reads on a legacy/uninitialized project could create GENESIS and convert absence into governance state merely by observing it;
- empty ProtocolSnapshot defaults would also have falsely represented absence as STANDARD/DISCUSSION.

Embodiment:
- new `protocol_is_initialized()` read predicate in protocol store;
- `protocol.status` is non-initializing by default;
- absent protocol returns `initialized=false`, `state=null`, ledger `present=false`, event_count=0/head=null;
- guard on absent protocol returns allowed legacy behavior with `initialized=false` and current_mode=null, without creating files;
- initialized status still verifies ledger and returns full current state;
- protocol status/guard/ledger.verify capability cards explicitly declare read + non_initializing traits.

Doctrine/currentness repair:
- future GENESIS records no longer encode only the old shorthand PDVER loop;
- protocol_version advanced to 1.1, method_version=2.0;
- new GENESIS records carry the full current build metabolism:
  FIX_INTENDED_OUTCOME -> INSPECT_REALITY_ANCESTRY_CONSTRAINTS -> COMPOSE_BEFORE_INVENTION -> PROBE -> DERIVE -> VERIFY -> BUILD_SMALLEST_JUSTIFIED_CHANGE -> ATTACK -> ISOLATE_FAILURE -> STRIP_MUTATE -> EMBODY -> RECURSE -> CSC_SEMANTIC_GATE_RELEASE_QUALIFICATION;
- AXIOM-01 is carried in new genesis payloads;
- historical ledgers are not rewritten.

Verification:
- `tests/test_protocol_read_nonmutating.py`: 5/5 PASS;
- existing `tests/test_protocol_runtime.py`: PASS;
- combined protocol focused suite: 13/13 PASS;
- full V30 pytest suite PASS.

## A-021 — SOP/governed-ingestion truth, currentness, concurrency, and resource defects
Severity: P0/P1 governed-corpus integrity
Status: FIXED for current slice in V30 working tree; resource claim ceiling remains

Observed:
- Merkle parser referenced undefined `traversal_match` instead of `merkle_match`;
- read helpers created corpus directories while merely checking missing state;
- registered source could change after integrity verification while state still said `verified=true`;
- chunk acknowledgment could omit `content_sha256` and advance on token alone;
- no per-corpus synchronization across next/ack/complete/reset;
- repeated/concurrent `next_chunk` could mint competing ack tokens for the same unacked chunk;
- proceed guard trusted registration-time verification + completion without fresh source-currentness;
- ZIP archive metadata hashed by whole-file `read_bytes()`;
- package source had no file-count / uncompressed-size / single-member preflight limits;
- `sop.ingest.next_chunk` was falsely declared non-mutating despite persisting issued-token/cursor state.

Embodiment:
- Merkle parser fixed;
- read path helpers no longer mkdir; mutations create parents only at write boundary;
- per-corpus RLock serializes in-process state transitions;
- package preflight limits: 5000 files, 256 MiB total uncompressed, 64 MiB single member;
- ZIP archive identity uses streaming `sha256_file` + stat size;
- current source file hash revalidated before chunk delivery; stale source => `SOP_SOURCE_CHANGED`;
- ack requires exact `content_sha256`; omission => `SOP_CHUNK_SHA_REQUIRED`;
- unacked chunk is idempotently replayed with exact original content/hash/token instead of minting replacement authority;
- final guard re-inspects package and compares registered/current file identities + ZIP archive identity;
- guard explicitly reports `registered`, `integrity_verified_at_registration`, `source_current`, `ingestion_started`, `ingestion_complete`, `proceed_allowed`;
- proceed requires verified registration + fresh source + complete ingestion + no pending file receipt + completed_at;
- capability metadata now reflects actual effects; notably `sop.ingest.next_chunk` is a state mutation and therefore effectively approval-gated under current strict policy.

Verification:
- `tests/test_sop_ingest_integrity.py`: 6/6 PASS;
- `tests/test_sop_effect_contract.py`: 3/3 PASS;
- focused SOP cluster: 9/9 PASS;
- full V30 pytest suite PASS.

Open claim ceiling / next SOP seams:
- accepted package members are still materialized to bytes/text during package inspection and character-chunk delivery; package preflight prevents pathological sizes but true streaming member inspection/chunking is not yet embodied;
- RLock protects one receiver process only; multi-process shared-state locking is not yet proven;
- guard source re-inspection can be intentionally expensive for a large but accepted package; future async/currentness receipts may be preferable if governed corpora grow materially.

## A-022 — transfer authority/scope/currentness/integrity defects
Severity: P0/P1 binary transport authority
Status: FIXED for current slice in V30 working tree; export snapshot claim ceiling remains

Observed:
- project-scoped transfer path resolution still accepted absolute/escaped paths into other globally mounted roots;
- several direct HTTP transfer routes (meta/chunk/file/upload/finalize) lacked receiver API-key auth;
- mutating direct HTTP routes bypassed native tool approval/policy authority;
- import chunk SHA was optional despite per-chunk verification claims;
- transfer ticket manifests had no integrity digest;
- overwrite import ticket was not bound to destination state at ticket creation, allowing a later-appearing/changed destination to be overwritten under stale authority.

Embodiment:
- project_id now constrains resolved transfer paths to exact project root; unscoped transfer retains mount-root behavior;
- ticket manifests carry canonical `manifest_sha256` and `_load()` rejects corruption/drift;
- import create records destination identity (existence/type/size/mtime/SHA for existing files);
- finalize requires current destination identity to equal creation-time identity before atomic replace;
- chunk writes require exact `chunk_sha256`;
- all direct HTTP transfer routes require receiver API-key authentication;
- HTTP import/create, upload-chunk, and finalize delegate through native `dispatch_tool` with separate authority envelope, inheriting bound approval/policy/mode gates;
- direct adapter preserves flat success payload while adding policy receipt fields;
- capability effect traits now explicitly expose ticket scope, exact offset, required chunk hash, destination binding, full-hash verification, atomic replace, and postcondition verification.

Verification:
- exact project-scope escape rejection PASS;
- manifest tamper detection PASS;
- ticket expiry PASS;
- missing chunk SHA leaves offset unchanged PASS;
- overwrite destination drift blocks finalize PASS;
- happy import full-hash + atomic finalize PASS;
- concurrent same-offset writes: exactly one advances PASS;
- all eight direct HTTP route classes reject missing API key PASS;
- mutating direct HTTP adapter delegates to native authority dispatch PASS;
- effect-contract checks PASS;
- `tests/test_transfer_plane_hostile.py`: 10/10 PASS;
- full V30 pytest suite PASS.

Claim ceiling / residual:
- export ticket records full source SHA and size/mtime, and each chunk carries its own SHA; ordinary source changes are detected before reads;
- export does not stage an immutable source snapshot. A deliberately engineered in-place rewrite preserving cheap stat identity could evade pre-read currentness until the client compares the fully assembled payload against the ticket SHA. Do not claim immutable export snapshot semantics yet.

## A-023 — plugin reload partial mutation, stale ghosts, collision, and stale-health defects
Severity: P0/P1 capability-surface currentness
Status: FIXED in V30 working tree

Observed:
- plugins registered directly into the live registry while loading sequentially;
- a plugin could register one or more tools and then raise, leaving a partial capability surface;
- reload did not remove stale plugin-owned tools before/after changed plugin contents;
- plugin/core name collisions could resolve differently at initial bootstrap vs later reload because core registrations occur after initial plugin load;
- loader inserted candidate modules into `sys.modules` without rollback on failure;
- `_load_plugins()` rebound `_PLUGIN_LOADS` / `_PLUGIN_ERRORS`, while state-health dependencies held references to old list objects, causing stale reload/health reporting;
- load records carried module/path but no source identity.

Embodiment:
- plugin source load records now include SHA-256;
- loader restores prior `sys.modules` state if any candidate plugin load/register fails;
- plugin registration occurs into an isolated candidate ToolSpec registry;
- duplicate plugin capability names are rejected;
- plugin/core capability collisions are rejected;
- live registry is changed only after the full candidate set loads successfully;
- prior plugin contribution remains live on failed reload;
- removed plugin files remove their former plugin-owned tools on successful reload;
- core registry remains separate from plugin contribution ownership;
- registry read/dispatch/catalog surfaces snapshot under registry lock;
- reload serialized under dedicated reload lock;
- plugin bookkeeping lists are updated in place, preserving references held by health/state tools;
- generation + plugin contract digest + source hashes + changed flag + exact reload receipt exposed;
- native lab health now includes plugin runtime currentness; older dependency fixtures receive a compatibility projection rather than failing.

Verification:
- partial registration then crash leaves live registry byte-for-byte/object-identical PASS;
- duplicate plugin capability transaction rejection PASS;
- core collision rejection/core tool untouched PASS;
- removed plugin stale-tool cleanup PASS;
- source change alters plugin source hash + plugin contract digest PASS;
- bookkeeping object identity remains stable PASS;
- failed reload reports error while preserving previous plugin contribution/generation PASS;
- `tests/test_plugin_transactional_reload.py`: 7/7 PASS;
- prior optional-browser aggregate health regression PASS;
- full V30 pytest suite PASS.

Claim ceiling:
- plugin code remains trusted local executable code; this transaction prevents partial/stale registry state, not malicious in-process Python from deliberately reaching other runtime globals;
- no sandbox/process isolation for plugin execution is claimed.


## A-017 — sync subprocess output was response-bounded but not execution-bounded
Severity: P1 shared resource/control-plane defect
Status: FIXED in V30 working tree

Observed:
- `run_subprocess_envelope()` used `subprocess.run(..., capture_output=True)`;
- callers such as `verify.gates` requested bounded stdout/stderr, but Python first materialized the entire child output in memory and only then sliced to the configured response ceiling;
- therefore a noisy approved command could exhaust receiver memory while still returning a nominally bounded envelope.

Affected shared callers include:
- synchronous execution/Python run;
- Git operations;
- `verify.gates`;
- semantic probes/search;
- selected state cleanup/reset paths.

Embodiment:
- shared sync subprocess output now spools stdout/stderr to local temporary files while the child runs;
- only the requested bounded prefix is read back into the envelope;
- truncation is derived from capture-file size;
- timeout preserves typed `TIMEOUT` semantics and kills/waits the launched process;
- stdin is disconnected (`DEVNULL`) to prevent synchronous server calls from waiting for interactive input;
- shell remains disabled;
- temporary capture directory is removed after envelope construction.

Verification:
- `tests/test_subprocess_bounded_capture.py`: 3/3 PASS
  - multi-megabyte stdout/stderr bounded to 4 KiB/3 KiB respectively;
  - truncation flags true;
  - capture temp directory cleaned;
  - nonzero exit semantics preserved;
  - timeout semantics preserved with bounded output.
- focused cross-plane regression cluster (subprocess + verification + Git + env isolation): 14/14 PASS.
- full V30 suite PASS.

Law embodied:
`BOUNDED RESPONSE != BOUNDED EXECUTION.`
`RETURN DECISION INFORMATION EARLY; STORE BULK WORK LOCALLY.`

## A-018 — verification plane lacked bounded gate cardinality and explicit evidence claim ceiling
Severity: P1 verification/agent-contract defect
Status: FIXED in V30 working tree for current `verify.gates` scope

Observed:
- risk/effect truth had already been corrected: `verify.gates` was high-risk, approval-required, mutation/execution class, and custom gates were proven capable of mutating project state;
- cwd was already resolved through canonical `safe_project_cwd()` using resolved-root confinement;
- however input/output schemas were generic objects;
- gate list had no hard cardinality ceiling;
- `passed=true` meant subprocess exit zero but the receipt did not explicitly state that this is command-exit evidence rather than arbitrary semantic truth.

Embodiment:
- max 32 gates per synchronous verification call;
- per-gate timeout remains server capped at 600s;
- output remains physically/response bounded through A-017 shared subprocess mechanism;
- typed nested input schema now exposes project_id/cwd/gates/stop_on_fail/timeout_each and `maxItems`;
- typed output schema now exposes overall status, evidence scope, semantic-claim ceiling, requested/attempted gates, stopped-early, timeout, duration, and results;
- per-gate receipt includes `evidence_scope=declared_gate_command_exit`;
- aggregate receipt includes:
  - `evidence_scope=declared_gate_command_exit_only`
  - `semantic_claim_verified=false`
  - requested/attempted gate counts
  - stopped-early flag
  - timeout_each_seconds
  - total duration.
- capability effect traits now additionally expose project-scope enforcement, bounded output, bounded gate count, and command-exit-only evidence semantics.

Verification:
- `tests/test_verify_gate_contract_bounds.py`: 5/5 PASS;
- existing `tests/test_verify_gate_effect_truth.py`: 2/2 PASS;
- shared bounded subprocess tests: 3/3 PASS;
- focused verification cluster: 10/10 PASS;
- full V30 suite PASS across **195 collected tests** with only the existing conditional Windows symlink-privilege skip.

Claim ceiling:
`verify.gates` verifies the exit/result behavior of the declared gate commands. It does not automatically elevate a zero exit code into proof of an arbitrary higher-order semantic claim unless that claim is separately defined/qualified by the caller/workflow.

Next frontier:
web/network target authority, SSRF, redirects, private-range/DNS currentness, and bounded response behavior.


## A-024 — `web.fetch` contract/currentness/credential/header/distillation gaps
Severity: P1 public-network authority + agent-contract truth
Status: FIXED in V30 working tree for current public-read capability scope

Prior earned baseline (A-018):
- http/https only;
- current DNS answers validated before initial request;
- every address must be globally routable;
- mixed public/private answers rejected;
- redirects revalidated before follow;
- final URL revalidated;
- response body physically bounded via `read(max_bytes + 1)`;
- initial/final target evidence and explicit DNS rebinding residual already returned.

Remaining gaps found:
- embedded URL username/password/userinfo was not explicitly rejected;
- URL length/control characters and User-Agent length/control/header injection had no explicit Runtime contract;
- redirect limit was only an implicit urllib default rather than a declared bound/receipt;
- `web.fetch` input/output schemas were generic objects;
- successful HTTP status was not surfaced;
- DNS validation evidence had no validation timestamp;
- raw body truncation could be false while distilled text was silently capped to 200k characters without a separate `text_truncated` fact.

Embodiment:
- URL length capped at 8192 characters;
- URL control characters rejected;
- embedded URL credentials/userinfo rejected with `WEB_CREDENTIALS_FORBIDDEN` before DNS/follow;
- User-Agent length capped at 512 characters and control/newline characters rejected;
- redirect ceiling made explicit at 5 and returned as `redirect_count` / `redirect_limit`;
- DNS target receipts include `validated_at_unix_ms`;
- successful `http_status` exposed;
- raw-body `truncated` and distilled `text_truncated` are separate facts;
- distilled text maximum explicitly returned as `text_max_chars`;
- typed input schema exposes url/user_agent/timeout/max_bytes bounds and rejects additional properties under strict validation;
- typed output schema exposes target/redirect/status/body/text/currentness/residual fields;
- capability effect traits additionally expose bounded redirects, URL-credential rejection, header-control rejection, DNS validation evidence, and explicit DNS-rebinding residual disclosure.

Residual / claim ceiling preserved:
- stdlib urllib performs its own connection-time DNS resolution; pre-request/redirect/final validation reduces but does not pin the socket to the validated address set. DNS-rebinding TOCTOU is therefore explicitly disclosed rather than falsely claimed eliminated.
- public `web.fetch` remains a credential-free external-read capability. Intentional authenticated/internal network access should be a distinct authority surface rather than an escape hatch.

Verification:
- existing SSRF/network-scope suite: 6/6 PASS;
- new `tests/test_web_fetch_contract_currentness.py`: 8/8 PASS;
- combined web qualification: **14/14 PASS**;
- full V30 suite PASS across **203 collected tests**, with only existing conditional Windows symlink-privilege skip.

Code/test identities:
- `baseline/pcmmad_receiver/lab_tools_ops.py` SHA-256 `fc8be362d8af28a6b7ba784e924dc781e1aef7598d79c983658778310b7e2c7e`
- `tests/test_web_fetch_network_scope.py` SHA-256 `5f499cf6d18d94742a095b2d7d8c00a121fc9f4e946595496c4bee00ea21b856`
- `tests/test_web_fetch_contract_currentness.py` SHA-256 `4bea1104854bdf15710a2ae4120388f749f6bf4a6994edda2819bdacca89f679`.

Next frontier:
continuity/context rehydration ranking + cache-currentness, because root-level rehydration has already been observed selecting `.pcmmad_sync_runs` ahead of registered continuity and briefly returning stale indexed excerpts after a manifest/file update.


## A-025 — Continuity rehydration conflated lexical relevance/recency with current authority
Severity: P0/P1 continuity-currentness / fresh-instance rollback defect
Status: FIXED in V30 working tree through ICF-CS v1.0 embodiment

Observed during real thread rollover:
- generic root-level rehydration could select `.pcmmad_sync_runs` execution logs ahead of registered continuity surfaces because transient/internal directories were normal recursive search candidates;
- after a registered Live Shadow update, rehydration could briefly return an older indexed excerpt because index-cache validity was TTL-only;
- required SOP surfaces `state.doctrine_snapshot`, `state.revisit_ledger`, and `state.trace_matrix` were classified but omitted from normal rehydration priority;
- core recovery anchors appeared only when lexical topic terms happened to match them, allowing a recent/noisy artifact to become easier to retrieve than current authority;
- root-level `.pcmmad_tmp_*` scratch files from artifact-update staging were also eligible as generic evidence.

Governing standard adopted:
**Intent–Constraint–Frontier Continuity Standard — ICF-CS v1.0**

Core law:
**DIRECTION != CONSTRAINTS != FRONTIER != HISTORY**

Authority laws preserved:
- `HISTORICAL_HANDOFF != CURRENT_INGRESS`
- `DONOR != AUTHORITY`
- `RECENT_TIMESTAMP != CURRENT_AUTHORITY`
- `STALE_GREEN != CURRENT_EVIDENCE`
- `CACHED_EXCERPT != CURRENT ARTIFACT WHEN SOURCE IDENTITY CHANGED`.

Registered generic doctrine:
- `state/doctrine_snapshot/INTENT_CONSTRAINT_FRONTIER_CONTINUITY_STANDARD.md`
- SHA-256 `0bd3bf72203dbf65d93dd68b66cf1502b64e304ec7298ae27068afb7eb7e06f0`.

Registered current ingress pointer:
- `checkpoints/ICF_CS_CURRENT.md`
- SHA-256 `b2206342e04d7d6185f8b804b6be5ecb505b3675e4958decd39eda37899e03cc`.

Embodiment in `context_engine.py`:
- new authority classes:
  - `state.current`
  - `continuity.icf_standard`
  - `continuity.intent`
  - `state.next_steps`
  - `state.doctrine_snapshot`
  - `state.revisit_ledger`
  - `state.trace_matrix`
  - `continuity.live_shadow`
  - `continuity.design_thread_stream`;
- root/project rehydration seeds these authority anchors in ICF cold-start order before topic evidence;
- authority anchors consume a bounded share of the caller budget so topic evidence still has room;
- topic search excludes already-seeded paths, preventing duplicate authority rows/budget waste;
- Doctrine/Revisit/Trace are first-class rehydration priorities;
- default recursive search/rehydration excludes transient/internal directories such as `.pcmmad_sync_runs`, VCS internals, caches, virtual environments, `node_modules`, and `_v30_backups`;
- `.pcmmad_tmp_*` and generic `.tmp` scratch files are excluded from default recursive context discovery;
- explicit targeting of an internal path/file remains available;
- index cache key canonicalizes resolved path;
- cache validity now binds canonical path + file size + `mtime_ns`, not TTL alone;
- cache state is protected by an `RLock`;
- typed `IndexCacheStats` now exposes `source_currentness`;
- rehydration response includes ICF-CS version, selected authority classes, and cold-start separation law.

Hostile qualification:
- new `tests/test_icf_cs_rehydration.py`: 6/6 PASS;
- context/ICF combined cluster: 20 PASS / 1 conditional Windows symlink-privilege skip;
- same-size file rewrite with forced `mtime_ns` change invalidates cached search content immediately;
- default root search ignores `.pcmmad_sync_runs` and `.pcmmad_tmp_*` topic matches;
- explicit internal-path search still works;
- root rehydrate seeds all nine ICF authority classes even when the query only matches transient noise;
- Live Shadow update is visible on the next rehydrate after warming the index;
- direct V30 rehydration against the actual `PCMMAD_RECEIVER_LAB` project root returned:
  - all nine ICF authority classes in order;
  - `unique_paths=true`;
  - `open_seams=[]`;
  - no sync/scratch noise;
  - cache currentness `canonical_path+size+mtime_ns`.
- 20 actual root-level `.pcmmad_tmp_*` scratch files from earlier artifact staging were identified and removed.
- complete V30 suite GREEN across **209 collected tests**, with only the existing conditional Windows symlink-privilege skip.

Current code/test identities:
- `baseline/pcmmad_receiver/context_engine.py` SHA-256 `a422f0a4f89456752e7ca222ff45e2fb71f92fd426b4dca7c60181451786ae5d`
- `baseline/pcmmad_receiver/api_wire_common.py` SHA-256 `75dfbe18f8323dc702d4cd99ea59d88bcfed315af53da9417570fc6464f0c541`
- `tests/test_icf_cs_rehydration.py` SHA-256 `99d2326b5fcbc0068ef3d1651e2da9cd70e95a08eb7e72cf30b9ae926fab4f90`.

Claim ceiling:
- this rehydration behavior is embodied/qualified in the V30 working tree only; the currently live receiver remains unpromoted and may still exhibit older root-level ranking/cache behavior.
- path+size+mtime_ns is a strong practical currentness identity, not a content digest. Higher-authority/digest-bound indexing can be added only if evidence shows timestamp/size identity is insufficient.

Next frontier:
reconcile the remaining Commander’s Intent open checklist against the current V30 tree/audit so no already-earned mechanism is accidentally reopened and no genuinely open release seam is hidden by stale status.


## A-026 — 28 native capabilities still exposed unknown/empty effect contracts
Severity: P1 capability-authority / adapter-discovery defect
Status: FIXED in V30 working tree for current 99-tool registry

Observed during registry reconciliation after ICF-CS adoption:
- 99 native tools / 16 families were present;
- 28 tools still returned `side_effect_class="unknown"` and empty `effect_traits`;
- these cards are future authority/discovery inputs for MCP, OBE/Skills, HUD, and policy, so leaving them unknown would force clients to guess from names;
- `mutating=false` is already a disproven proxy for effect truth.

The 28 affected tools covered:
- browser observational/capture tools;
- HUD/restart status tools;
- doctrine invariant reads;
- filesystem read/glob/grep/tree/zip;
- lab health/session/reflexion reads;
- project file/context/model/archive reads;
- semantic health.

Source-derived classifications:
- browser health/sessions/pages/content: `external_read` because they cross the local browser bridge/network and read external/browser state;
- browser screenshot: `external_interaction`, preserving `may_write_external_artifact` rather than falsely classing it as pure read;
- `lab.health`: `read_probe` because it reads Runtime/plugin/cache state and actively probes browser bridge health over network;
- `semantic.monster.health`: `read_probe` because it reads/hashes resources and spawns bounded Python dependency probes;
- project file search/rehydration: `read_cache` because they read project files while mutating only ephemeral index cache; rehydrate explicitly advertises `icf_authority_aware`;
- HUD status: `read_probe` over process/service health;
- restart status: read of persisted restart receipt/service state;
- doctrine/filesystem/project/model/archive/session/reflexion observational tools: explicit `read` with appropriate scope/boundedness traits.

Embodiment touched registration modules only; runtime behavior/policy was not intentionally changed:
- `lab_tools_browser.py`
- `lab_tools_state.py`
- `lab_tools_semantic.py`
- `lab_tools_doctrine.py`
- `lab_tools_filesystem.py`
- `lab_tools_project.py`
- `lab_plugins/operator_control.py`
- `restart_control.py`

Backup root:
`baseline/pcmmad_receiver/_v30_backups/AUDIT_EFFECT_CLASSIFICATION_V1`

Hostile registry invariant added:
`tests/test_capability_effect_completion.py`

It verifies:
- no native capability has unknown/empty effect contract;
- browser observation is explicit external read;
- screenshot preserves external-artifact claim ceiling;
- context search/rehydrate admit ephemeral cache writes;
- lab/semantic health probes do not masquerade as pure reads;
- local read families are explicit;
- HUD status is process/service probe.

Verification:
- focused effect/browser/HUD/semantic/ICF cluster: **34/34 PASS**;
- complete V30 suite: **GREEN across 216 collected tests**, with only the existing conditional Windows symlink-privilege skip;
- fresh registry readback:
  - tool_count = 99
  - unknown_side_effect_count = 0
  - empty_effect_traits_count = 0
  - effective_approval_required = 52
  - mutating_true = 47
  - side-effect classes now include read / read_cache / read_probe / read_reconcile / external_read / external_interaction / execution / mutation / ephemeral_mutation / runtime_mutation.

Current code identities:
- `lab_tools_browser.py` SHA-256 `9897debd140b28281a3bb8705c9d9c9fc16fc08a8adeac5598b2142670851189`
- `lab_tools_state.py` SHA-256 `084cfd11583f342de8676919c57ab6d6b374b8ad491bb6e6bea899d661990dac`
- `lab_tools_semantic.py` SHA-256 `76b6b11ac3b6cc220569e0e73fb2102f46c6c662ca0e492981498ca24008dbbf`
- `lab_tools_doctrine.py` SHA-256 `713418cc3845724e27991b36b8a20b9a6378c245a6c8787f1b7890dfbc19e4ed`
- `lab_tools_filesystem.py` SHA-256 `cbeff30b3d80ff517c8df3cf3a8d108006c32c6caa0cef98fa7de72d854fd48f`
- `lab_tools_project.py` SHA-256 `690f60b5410b4d506eacea2b53407d8f60f2c2de710fd32f089761feb535d847`
- `lab_plugins/operator_control.py` SHA-256 `af6e58abb0c74952a6eecd2e493f0b4f9c95f118c8c95e6a3a77100d5e09a108`
- `restart_control.py` SHA-256 `d3911384b2139e1fdda2e2f9b8026153dcda2a41076c1173bb09f6c8eeb05714`
- `tests/test_capability_effect_completion.py` SHA-256 `24c8ad5ab87783d49a39dba104ca4dcb378bf4fa1045646cb2c6b0e612def9cc`.

Claim ceiling / separation:
- this closes current **effect classification**, not the final native schema design;
- 67 current tools still use generic input schemas and 97 generic output schemas. That evidence is retained for later contract/projection work, but final schema redesign remains explicitly locked until whole-runtime convergence;
- effect metadata is descriptive contract truth. Automatic policy derivation from effect traits remains separately unearned unless hostile evidence supports it.

Next frontier:
capability **availability/currentness normalization** and schema/runtime/policy/imported-adapter parity should be distinguished empirically before further mutation.

## A-027 — Compact 30-operation OpenAPI adapter taught legacy inline boolean approval after Runtime moved to bound authority
Severity: P0 adapter-security / Runtime-projection parity defect
Status: FIXED AND QUALIFIED in V30 working tree

Observed:
- native `/lab/dispatch` and batch dispatch already accept authority as a separate envelope;
- Runtime approval is target/argument/contract-bound, short-lived, integrity-checked, single-use challenge authority;
- legacy embedded `payload.approval.permit` remains transitional/unbound only;
- the compact 30-operation OpenAPI/Custom-GPT compatibility template still instructed clients to place `{"approval":{"permit":true}}` inside capability payload;
- restart controller generates the active imported schema from this exact compact template, so the mismatch was an active compatibility/security problem rather than archival schema debt.

ICF-CS currentness consequence:
- the template was edited after the previous 216-test full-suite green;
- qualified ICF-CS correctly demoted that green result to historical evidence for the preceding bytes until this patch was requalified.

Embodiment:
- added reusable `BoundApprovalAuthority` schema with:
  - required `approval_handle`
  - required explicit `permit`
  - optional `operator_id`
  - optional `provenance`
  - `additionalProperties=false`;
- `LabDispatchRequest` now carries capability arguments only in `payload` and separate top-level `authority`;
- each `LabBatchRequest.steps[]` entry now carries capability arguments in `payload` and separate per-step `authority`;
- payload descriptions explicitly state that approval/authority metadata does not belong inside capability arguments;
- dispatch description tells clients to retry with exact challenge in the separate authority envelope and not embed approval inside payload;
- batch description states per-step bound authority and preserves non-atomic batch semantics;
- schema metadata advertises `x-pcmmad-authority-model=bound-authority-envelope-v1`;
- compact compatibility surface remains exactly **30 operations**;
- no MCP/native routes were added merely because the Runtime supports them;
- final schema redesign remains separately locked/deferred.

Hostile/parity regression:
`tests/test_compact_schema_authority_parity.py`

It proves:
- operation count remains 30 with unique operation IDs;
- dispatch projects separate authority;
- batch projects authority per step;
- authority contract requires handle + permit and is closed to arbitrary fields;
- compact schema no longer teaches legacy inline boolean approval;
- endpoint descriptions explain the separate bound authority model;
- restart controller still publishes this exact compact template to the active schema path.

Focused qualification:
- compact schema parity
- native bound approval dispatch
- approval authority integrity/replay/currentness
- HUD approval forwarding/smuggling rejection
- transfer HTTP→native authority delegation
- protocol non-expansion of compact action schema
- schema-authority constraint pipeline

Result: **59/59 PASS**.

Complete V30 suite on current schema bytes:
- **223 collected tests**
- GREEN
- only the existing conditional Windows symlink-privilege skip.

Current identities:
- compact schema SHA-256 `ae1459582f515395ca58905133d643875ef1ebfd168ce5b36bcc665077c1433e`
- parity test SHA-256 `6d54a90aa020e8c958beb0e1356705544849f2dae94d13ed1b25a27802806f51`.

Promotion:
- compact adapter authority projection is now EARNED for V30 working-tree scope;
- previous 216-test green remains historical evidence but is superseded by current 223-test green for these bytes.

Claim ceiling:
- this is a compatibility/security correction to the inherited 30-operation adapter, not the final schema redesign;
- V30 working-tree schema is not the live imported schema until explicit promotion/restart of V30;
- legacy inline approval still exists in Runtime as a transitional compatibility path when enabled, but the compact adapter no longer advertises or depends on it.

Next frontier:
return to native capability availability/currentness: distinguish registered capability existence from executable-now availability/blockers/currentness, then compare projection parity without freezing final schema ontology.

## A-028 — Native registry conflated capability registration with executable-now availability/currentness
Severity: P1 Runtime truth / capability-discovery currentness
Status: FIXED AND QUALIFIED in V30 working tree for current provider model

Observed after effect-contract completion:
- native cards described identity/schema/effects/authority but had no first-class availability/currentness semantics;
- some registered capabilities could be unusable now because dependencies/providers were absent;
- semantic search already knew its default runtime could be unavailable, but that truth lived only inside semantic-specific health/search paths;
- browser capabilities could remain registered while the local browser bridge was down;
- treating `registered == available` would therefore create a false-green discovery surface;
- making `/lab/tools` perform hidden health probes was rejected because capability discovery must remain cheap, deterministic, and bounded.

Derived separation:

`REGISTRATION != CAPABILITY_AVAILABILITY != TARGET_HEALTH`

Examples:
- `lab.health` may be callable even when the browser bridge it reports on is down;
- `semantic.monster.health` may be callable specifically to explain why semantic search is unavailable;
- `semantic.monster.search` may be registered while its **default runtime** is unavailable;
- explicit per-call semantic path/runtime overrides may change search outcome and are therefore outside the default-runtime probe claim.

Embodiment:
- `ToolSpec` now carries static availability-contract metadata:
  - `availability_mode` (`resident` or `dynamic`)
  - `availability_scope`
  - `availability_provider_id`
  - optional provider callable;
- cards expose `availability` without executing providers;
- resident cards expose handler dispatchability using basis `registered_handler`; this does **not** claim target/input/result success;
- dynamic cards expose `status=unknown`, `available=null`, and `basis=explicit_probe_required` until an explicit currentness read occurs;
- availability semantics participate in `contract_digest`; transient probe results do not;
- new native capability `lab.capabilities.availability` performs explicit bounded currentness checks for requested tools only;
- request bound: max **32** tool names;
- unknown capability names fail closed;
- requested target capabilities are never invoked merely to check availability;
- shared provider probes are deduplicated once per request;
- provider exceptions become `status=unknown` with bounded error evidence, never fake green;
- returned rows include tool identity, registration state, mode/scope/provider, contract digest, status/available, blockers, basis, and checked timestamp.

Provider embodiments currently earned:

### Browser bridge
- all browser/procedure browser capabilities use shared dynamic provider id `browser_bridge`;
- scope `browser_bridge`;
- one bounded `/health` bridge probe is shared across all requested browser capabilities in one availability request.

### Semantic default search runtime
- `semantic.monster.search` uses dynamic provider id `semantic.monster.default_runtime`;
- scope explicitly states `default_runtime; per-call explicit path/runtime overrides may change outcome`;
- `semantic.monster.health` itself remains resident/callable because it is the diagnostic probe surface.

Hostile regression:
`tests/test_capability_availability_contract.py`

It proves:
- card listing never executes dynamic providers;
- resident availability means registered-handler dispatchability only;
- availability semantics change contract digest;
- shared providers probe once per request;
- provider exceptions fail to UNKNOWN rather than green;
- max-32 request ceiling and unknown-tool fail-closed behavior;
- actual browser cards share dynamic `browser_bridge` contract;
- semantic search is dynamic for default runtime while semantic health remains resident;
- semantic default-runtime failure does not overclaim explicit override impossibility;
- resident availability read does not invoke the target handler.

Qualification:
- new availability contract suite: **9/9 PASS**;
- adjacent effect/semantic/plugin/approval/HUD/MCP/lab-health currentness cluster: **60/60 PASS**;
- complete V30 suite on current bytes: **232 collected tests GREEN**, with only the existing conditional Windows symlink-privilege skip.

Direct current readback:
- native registry = **100 tools / 16 families**;
- one explicit request for `browser.health`, `browser.pages.list`, `browser.content`, `semantic.monster.search`, and `lab.health` performed exactly **2 provider probes**:
  - one shared browser bridge probe for all three browser capabilities;
  - one semantic default-runtime probe;
  - resident `lab.health` required no provider probe;
- current browser bridge result: `unavailable`, blocker `browser_bridge_unavailable`;
- current semantic default-runtime result: `unavailable`, blocker `no_qualified_python_runtime`;
- current `lab.health` result: `available`, basis `registered_handler`;
- this proves provider health is not collapsed into resident capability callability.

Current identities:
- `control_plane_models.py` SHA-256 `5644bd4e821bdf5ebaa3f102aff580f70c9d09ac396434eeb35690b96c2a28ce`
- `lab_tools.py` SHA-256 `f27b4029ae9377217f479f4888dc570eca06cea60c5251b3f918fee107497fbf`
- `lab_tools_browser.py` SHA-256 `9a592a039e780ff78a6e882aa222b17fb6dce83fd2e549fc9e56b2480171ca71`
- `lab_tools_semantic.py` SHA-256 `205a21b30373a78f62ea2872c03d4dc9bf429ea83b8d99ecb8e62933da6fe6f0`
- `tests/test_capability_availability_contract.py` SHA-256 `e37711ad26d7264e1d9efa44742909e71a8ff9c19cdb57fdb0e1f1552ef1a92a`.

Claim ceilings:
- current dynamic provider coverage is deliberately narrow and evidence-backed: browser bridge + semantic default search runtime;
- resident status proves handler registration/callability, not target health or successful execution for arbitrary arguments;
- semantic availability result applies to the resolved **default** runtime only; explicit per-call overrides can change outcome;
- availability reads are explicit probes and may perform bounded network/process/resource checks depending on provider;
- plugin-loaded capabilities default to resident-handler availability unless a future plugin mechanism explicitly supplies a dynamic provider; plugin code sandboxing remains separately unearned;
- automatic effect/availability→policy inference remains unearned;
- live receiver remains unpromoted and does not yet expose this V30 availability contract.

Next frontier:
reconcile remaining schema/runtime/policy/imported-adapter parity and identify which dynamic dependency/service families genuinely need first-class availability providers next, without turning native discovery into a health scan or beginning the locked final schema redesign.