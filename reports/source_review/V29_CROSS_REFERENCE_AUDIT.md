# PCMMAD V29 source-corpus cross-reference audit

Generated: `2026-07-29T23:00:49.028158+00:00`

## Project boundary

PCMMAD Receiver remains the executable product. Forge and CTO/CSC dumps are evidence and doctrine sources only.

## Corpus scale

- `/mnt/data/pcmmad_deep_dive/original/PCMMAD_receiver` — 2724 files, 84,146,135 bytes
- `/mnt/data/pcmmad_deep_dive/v28/PCMMAD_receiver` — 1444 files, 36,762,716 bytes
- `/mnt/data/pcmmad_deep_dive/forge/FORGE_DOCTRINE_AND_STANDARDS_2026-04-11` — 14 files, 263,344 bytes
- `/mnt/data/pcmmad_deep_dive/csc` — 3781 files, 103,309,497 bytes

## Forge package review

| Source | Decision | Normative lines | PCMMAD disposition |
|---|---:|---:|---|
| `00_INDEX/FORGE_DOCS_FOLDER_INDEX_2026-04-11.md` | evidence_only | 0 | Inventory/navigation only; no runtime primitive. |
| `00_INDEX/FORGE_STANDARDS_READING_ORDER_AND_AUTHORITY_MAP_2026-04-11.md` | translated | 1 | Authority/conflict rules translated into PCMMAD-native source authority documentation. |
| `01_FOUNDATIONS/CODEX_OMEGA_BIBLE.md` | selective | 0 | Quality horizon retained; physical/metaphorical claims are not treated as executable proof. Zero-stub, explicit-mode, verified-truth, observability, resilience, and holonic boundary vectors retained where testable. |
| `02_RUNTIME_DOCTRINE/90_SHALL_READ_APPEND_ONLY_PROTOCOL_BEFORE_MUTATING_CORPUS.md` | embodied | 12 | Append-only hash-chained protocol ledger, supersession, sealed artifact identity, and derived sidecar state. |
| `02_RUNTIME_DOCTRINE/PCMMAD_Canonical_Runtime_Specification.md` | canonicalized | 27 | Copied into PCMMAD doctrine and embodied as typed modes, objective, constraint, continuity, claim, artifact, promotion, rigor, waiver, and mode-gate records. |
| `03_FORGE_STANDARDS/FORGE_ANTI_PATTERN_TO_INVARIANT_REFACTOR_PASS_PROTOCOL_2026-04-11.md` | translated | 20 | Applied as the V29 anti-pattern-to-invariant refactor method; no Forge namespace imported. |
| `03_FORGE_STANDARDS/FORGE_ONE_PAGE_SCORING_SHEET_2026-04-11.md` | translated | 0 | Mapped to PCMMAD release audit rubric and promotion decision. |
| `03_FORGE_STANDARDS/FORGE_UNIFIED_CODE_STANDARDS_AND_DOCTRINE_2026-04-11.md` | selective | 25 | Typed boundaries, specimen/governance split, lifecycle artifacts, verification anchors, and re-architecture permission retained; Forge/LBE/corpus-specific terms remain source-local. |
| `03_FORGE_STANDARDS/UNIFIED_CODE_STANDARDS_AGNOSTIC_2026-04-11.md` | normative | 16 | Already present in V28 and remains the implementation-facing normative standard. |
| `04_CORPUS_DATASET_DOCTRINE/CHIMERA_DATASET_BINDING_READINESS_AUDIT_2026-04-10.md` | not_imported | 0 | Chimera dataset binding is not a PCMMAD receiver capability; only its anti-overstatement discipline informs audit wording. |
| `04_CORPUS_DATASET_DOCTRINE/DATASET_ENGINEERING_LAYER_MANIFEST_2026-04-10.md` | evidence_only | 0 | Dataset package inventory, not a receiver runtime contract. |
| `04_CORPUS_DATASET_DOCTRINE/DATASET_SPLIT_HYGIENE_AND_CONTAMINATION_CONTROL_2026-04-10.md` | selective | 0 | Contamination and source/derived separation applied to release packaging; dataset split mechanics not imported. |
| `04_CORPUS_DATASET_DOCTRINE/TRAINING_CORPUS_ARCHITECTURE_SPECIMEN_GOVERNANCE_SPLIT_AND_NEXT_FAMILIES_2026-04-09.md` | selective | 0 | Specimen/governance sidecar split and lineage retained; training-family roadmap not imported. |
| `04_CORPUS_DATASET_DOCTRINE/TRAINING_DATASET_CARD_AND_DATASHEET_2026-04-10.md` | selective | 0 | Datasheet-style lineage/limitations influence release audit; training-specific fields not imported. |

## CSC dump cross-check

The `e drive csc` and `e drive csc alternate` trees contain 1705 common paths: 1645 identical and 60 different. The authoritative 12 SOP files are already byte-identical to the V28 package.

The dump remains preserved as evidence. Repeated run reports, cache/vendor material, project-specific CTO extension history, and alternate tree copies are not copied into the runtime body.

## Extracted gains

| Gain | Decision | Embodiment / rationale |
|---|---|---|
| `native_protocol_state` | implemented | protocol_models.py, protocol_store.py, lab_tools_protocol.py |
| `append_only_mutation_honesty` | implemented | events.jsonl hash chain, superseding revisions, sealed artifact invariant |
| `discourse_build_mode_gate` | implemented_compatible | protocol.guard.check, PCMMAD_PROTOCOL_POLICY_MODE off/advisory/strict |
| `proportionate_rigor` | implemented | STANDARD/ELEVATED/CRITICAL evidence thresholds |
| `evidence_freshness_and_authority` | implemented | evidence status/verifier/timestamps/expiry/distinctness |
| `waiver_advisory_discipline` | implemented | scoped owned expiring waiver records; invalid waiver rejection at promotion |
| `promotion_lineage` | implemented_at_protocol_level | append-only promotion events committed by global ledger hash chain; latest projection remains rebuildable |
| `branch_topology` | not_imported | Target-specific extension certificate topology is not a proven PCMMAD receiver requirement; artifact provenance and MERGE mode preserve the general invariant without importing CTO-specific machinery. |
| `dataset_split_mechanics` | not_imported | Not a receiver runtime capability. Contamination and sidecar invariants are retained instead. |

## No-loss rule

V28 is the executable parity anchor. Additions are promoted only after the existing route/tool/schema and regression contracts remain green. Source volume or recency alone does not authorize runtime change.

