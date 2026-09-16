# Microseed / Veya Mechanism Harvest Matrix — Pass 1

## Transfer law
Donor != authority. Copy implementation only where isomorphic; otherwise steal invariant/scar/process law and re-derive PCMMAD-native embodiment. Ordinary-path effect must be proven; library presence is scaffolding only.

## Verified donor mechanisms surfaced

### H1 — Embodiment authority firewall [HIGH / COPY-INVARIANT + TEST PATTERN]
Veya chamber explicitly projects embodiment_role=RESEARCH_EMBODIMENT, embodiment_scaffold_authority=NONE, observation_authority=NONE, project_write_authority=NONE, canon_write_authority=NONE, authority_gain=NONE. Protocol laws: EMBODIMENT_SCAFFOLD != COGNITIVE_MECHANISM; INTERACTION_PRESSURE -> HYPOTHESIS, NOT AUTHORITY; observation != evidence qualification.
PCMMAD transfer: universal operator/project-provisioning/security sandboxes should carry explicit authority-ceiling metadata in every result/receipt and reject promotion from sandbox observation directly to standing/global authority.

### H2 — Clean experiment -> earn -> recover -> embody -> pressure -> new clean experiment [HIGH / PROCESS LAW]
Veya embodiment protocol uses CLEAN_EXPERIMENT -> EARN -> RECOVER -> EMBODY -> PRESSURE -> NEW_CLEAN_EXPERIMENT.
PCMMAD transfer: security/HA changes should not be promoted from unit warfort directly. Clean isolated attack establishes mechanism; recovery/embodiment puts it in ordinary server path; ecological agent-server pressure follows; then new clean reproduction tests causal attribution.

### H3 — Research OS authority ceiling [HIGH / DIRECT PROCESS IMPORT]
Unified V3 declares PROCESS/COLLABORATION AUTHORITY ONLY; NOT project-state, organism architecture, or canonical promotion authority. Research survival != canonical promotion; emergent capability != emergent authority; report count != evidence count.
PCMMAD transfer: make Research OS receipts structurally authority-neutral and require explicit promotion capability to graduate laws/scars globally.

### H4 — Attention Reservoir before Helix successor [HIGH / DIRECT PROCESS IMPORT]
Reservoir preserves neglected hypotheses, contradictions, anomalies, alternative frames, deferred-but-live signals; breadth selection occurs before local Helix successor becomes next global attack.
PCMMAD transfer: security/provisioning campaigns need a persisted reservoir so locally obvious fixes (e.g. ACLs) cannot suppress broader failure domains (credential theft, principal compromise, project-root aliasing, recovery-root compromise).

### H5 — OARR bounded adversarial culling [HIGH / DIRECT PROCESS IMPORT]
OARR performs repeated observation, adversarial attack, replay, revision; bounded inner slice <=5; no quiet sixth ranger.
PCMMAD transfer: each sharp discriminator gets bounded attack/replay/revision subcycle and explicit survivor/killed/unknown state rather than unlimited retry.

### H6 — CSC audit-only ceiling [HIGH / DIRECT SECURITY VALUE]
CSC/Genome is assurance/shadow plane; default audit_only, veto/enforcement/promotion NONE unless explicitly earned. Same-lineage re-expression is not an independent epistemic vote.
PCMMAD transfer: security reviewer/verification machinery must not share authority with the mechanism it audits; same implementation lineage cannot count as independent confirmation.

### H7 — Hard-stop UNKNOWN + reopen condition [HIGH / DIRECT CONTINUITY VALUE]
Research OS explicitly permits hard-stop/UNKNOWN with reopen condition.
PCMMAD transfer: first-class negative-evidence/reopen records should be carried into Live Shadow/fresh ingress so new threads do not retry dead paths without new evidence.

