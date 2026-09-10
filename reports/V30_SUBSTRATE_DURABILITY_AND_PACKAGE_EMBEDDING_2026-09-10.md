# V30 Substrate Durability + Package Embedding — 2026-09-10

Status: **DETACHED SOURCE CANDIDATE QUALIFIED / PUBLICATION PENDING**

Base Git/source head:
`01a5e1d75ccb6e1da310c7a2aa47922ccbe25bdc`

Scope: server only. No schema redesign, no live Runtime reload, no private UCM import, and no Microseed engineering work were performed.

## 1. Why this campaign exists

An external architecture review correctly identified that several state-bearing server paths were relying on weaker storage discipline than the authority layer above them, and that the source tree had no supported installed-package embedding boundary. The review also contained several overstatements; those were audited before mutation.

The architectural distinction retained from the review is:

`AUTHORITY_RIGOR != SUBSTRATE_RIGOR`

Operationally, five obligations remain separate:

`AUTHORIZATION != CONCURRENCY_CONTROL != DURABLE_ACKNOWLEDGEMENT != INTERRUPTION_RECOVERY != CONSEQUENCE_READBACK`

## 2. Verified pre-repair baseline

At base head `01a5e1d...`:

- 74 top-level Runtime Python modules;
- 34,592 Python source lines in `baseline/pcmmad_receiver/*.py`;
- 178 internal bare-import edges;
- zero explicit-relative internal imports;
- one import-cycle component: `lab_tools <-> lab_tools_filesystem`;
- `import pcmmad_receiver.lab_tools` failed with `ModuleNotFoundError`;
- `pip wheel .` failed because setuptools package discovery was not defined;
- complete Runtime qualification: **742 collected / 740 passed / 2 skipped / 0 failed**.

The existing substrate already contained a good `save_json_atomic`: same-directory temporary file, flush+fsync, atomic `Path.replace`, bounded Windows sharing-violation retry, and cleanup. The problem was inconsistent use, not absence of the primitive.

## 3. Session durability and note-write complexity

### Pre-repair

`lab_state.append_session_note` read the whole session JSON, appended one note in memory, then rewrote the whole file. Direct library callers therefore depended on external dispatcher fencing for lost-update protection, and each note was O(n) in accumulated session history.

### Repair

Session persistence now separates:

- bounded mutable metadata snapshot: `<session_id>.json`;
- durable append-only note journal: `<session_id>.notes.jsonl`;
- per-session cross-process serialization guard.

`append_session_note` now:

1. acquires the session storage guard;
2. verifies the session snapshot exists/is readable;
3. appends exactly one durable note row;
4. returns the folded `LabSessionRecord` view.

It does **not** rewrite the snapshot during the normal note path.

`get_session` preserves the public contract by folding legacy notes embedded in old snapshots plus the new note journal.

A 100-note hostile regression verifies the session snapshot bytes remain exactly unchanged across all 100 note appends.

`SESSION_NOTE_APPEND != SESSION_SNAPSHOT_REWRITE`

## 4. Shared byte-level serialization

A generic `cross_process_file_guard(path)` now lives in `shared_core` using the existing proven one-byte `msvcrt` / `fcntl` locking model. It carries no project-authority semantics.

Project mutation authority delegates its low-level file lock to that shared primitive and continues translating contention to its authority-specific `PROJECT_MUTATION_GUARD_BUSY` taxonomy.

`STORAGE_SERIALIZATION != MUTATION_AUTHORITY`

The shared `append_jsonl` primitive now performs:

- per-file cross-process serialization;
- append;
- flush;
- fsync.

This strengthens existing callers including session notes, Andon, reflexion, execution commit ledgers, worker commit ledgers, and legacy commit ledgers without sharing their semantic layers.

Hostile regression: four concurrent processes x 25 rows x ~4 KB payload each -> **100/100 valid unique JSON rows**.

## 5. Andon failure semantics

