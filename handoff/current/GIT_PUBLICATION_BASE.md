# PCMMAD Receiver V30 — Git Publication Receipt

Date: 2026-09-05 22:13 ET
Status: VERIFIED REMOTE PUBLICATION — CURRENT PRE-HANDOFF BASE THROUGH A-030 RECONCILIATION
Scope: source/evidence publication only; **NOT live Runtime deployment/promotion**.

## Repository authority
Local Git root:
`E:\new pc\AI_Pushes_Sandbox\projects\PCMMAD_RECEIVER_LAB\V30_WORKING\PCMMAD_receiver`

Remote:
`https://github.com/SEng-Kitathas/AI-Server-InfrA.git`

Branch/upstream:
`main` / `origin/main`

## Current verified pre-handoff head
Commit:
`f63f31f7f2ae89f9253d21609a1d431df29e0a69`

Tree:
`6dbdc6fa9a42531ae0252b634cfd3f8e0d749ba3`

Subject:
`Reconcile A-030 projection currentness`

This commit follows:
- A-028 availability/currentness publication `2d6549f01327c7b3250cc863d64cc3eca18417e3`;
- A-029 MCP availability publication `e777bd4fdcd2ec942f2269903bf8129b53cf33cd`;
- A-030 HUD availability publication `7aee592978aafe9d1dc14cffefa4bf95516b271a`;
- A-030 projection-currentness reconciliation `f63f31f7f2ae89f9253d21609a1d431df29e0a69`.

Fresh qualification/readback before current handoff mutation:
- complete V30 suite: **245 collected tests GREEN**;
- local HEAD = remote `refs/heads/main` = `f63f31f7f2ae89f9253d21609a1d431df29e0a69`;
- working tree clean;
- tree = `6dbdc6fa9a42531ae0252b634cfd3f8e0d749ba3`.

## Current handoff mutation boundary
The user explicitly requires a Git-contained ICF-CS recovery snapshot and complete Runtime↔OBE/Skills handoff because the chat thread is saturated.

That handoff snapshot is the next intended commit. Therefore this receipt records the exact published **base before the handoff snapshot mutation**. After the handoff commit/push, this receipt must be advanced to the new remote head.

## Publication hygiene
Repository excludes local/non-source surfaces including `.worker_selftest/`, `.pcmmad_sync_runs/`, `.pytest_cache/`, `**/_v30_backups/`, `*.bak.*`, and `operator_hud/runtime/`.

`.gitattributes` retains `* -text` so Git does not normalize byte-sensitive source/manifests.

## Authority ceiling
`GIT_PUBLICATION != LIVE_RUNTIME_PROMOTION`

`GIT_HANDOFF_SNAPSHOT != LIVE_PROJECT_STATE_PROOF`

The GitHub repository is durable source/publication lineage and recovery evidence. It does not imply the live Desktop receiver/HUD/services are running V30 or that commit-bound snapshots outrank fresher canonical local/runtime state.
