# Conflict of Interest Analysis: Anthropic Employment + Ottolabs

**Date:** 2026-04-09
**Prepared by:** Otto (researcher agent)
**Topic:** Strategic and legal analysis of running Ottolabs (WebAssist, Otto AI platform) as a full-time Anthropic employee

---

## Executive Summary

The conflict is **real but manageable** with proactive disclosure and proper structure. The biggest risk is not what you do **after** joining Anthropic — it's what you sign on day one without reading it. The PIIA (Proprietary Information and Inventions Agreement) is the decisive document. If Ottolabs is not listed as a prior invention before signing, Anthropic may have grounds to claim ownership of anything developed during employment that "relates to" their business — and building AI-powered services on top of Claude's API clearly relates to Anthropic's business.

**The path forward exists. It requires negotiation before day one, not after.**

---

## 1. The Legal Landscape

### 1.1 California Labor Code Section 2870

Anthropic is headquartered in San Francisco. If Mev works as a California-based employee (even remotely), Cal. Labor Code § 2870 provides critical protections:

**Employers CANNOT claim inventions if all of the following apply:**
- Developed entirely on personal time
- Without using employer's equipment, supplies, facilities, or trade secret information
- Does NOT relate to employer's business or anticipated R&D
- Does NOT result from work performed for the employer

**The fatal exception for Ottolabs:** The carve-out for "relates to employer's business" is extremely broad and will almost certainly apply. Anthropic's core business is AI services — specifically, building Claude and enabling developers to build on Claude. Ottolabs (WebAssist, Otto) does exactly that: it builds AI-powered services using Claude. A court would likely find this "relates to" Anthropic's business regardless of when or where the work was done.

**Critical:** If Mev is employed as a remote worker from Sri Lanka under Sri Lankan law, there is NO equivalent of Cal. Labor Code § 2870. Sri Lankan employment law is far less protective of employee IP rights. The employment jurisdiction matters enormously.

### 1.2 Standard Big Tech PIIA Provisions

Anthropic, like Google, Apple, Meta, OpenAI, and every other Bay Area AI company, will require signing a PIIA (Proprietary Information and Inventions Agreement) on day one. Standard PIIA language claims ownership of any invention:

- Created during the employment period
- Using company resources (computers, APIs, internal tools, trade secrets)
- That "relates to" the company's business
- That results from the employee's work duties

**The "relates to" standard is the danger zone.** Courts have interpreted this broadly. If you use any Anthropic internal knowledge — model roadmaps, capability benchmarks, unpublished API features, internal tooling — and that knowledge improves Ottolabs, even indirectly, Anthropic may claim an interest.

**The Prior Inventions Schedule:** Most PIIAs include a Section where employees can list prior inventions that are explicitly excluded from the agreement's scope. **This is Mev's primary legal shield.** If Ottolabs is listed in this schedule before signing, it is carved out from Anthropic's IP claims — assuming the listing is specific enough (project name, description, date of creation). If this schedule is left blank or vague, the carve-out is lost.

### 1.3 What Anthropic's Own Terms Say

**Commercial API Terms (confirmed from anthropic.com/legal/commercial-terms):**
- Prohibit building "a competing product or service, including training competing AI models or reselling the Services"
- **Ottolabs is NOT in violation of this:** WebAssist and Otto are AI-powered service businesses, not competing LLMs, not retraining models, not reselling the API
- Customer Content cannot be used to train Anthropic models (opt-in)

**Consumer Terms (confirmed from anthropic.com/terms):**
- Same competitive product restriction
- IP in Outputs belongs to the customer (Ottolabs retains its output IP)
- Anthropic retains ownership of the Services themselves

**Bottom line on API terms:** Ottolabs' current model is compatible with Anthropic's commercial terms. The tension is in the **employment agreement**, not the API terms.

### 1.4 Non-Compete Clauses

Non-compete agreements are **unenforceable in California** as a matter of public policy (Cal. Bus. & Prof. Code § 16600). Even if Anthropic includes a non-compete in the employment contract, Mev cannot be legally barred from running Ottolabs in California.

**Exceptions that still apply even in California:**
- Non-solicitation of Anthropic employees (enforceable)
- Non-solicitation of Anthropic customers (likely enforceable)
- Confidentiality obligations (fully enforceable)
- IP assignment obligations (enforceable where the "relates to" test is met)

---

## 2. Risk Analysis

### 2.1 IP Claim Risk — HIGH

**Scenario:** Anthropic's legal team determines that improvements made to Ottolabs during employment — even on personal time — "relate to" Anthropic's AI services business. They argue Mev used internal knowledge of model capabilities to optimize Otto's prompts, workflows, or API integration.

**Probability:** Medium-high if Mev uses ANY Anthropic internal knowledge (model benchmarks, unreleased capabilities, internal tooling) to improve Ottolabs.

**Consequence:** Anthropic could claim ownership of Ottolabs' software systems, require cessation of operations, or demand revenue share.