The demonstrated failure path was reproduced conceptually from source: the stop row was persisted, session parsing failed, and the recovery branch attempted `row.payload[...]` even though `AndonEventRecord` has no `payload`, masking the real failure with `AttributeError`.

Repair introduces explicit consequence/projection fields:

- `stop_recorded`;
- `session_pause_projected`;
- `session_update_error`.

`pull_andon` now durably records the stop first, then attempts the softer session-pause projection. Projection failure returns a record that says the stop is durable while pause projection failed; it does not mask the failure or imply that the stop itself disappeared.

`STOP_EVENT_RECORDED != SESSION_PAUSE_PROJECTED`

The local shadow `lab_state.append_jsonl` implementation was removed; `lab_state` uses the shared durable/serialized primitive.

## 6. Observation versus reconciliation

Audit confirmed that several nominal observation surfaces were actually performing reconciliation:

- `project.mutation.inspect` could reconcile expiry and therefore acquired the mutation transition guard;
- `execution.status`, `execution.output`, `execution.progress`, and `execution.wait` called job finalization and could write state / advance the queue.

This explained why a read-only inspection could encounter `PROJECT_MUTATION_GUARD_BUSY`: some reads were not actually read-only.

Repair:

- `project_mutation_authority.observe_lease` is a pure persisted-state read;
- native `project.mutation.inspect` is now `mutating=false`, `side_effect_class=read`, `non_reconciling`;
- explicit authority lifecycle operations retain guarded reconciliation;
- execution status/output/progress/wait observe persisted job state and do not finalize or advance the queue themselves;
- scheduler/supervisor machinery remains the reconciliation owner.

A dispatch-level hostile test holds the project transition guard and proves `project.mutation.inspect` still returns promptly.

`OBSERVATION != RECONCILIATION`

`READ_API SHALL NOT ACQUIRE MUTATION AUTHORITY MERELY TO MAKE THE READ MORE CURRENT`

## 7. Supported package embedding boundary

### Pre-repair

Runtime source relied on its own directory being injected onto `sys.path`; all 178 internal imports were bare top-level imports. Package import failed, and the repository could not build a wheel with default setuptools discovery.

### Repair

- all **178 internal import edges** are explicit package-relative imports;
- structural audit reports **0 bare internal imports**;
- `baseline/pcmmad_receiver/__init__.py` establishes the canonical package namespace without eagerly importing the runtime;
- `pyproject.toml` explicitly discovers the package from `baseline` and includes `lab_plugins` namespace content plus required package data;
- thin compatibility modules at `baseline/*.py` preserve legacy flat imports by aliasing directly to the canonical package modules;
- legacy-first and package-first imports resolve to the same module objects and same tool registry;
- existing test/tool bootstrap paths now use the supported `baseline` compatibility root rather than treating the package directory as a top-level module repository;
- `server.py` and `execution_worker.py` retain direct-file compatibility through a bounded package bootstrap before relative imports.

Verified package identity:

- package-only: **158 tools / 0 plugin errors**;
- package-first then legacy: same `lab_tools`, same `shared_core`, same registry;
- legacy-first then package: same identities;
- clean wheel build: PASS;
- clean target install: PASS;
- installed package: **158 tools / 0 plugin errors**;
- wheel contains Runtime package, `lab_plugins/transfer.py`, and flat compatibility modules.

`PACKAGE_IMPORT_WORKS != SINGLE_RUNTIME_IDENTITY`

The repair earns both.

## 8. A-042 historical recovery placement

The 13 A-042 WIP payloads plus `A042_WIP_INVENTORY.json` were confirmed to be frozen historical recovery evidence, not a live source fork.

They are moved byte-for-byte from:

`handoff/current/wip/`

to:

`handoff/archive/a042_wip_recovery_2026-09-07/`

Every archived payload retains the exact size and SHA-256 declared by the original inventory. The pinned `A042_PROJECT_MUTATION_AUTHORITY_WIP.py` remains exactly 20,926 bytes / SHA `5e294d1ae20601d9a5404f5b4712d82c676ca6acc55c9530a5787dc6239ed04e`.

