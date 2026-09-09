# V30 Governance Enforcement Donor Pressure Campaign — 2026-09-09

Status: **SOURCE ENGINEERING QUALIFIED / PUBLICATION PENDING**

## Intent

Audit the Rahl doctrine/governance enforcement machinery as a donor against current AI-Server-InfrA and pull only missing deterministic Runtime seams, using the same hostile-engineering pattern previously used for the operating Skill library.

Donor authority remains NONE for Focused-E2. This campaign does not promote Rahl doctrine and does not create a parallel Runtime authority plane.

## Current receiving baseline

Server base: `d136695c9493bb0668ab4fbf50f7557281e58768`.

Isolated detached worktree:
`PCMMAD_RECEIVER_LAB/quarantine/governance_dyno/AI-Server-InfrA`

Live process/deployment was not changed.

## Donor pressure readback

Read-only/isolated donor hostile suites were re-executed from the Rahl project:

- Continuity Guard v0.2: **29/29 expected outcomes**.
- Governance Contact resolver: **27/27 hostile rejected + 3/3 positive controls**.
- Focused-E2 v0.2: **32/32 hostile rejected + 5/5 positive controls**.
- Pressure-grammar clean-room: PASS, eight countermodels reproduced.
- Evaluator-semantics clean-room: PASS, nine countermodels reproduced.

No mutating qualifier was rerun.

## Composition-before-invention result

Existing Runtime mechanisms already satisfy these deterministic responsibilities and were not duplicated:

- capability contract identity/currentness with `expected_contract_digest` / `CAPABILITY_CONTRACT_STALE`;
- project mutation lease + persistent generation fencing;
- bound approval authority;
- authority envelope separation (`AUTHORITY_IN_CAPABILITY_PAYLOAD` rejection);
- append-only protocol/event history;
- sealed artifact identity + additive supersession;
- bounded result handles + range retrieval;
- durable execution/supervision/readback.

Focused existing Runtime discriminator: **55/55 PASS**.

Therefore the Rahl continuity guard was **not transplanted wholesale**. Its mutation-fence/close/history responsibilities compose from existing Runtime authority/protocol/postcondition mechanisms. The missing semantic-contact precondition is supplied by the governance-contact seam below.

## Missing seams earned by pressure

### 1. Task-scoped governance contact resolution/admission

Current Runtime had doctrine read/search and currentness primitives but no deterministic mechanism that could:

- derive the minimum known governance contacts from a declared task;
- require project-local orientation coverage so a catalog cannot define completeness by omission;
- bind receipts to exact contact-set/task scope;
- distinguish semantic contact from ACK/hash/location;
- recheck current local bytes at admission;
- fail on historical/unknown/contradictory currentness;
- remain explicitly authority-neutral.

Candidate native tools use explicit v1 input schemas, capability version `1.0.0`, schema version `1`, and therefore participate in native contract-digest currentness / `CAPABILITY_CONTRACT_STALE`.

- `governance.contacts.resolve`
- `governance.contacts.admit`

### 2. Lawful finite exhaustion mechanics

Current Runtime could execute jobs and store results but had no native deterministic lawful-frame primitive. Candidate adds:

- `governance.exhaustion.enumerate`
- `governance.exhaustion.evaluate_table`
- `governance.exhaustion.compress_witnesses`

The implementation preserves:

- `INDEPENDENT_BOOLEAN_BASIS` vs `CONSTRAINED_FINITE_GRAMMAR`;
- no universal `2^n * |E|` assumption;
- exact lawful joint frame as required count;
- insufficient budget => zero partial evaluations;
- evaluator semantics separate from grammar;
- full responsibility-frame Pareto relation, not Boolean `changed` collapse;
- typed evaluator failure distinct from valid unchanged;
- bound grammar/environment/evaluator/baseline identity/currentness;
- minimal witnesses over lawful semantic-state order;
- no superset inheritance without explicit monotonicity evidence;
- finite-frame claim ceiling, never world completeness.

Evaluator execution itself is not duplicated. `evaluate_table` validates already-produced effect evidence. Existing Runtime execution/capability machinery remains the execution plane.

## Scar earned during native embodiment

The first native Governance Contact implementation verified a contact-set digest but did not re-derive the contact set from the current catalog + task during admission.

That would have allowed a caller to delete a required contact, recompute a self-consistent digest, and present the smaller set.

The donor hostile class `contact_set_self_deletion_and_resign` exposed the architectural requirement before source publication.

Repair:

`admit_contact_set` now requires current catalog + task, re-derives the requirement set, and requires exact equality before receipt admission.

Earned invariant:

`CONTACT_SET_DIGEST_VALID != CONTACT_SET_COMPLETE`

`ADMISSION_REQUIRES_CURRENT_REDERIVATION`

A second pressure review found that local commit recheck must not permit an arbitrary absolute host path when projected as a project-scoped Runtime capability. Local-file recheck is now confined to the declared project root.

Earned invariant:

`LOCAL_RECHECK != ARBITRARY_HOST_FILE_READ`

## Candidate qualification

Native governance tests: **57/57 PASS**.

These include translated hostile pressure for grammar, evaluator, witness, contact-currentness, self-deletion/re-sign, catalog/task drift, local-source drift, and project-scope confinement.

Full isolated Runtime on candidate bytes:

- collected: **513**
- passed: **512**
- failed: **0**
- conditional skip: **1**

The same exact candidate files were then ported to the canonical source worktree.

Focused source gate (57 governance + 55 existing composition regressions): **112/112 PASS**.

Full canonical source Runtime:

- collected: **513**
- passed: **512**
- failed: **0**
- conditional skip: **1**

Large-result smoke used a 12-pressure Boolean fixture (4096 lawful cases). Native dispatch stored the 757,303-byte result server-side and bounded range retrieval returned the requested 2,048-byte first chunk with `eof=false`. No giant result was materialized into the caller response.

Campaign aggregate result:
`PCMMAD_RECEIVER_LAB/quarantine/governance_dyno/GOVERNANCE_DONOR_PRESSURE_CAMPAIGN_RESULT.json`

Campaign SHA-256:
`d75dfec96250cc533fe97e0caeafa21c136ebb3ab4f7f04f444187aee65c76d8`

## Authority / claim ceiling

This candidate does not mean:

- Rahl verifier became Runtime authority;
- Focused-E2 became binding doctrine;
- broad E0-E5 was promoted;
- finite grammar exhaustion proved world completeness;
- contact satisfaction granted mutation authority;
- engineering source was live deployed.

Preserve:

`CONTACT_SET_SATISFIED != AUTHORITY_GRANTED`

`FINITE_GRAMMAR_EXHAUSTED != RESPONSIBILITY_WORLD_EXHAUSTED`

`DONOR_MECHANICS_QUALIFIED != DOCTRINE_PROMOTED`

`ENGINEERING_SOURCE != LIVE_PROCESS_TRUTH`

## Next gate

Inspect exact candidate bytes/diff/EOL hygiene, publish engineering source only if the sealed candidate remains green, and independently read back remote `main`. Live reload/promotion remains separately gated.
