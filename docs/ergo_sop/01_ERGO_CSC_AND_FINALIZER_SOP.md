# 01 — ERGO CSC and Finalizer SOP

## Purpose
Define how CSC and the task finalizer operate inside the Ergo-Light project.

## Required operating method
- run CSC locally against this project root
- do not rely on cross-project hardcoded paths
- do not finalize a task without a current CSC event report and finalizer summary
- keep outputs under `data/csc_native/` and `data/csc_runs/`

## Finalizer rule
`system/finalize_task.py` is the active task finalizer for Ergo-Light.
It SHALL:
- create a timestamped run directory
- invoke the local CSC universal runner
- produce a machine-readable summary
- report whether CSC-clean state was achieved

## Output rule
Finalizer and CSC outputs must land inside this project and must not silently depend on another project's data roots.

## Code doctrine rule
All code mutation should be read against `docs/ergo_doctrine/01_ERGO_CODE_DOCTRINE_BINDING.md` and `docs/ergo_sop/02_ERGO_UNIFIED_CODE_STYLE_GUIDE_SOP.md` before promotion-grade claims are made.
