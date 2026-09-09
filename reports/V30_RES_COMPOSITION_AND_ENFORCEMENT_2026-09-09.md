# V30 RES Composition + Enforcement Pressure Campaign — 2026-09-09

Status: **CANONICAL SOURCE QUALIFIED / PUBLICATION PENDING**

Base server HEAD: `016eacee04113be6f499cf00d29af0e04ec8a9ec`

Doctrine donor: sealed R4.4 `07C_RESEARCH_EPISTEMIC_SHADOW_PROTOCOL.md`, exact epoch-42 RES and coverage audit from project `rahl-engineering-canonical-sop-r4-20260902`.

Authority effect: **NONE**. This work does not edit or release ICF-CS, promote RES content to doctrine, or create a new Runtime authority plane.

## Campaign question

Audit the nine RES server-policy requirements against the current 121-tool Runtime, reuse all existing deterministic mechanisms that already satisfy them, hostile-test the remaining gaps, and build only the smallest server-native seam that failed composition.

The governing split remains:

`RES_DOCUMENT != RES_EMBODIMENT`

`RES_EMBODIMENT != NEW_RES_DATABASE_OR_RUNTIME_SUBSYSTEM`

`RES_CONTENT != GOVERNING_DOCTRINE`

## Before-state discriminator

A direct probe on untouched `016eace...` established that existing Runtime already supplied:

- authoritative append-only protocol ledger;
- sealed artifact identity and additive supersession/adjudication machinery;
- project mutation leases/generation fencing;
- bounded result handles/range retrieval;
- explicit promotion/adjudication plane;
- generic continuity event recording.

But four RES-specific obligations were absent:

1. `ContinuityKind` did not include `RESEARCH_EPISTEMIC_SHADOW`;
2. the context engine classified the canonical RES path as generic rather than a continuity surface;
3. the canonical seven-state RES truth grammar was not represented by generic protocol evidence/claim enums;
4. no native RES policy/projection/readiness capability existed.

A deeper source read exposed one additional embodiment omission: project initialization did not create `continuity/research_epistemic_shadow[/addenda]`, and the artifact target map did not recognize the RES continuity directory.

Pre-implementation probe SHA-256:
`c7cd57a5d56c1f91b14060f088cf3e0a43d82753a2127556977b9115b381c80a`

## Composition matrix

| Canonical RES responsibility | Existing Runtime composition | Missing seam / result |
|---|---|---|
| Durable RES storage | project filesystem + artifact registration | add canonical RES directory/artifact target only |
| Append-oriented history | authoritative hash-chained protocol ledger + sealed addendum artifacts | reuse; no RES database |
| Exact identity/currentness | SHA-256 artifact registration + contract/currentness/readback | reuse |
| Provenance/evidence links | protocol artifact/evidence refs + RES claim provenance validation | thin RES validation |
| Canonical truth states | generic claim/evidence enums are not equivalent | thin canonical RES grammar |
| Visible promotion/demotion/supersession | generic promotion plane exists; RES semantics require visible addendum transitions | thin RES transition validator; no new authority |
| Consolidated snapshot | project artifact + context/retrieval | thin 22-section/truth/firewall validator; machine projection derives from addenda |
| Material update triggering | no daemon required | deterministic classifier: REQUIRED / RECOMMENDED / NO UPDATE |
| Research handoff currentness + doctrine firewall | protocol ordering, registered hashes, currentness, mutation authority exist | thin project-derived readiness gate + explicit authority-neutral contract |

Net result: **composition dominates**. No new persistence engine, scheduler, result store, database, daemon, transport family, or authority plane was earned.

## Native seam added in isolated clone

Five read-only capabilities were added to the existing `continuity` family:

- `continuity.res.addendum.validate`
- `continuity.res.addenda.project`
- `continuity.res.snapshot.validate`
- `continuity.res.materiality.classify`
- `continuity.res.handoff.readiness`

The source registry becomes **126 tools**, but no new capability family is created.

Additional small embodiment wiring:

- `ContinuityKind.RESEARCH_EPISTEMIC_SHADOW`;
- canonical RES project directories created during project initialization;
- `continuity.research_epistemic_shadow` artifact target mapping;
- context-engine classification/priority for RES;
- existing `protocol.continuity.record` accepts RES as a continuity kind.