**Mitigation:**
1. List Ottolabs explicitly in the PIIA Prior Inventions schedule before day one
2. Maintain strict separation: zero use of Anthropic internal knowledge for Ottolabs
3. Keep Ottolabs development entirely on personal devices with no Anthropic credentials
4. Use Ottolabs' own commercial API account — not Mev's Anthropic employee account

### 2.2 Insider Information Risk — HIGH

**Scenario:** As an Anthropic employee, Mev learns (legitimately via work) that Claude 4 will launch with 2x context window in 3 months. Ottolabs' product roadmap is adjusted accordingly. This constitutes use of material non-public information for competitive advantage.

**Sub-scenario:** If Anthropic ever goes public, this becomes securities fraud exposure.

**Probability:** Unavoidable if Mev has access to product roadmap discussions.

**Consequence:** Termination for cause (losing unvested equity), potential legal action, reputational damage in AI community.

**Mitigation:**
- Disclosure and written consent from Anthropic legal
- Firewall between Mev's employment knowledge and Ottolabs business decisions
- Ottolabs board/co-founder separate from Mev who makes product decisions independently

### 2.3 Equity Conflict — MEDIUM

**Scenario:** Anthropic offers a standard compensation package with equity. Mev holds equity/ownership in Ottolabs. Decisions that benefit Ottolabs could harm Anthropic's interests (e.g., pushing for an API feature that primarily benefits Ottolabs-type businesses, or allocating mental bandwidth away from Anthropic duties).

**Consequence:** Conflict of interest claim, forced divestiture of Ottolabs equity, performance issues.

**Mitigation:**
- Transparent disclosure of Ottolabs ownership stake in the hiring process
- Written carve-out in employment agreement permitting ongoing Ottolabs ownership
- Clear delineation: Mev is not using Anthropic role to advocate for Ottolabs interests

### 2.4 Time Allocation Risk — MEDIUM

**Scenario:** Anthropic expects full-time engagement. Ottolabs (heartbeat system, WebAssist, customer issues) demands Mev's attention during work hours.

**Probability:** High — Otto's current architecture requires Mev's oversight for key decisions.

**Consequence:** Performance issues, policy violation (moonlighting during work hours), termination.

**Mitigation:**
- Otto must become more autonomous before Mev joins Anthropic full-time
- Clear policy: zero Ottolabs work during Anthropic work hours
- If Ottolabs has revenue, potentially hire operational help

### 2.5 API Access Subsidy Risk — MEDIUM

**Scenario:** Anthropic employees receive free or discounted API access. Mev uses this credit for Ottolabs.

**Probability:** Low if Ottolabs has its own API account. High if accounts are mixed.

**Consequence:** Policy violation, potential claim that Ottolabs is subsidized by Anthropic resources (strengthening IP claim).

**Mitigation:** Separate Ottolabs API account under the Ottolabs entity. Never use Mev's employee account for Ottolabs workloads.

### 2.6 API Terms Violation Risk — LOW

Based on confirmed Commercial Terms review: Ottolabs does not compete with Anthropic's services, does not train competing models, does not resell the API. This risk is low as currently structured.

---

## 3. Upside Scenarios

These benefits only materialize if the relationship is **explicitly approved in writing** by Anthropic.

| Upside | Mechanism | Value |
|--------|-----------|-------|
| **Early API access** | Beta model access before public release | Significant competitive advantage for Ottolabs feature roadmap |
| **Direct feedback loop** | Bug reports, feature requests get traction from internal advocate | Saves months of external dev cycle |
| **Engineering network** | Connections to Anthropic researchers, safety team, product team | Potential partnerships, hiring signal for future Ottolabs full-time transition |
| **Credibility signal** | "Built by an Anthropic engineer" is extremely powerful for B2B sales | Unlocks enterprise client conversations |
| **Learning compounding** | Hands-on understanding of model limits, prompting, safety constraints → better Ottolabs products | Non-transferable advantage |
| **Funding introductions** | Anthropic network includes Spark Capital, Google Ventures, Salesforce Ventures investors | Potential warm intros for Ottolabs raise |
| **Mission alignment** | Both Ottolabs and Anthropic serve "AI for humanity" mission | Narrative coherence, no cognitive dissonance |

---

## 4. Disclosure Norms in the AI Industry

The AI industry in 2026 has evolved norms around this:

1. **Disclosure is expected, not optional.** Companies like OpenAI, Anthropic, DeepMind track employees' public profiles and side projects. Surprise discovery of an undisclosed side business is treated as a policy violation, not an oversight.

2. **Many companies permit non-competing side projects.** The standard is: (a) fully disclosed, (b) doesn't use company time/resources, (c) doesn't compete with company business, (d) doesn't use confidential information. Ottolabs meets (a)-(d) if managed carefully.

3. **Written consent is the gold standard.** A verbal "sure, fine" from a hiring manager is not protection. Mev needs a written carve-out, ideally in the offer letter or an addendum to the employment agreement, explicitly permitting continued operation of Ottolabs.

4. **"Prior Inventions" schedule in the PIIA is the legal protection.** Every AI company uses this form. Filling it in completely is the difference between protected and exposed.

---

## 5. Questions Mev MUST Answer Before Applying

