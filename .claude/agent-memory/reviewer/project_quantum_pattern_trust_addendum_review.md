---
name: project_quantum_pattern_trust_addendum_review
description: Pattern-Based Trust Under Quantum Threat technical addendum (267e29ae, 2026-04-12). Step 1: MINOR_CHANGES 7.5/10. Step 1 fixes applied. Step 3 stress-test: NEEDS_CHANGES — 2 new criticals on core argument precision. Core argument: "cannot forge" ≠ "cannot impersonate"; "algorithm survives" ≠ "system survives".
type: project
---

"Pattern-Based Trust Under Quantum Threat: The Architectural Response"
Content DB ID: 267e29ae-8550-4f0b-b25f-560a4bc6dfcb
Review date: 2026-04-12, WF Step 1 + Step 3 stress-test
Verdict: Step 1 — MINOR_CHANGES 7.5/10 → 8.5/10 after fixes. Step 3 stress-test — NEEDS_CHANGES on 2 new criticals in core argument.

## Step 3 Stress-Test Results (Core Argument Analysis)

**Stress-test verdict: NEEDS_CHANGES — 2 new criticals not caught in Step 1**

### Critical 1: "cannot forge" ≠ "cannot impersonate via governance" — core claim precision failure

The central claim — "They do not gain your Ec score. They do not gain your Is measurement. They do not inherit your Dv trajectory" — is technically accurate at the *storage layer* but misleading at the *governance layer*. The adversary gains the ADDRESS the score is bound to (mapping(address=>DPCScore) in DPCRegistry.sol:17). All governance functions check msg.sender, which the adversary now controls. They can exercise the accumulated governance weight without forging any history.

The distinction that matters:
- FORGERY (inserting fabricated events retroactively): Hard after migration ✓ — this is what the article defends against
- IMPERSONATION (exercising existing authority via address control): Possible via key extraction — this is what requires migration

The article's defense against impersonation is migration, but this precondition lives in The Migration Path section and is never stated in The Core Distinction. A technical reader who only reads the Core Distinction section walks away believing behavioral trust is structurally quantum-proof. It is not — it is quantum-proof at the forgery layer and migration-dependent at the identity binding layer.

**Fix:** Add one sentence to The Core Distinction: "The behavioral record cannot be retroactively forged by key derivation — but the address that behavioral authority is bound to can be controlled. The identity binding layer requires migration; the behavioral algorithm does not."

The Pink Paper (quantum-trust-and-the-value-shift.mdx line 96) actually has stronger framing: "The adversary can impersonate a key. It cannot impersonate a history." The addendum should echo this explicitly.

### Critical 2: "The DPC algorithm survives all nine" — category error

"The DPC algorithm survives all nine. The address binding survives none of them."

This claim conflates:
- The behavioral scoring FORMULA (P = Ec^α × Is^β × max(Dv, ε)^γ) — survives all nine because it has no cryptographic operations ✓
- The governance SYSTEM built on DPC scores — does NOT survive attacks 1, 3, 4 without migration

Specifically:
- Attack 3 (VALIDATOR_ROLE capture): arbitrary scores injected via batchUpdateScores() → the algorithm doesn't prevent this, it processes injected data faithfully
- Attack 4 (CONFIG_ROLE/setRegistry()): registry rerouted globally → the algorithm isn't even consulted
- Attacks 1, 2: the algorithm's output is hijacked by whoever controls the address

The algorithm formula survives; the algorithm's *integrity* requires migration to defend the role access control layer.

**Fix:** Change "The DPC algorithm survives all nine" to "The DPC behavioral formula contains no cryptographic operations and is therefore computationally quantum-resistant. The governance system that acts on its outputs requires migration to defend the identity and role access control layers against vectors 1–4."

### Warning: Reputation attack vs. key-break attack — not explicitly named as separate classes

Task specifically asked: "Is the reputation attack surface (slow, visible, on-chain) argument sufficiently distinguished from the key-break attack?"

**Answer: NO — not explicitly.** The article describes both threat types and their defenses, but never names them as separate attack classes in the same sentence:

- Reputation farming (Sybil): slow, requires active behavioral work, generates on-chain footprint, detectable
- Key-break attack: instantaneous (given quantum compute), silent, steals existing reputation, requires no behavioral work

The article's "requires the irreversible passage of time" sentence defends against reputation farming. Migration defends against key-break. These are never contrasted explicitly.

**Fix:** Add one sentence to The Core Distinction or The Dual-Trust Model: "These are different attack classes: reputation fraud requires months of behavioral work and leaves an on-chain pattern; key-break attack requires quantum compute and is silent until deployment. Pattern-based trust defends against the first structurally; the dual-trust architecture's migration path defends against the second."

### Secondary finding: Pink Paper Section II Microsoft claim not fixed

The main Pink Paper (quantum-trust-and-the-value-shift.mdx, line 72) still reads: "Microsoft has integrated post-quantum primitives into Azure and Windows." The addendum's equivalent was correctly fixed to "announced post-quantum migration roadmaps... with integration underway." The Pink Paper's Section II has the same original imprecise claim — not corrected in commit 01183d6 (which only updated the addendum in the content DB and made metadata/structural changes to the Pink Paper). If both documents are published together, the inconsistency is visible.