### H8 — Counterpart/session currentness and earned-neutral models [MEDIUM-HIGH / IMPLEMENTATION QUARRY]
Veya chamber binds counterpart_id + counterpart_epoch + current_session_id; current preference/recurrence/model resolvers only project research-qualified current state. Neutral counterpart model deliberately preserves unearned fields as unknown.
PCMMAD transfer: universal operator grants and remote principals should bind principal identity + authority epoch + session/current grant, with unknown privileges absent rather than inferred. This strengthens stolen-credential containment and grant replay resistance.

### H9 — Persistent experimental state separated from canon [HIGH / ARCHITECTURAL TRANSFER]
Veya embodiment state persists biography/evidence/state SQLite outside research Git while remaining explicitly non-canonical.
PCMMAD transfer: project shards and hostile sandboxes need persistent experiment ledgers that survive sessions but cannot silently become project/global continuity or doctrine.

### H10 — Evidence bus / scars / dual continuity machinery [HIGH / COMPOSITION TARGET]
Unified V3 names Evidence Bus, Semantic Helix runtime, Attention Reservoir runtime, Double Helix continuity runtime, CSC discrimination/self-audit, OARR hostile lab, PDVER qualification surfaces.
PCMMAD transfer: do not create duplicate monoliths. Map these onto existing RES, Live Shadow/DTS, qualification lifecycle, governance witness, research gate and result handles; import missing semantics only.

## Negative-space candidates for Pass 2
- role-conditioned heldout prediction / same-stimulus controls as generic security evaluator-separation mechanism;
- recurrent counterpart interaction as principal/session continuity stressor;
- neutral unknown-field modeling for least-authority defaults;
- evidence-bus topology for provenance-aware security findings;
- Double Helix for previous/current continuity transition validation;
- PDVER provider qualification for effect truth and break-glass provider replacement;
- goal/subgoal expiry and monopoly machinery for standing universal-authority lifetime/attention capture;
- revision-vs-update distinctions for doctrine/security-policy mutation.

## Sharpest next discriminator
Can H8 (identity+epoch+session binding with unknown privileges absent) compose with existing capability leases/standing authority to give Tommy standing universal access while a stolen ordinary CustomGPT/API credential remains project-contained? Attack replay, privilege inference, session substitution, grant downgrade/upgrade, and project->machine authority composition.

## Pass 1 embodiment discriminator — H8
Implemented an experimental PCMMAD-native `operator_authority.py` from the Veya counterpart/session-currentness invariant: principal_id + principal_epoch + session_id + explicit scope + expiry are integrity-bound. Only LOCAL_OPERATOR_ROOT can issue. PROJECT scope cannot satisfy MACHINE. Project mutation/standing authority has an explicit non-composition law. Unknown/unbound privilege is absent.

OARR attacks 9/9 PASS: exact grant; stolen grant/wrong principal; stale principal epoch; session substitution; PROJECT->MACHINE attempt; scope tamper; expiry; project-authority composition; nonlocal issuer mint attempt.

Evidence ceiling: library/test scaffold only. This does NOT yet prove server-enforced containment of a stolen normal API credential. Ordinary request authentication currently identifies possession of GITHOME_API_KEY, not a cryptographically distinct operator principal.

### New discriminator learned from H8
Binding an operator grant to `principal_id` is meaningless if the server accepts caller-supplied principal identity under the same bearer API key. The principal must be derived from a separately authenticated credential/channel or locally issued session, not trusted from request JSON.

Earned candidate law: CLAIMED PRINCIPAL != AUTHENTICATED PRINCIPAL. A HIGHER AUTHORITY GRANT MUST BIND TO AN IDENTITY THE LOWER AUTHORITY CREDENTIAL CANNOT ASSERT OR MINT.

## Next sharpest discriminator
Derive the minimal two-principal authentication model: ordinary remote agent credential remains project-scoped; operator-universal credential/session is cryptographically separate and locally provisioned. Prove a stolen ordinary API key cannot mint/assert/replay operator principal or MACHINE grant. Then wire H8 at the ordinary machine-scope admission boundary and rerun attacks over actual HTTP/server policy, not direct function calls.
