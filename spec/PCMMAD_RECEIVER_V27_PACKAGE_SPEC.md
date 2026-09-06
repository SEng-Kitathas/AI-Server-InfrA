# PCMMAD Receiver V27 Package Spec

## Package under evaluation
`PCMMAD_RECEIVER_V27_TOOL_PRIMITIVES_AND_EXECUTION_REDUCTION_PACKAGE.zip`

## Verified content classes
- Flask receiver/server routes
- lab tool router and primitives
- execution, power, context, filesystem, project, SOP, browser, and research tool surfaces
- compact OpenAPI/action schema
- package manifests and audit reports

## Required evaluation gates
- ZIP traversal safety
- extraction manifest
- Python compileall over extracted package
- static inventory of modules/classes/functions/imports
- CSC finalizer on lab/control surfaces

## Baseline promotion boundary
`baseline/pcmmad_receiver/` is a candidate/evidence surface until explicit promotion. Baseline findings are reported but do not define finalizer failure for control surfaces.

## Schema authority gate
The receiver CSC finalizer SHALL run `tools/csc_native/receiver_schema_authority_gate.py` to enforce that the compact 30-action schema is authoritative, every schema path exists at runtime, and runtime-only routes are classified internal/legacy.

## Baseline self-test gate
The receiver CSC finalizer SHALL run `tools/csc_native/receiver_baseline_selftest_gate.py` to verify baseline compile health, server hardening tests, app importability, tool registry health, and subprocess envelope behavior.
