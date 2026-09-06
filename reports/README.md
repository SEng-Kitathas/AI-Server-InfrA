# Verification and lineage reports

This directory is a governance/evidence sidecar, not executable release-body authority.

- `V29_REFACTOR_AUDIT.*` is the human/machine promotion audit.
- `V29_RELEASE_VERIFICATION.json` is the aggregate executable gate result.
- `source_review/` contains corpus inventory, hazard inventory, CSC comparison, and V28-to-V29 body differences.
- `lineage/` retains historical schemas/manifests for provenance only.
- Individual gate reports retain sandbox-local paths and timestamps as truthful run evidence; those paths are not deployment configuration.

The immutable executable/configuration body is governed by `PACKAGE_MANIFEST_V29.json` and `MANIFEST.sha256`. Reports and mutable runtime data are deliberately excluded from that body manifest.
