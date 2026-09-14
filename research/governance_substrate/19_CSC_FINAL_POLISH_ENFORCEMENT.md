# CSC / Final Polish Enforcement

## CSC_ENFORCEMENT_G56_20260914
- External code-quality review exposed CONFIGURED != ENFORCED for Ruff/CSC. Verified current correctness scan initially had 38 F821/B023/F403/F405 findings. Load-bearing F821 and B023 defects were repaired; test star imports were made explicit. api_wire_models star-import facade remains a deliberate compatibility surface and is not yet mechanically rewritten.
- Mandatory CSC code-health gate added: tools/csc_native/csc_code_health_gate.py. Current blocking correctness rules F821+B023 are CLEAN. Gate authority=AUDIT_ONLY.
- Microseed-derived final-polish gate added: tools/final_polish_gate.py. It composes CSC correctness + continuity/observability regression and grants authority NONE. CONFIGURED_STANDARD_REQUIRES_ENFORCING_CONSUMER is embodied as promotion qualification.
- CI now invokes CSC correctness and final-polish before full clean-box suite. tools/verify_release.py now consumes CSC code-health as part of release cleanliness. Enforcement regression tests added.
- Continuity scar closed structurally with tools/reseal_handoff_snapshot.py; rollover mutation must reseal manifest before checkpoint/publication.
- Tracked build/lib count is 0 in current Git. build remains ignored. Opus build/lib finding was stale against current branch.
- Remaining quality debt: F403 api_wire_models compatibility facade; broad E/F/I/UP/B/SIM historical style debt; contract docstring coverage; print/global review. These are ratchet work, not permitted to weaken current correctness gate.
- Cross-arm/Microseed law: DECLARED STANDARD != EMBODIED STANDARD. A declaration with no enforcing consumer creates qualification debt and cannot support promotion claims.
