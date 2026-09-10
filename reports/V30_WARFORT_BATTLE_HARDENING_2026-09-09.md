# V30 Warfort Battle-Hardening Campaign — 2026-09-09

Status: **CANONICAL SOURCE QUALIFIED / PUBLICATION PENDING**

Base Git/source head:
`ecd99d600783dde06da718160c3fa02655fc3897`

Base source qualification before warfort mutation:
- complete Runtime: **676 collected / 675 passed / 1 conditional skip / 0 failed**.

Campaign doctrine:

`WARFORTS NOT CATHEDRALS`.

The goal was not another architecture pass. The goal was to bring a disposable clone to the exact current Git/doctrine/continuity frontier and attack consequence boundaries, currentness, concurrency, crash recovery, filesystem namespace identity, canonical serialization, transfer identity, archive extraction, and parallel-test isolation until deterministic defects stopped surfacing.

Live Runtime was not mutated/reloaded during this campaign.

## 1. Current-state parity fixture

A read-only copy of the registered server continuity/checkpoint state was created under:
`quarantine/warforts/current_state_fixture/`

Fixture manifest:
- bytes: `11030`;
- SHA-256: `7e3e6946fe88245dffbd738a452451d4ae56e25754bdfb6693acf45dcd802c18`.

The fixture includes current state, next steps, doctrine snapshot, revisit, trace, live shadow, DTS, and current checkpoints. It was exercised through the actual ICF-CS v1.2 ingress path in non-user/non-research mode and successfully bound the exact v1.2 standard rather than relying on synthetic labels alone.

## 2. Fresh-ingress TOCTOU defects

The first hostile race suite found four deterministic currentness holes:

1. ICF-CS standard bytes could change after the initial currentness check while project context was being assembled.
2. RES could become materially stale after its initial handoff-readiness check but before ingress returned READY.
3. UCM authoritative head could advance after `read_core` but before ICF ingress returned READY.
4. `ucm.read_core` itself could assemble one packet across two different ledger heads.

Repairs:
- final end-of-ingress exact ICF standard reread;
- final required RES readiness reread;
- final required UCM authoritative head/snapshot reread bound to packet head;
- final UCM packet head reread after core construction.

The returned ingress packet is now consequence-bound to the end of the composed read sequence.

Earned laws:

`INGRESS_START_CURRENT != INGRESS_END_CURRENT`.

`COMPOSED_READINESS_REQUIRES_FINAL_CONSEQUENCE_READBACK`.

## 3. UCM crash/recovery defects

Pressure simulated an authoritative ledger append succeeding followed by derived snapshot materialization failure.

Before repair:
- idempotent retry correctly recognized the already-landed event;
- but it returned replay success while the derived snapshot remained stale;
- subsequent bounded reads could still fail until separate compaction.

Repair:
- idempotent consequence replay now checks snapshot currentness;
- when the authoritative ledger already contains the exact consequence and the snapshot trails it, replay rebuilds the bounded derived snapshot cache before returning success.

`CONSEQUENCE_REPLAY != RECOVERY_COMPLETE WHILE_DERIVED_STATE_STALE`.

Additional recovery attacks proved:
- truncated ledger does not allow a newer snapshot to masquerade as current;
- corrupted ledger tails fail integrity rather than partial-successing;
- corrupted snapshot section objects fail as `MEMORY_SNAPSHOT_CORRUPT`;
- 120-event canonical churn retains bounded derived snapshots while the ledger remains authoritative;
- cross-process same-head CAS yields one commit + one currentness failure;
- cross-process same-idempotency mutation yields one consequence + one replay.

## 4. Semantic ambiguity defects

UCM identity/referent resolution previously sorted equal-precedence entries by stable key. Two conflicting top-precedence active meanings therefore produced an arbitrary deterministic answer rather than a semantic conflict.

Repairs:
- conflicting top-precedence identities -> `UCM_IDENTITY_AMBIGUOUS`;
- conflicting top-precedence referents -> `UCM_REFERENT_AMBIGUOUS`;
- equal-precedence duplicate semantic values remain resolvable;
- historical/superseded entries do not create active ambiguity.

A related problem allowed multiple current collaboration contracts, later selected by key ordering. Canonical UCM now enforces one current collaboration contract; a second current sibling fails as `UCM_COLLABORATION_CONFLICT` and change must use explicit transition semantics.

`EQUAL_PRECEDENCE != LICENSE_FOR_ARBITRARY_TIEBREAK`.

`MULTIPLE_CURRENT_CONTROL_CONTRACTS != DETERMINISTIC_STATE`.

## 5. Tenant/filesystem identity defects

### UCM profile case aliasing

On a case-insensitive Windows filesystem, `CaseUser` and `caseuser` addressed one directory while ledger records preserved distinct profile strings. This could corrupt or cross logical tenant identity.

Repair:
- UCM profile IDs canonicalize ASCII case after namespace validation;
- legacy event profile IDs are compared through the same canonical identity during readback.

### Project case aliasing

Existing project `CanonicalProject` could be reopened as `canonicalproject`, again yielding two logical IDs over one filesystem directory.

