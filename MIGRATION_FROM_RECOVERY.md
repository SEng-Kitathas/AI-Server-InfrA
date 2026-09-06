# Migration from recovery media

1. Keep the original surviving ZIP immutable and private.
2. Extract V29 beside any partial recovery copy, not over it.
3. Configure `GITHOME_API_KEY` as a User environment variable.
4. Configure root/mount variables around the surviving D:/E: data rather than moving those folders.
5. Run Setup, then Verify, then local-only Start.
6. Initialize protocol state per project only after confirming the intended rigor and starting mode.
7. Use advisory mode during migration; promote strict mode after existing workflows have explicit mode transitions.
8. Verify ngrok and the Custom GPT callback before making V29 the canonical launcher target.