All RES-native tools are read-only and declare `authority_neutral`. Durable writes continue to use the existing project/protocol/artifact mutation surfaces.

## RES policy semantics

### Canonical truth grammar

Exactly:

- `VERIFIED`
- `OBSERVED`
- `INFERRED`
- `HYPOTHESIZED`
- `INTUITION_SIGNAL`
- `UNKNOWN`
- `REJECTED_DEMOTED`

RES claims require explicit provenance. `VERIFIED`, `OBSERVED`, and `REJECTED_DEMOTED` also require evidence references.

### Visible transition law

RES claim updates cannot silently rewrite prior epistemic state. Addenda require an explicit transition:

- `CREATE`
- `PROMOTE`
- `DEMOTE`
- `SUPERSEDE`
- `REAFFIRM`

Existing claim transitions bind the exact prior `claim_digest`; addenda bind the exact prior addendum head. Promotion/demotion/supersession require evidence. `DEMOTE` preserves the canonical `REJECTED_DEMOTED` state. The Runtime does not pretend that RES truth states are a total mathematical ranking; it enforces visibility/currentness/evidence rather than inventing unsupported epistemology.

### Consolidated snapshot

A consolidated Markdown snapshot must:

- identify form `RES CONSOLIDATED SNAPSHOT`;
- contain all 22 canonical R4.4 sections exactly once and in order;
- use only canonical truth-state prefixes when a truth-state prefix is present;
- contain explicit truth-state claims;
- preserve `RES_CONTENT != GOVERNING_DOCTRINE`.

The validator returns a semantic-content UTF-8 hash under the explicit name `content_utf8_sha256`; file-byte currentness remains the artifact/file SHA surface.

### Material-update policy

The canonical material epistemic event classes are represented explicitly. A material listed event yields `RES_UPDATE_REQUIRED`; a declared non-material occurrence yields `RES_UPDATE_RECOMMENDED`; unknown/non-epistemic events yield `NO_RES_UPDATE`. `RESEARCH_HANDOFF_CHECKPOINT` is always `RES_UPDATE_REQUIRED`.

No background daemon rewrites RES every turn.

### Research handoff gate

For a research-intensive handoff, Runtime derives readiness from current project state rather than trusting a caller-supplied “ready” Boolean.

It requires:

- canonical RES snapshot exists;
- snapshot passes the 22-section/truth/firewall validator;
- current snapshot bytes match a registered `continuity.res.snapshot` artifact;
- any registered RES addendum chain has valid exact hashes and append/currentness chain;
- an RES artifact update exists at or after the latest material protocol change;
- a RES continuity event acknowledges the latest RES artifact update;
- when an addendum rather than a newer snapshot is what closes a material change, it must carry provenance/evidence linking it to the latest material protocol event.

Failure is structured as:

`HANDOFF_EPISTEMIC_CONTINUITY_INCOMPLETE`

Readiness remains authority-neutral:

`RES_HANDOFF_READY != PROJECT_MUTATION_AUTHORITY`

## Hostile pressure and scars

The dedicated RES suite contains **43 tests**, including hostile attacks against:

- invented truth states;
- missing provenance;
- VERIFIED/OBSERVED without evidence;
- demotion without defeating evidence;
- authority smuggling;
- unknown material-event classes;
- duplicate claims;
- empty addenda;
- stale addendum heads;
- existing claims silently restarted as CREATE;
- truth-state changes hidden under REAFFIRM;
- malformed DEMOTE/PROMOTE transitions;
- wrong prior claim digests;
- reordered addendum chains;
- missing/reordered/duplicated snapshot sections;
- non-canonical snapshot truth prefixes;
- missing doctrine firewall;
- wrong snapshot form;
- missing truth-state claims;
- missing/unregistered/hash-drifted RES snapshots;
- material protocol changes hidden by an ACK-only continuity event;
- fresh but unrelated addenda attempting to mask a material event;
- stale capability-contract invocation.

Three implementation/audit scars were caught before source publication:

1. RES tool module compiled but was not wired into the native registry on the first clone pass. The unchanged tests returned `UNKNOWN_TOOL`, exposing the wiring defect.

   `IMPLEMENTATION_PRESENT != CAPABILITY_REGISTERED`