### Legal/Structural (Answer Before Application)

1. **What jurisdiction will the employment contract use?**
   → California law (favorable) vs. Sri Lanka law (unfavorable) vs. another jurisdiction matters enormously for IP protections. Confirm before signing.

2. **Is Ottolabs currently a separate legal entity?**
   → An incorporated company (LLC, PTE Ltd, etc.) is far harder for Anthropic to claim ownership of than a personal project. If Ottolabs is not incorporated, do it before day one at Anthropic.

3. **Are there existing third-party investors or co-founders in Ottolabs?**
   → Third-party stakeholders create legal barriers to any IP claim and establish prior ownership. Even a simple SAFE investment from a friend creates documented prior ownership.

4. **What date does Ottolabs "exist" from — and can it be documented?**
   → Git commit history, domain registration dates, business registration dates, prior investment documents all establish prior ownership before employment. Catalog these now.

### Negotiation Questions (Raise During Offer Stage)

5. **Does the PIIA include a Prior Inventions schedule, and will Anthropic accept Ottolabs as a listed prior invention?**
   → This is the core negotiation. Ask explicitly. If they say no to the carve-out, that's a red flag.

6. **Will Anthropic provide a written moonlighting approval for Ottolabs in the offer letter or employment addendum?**
   → Must be in writing. Ask for it explicitly as a condition of acceptance.

7. **What is Anthropic's policy on employees using the Claude API for personal projects?**
   → Need written clarity: is Ottolabs permitted under the employee moonlighting policy?

8. **What is the scope of the PIIA — does it cover work done outside California?**
   → If Mev works remotely from Sri Lanka, what law applies?

### Operational Questions (Decide Before Starting)

9. **Can Ottolabs operate with significantly reduced Mev involvement?**
   → If Otto requires 2+ hours/day of Mev's active oversight, this becomes a time-conflict problem. How much can Otto self-operate before Mev joins Anthropic?

10. **Is Ottolabs' API account completely separate from any Anthropic credentials?**
    → The Ottolabs API account must be under the Ottolabs entity with its own billing. No crossover with Mev's Anthropic employee account ever.

11. **Which role is Mev applying for at Anthropic?**
    → A frontend role with minimal model access creates low IP risk. A prompting/research/policy role creates high insider information risk. Role scope changes the risk profile significantly.

12. **Is Mev prepared to pause active Ottolabs development during the 90-day probation/cliff period?**
    → The highest risk window is day one to month four. Slowing Ottolabs development during this window reduces IP exposure and performance risk.

---

## 6. Recommended Pre-Application Actions

In rough priority order:

**Must-do before applying:**
1. **Incorporate Ottolabs** as a separate legal entity (if not done) — creates documented prior ownership
2. **Document all prior Ottolabs invention dates** — git history, domain registrations, any prior sales/customers
3. **Separate API account** — ensure Ottolabs has its own commercial Claude API account under the entity, not linked to Mev personally

**Must-do at offer stage:**
4. **Request Prior Inventions carve-out** — specifically name Ottolabs, WebAssist, Otto AI system in the PIIA schedule
5. **Request written moonlighting approval** — in the offer letter or separate employment addendum
6. **Have a lawyer review the PIIA** before signing — employment IP attorneys can flag aggressive clauses that go beyond California norms

**Should-do before starting:**
7. **Build Otto's operational autonomy** — reduce Mev's daily management burden so Ottolabs can run without constant oversight during work hours
8. **Clarify Anthropic's employee API policy** — get written confirmation that Ottolabs (separate entity) can continue using the commercial API
9. **Decide Mev's role in Ottolabs post-join** — minority equity holder who is hands-off? Active co-founder? The answer affects disclosure and compliance

---

## 7. The Honest Strategic Assessment

**The upside case:** Anthropic employment + Ottolabs is a high-leverage combination. "Built by an Anthropic engineer" unlocks enterprise sales, investor introductions, and credibility that takes years to build otherwise. Early API access and internal feedback loops could accelerate Ottolabs by 12-18 months. The mission alignment is genuine.

**The downside case:** Getting this wrong doesn't just cost the Anthropic job. It could cost Ottolabs' IP, especially if Anthropic argues that the systems built during employment (Otto's memory architecture, WebAssist's LLM orchestration layer) "relate to" their AI services business. The damage could follow Mev for years.

**The path:** Disclose early, negotiate hard at the offer stage, get everything in writing, incorporate before day one, and maintain strict operational separation after starting. If Anthropic won't provide written approval for Ottolabs to continue operating, that is a clear signal that the arrangement won't work — and it's better to know that before signing.

---

## Sources

- Anthropic Commercial Terms of Service: https://www.anthropic.com/legal/commercial-terms (reviewed April 2026)
- Anthropic Consumer Terms: https://www.anthropic.com/terms (reviewed April 2026)
- Anthropic Usage Policy: https://www.anthropic.com/legal/aup (reviewed April 2026)
- California Labor Code § 2870 (leginfo.legislature.ca.gov, reviewed April 2026)
- Research by Otto researcher agent, April 9, 2026