Repair:
- project IDs preserve their established spelling/lineage;
- when an existing sibling differs only by case, a case-variant alias request fails before state read/write.

### Namespace-special IDs

Project/profile validators accepted filesystem-special names such as:
- `.` and `..`;
- trailing-dot/space aliases;
- Windows devices `CON`, `NUL`, `PRN`, `AUX`, `COM1..9`, `LPT1..9`, including extension forms such as `con.txt`.

They are now rejected before path construction.

`FILESYSTEM_CASE_VARIANT != DISTINCT_LOGICAL_IDENTITY`.

`REGEX_VALID_ID != FILESYSTEM_NAMESPACE_SAFE_ID`.

## 6. Hardlink consequence escape

Path containment was not sufficient for mutable files.

A real NTFS hardlink attack proved that an in-project pathname could share its inode with an external file. Both overwrite and append through the in-project name mutated the external file while pathname containment still passed.

Repair:
- shared `ensure_safe_mutation_target_identity` rejects multiply-linked existing regular files before mutation;
- the same guard is wired into every discovered direct write path:
  - native project write;
  - mounted filesystem write;
  - HTTP/power project write;
  - legacy commit/write path.

Direct route regressions prove the protection is not confined to one API surface.

`PATH_CONTAINMENT != INODE_OWNERSHIP`.

`PROJECT_LOCAL_PATHNAME != PROJECT_OWNED_FILE_IF_HARDLINKED`.

## 7. Canonical JSON poison

Python JSON permissiveness was broader than the portable canonical UCM contract.

Hostile writes showed:
- `NaN` accepted;
- `+Infinity` accepted;
- `-Infinity` accepted nested in objects/lists;
- lone UTF-16 surrogate crashed hashing via raw `UnicodeEncodeError`;
- very deep nested JSON remained accepted.

Repair:
- iterative pre-hash canonical JSON validation;
- only JSON scalar/container types allowed;
- all floating-point values must be finite;
- all strings and object keys must strict-encode UTF-8;
- depth bounded at 64;
- node count bounded at 50,000;
- invalid data fails as `UCM_CONTRACT_INVALID` before fingerprinting/hash/append.

Property tests exercise finite-float acceptance, all IEEE non-finite rejection, and the exact depth boundary.

`CANONICAL_JSON != PYTHON_JSON_PERMISSIVENESS`.

`INVALID_CANONICAL_VALUE != HASHING_EXCEPTION`.

## 8. Windows ZIP namespace defects

The existing archive hardener already rejected:
- traversal;
- absolute paths;
- drive-qualified paths;
- UNC paths;
- symlink/special ZIP entries;
- basic casefolded duplicate destinations.

Warfort attacks found it still accepted Windows-specific destination aliases:
- NTFS alternate data stream names (`file.txt:stream`);
- reserved device components (`CON`, `NUL`, `COM1`, etc.);
- trailing-dot paths;
- trailing-space paths;
- distinct ZIP strings that collapse to the same Windows destination identity.

Repair:
- every POSIX ZIP component is checked against Windows destination semantics;
- ADS/colon-qualified components rejected;
- Windows-forbidden component characters rejected;
- reserved device stems rejected even with extensions;
- trailing-dot/space aliases rejected;
- duplicate normalized destinations use Windows destination identity rather than naïve string casefolding.

New + pre-existing archive hardening suite: **17/17 PASS**.

`ZIP_MEMBER_STRING != WINDOWS_EXTRACTION_IDENTITY`.

## 9. Windows atomic replace contention

Repeated four-worker full-suite runs exposed an intermittent but real Runtime failure in execution worker restart recovery.

Observed failure:
- worker/receiver contention on active job JSON;
- `NamedTemporaryFile -> Path.replace(job.json)` intermittently failed with WinError 5 / WinError 32;
- teardown could then fail deleting the still-open job file.

JUnit capture localized the exact primitive: `shared_core.save_json_atomic()` performed one replacement attempt with no transient sharing-violation retry.

Repair:
- fsync temp file before publication;
- bounded retry window `0.75s`;
- exponential delay from `2ms` up to `50ms`;
- retry only transient Windows sharing/access violations (`winerror 5/32/33` / Windows PermissionError);
- non-transient errors fail immediately;
- temp file cleanup occurs on success or failure;
- atomic replacement semantics retained; no in-place partial-write fallback.

Direct fault-injection regression:
- two transient failures then success -> commits correct JSON;
- persistent lock -> visible failure + original file intact + no temp leak;
- non-transient error -> single attempt only.

After repair, six consecutive full four-worker runs across `loadscope`, `load`, and `worksteal` completed green before later transfer hardening, and final post-transfer burns also completed green.

`ATOMIC_REPLACE != SINGLE_REPLACE_SYSCALL_ON_WINDOWS`.

`TRANSIENT_SHARING_VIOLATION != PERSISTENT_WRITE_FAILURE`.

## 10. Cross-process profile containment flake

A later four-worker burn exposed a second Windows-only flake in the legacy six-process UCM append test:
`profile path escapes continuity root`.