`handoff/current/` now carries only `A042_HISTORICAL_WIP_RECOVERY_POINTER.md`; current snapshot manifest WIP entries are removed and the locator is manifested instead.

`HISTORICAL_RECOVERY_EVIDENCE != CURRENT_WIP`

## 9. Structural readback

Final detached candidate structural audit:

- package Python files including new `__init__`: 75;
- original runtime module count excluding `__init__`: 74;
- explicit-relative internal import statements: **178**;
- bare internal imports: **0**;
- cycle components: exactly one, `lab_tools <-> lab_tools_filesystem`;
- A-042 inventory declares 13 payload files and every archived hash matches;
- `handoff/current/wip` absent;
- current snapshot manifest has zero `wip/` entries;
- current historical locator is manifested;
- `lab_state` has no local `append_jsonl` definition;
- session note journal is active;
- note append does not call atomic snapshot publication;
- shared JSONL append uses cross-process guard + fsync.

The one import cycle is unchanged from the pre-repair architecture; this campaign did not invent or worsen dependency cycles.

## 10. Projection-level read truth and wire serialization

A final projection audit found the native read/reconcile split had not yet propagated through every HTTP wrapper.

Pre-repair:
- power `/project/execution/wait` polled through `_finalize`;
- direct execution `_status_payload` finalized jobs;
- direct output finalized jobs before reading logs;
- direct list explicitly drained the queue and finalized each job.

Repair:
- power wait polls persisted job records only;
- direct status/output/list read persisted job records without finalization or queue advancement;
- reconciliation remains owned by scheduler/supervisor and explicit mutating lifecycle operations.

Behavioral regressions wire `_finalize` / `_drain_queue` to fail if any of these observation paths touch them.

That audit also exposed two pre-existing response-model defects in the published parent:
- `ExecutionOutputResponse.to_dict()` called `TextWindow.to_dict()`, but `TextWindow` had no such method;
- `ExecutionListResponse.to_dict()` called `CorruptJobFileRecord.to_dict()`, but the corrupt-record model also lacked it.

Both models now provide explicit dictionary serialization, including a hostile corrupt-job diagnostic response.

`PROJECTION_READ != HIDDEN_RECONCILIATION`

`DIAGNOSTIC_PATH != SERIALIZATION_EXCEPTION`

## 11. Qualification

Focused substrate/package/authority/execution gate on final candidate:
- **63 passed / 13 subtests passed**.

Dedicated session/Andon durability gate after final append serialization:
- **9/9 PASS**.

Package embedding gate:
- **6/6 PASS**.

Complete Runtime on final candidate:
- **769 collected / 767 passed / 2 skipped / 0 failed**;
- Python 3.12.10.

Four-worker parallel qualification:
- `loadscope`: **767 passed / 2 skipped / 103 subtests passed**;
- `worksteal`: **767 passed / 2 skipped / 103 subtests passed**.

EOL-aware whitespace gate:
`git -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol diff --check` -> PASS.

The plain Git whitespace checker interprets repository CRLF as trailing whitespace and is not the governing gate for this Windows source tree; no destructive newline normalization was performed during final recovery.

## 12. Claim ceiling

Earned at detached-source depth:

- session note writes are O(1) with respect to prior note history at the write path;
- mutable session metadata is atomically published and cross-process serialized;
- shared JSONL append has serialization + flush + fsync;
- Andon durable-stop and session-projection outcomes are independently observable;
- read-only lease/execution observation no longer secretly reconciles state across native and HTTP projections;
- execution output/list wire diagnostics serialize correctly even for bounded windows and corrupt job-file records;
- installed package embedding works with full 158-tool Runtime and one module/registry identity;
- historical A-042 WIP is no longer presented as current source while exact evidence is preserved;
- full sequential and parallel Runtime qualification is green.

Not yet earned at this report stage:

- canonical-source publication;
- GitHub publication/readback;
- live Runtime reload;
- actual private UCM import;
- schema redesign;
- claim that every direct writer in the repository has undergone a complete durability classification.
