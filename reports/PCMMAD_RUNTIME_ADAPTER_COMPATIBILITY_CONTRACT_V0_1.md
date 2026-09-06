# PCMMAD Runtime / Adapter Compatibility Contract v0.1

Status: ACTIVE CROSS-THREAD ARCHITECTURE CONTRACT
Purpose: keep the V30 server compatible with normal ChatGPT Project + Skill + MCP/App operation while preserving legacy Custom GPT/OpenAPI compatibility and avoiding platform lock-in.

## Canonical architecture

PCMMAD LABORATORY RUNTIME
  - capability core
  - native dispatcher
  - durable execution/job system
  - projects/repos/mounts/nodes
  - artifact/result/continuity state
  - auth/policy/approval
  - capability registry
  - verification/readback semantics

Transport / client adapters
  - MCP adapter
  - OpenAPI / Custom GPT Actions adapter
  - local CLI
  - Operator HUD
  - MailBridge / future adapters

AI-side operating intelligence
  - PCMMAD Skills / OBE
  - project-local instructions/context
  - model as replaceable co-processor

## Non-negotiable authority rule
Transport is not architecture authority.

MCP/OpenAPI/HUD/CLI SHALL NOT independently define or own:
- project identity
- job lifecycle
- artifact identity
- process ownership
- continuity state
- capability semantics
- approval policy
- mutation/readback truth

All such semantics originate in the Laboratory Runtime.

## Adapter-neutral capability core
Every server-native capability SHOULD expose stable machine-readable metadata sufficient for arbitrary future clients:
- capability_id
- domain/category
- version
- description
- availability/degraded state
- read_only vs mutation
- reversible vs irreversible
- idempotent vs non-idempotent
- required project/node/repo/model/browser context
- authority / approval class
- credential class where relevant
- sync/async/durable/replay support
- estimated runtime/resource class where knowable
- result type / artifact outputs
- preconditions
- postconditions
- verification/readback method
- known failure classes
- deprecation/supersession metadata

## MCP projection rule
Do NOT flatten the full native registry into hundreds of MCP tools merely because MCP permits it.

Preferred MCP projection: small stable typed control vocabulary, roughly:
- runtime.identity
- runtime.status
- capabilities.list
- capabilities.describe
- capabilities.invoke
- projects.resolve
- projects.bootstrap / continuity.read
- jobs.submit
- jobs.status
- jobs.wait
- jobs.cancel
- results.get
- batch.invoke

The exact tool set may change after empirical qualification, but the principle is stable: lazy capability discovery over a broad native registry.

## No opaque god-tool rule
Do NOT reduce the whole runtime to `dispatch(command: string)`.

The adapter must preserve:
- typed capability identity
- structured args/results
- safety classification
- discoverability
- lifecycle semantics
- bounded errors
- verification/readback contract

`capabilities.invoke(capability_id, args)` is acceptable only when paired with strong `list/describe` surfaces and the native registry remains authoritative.

## Skills split
Skills are AI-side workflow/operator doctrine, not process daemons.

Examples of AI-side responsibilities:
- project rehydration
- hostile engineering campaign routing
- evidence/currentness resolution
- connector capability scouting
- artifact sealing judgment
- cross-project donor mining
- mission-control workflow
- tool/workspace intent routing

Deterministic stateful mechanisms live server-side where the state lives.

Promotion rule:
Skill behavior -> repeatedly demonstrated invariant -> model discretion no longer desirable / composition insufficient -> server-native embodiment.

## Vendor neutrality
The runtime SHALL NOT depend on OpenAI-, Anthropic-, Google-, or any single hosted-model concepts for internal truth.

Provider-specific adapters MAY exist as leaves.
Model/vendor identity is metadata, not authority.

Core protocol expectations:
- HTTP/JSON or equivalent neutral machine contracts
- stable versioned schemas
- deterministic error envelopes
- explicit approval/mutation semantics
- result handles for large outputs
- resumability where relevant
- bounded outputs / pagination / ranges
- machine-readable receipts

## Custom GPT / OpenAPI role
Custom GPT Actions remain a compatibility adapter, not the canonical architecture.

Existing compact OpenAPI/router work SHALL remain functional during V30 unless a replacement path is proven and an explicit migration plan exists.

The current 30-operation compact projection and server-native registry separation are treated as useful ancestry for the MCP projection.

## AI/operator UX invariant
A competent unfamiliar AI agent should be able to:
1. discover runtime identity and health
2. discover current capabilities lazily
3. understand mutation/approval/readback requirements
4. resolve the intended project/node/resource
5. invoke the narrowest lawful capability
6. distinguish submitted/started/completed/durable/registered/promoted states
7. resume after interruption
8. verify consequence from machine truth
9. operate without hidden vendor-specific knowledge

The same native state should support the human Operator HUD.

