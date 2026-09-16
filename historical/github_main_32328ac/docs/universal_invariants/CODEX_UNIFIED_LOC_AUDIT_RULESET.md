# CODEX + Unified Standards LOC Audit Ruleset

## Uploaded doctrine basis

- `CODEX_OMEGA_BIBLE.md` — sha256 `9d4f70d54994fd9e620452bed750cb8d7b83841668ea31a9f137ce9dffdc8fad` — 170766 bytes.
- `UNIFIED_CODE_STANDARDS_DOCTRINE_v1.2.md` — sha256 `a00fc7c36b5a090c131e0b02eb8a7fb8352f04c53696400b8635eeba8c29f5c2` — 24169 bytes.

## Machine-checkable rule families

- `OMEGA_L1_NO_STUBS`: no TODO/FIXME/HACK/stub/placeholder/NotImplemented patterns.
- `OMEGA_L4_EVIDENCE_BOUNDARY`: no unsupported certainty language in load-bearing code comments.
- `UCS_FAILURE_LOCALITY` / `UCS_ERROR_VALUES`: no silent/broad failure handling without structured conversion.
- `UCS_TYPED_BOUNDARY`: no soft dict/object/Any boundaries without pressure toward typed request/result objects.
- `UCS_SUBSTRATE_SOVEREIGNTY`: no brittle dependency/path/import truth leakage.
- `UCS_COGNITIVE_CONSERVATION`: working-memory limits for parameters, nesting, function/file/class length.
- `UCS_JSON_BOUNDARY`: central JSON boundary discipline.
- `UCS_COMMAND_BOUNDARY`: subprocess only through hardened envelopes; `shell=True` is blocker.
- `UCS_STATE_DISCIPLINE`: mutable global state requires explicit lifecycle.

This ruleset is an audit embodiment, not a claim that all doctrine can be reduced to regex/AST checks.
