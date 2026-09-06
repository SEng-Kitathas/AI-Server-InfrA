# Gemini Guide-Derived Codebase Evaluation Rubric

This project-local rubric is derived from the uploaded Gemini `.mht` guides.

## Source status
- `Code Style Best Practices Guide - Google Gemini.mht`: substantive guide body extracted.
- `Code Quality_ An Exhaustive Breakdown - Google Gemini (2).mht`: substantive full guide body extracted and used as replacement for the earlier incomplete shell capture.
- `Codebase Hygiene_ What Not To Do - Google Gemini (1).mht`: substantive guide body extracted.

## Evaluation axes
- Readability and semantics: naming, magic values, comment quality, formatting, spatial rhythm.
- Architecture and structure: modularity, DRY, coupling/cohesion, cyclomatic pathing, orthogonality, type-state sovereignty.
- Performance and efficiency: algorithmic complexity, resource management, redundancy, dependency health.
- Reliability and security: explicit error handling, input validation, security hygiene, edge cases, portability.
- Testing and documentation: coverage, test quality, API documentation, traceability.
- Hygiene: avoid big-bang refactors, cargo-cult abstractions, vague primitives, pyramid-of-doom nesting, representation leakage, and over-generic internals.

This rubric is separate from the clean CSC LOC audit and is used for additional evaluation, not as a replacement for existing gates.