The containment check used case-sensitive `Path.relative_to()` even though the storage substrate is case-insensitive Windows filesystem identity.

Repair:
- resolved path containment now uses `os.path.normcase + os.path.commonpath`;
- true escapes still fail closed;
- transient/OS canonical casing differences no longer create false escapes.

Post-repair targeted stress:
- legacy six-process concurrent append test: **10/10 consecutive PASS**.

`PATH_STRING_CASE != WINDOWS_PATH_IDENTITY`.

## 11. Transfer plane file-object identity defects

Warfort transfer attacks found four deterministic holes.

### Import stage replacement/hardlink swap

After an import ticket was created, its `.part` staging pathname could be deleted and replaced by:
- a hardlink to an external file;
- a different regular file.

`append_chunk` trusted the stage pathname and would write through the replacement.

Repair:
- import tickets bind the stage file-object identity (`st_dev`, `st_ino`) at creation;
- stage link count must remain exactly one;
- identity is checked before every chunk write and before finalization.

### Export source currentness

Export ticket currentness originally checked only source size + mtime before a chunk read. An attacker could:
- rewrite same-size content and restore original mtime;
- replace the source inode with a new same-size/same-content/same-mtime file.

Repair:
- export tickets bind full source path identity at creation: size, mtime, SHA-256, and file-object identity;
- every chunk read verifies inode/device identity, metadata identity, and full content SHA before returning data.

New transfer identity + existing hostile transfer suite: **15/15 PASS**.

`PATH + SIZE + MTIME != FILE_CURRENTNESS`.

`TRANSFER_STAGE_PATH != TRANSFER_STAGE_OBJECT_IDENTITY`.

## 12. Property/fuzz pressure

Hypothesis-based tests add randomized pressure over:
- filesystem-safe project/profile identifiers;
- reserved-device identifiers;
- trailing-dot/space/ADS ZIP aliases;
- reserved Windows ZIP device components;
- finite IEEE float acceptance;
- NaN/Infinity rejection;
- canonical JSON depth boundary.

The property harness itself initially overclaimed that every regex-valid identifier must be accepted; Hypothesis found `NUL`. The harness was corrected to distinguish explicit namespace rejection from valid safe identifiers rather than weakening the Runtime validator.

`FUZZ_FAILURE != PRODUCT_FAILURE UNTIL ATTACK_CONTRACT_IS_VALID`.

## 13. Current-state and authority boundaries preserved

The current-state parity fixture successfully rehydrates under exact active ICF-CS v1.2 bytes.

No warfort repair changes:
- sealed R4.4 authority;
- ICF-CS v1.2 continuity/process authority;
- RES authority firewall;
- UCM authority firewall;
- compact 30-operation transport schema;
- project mutation lease/generation semantics;
- live Runtime process.

`SOURCE_HARDENING != LIVE_PROMOTION`.

## 14. Final detached acceptance

All warfort-specific tests together:
- **65 passed**;
- **1 skipped** (platform symlink capability dependent);
- **17 property subtests passed**.

Sequential complete Runtime on final warfort bytes:
- collected: **742**;
- passed: **740**;
- skipped: **2**;
- failed: **0**;
- Python 3.12.10.

Canonical source independently reproduced the final candidate:
- all warfort-specific tests: **65 passed / 1 skipped / 17 property subtests passed**;
- complete Runtime: **742 collected / 740 passed / 2 skipped / 0 failed**;
- four-worker `loadscope`: **740 passed / 2 skipped / 103 subtests passed**;
- four-worker `worksteal`: **740 passed / 2 skipped / 103 subtests passed**.

Parallel burn history:
- before atomic/profile fixes, repeated xdist exposed deterministic intermittent worker-restart and profile-root failures;
- after atomic/profile repairs, six consecutive four-worker full runs across `loadscope`, `load`, and `worksteal` passed at the then-current 728-test frontier;
- after final transfer hardening, independent final four-worker runs:
  - `loadscope`: **740 passed / 2 skipped / 103 subtests passed**;
  - `worksteal`: **740 passed / 2 skipped / 103 subtests passed**.

Targeted cross-process UCM append after containment repair:
- **10/10 consecutive PASS**, six child processes each iteration.

## 15. Claim ceiling

This detached campaign earns:
- the listed deterministic defects were reproduced and repaired in an isolated clone;
- current source survives sequential and repeated parallel pressure at final candidate depth;
- current continuity fixture is compatible with exact ICF-CS v1.2 ingress;
- Windows pathname/inode/archive/replace semantics are materially stronger than the published parent;
- UCM ingress/currentness/recovery/ambiguity/serialization boundaries are materially stronger than the published parent;
- transfer tickets bind file-object/content identity rather than pathname metadata alone.

It does **not yet** earn at this report stage:
- canonical-source publication;
- GitHub remote publication/readback;
- live Runtime reload;
- actual private UCM import;
- proof that no future hostile class exists.

The campaign intentionally stops adding new feature surface here. Promotion requires exact-byte canonical port + independent sequential and parallel qualification.