## Cross-thread compatibility requirement
Any MCP/App/Skill work occurring in another thread MUST target this contract rather than inventing a parallel job/project/artifact/capability model.

When a mismatch is found:
- preserve runtime authority
- adapt at the projection boundary where possible
- escalate only if a native runtime invariant is genuinely insufficient
- record the incompatibility and discriminator before changing the core

## Immediate implications for V30 work
- capability registry modernization should anticipate lazy `list/describe/invoke`
- async/job lifecycle work must remain adapter-neutral
- restart/control/transfer/HUD tools should expose neutral metadata and receipts
- schema/runtime parity audits should include MCP projection readiness
- result/artifact handles should become first-class enough for constrained clients
- approval envelopes must remain transport-neutral
- plugin families should not require any one adapter
- Operator HUD and MCP should consume the same capability descriptions, not separate hand-maintained catalogs

## Cross-thread refinement — typed lazy invocation and native authority objects

### `capabilities.invoke` SHALL NOT become a disguised god-tool
Lazy invocation must remain contract-bound and typed.

Required flow:
1. `capabilities.list(...)`
2. `capabilities.describe(capability_id)`
3. receive current descriptor including `capability_version`, `schema_version`, and `schema_hash` / `contract_digest`
4. invoke with `capability_id`, `expected_schema_hash`, structured arguments, optional idempotency key, and optional approval handle
5. runtime rejects stale remembered contracts with a typed error such as `CAPABILITY_CONTRACT_STALE`

Arbitrary command text is not an acceptable substitute for capability identity + current contract.

### Capability currentness
Native capability descriptors SHOULD carry:
- capability_version
- schema_version
- schema_hash / contract_digest
- probe-free availability contract plus explicit bounded availability/currentness read for dynamic providers
- deprecation/supersession identity

Client-side remembered schemas SHALL NOT silently outrank current runtime contracts.

Current earned V30 rule: `REGISTRATION != CAPABILITY_AVAILABILITY != TARGET_HEALTH`. MCP manifest cards preserve the native availability contract without executing providers; explicit currentness comes from bounded native availability probes.

### Approval is a native authority object, not a boolean
Current V30 embodiment: target/argument/contract-bound, short-lived, integrity-checked, single-use approval challenges are now native Runtime authority; adapters pass the separate authority envelope rather than manufacturing boolean approval. Legacy inline approval is transitional compatibility only.

Approval SHALL be modeled as an expiring, target-bound runtime object/handle where the operation warrants durable authority semantics.

An approval object SHOULD bind at least:
- approval identity / handle
- capability identity + version/contract digest
- target identity
- arguments digest or constrained argument set
- granted authority class
- issuing operator/provenance surface where available
- issued_at
- expires_at
- single-use/reuse semantics
- consumption/revocation state

An approval obtained for target A SHALL NOT silently authorize target B.
`approved=true` is insufficient as a canonical authority model.

### Process ownership is a native identity object, not PID-only
PID alone is not a stable ownership proof.

Runtime process identity SHOULD converge toward a tuple/object containing:
- pid
- process creation/start time
- executable identity/path/hash where feasible
- command fingerprint
- runtime owner
- job/service identity
- node identity
- supervision generation / owner epoch where useful

PID reuse or stale PID readback SHALL NOT be allowed to impersonate current process ownership.

### Adapter-only durable truth is forbidden
Permitted adapter-local state includes transport/session representation such as:
- MCP session id
- HTTP cursor
- HUD window layout
- CLI formatting preference

Adapters SHALL NOT invent durable authoritative forms of:
- job
- project
- approval
- artifact
- process ownership
- continuity
- native capability

If adapter state cannot be derived from or reconciled into a native Runtime object, treat it as an architecture smell.

### `jobs.wait` projection
The Runtime owns waitable job lifecycle semantics. Adapters MAY represent waiting as:
- bounded wait/poll
- progress notifications
- subscription/stream
- repeated status polling

No transport representation becomes the canonical definition of waiting.

### `results.get` projection
Results SHOULD support bounded retrieval rather than unconditional context materialization:
- result handle
- metadata
- MIME/type
- byte size
- sha256/content identity
- preview
- range/chunk retrieval
- artifact linkage
- currentness/immutability metadata

### `batch.invoke` semantics
Batch MUST explicitly state:
- ordering
- parallelism
- partial-failure behavior
- per-operation result identities
- per-operation idempotency
- cancellation behavior
- atomicity (default false unless explicitly guaranteed)

`batch` SHALL NOT imply transaction.

### `capabilities.list` narrowing
Capability discovery SHOULD support bounded filters such as:
- domain/category
- tags
- read vs mutation
- requires_project
- requires_node
- available_only
- free-text query
- limit/page/cursor

The goal is lazy, targeted discovery rather than re-materializing the full laboratory schema through MCP.
