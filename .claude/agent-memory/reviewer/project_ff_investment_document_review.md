---
name: F&F Investment Document Review
description: Family & Friends investment document review (2026-03-29): NEEDS_CHANGES (7.5/10). Critical math contradiction in Scenario 2 (narrative says 1.5x-2x, worked example shows 0.5x loss). Jurisdiction mismatch (Reg D cited but Mev is non-US). Dilution not shown in Breakout math. No mention of separate SAFE contract. Pattern: F&F docs must reconcile narrative promises with worked examples — contradictions poison relationship trust.
type: project
---

F&F investment document reviewed 2026-03-29. File: `~/otto/docs/ff-investment-document-2026.md`. Content DB ID: `8f1c8f60`.

**Why:** High relationship-capital stakes — document will be sent to Mev's personal network. Errors or misleading math could damage real relationships.

**How to apply:** Before clearing for send, confirm all 5 critical fixes below are applied.

## Verdict: NEEDS_CHANGES (7.5/10)

## Critical Issues

1. **Scenario 2 math contradiction** (line 154 vs line 156): Narrative says "1.5x–2x return over 5–7 years." Worked example shows $5,000 → $2,500 (0.5x — a loss). These directly contradict each other. A family member who re-reads before signing will catch this and lose trust.

2. **Dilution omitted from Breakout math** (line 168): $5K/$3M = 0.167% ownership calculated pre-Series A. At conversion, the Series A itself creates new shares — diluting that 0.167%. The "5x return" ($25,000) is overstated by the amount of Series A dilution. Must add one line: "This percentage will be diluted by the Series A shares, so actual value will be somewhat lower."

3. **Reg D 506(b) notice may be inapplicable** (line 213): Mev is non-US based. If investors are also non-US residents, citing US securities law as the compliance framework is misleading at best, legally incorrect at worst. Either: (a) confirm all investors are US residents, or (b) replace with "this offering is a private placement made exclusively to personal contacts of the founder, not a public solicitation" and get local legal advice for jurisdiction.

4. **"Outside investors get better information"** (line 38): "Outside investors get better information and terms because they negotiate them." This line could be read by a regulator as acknowledging differential disclosure to different investor classes — a red flag under any securities regime. Reframe: "Outside investors negotiate harder on terms. You get access earlier at a lower cap."

5. **No mention of separate SAFE agreement** (Section 6, Section 9): The document has a signature line but doesn't say a formal SAFE contract will follow separately. Family members may believe signing this document completes the investment — then be surprised when a separate legal agreement arrives. Add: "A separate SAFE agreement (the actual legal contract) will be provided for signature after you confirm your interest."

## Warnings

6. **48-hour personal response commitment** (Section 8): Real promise, easy to break when things go wrong. Worst time Mev will feel like responding is when things are bad — which is exactly when investors will reach out. Consider softening to "within a few business days" or scoping: "for non-urgent queries."

7. **"We will tell you before you hear it elsewhere"** (Section 7): Near-impossible to guarantee if bad news spreads socially. This sets up a specific betrayal scenario — one mutual friend telling another before Mev sends his update. Soften to: "We will communicate significant developments to investors promptly."

8. **Failure is "most likely outcome"** phrasing in scenario table (line 182): Calling failure "Significant — this is early-stage" is honest but may prevent investment entirely from non-sophisticated investors. The document is legally protected but practically unusable if no one invests. Consider: "Real risk — statistically common in early-stage" which is accurate without reading as a prediction.

9. **Tax implications not mentioned**: Neither a disclaimer nor advice to consult a tax advisor on investment implications. For international investors especially, this is a gap.

10. **"Survival" scenario underminer** (line 156 note): The parenthetical "(Note: small exits often do not return early investors well — this is why honest projection matters)" is correct but deflates the survival scenario entirely. At this point the document has three scenarios: loss, loss-with-a-smile, and maybe-ok. One honest positive statement in the survival case would balance without being misleading.

## What's Good

- Opening letter: excellent. "Do not invest because you care about me" is exactly right. Sets the relationship frame before money is mentioned.
- Risk section is thorough and honest. Six specific risks, two "do not invest what you can't lose" statements. Legally protective.
- SAFE explanation in plain English is clear and accurate. Non-sophisticated investors will actually understand it.
- Communication commitments are specific and credible (quarterly, 48h for major events, annual summary).
- Section 7 "What Happens If Things Go Wrong" is unusually good for a F&F doc — covers wind-down, no personal liability, and the relationship strain scenario directly.
- Placeholders table is comprehensive. No accidental gaps in what needs to be filled before sending.

## Relationship-Capital Risk Rating

**6.5/10 (Medium-High Risk before fixes)**

Primary risk vectors:
- The Scenario 2 math contradiction (narrative vs example) is the #1 relationship time-bomb — gets found at re-read or during bad news conversation
- The 48-hour/tell-you-first promises create specific betrayal scenarios
- The Reg D notice for non-US investors creates false legal framing

After fixes: risk drops to ~4/10 (acceptable for F&F round).
