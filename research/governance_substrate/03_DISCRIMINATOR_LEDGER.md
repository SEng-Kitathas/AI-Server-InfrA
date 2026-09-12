# Discriminator Ledger

## D0 — Does Microseed governance transfer require reclassifying Microseed?
Result: NO. Mechanisms transfer cleanly under donor boundary. Reclassification rejected.

## D1 — Does governance require a new authority plane?
Result: NO. A non-authoritative verifier over existing owners detects the first contradiction classes. New authority plane rejected.

## D2 — Can the verifier detect projection/authority confusion on real PCMMAD concepts?
Result: NARROW YES. Bound relations for capability contracts, global doctrine, mutation generations, migration receipts, and receiver restart. Hostile owner substitution/admission bypass/derived authority escape: 6/6 detected; combined kernel suite 11/11 PASS.

Evidence ceiling: tests currently inject observations into real-surface relation models; they do not yet acquire live observations from the owning subsystems. Therefore this does NOT establish an operational governance substrate.

## Sharpest next discriminator
Do not add more relation types. Compose observation adapters from existing read-only owner APIs and require the kernel to discover contradictions from actual subsystem outputs. Then corrupt only a derived/projection surface in a sandbox and prove: (1) contradiction detected, (2) authoritative owner unchanged, (3) kernel performs no repair/mutation, (4) UNKNOWN when owner evidence is unavailable.

## D3 — Can composed owner observations detect projection corruption without authority leakage?
Result: NARROW YES. Read-only adapters were composed for capability-contract and global-doctrine owners. Combined governance suite: 16/16 PASS. A live in-process registry/orient probe used five real capability cards, observed a clean projection as CONSISTENT, corrupted only fs.glob input_schema in the projection, detected PROJECTION_CONTRADICTION, and proved the authoritative registry digest byte-for-byte unchanged. Governance authority remained NONE. Owner-unavailable doctrine observations return UNKNOWN even when the projection claims currentness.

Scar: the first observer implementation accidentally allowed the source mismatch code to overwrite the normalized PROJECTION_CONTRADICTION code via dictionary merge order. Hostile test caught it. Preserve source_code separately; normalization must not destroy governing classification.

Evidence ceiling: capability observation is now operational against actual registry/orient code in the isolated candidate process. Doctrine UNKNOWN behavior is tested against the real owner contract but not yet a persisted promoted doctrine instance. No mutation/recovery action is permitted to the governance kernel.

## Sharpest next discriminator
Attack whether the kernel adds information or merely restates pairwise equality checks. Build a three-surface contradiction where two derived projections agree with each other but disagree with the authoritative owner. Require owner-anchored governance to reject majority/consensus. Then compare against a control implementation using projection consensus. If both behave the same, the governance abstraction has not earned itself. If governance rejects false consensus while the naive control accepts it, the authority-anchored mechanism earns independent value.

## D4 — Does authority anchoring add value beyond projection consensus?
Result: YES, narrowly and discriminatively. Control: two identical stale projections agree, so naive projection consensus returns true. Governance: each is compared to the declared authoritative owner and both are rejected as CONTRADICTION. When the owner is unavailable, two agreeing projections still produce UNKNOWN rather than truth. Combined governance suite: 18/18 PASS.

Earned invariant: PROJECTION CONSENSUS != AUTHORITY. Agreement among derived surfaces cannot manufacture currentness or truth. This is independently useful beyond a pairwise equality helper because it changes the result specifically when correlated/stale projections agree.

## Sharpest next discriminator
Attack correlated authority failure instead of projection failure: present an apparently valid authoritative owner whose currentness witness is stale or cryptographically inconsistent while projections agree with it. Governance must not bless owner identity alone. It must require an independently checkable currentness/integrity witness and return STALE/CONTRADICTION/UNKNOWN as appropriate. If owner-name anchoring is sufficient to pass, the kernel is naive and fails the hypothesis.

## D5 — Is rightful owner identity sufficient without currentness/integrity?
Result: NO, and the naive kernel initially FAILED this discriminator. A fake owner naming itself GLOBAL_DOCTRINE with status CURRENT but digest_valid=False was incorrectly accepted as CONSISTENT because the observer checked owner identity but not the integrity witness. Hostile test exposed the defect. The observer now requires authority=GLOBAL_DOCTRINE, status=CURRENT, and digest_valid=True before owner evidence is usable.

Persisted attack: create a legitimately promoted doctrine in an isolated root, tamper its law bytes while leaving the stored digest and agreeing projection unchanged. global_doctrine.inspect correctly returns DIGEST_MISMATCH / authority NONE; governance returns UNKNOWN, never consistency. Valid persisted owner + matching projection remains CONSISTENT. Combined governance suite: 21/21 PASS.

Earned invariant: AUTHORITY IDENTITY != CURRENT AUTHORITY. Rightful ownership is necessary but insufficient; use requires a current/integrity witness appropriate to that authority.

Important scar: this discriminator found a real naivety in the experimental governance adapter, not in Microseed or the existing global_doctrine owner. The owner already failed closed correctly; governance had failed to consume the owner's integrity witness.

## Sharpest next discriminator
Test witness independence. A currentness witness that is merely self-asserted by the same corrupted owner is not independent evidence. Determine, surface by surface, whether integrity/currentness can be checked from immutable bytes, external generation/lease state, signed/hash-bound receipts, or an out-of-failure-domain observer. Reject circular witnesses. Attack with owner + witness fields that agree internally but contradict recomputation/external evidence.