### What the Step 1 fixes preserved correctly

All 4 Step 1 critical fixes were applied correctly:
- Literature overclaim scoped ✓
- VALIDATOR_ROLE contradiction scoped ("under dual-trust model with migrated role access control") ✓ — but still insufficient, see Critical 1 above
- Microsoft integration claim in ADDENDUM corrected ✓ (Pink Paper has same uncorrected claim)
- DPC attestation contamination gap added as one sentence ✓ — but timing-conditional, not structural

The attestation contamination fix is correct but should be framed as: "behavioral record integrity requires PQ migration of validator keys, not just timing." The current framing "designed to complete within the 2026–2027 window" makes it a timing bet rather than a structural guarantee.

**Audience scores:**
- Target audience (builders/Gen Z/crypto-native): 8.5/10
- Skeptic lens: 5.5/10
- Journalist lens: 7.5/10

**Critical Issues (must fix):**
1. "Zero prior coverage across the full academic corpus" — no methodology, no databases named. For technical readers this reads as overclaim. Fix: scope to "no prior coverage found in the SBT, reputation, and on-chain governance literature across April 2026 searches" or add methodology footnote.
2. "The only way to acquire a behavioral score is to earn it" (Dual-Trust section) — contradicts attack vector 3 (VALIDATOR_ROLE capture enables arbitrary score injection). Internally inconsistent. Fix: scope to "under the dual-trust model with migrated role access control" or add explicit caveat that vectors 1-9 are the threat model being resolved.
3. Microsoft integration claim: "integrated post-quantum primitives into Azure and Windows" — too broad for April 2026 state. Windows has PQ announcements; Azure has some PQ-protected services but full integration is ongoing. Fix: "announced post-quantum integration roadmaps for Azure and Windows" or cite specific services.
4. DPC attestation contamination gap: The article correctly notes DPC algorithm has no crypto ops. But behavioral events are attested on-chain via ECDSA. Under HNDL, a quantum adversary could contaminate the behavioral record *before* identity re-binding by forging attestations with extracted validator keys. This is related to attack vector 3 but is not explicitly addressed as a pre-migration risk. Fix: one sentence in The Migration Path section: "The 30-day migration window is designed to precede the practical quantum attack timeline; attestation contamination risk increases as Q-Day approaches."

**Warnings (should fix):**
1. "HNDL collection is already active" — stated as established fact. This is the standard threat model assumption but should be "is assessed to be ongoing" or "is a known state-level capability" to match epistemic precision elsewhere.
2. "epistemic consensus" in The Dual-Trust Model — jargon. Replace with "community-validated record" which is already in the same paragraph and clearer.
3. Phase 1 timing: "30-day time-lock" appears without context of when Phase 1 deployment opens. For builders the question is: how soon? Even "timed to precede the 2027 attack window" would help.
4. Attack vector 4 (CONFIG_ROLE/setRegistry) describes the vulnerability but doesn't forward-reference the Phase 2 mitigation (5-of-N multi-sig). A reader skimming only the vectors section will think there's no known mitigation. Simple fix: "(mitigated in Phase 2 via multi-sig threshold — see Migration Path below)".

**Suggestions:**
- FN-DSA-512 should mention FIPS 206 for journalist completeness (FIPS 204 = ML-DSA, FIPS 205 = SLH-DSA, FIPS 206 = FN-DSA).
- The formula P = Ec^α × Is^β × max(Dv, ε)^γ is good for technical readers — consider a one-line plain-language expansion for Gen Z readers who encounter this via social sharing.
- Cross-reference to research note 754a8ce4 in the footnote is good practice — keep it.

**What's Good:**
- "Quantum computers break the wall. They do not break the record." — Best opening beat in SOS technical library. Do not touch.
- Closing kicker is exceptional: "Pattern-based trust is not a response to the quantum threat. It was always the correct architecture. The quantum threat is the event that makes it visible." — keep verbatim.
- "The key is the lock. The history is the name on the door. You can pick a lock. You cannot rename a building." — Strong and visual. Correctly marked DO NOT REPEAT.
- Tense discipline is consistently excellent throughout — "is designed to," "is planned to," "is specified" — best tense discipline in the SOS technical library.
- CONFIG_ROLE/setRegistry() correctly identified as most severe vector (consistent with research note 754a8ce4 at 8.5/10 validation).
- All 9 attack vectors with code references — clinical enumeration, no breathlessness, appropriate for technical audience.
- Additive migration framing is strategically correct for builders (no behavioral history disruption).
- NIST FIPS citations are accurate (FIPS 203=ML-KEM, 204=ML-DSA, 205=SLH-DSA all finalized Aug 2024).
- Google Chrome ML-KEM integration claim is correct.
- No DPC present-tense issues (recurring pattern in SOS library — clean here).
- No {topic} template bug (recurring systemic issue — clean here).
- Disclaimer block at top and footnote are both present and correct.

**Do not touch:**
- Opening distinction (cryptographic vs pattern-based) — perfectly framed
- "Quantum computers break the wall. They do not break the record."
- All 9 attack vector enumeration structure and code references
- Closing kicker
- "The key is the lock..." metaphor
- Any tense constructions using "is designed to / is planned to / is specified"
