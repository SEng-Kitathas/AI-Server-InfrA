# V30 CONTINUITY CONVERGENCE CLASSIFIER DERIVATION

Date: 2026-09-07
Status: QUALIFIED ENGINEERING CANDIDATE / PUBLICATION PENDING
Live promotion: NOT PART OF THIS CAMPAIGN

## Quarry

Cross-domain raid R12 (distributed version vectors / causal convergence) asked how PCMMAD should distinguish an old replica from a genuinely divergent replica across continuity, Git-mirror, and live-runtime surfaces.

Current-tree audit found strong per-plane hashes and Git commits, but no one Runtime capability that classified cross-plane observations as current, stale-known-ancestor, ahead, or divergent. Plain hash inequality was insufficient: `A != B` cannot prove whether A is an ancestor, a descendant, or an unrelated sibling.

The project commit ledger already retains chronological registered artifact hashes. Git already retains cryptographic commit ancestry. R12 therefore does not require inventing timestamps as authority or building a distributed database; it requires a conservative read layer over existing lineage evidence.

## Derived laws

- `HASH_MISMATCH != DIVERGENCE_PROOF`.
- `STALE_REPLICA_REQUIRES_ANCESTRY_EVIDENCE`.
- `UNKNOWN_HASH != KNOWN_AHEAD_VERSION`.
- `LOCAL_UNREGISTERED_BYTES != REGISTERED_CURRENTNESS`.
- `GIT_DIVERGENCE_REQUIRES_ANCESTRY_TEST`, not timestamp ordering.
- `CONVERGENCE_CLASSIFICATION != MERGE_AUTHORITY`.
- `EXPLICIT_OBSERVATION != SILENT_PLANE_CROSSING`.

## Embodiment

New native read-only capability:

`continuity.convergence.inspect`

The tool count rises from 107 to 108. The capability does not mutate continuity and does not fetch live/remote state implicitly. Callers provide explicit observations with source labels.

### Registered artifact lineage

The Runtime reads `system/ledger/commits.jsonl` for one exact `artifact_class` + `logical_name`, validates matching registered SHA-256 values, and collapses consecutive re-registrations of identical bytes so they do not create false content generations.

It compares current local file bytes with the latest registered hash. If they differ, `registration_current=false` and the overall status fails closed as `local_unregistered`; a matching external observation cannot promote those unregistered bytes into registered truth.

Artifact observation relations:

- `equal_current` — exact current registered bytes;
- `stale_known_ancestor` — observed hash is a known earlier registered content generation;
- `ahead_or_divergent_unproven` — caller claims a later generation but local lineage cannot prove ancestry;
- `divergent` — unknown hash with a claimed generation not ahead of local;
- `divergent_or_ahead_unknown` — unknown hash with no usable generation claim;
- `matches_unregistered_local` / `local_unregistered` — local bytes have advanced outside the registered lineage.

Unknown artifact hashes are never called “ahead” solely from hash inequality.

### Git ancestry

Git observations require a project-relative path naming the exact grounded Git repository root. Subdirectory repo ambiguity and project-root escape are rejected.

Commits are classified using Git's actual object graph and `merge-base --is-ancestor`:

- `equal_current`;
- `stale_known_ancestor`;
- `ahead_known_descendant`;
- `divergent`;
- `unknown_commit`;
- `git_relation_unknown` if ancestry cannot be established safely.

Divergent/unknown relations remain `human_conflict_required=true`; the Runtime does not auto-merge them.

## Real-project discriminator

The registered capability was executed locally against the real project with:

- Git target: current engineering `HEAD` `44e80e05944cfb03b1054dd9e73bd1fe86da62e8`;
- explicit observation: frozen live Runtime feature `4163606459324feaa31252b3c2a6d58d73aaff46`.

Result:

- live resolved exactly to `4163606459324feaa31252b3c2a6d58d73aaff46`;
- relation: `stale_known_ancestor`;
- `human_conflict_required=false`;
- overall status: `stale_observation`.

That replaces narrative-only “live is older” with machine-computable Git ancestry evidence while still keeping Git engineering state and live deployment state distinct.

## Hostile evidence

`tests/test_continuity_convergence_classifier.py` proves:

1. duplicate registration of identical bytes does not create a false content generation;
2. registered current, known stale ancestor, and unknown divergence are distinguished;
3. unregistered local bytes fail closed even when an observation matches those bytes;
4. hermetic Git history distinguishes stale ancestor, ahead descendant, sibling divergence, and unknown commit without timestamps;
5. a Git subdirectory cannot masquerade as the exact grounded repository root.

Focused convergence classifier: **4/4 PASS**.
Registry/capability/manifest/idempotency adjacency: **29/29 PASS**.
Full suite: **387 collected / 386 passed / 0 failed / 1 skipped**.
Changed/new Python compile: PASS.
Native registry import: PASS; tool count 108; `continuity.convergence.inspect` is `side_effect_class=read`, category `continuity`.

## Claim ceiling

This campaign classifies observed lineage. It does not:

- merge divergent continuity;
- choose conflict winners;
- infer causal ancestry from timestamps;
- silently poll live/remote planes;
- claim that unknown artifact hashes are descendants;
- replace the existing registered-artifact or Git truth planes.

Known stale ancestry can drive refresh pressure. Divergent or unproven relations remain explicit conflict evidence for human/governed handling.

No live Runtime promotion is part of this campaign. Live remains frozen on the previously promoted feature until remaining server campaigns converge.

## Sequencing

After publication, audit R13 peer/workload identity (WireGuard/Tailscale donor). R8 lease renewal and R11 caller-owned result cursors remain substantially embodied/retired by current-tree evidence. R10/final schema remains LAST and untriggered pending whole-runtime convergence plus explicit user `hells yeah, ready`.
