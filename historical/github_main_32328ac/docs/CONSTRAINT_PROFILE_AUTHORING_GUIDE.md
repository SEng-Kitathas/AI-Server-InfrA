# Constraint Profile Authoring Guide

A constraint profile binds project doctrine, quality gates, runtime gates, and claim permissions into a finalizer-readable contract.

## Required profile behavior

A profile must define:

- source classes: canonical doctrine, candidate doctrine, generated evidence, active source, archives, and nonbinding references;
- gate families: LOC/code shape, guide/style, doctrine/SOP/CSC, semantic footgun/dataflow, runtime smoke, and package/readback when relevant;
- claim effects: what each failing/stale/skipped gate blocks;
- freshness rules: when prior evidence can be reused;
- refactor policy: when bounded patch is enough and when full refactor is justified.

## Non-negotiable rule

The profile must not weaken coverage to reduce stress. Coverage is full. Execution can be incremental only when freshness/evidence proves it is safe.

## Claim permission model

Claims are not prose. They are permissions derived from gate evidence.

Common claims:

- `reply_claim_clean`
- `runtime_working`
- `promotion_clean`
- `package_clean`

A profile may add project-specific claims, but each claim needs a required gate set and blocking semantics.

## Recommended gate result shape

```json
{
  "gate_id": "semantic_footgun_dataflow",
  "gate_family": "semantic_logic",
  "status": "pass|fail|skip|stale|not_applicable",
  "profile": "promotion",
  "claim_effects": ["blocks_promotion"],
  "recommended_action": "bounded_patch",
  "finding_count": 0,
  "strict_failure_count": 0,
  "evidence_path": "reports/...",
  "freshness": "fresh"
}
```

## Source classification

Historical discussion and large corpus folders can inform doctrine, but they are not automatically binding. The pipeline must classify sources before enforcing them.

Binding order should be:

1. active project profile
2. canonical doctrine/SOP
3. project-specific gates
4. candidate doctrine with explicit promotion
5. historical/reference material

## Refactor discipline

Finalizer findings should recommend `bounded_patch` unless a gate proves structural incoherence, repeated local repair failure, or explicit profile policy requires `full_refactor`.
