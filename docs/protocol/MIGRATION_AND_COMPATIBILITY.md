# Protocol migration and compatibility

The V29 protocol plane is additive.

- Existing routes remain present.
- Existing 30 Custom GPT operations remain present and unique.
- Existing projects are not auto-mutated.
- Existing project files are not moved.
- Protocol state begins only when `protocol.initialize` or another protocol mutation is called.
- Default protocol dispatch enforcement is advisory.
- Strict mode is an operator deployment decision through `PCMMAD_PROTOCOL_POLICY_MODE=strict`.

Recommended adoption:

1. initialize a project in `AUDIT`
2. record the active objective and required constraints
3. record continuity and claims discovered during audit
4. transition to `BUILD_PLAN`, then `BUILD_COMMIT` before specimen mutation
5. register emitted artifacts and evidence
6. transition to `PROMOTION`
7. adjudicate claims/artifacts under the configured rigor level
8. verify the ledger before release promotion