2. Snapshot validation initially labeled a newline-normalized text hash simply `sha256`, creating ambiguity with exact file-byte identity. The field was renamed `content_utf8_sha256`; file currentness remains `sha256_file`/artifact identity.

   `NORMALIZED_CONTENT_HASH != FILE_BYTE_IDENTITY`

3. A fresh RES addendum could initially have satisfied ordering after a material change without proving semantic contact with that change. The handoff gate now requires provenance/evidence binding to the latest material protocol event when the addendum is the currentness-closing artifact.

   `FRESH_RES_ARTIFACT != MATERIAL_EVENT_COVERAGE`

A fourth hygiene issue was caught during clone work: a helper doubled CR characters in CRLF-tracked files. Parent EOL conventions were restored before qualification.

## Real epoch-42 RES discriminator

The actual project RES was validated directly:

Path:
`E:\new pc\AI_Pushes_Sandbox\projects\rahl-engineering-canonical-sop-r4-20260902\continuity\research_epistemic_shadow\RESEARCH_EPISTEMIC_SHADOW.md`

Bytes: `17377`

File SHA-256:
`24b0e9899a4388ad905746f897ad6dac20c8c1de9e2d3f7e63f612f6c416aec9`

Result:
- 22/22 canonical sections;
- canonical truth grammar only;
- doctrine firewall present;
- VALID;
- authority effect NONE.

Post-implementation composition probe SHA-256:
`2b1fb7576aca030400e1c6be2ec2912f1e2f87964f3c067886a5f4d82bb45e9e`

## End-to-end isolated Runtime smoke

Using real native dispatch and a synthetic project:

1. registered valid RES snapshot + RES continuity event -> `HANDOFF_READY`;
2. appended a material protocol claim -> `HANDOFF_EPISTEMIC_CONTINUITY_INCOMPLETE` with `RES_STALE_AFTER_MATERIAL_PROTOCOL_CHANGE`;
3. registered a handoff addendum carrying exact `protocol:event:<event_hash>` provenance + RES continuity acknowledgement -> `HANDOFF_READY`;
4. projected 96 RES addenda with `store_result=true` -> existing result store offloaded the 62,418-byte result and returned a bounded handle rather than dumping the full history through the control response.

Smoke result SHA-256:
`335774bf70c8cbe0990f4fd07e6c56b64b64d908844e62798890e614ba6061b5`

## Qualification

Dedicated RES tests:
**43/43 PASS**.

Focused composition/integration gate:
- collected 176;
- passed **175**;
- conditional skip **1**;
- failed **0**.

Full isolated Runtime:
- collected **556**;
- passed **555**;
- conditional skip **1**;
- failed **0**;
- Python 3.12.10.

The exact candidate files were then ported to canonical source.

Canonical source focused composition/integration gate:
- collected **176**;
- passed **175**;
- conditional skip **1**;
- failed **0**.

Canonical source full Runtime:
- collected **556**;
- passed **555**;
- conditional skip **1**;
- failed **0**.

Python compile: PASS.
Whitespace/EOL-aware `git diff --check`: PASS before publication.

## ICF-CS authority boundary

This campaign deliberately does **not** edit `INTENT_CONSTRAINT_FRONTIER_CONTINUITY_STANDARD.md` or claim an additive ICF-CS release.

The released v1.1 omission of explicit RES ingress remains a doctrine-authority decision for the doctrine/governance plane:

`RUNTIME_RES_EMBODIMENT != ICF_CS_SUCCESSOR_RELEASE`

The server now provides the deterministic mechanism needed to enforce RES where a governed project declares it. Whether every governed target must automatically include RES in universal ingress requires a separately qualified additive doctrine release.

## Claim ceiling

This campaign earns:

- RES is a first-class project continuity surface in source;
- canonical RES truth/transition/snapshot/materiality policy is machine-checkable;
- research handoff can fail closed on missing/stale/unbound RES;
- large RES projections reuse bounded server result handles;
- no new RES authority/database/execution/transport subsystem is necessary.

It does not earn:

- automatic ICF-CS successor authority;
- RES synthesis -> doctrine promotion;
- semantic omniscience about whether every research event was correctly declared material;
- universal proof that every future R4.4 embodiment remains complete;
- live-process availability before deliberate reload/readback.

Next gate after source publication: live embodiment remains separate and explicitly authorized; ICF-CS overlay reconciliation remains in the doctrine plane.
