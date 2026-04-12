---
name: articles_written
description: Topics and angles covered in all articles written — check before writing to avoid repeating ground
type: project
---

## Otto / Agent OS

### Otto: Agent OS Pink Paper ← v3 2026-04-12
- **DB ID**: 61534c50-21ae-4774-8aa6-fb7c7593d3b8 (v3, supercedes 9abcdba3)
- **Angle**: Technical pink paper for Otto as cognitive OS — 9 sections. Reasoning Kernel (AgentOS/IVT/RIC/S-MMU + Claude-vs-Otto line drawn), Memory as Physics (6 layers, 5-strategy retrieval), Self-Improvement Engine (RL2F with metric definitions, JiTEI honestly named, AutoEvolve with concrete example, MARS with scope/latency), The Pulse (dual heartbeat, 22 active agents), The Nervous System (Harmonic Mapping, alignment through entanglement with Goodhart's Law addressed, attestation generation, Human Supremacy of Will, task allocation constraint), Production Learnings, Phase 3 roadmap, constitutional purpose reference
- **File**: /mnt/media/projects/my3ye-web/content/blog/otto-agent-os-pink-paper.mdx
- **Status**: draft (~3,600 words, v3)
- **Story beat**: Law + Frame
- **Key constraint applied**: ALL blockchain/on-chain features in conditional tense — Phase 3 roadmap, NOT live. Agent economy: agents CANNOT accumulate governance scores (Human Supremacy of Will, constitutional). Governance factors now named as Ec/Is/Dv (aligned with Pink Paper No. 2 v4).
- **Stats**: 1,749+ completed tasks, 22 active agents, 182 catalog (April 2026 verified)
- **Competitive context**: surveyed 8 frameworks (April 2026) — methodology noted, language softened from "benchmark" to "survey"
- **TERMINOLOGY**: JiTRL renamed to JiTEI (Just-in-Time Experience Injection). All future references must use JiTEI. Benchmark claim softened to "survey."
- **v3 changes (2026-04-12)**: All critiques addressed. RL2F: added prediction categories (task/priority/blocker), random baseline (15%), honest "starting score not good score" framing. JiTRL→JiTEI: renamed, acknowledged "not RL." AutoEvolve: concrete example (dedup threshold 0.92→0.96, 60% false-positive reduction). MARS: activation scope + latency cost (3x). Benchmark→survey with methodology. Claude-vs-Otto paragraph added. Nervous System: Goodhart's Law (scorer/scored separation), task allocation auditability. Agent economy: Ec/Is/Dv named. Closing: constitutional purpose + four guardrails.
- **What NOT to repeat**: S-MMU paging model as the OS metaphor, "Memory is the substrate" as the pivot line, dual heartbeat as "execution + reflection" rhythm, goldfish memory bug, compound decay narrative, nervous system framing (owns alongside No. 2), Claude-as-engine/Otto-as-vehicle analogy (owns this), dedup 0.92→0.96 as AutoEvolve example (owns this)

### Pattern-Based Trust Under Quantum Threat: The Architectural Response ← NEW 2026-04-12
- **DB ID**: 267e29ae-8550-4f0b-b25f-560a4bc6dfcb
- **Angle**: Technical addendum to Pink Paper No. 2. Central claim: DPC behavioral algorithm is quantum-resistant by construction; ECDSA address binding is not. Documents 9 code-verified attack vectors (zero prior academic coverage). Dual-trust model: behavioral primary (DPC) + PQ crypto secondary (ML-DSA-65). 4-phase migration path.
- **File**: DB only
- **Status**: draft (~1,180 words)
- **Story beat**: Law
- **Parent**: eea0ead6 (Pink Paper No. 2)
- **Research anchor**: research note 754a8ce4 (8.5/10 validated)
- **What NOT to repeat**: "The key is the lock. The history is the name on the door. You can pick a lock. You cannot rename a building." as THE closing metaphor for this distinction. Nine attack vectors (numbered 1-9) fully covered. Do not revisit CONFIG_ROLE/setRegistry as a surprising discovery — already named.

## Technology / Protocol Explainers

### The Proof That Reveals Nothing ← NEW 2026-04-10
- **DB ID**: 6038138f-3242-4e48-8a15-251be596f09d
- **Angle**: ZK proofs explained via MY3YE brand voice — proof and disclosure can be separated (Goldwasser/Micali/Rackoff 1985); SNARKs removed interactive requirement; zkEVM as practical example; closing pivot to the-machine-needs-no-priest architecture
- **File**: /mnt/media/projects/my3ye-web/content/blog/the-proof-that-reveals-nothing.mdx
- **Status**: draft
- **Story beat**: The Law + The Mission
- **What NOT to repeat**: lock-combination example as the "prove without telling" illustration; keeper-asymmetry as THE argument (owned by The Machine Needs No Priest); "operator is structurally unnecessary" as the blockchain punchline

## SOS Systems / 505 Systems

### 505 Systems: The Governance Organism (Foundational Pink Paper) ← v2 2026-04-12
- **DB ID**: 99380ece-1d78-4861-b248-e4b35016fe78
- **Angle**: Foundational specification document — the canonical SOS Systems Pink Paper. v2 expands Section IV to include all three contribution dimensions (digital/physical/resource) and adds new Section V: Capital Contributions with constitutional exclusion + dual-track scoring model (P_gov / P_econ).
- **v2 changes (2026-04-12)**: Physical labor (Lh/St/Qp/Rk variables + Is_physical/Ec_physical/Dv_physical formulae), Resource contributions (FMV/U/Dc/Dp/Mn variables + Is_resource/Ec_resource/Dv_resource formulae), Capital dual-track (C_econ formula, CapitalRegistry planned, κ=0.3 starting / max 0.5, constitutional capital exclusion from P_gov, labor minimum for any capital reward). Rw renamed Dv throughout. New Section V: Capital. Renumbered V→VI through X→XI. New disclaimer adds CapitalRegistry and SplitEngine to planned contracts.
- **File**: /mnt/media/projects/505-systems-web/content/sos-systems-governance-organism-pink-paper.mdx
- **Status**: draft (~4,731 words, v2)
- **Story beat**: The Law + The Mission
- **Key constraint applied**: Status=early, no deployed contracts. LaborAttestation, ContributionRegistry, GovernanceWeight, CapitalRegistry, SplitEngine, ResourceRegistry — all in future/conditional tense.
- **What NOT to repeat**: Physical labor Lh/St/Qp/Rk formula (owns this), resource FMV/U/Dc/Dp/Mn depreciation model (owns this), C_econ = Cd × min(Ct/180)^0.5 × Cf (owns this), P_gov / P_econ dual-track split (owns this), κ constitutional maximum 0.5 (owns this), labor earns ≥67% constitutional guarantee (owns this), capital exclusion as anti-capture (not anti-investor) framing (owns this), physical-and-digital score comparably by design (owns this), per-address capital cap 10% (owns this), minimum labor requirement P_gov > 0 for any capital reward (owns this)

### Quantum Trust and the Value Shift ← v4 2026-04-12
- **DB ID**: eea0ead6-10ab-4658-972b-c002413a4819
- **Angle**: Pink Paper No. 2 — the Post-Secret Economy. 11 sections. Constitutional purpose: prosperity of all beings. Governance formula: P = Ec^α × Is^β × max(Dv, ε)^γ (machine-verifiable, no peer review). Four constitutional guardrails: Mutation Principle, Veil of Intent, Human Supremacy of Will, Actualization Principle. Covers: Pattern Crisis (math-as-wall→math-as-lens), vulnerability inventory (secp256k1/SNARK exposure, dormant wallet 3.7M BTC), Post-Secret Economy thesis, Proof of Vitality (PoS→PoV, Wealth=Metabolic Rate), Intelligence Layer (AI as nervous system, Goodhart's Law addressed, task allocation constraint), Quantum Alliance (quantum as foundation, QKD honest 5-10yr timeline, SP1), Shadow Problems (all four + Veil blind spots acknowledged), Constitutional Guardrails (all four + enforcement mechanism + immutable/upgradeable split), Migration Architecture (ceremony with time-lock and threshold), honest PoS tradeoff.
- **File**: /mnt/media/projects/505-systems-web/content/quantum-trust-and-the-value-shift.mdx
- **Status**: draft (~5,200 words, v4)
- **Story beat**: The Law + The Frame + The Mission
- **Key constraint applied**: ALL SOS contracts in future/conditional tense — no deployed contracts. Status=early verified.
- **v4 changes (2026-04-12)**: Replaced Rw (Weighted Resonance, required peer review) with Dv (Direction of Value, machine-verifiable accessibility delta). Added real math (multiplicative formula, Ec decay function, Is observables, Dv measurement). Added constitutional purpose "prosperity of all beings." Added 4th guardrail (Actualization Principle — no predicted contributions). Added enforcement mechanism (immutable core + upgradeable parameters). Added Goodhart's Law response. Added task allocation constraint. Added QKD timeline honesty. Acknowledged Veil of Intent blind spots. Tightened migration ceremony (time-lock + threshold). Added honest PoS tradeoff.
- **CRITICAL TERMINOLOGY CHANGE**: Rw (Weighted Resonance) is RETIRED. Replaced by Dv (Direction of Value). DPC formula is now P = Ec^α × Is^β × max(Dv, ε)^γ. All future articles must use Dv, not Rw. "Peer review" is no longer part of the governance formula.
- **What NOT to repeat**: Post-Secret Economy framing (owns this), math-as-wall→math-as-lens metaphor (owns this), Proof of Vitality / Wealth=Metabolic Rate (owns this), AI-as-nervous-system / Harmonic Mapping (owns this), four shadow problems (all four — owns), four constitutional guardrails (Mutation, Veil, Supremacy, Actualization — owns all), Dv as accessibility measurement (owns this), Sovereignty Through Verifiability (owns this), dormant wallet as "first quantum theft" (owns this), quantum-as-ally/foundation (owns this), States→Corporations→Organisms civilizational arc, Goodhart's Law scorer/scored separation (owns this), multiplicative formula structure as constitutional (owns this)


### The Answer Cannot Be Nobody
- **DB ID**: 3a0e28e4 (original, ready status) | 131729c6 (rewrite, draft)
- **Angle covered**: Governance architecture — DAOs fail, 505 is the organism not committee, DPC, three layers
- **Rewrite angle** (131729c6): Solo founder + AI narrative — one founder, Otto as operating AI, vision is the product, article is evidence of how it gets built
- **Status**: Rewrite is draft, awaiting Mev review

### SOS Systems: The Ladder Out
- **DB ID**: 42a3bfae
- **Angle covered**: Human angle — 121M displaced, access shortage not talent shortage, refuge + education ladder, not charity but physics

### The Base or the Empire ← NEW 2026-03-27
- **DB ID**: 1b6f0493-5024-4720-a10d-a013f83704c6
- **Angle covered**: AI empire vs open base framing — for intelligent non-Web3 audience (policy analyst, economist, technologist). Central tension: AI being built as chokepoints/empire vs SOS as open governed base. Ladder metaphor as reveal mechanism: milestones make organizational choices legible without accusation.
- **File**: /mnt/media/projects/505-systems-web/content/the-base-or-the-empire.mdx
- **Status**: draft
- **Story beat**: The Frame + The Law
- **What NOT to repeat**: AI-as-empire vs open-base tension (this piece owns it), ladder-as-reveal mechanism, "Watch who joins. Watch who doesn't." kicker

## MY3YE Ecosystem

### The Machine Needs No Priest ← OPTIMIZED 2026-03-30
- **DB ID (original)**: 5f08b83a-0f46-4ded-8423-ba78b8258e5a (draft)
- **DB ID (optimized)**: 4054fa28-4680-4281-9a1a-964a90fad964 (status=ready)
- **Angle**: Governance architecture — keeper asymmetry as old model; encoding rules into machines as structural inversion; three projects (Otto, SOS Systems, Koink) as evidence; why this matters beyond crypto; The Work as closing discipline statement
- **File**: /mnt/media/projects/my3ye-web/content/blog/the-machine-needs-no-priest.mdx
- **Status**: ready (optimized for Paragraph publication)
- **Story beat**: The Law + The Mission
- **Optimization changes**: (1) Broken link my3ye.xyz/protocol removed, (2) SOS Systems tense fixed to conditional/future, (3) Koink tense fixed to conditional/future, (4) Em dash→period for closing rhythm, (5) Date 2026-03-19→2026-03-30, (6) tags and published added, (7) category governance→protocol, (8) Paragraph CTA added
- **What NOT to repeat**: keeper asymmetry as THE argument, "capture the priest, capture the temple" triptych, "The rules are the machine. The machine is the rules." as the center pivot, "structurally unemployed" as the payoff line, encoding discipline (not inspiration/vision-casting) as the work frame

### Before the Protocol, the Proof (eaf5395d)
- **Angle**: Honest accounting — what exists NOW (Otto operational, WebAssist live, inception articles published) vs what is in development (ONEON, Tusita, SOS Systems, Shakrah, Panik — early) vs what is in design (Koink, Ottolabs, Music/Travel/Market/Properties — concept). Ecosystem emergence as founding story + invitation.
- **Story beats**: Mission + Dream
- **Status**: draft
- **File**: /mnt/media/projects/my3ye-web/content/blog/before-the-protocol-the-proof.mdx
- **Does NOT repeat**: lake/river as central frame, civilization collapse angle, Decentralized Eye reframe

### What We Are Building (474227ce)
- **Angle**: Full ecosystem founding vision — lake/extractive vs river/contributive, 10 protocols overview
- **Status**: published

### The Frequency Is Transmitting (fd3b2dcb)
- **Angle**: MY3YE inception article for Paragraph — overall ecosystem
- **Status**: draft — FLAGGED: Koink stated as live (it's concept status)

### What Survives the Weekend (34cdb76c)
- **Angle**: EasyA editorial — Web3 credibility, open code, agents in production
- **Status**: draft — BLOCKED: needs public GitHub repo URL

## Content written 2026-03-19 (content library rewrite)
6 blog article replacements (philosophy + tech), 7 inception articles across projects, MY3YE landing page copy (b6a0daef)

## MY3YE Landing Page — Fresh v2 (2026-03-27)
- **DB ID**: 70fbf60b-dc21-4244-9127-4e74acdb6daf
- **Commit**: f6aa790
- **Angle**: Blank-slate rewrite. Hero leads with RIVER LAW ("Power is not a lake. Power is a river.") instead of Decentralized Eye/watching frame.
- **Manifesto**: New title "The River Does Not Ask Permission." New spine: The System → River → Law → Pattern → Physics → Encoding → The Seat → The Edge → The Game → The Close.
- **CTA**: Canonical "We are asking you to build." Sub-message leads with $0 raised / 60% to builders as the concrete proof.
- **Font fix**: CTA H2 bumped from `lg:text-4xl` → `lg:text-5xl` for consistency with Mechanism/Protocols H2s.
- **What NOT to repeat**: watching/seeing distinction as hero frame, "Decentralized Eye" as section title, "The Core Principle" as Proof of Grit callout eyebrow.

## MY3YE Landing Page — Diagnosis/Declaration/Build/Call arc (2026-04-07)
- **DB ID**: caa61929-98ae-4988-b6c8-e1125f97fd50
- **Angle**: 4-beat movement structure. REMOVES the 9-paragraph arc prose letter from hero. DIAGNOSIS uses "design framing" (not wound framing — "The game was designed this way. Not broken. Designed."). DECLARATION uses canonical "Power is not a lake" as H1. THE BUILD names categories not individual protocols. THE CALL uses canonical three-line build ask.
- **What NOT to repeat**: design-framing of diagnosis (this owns it), "your contribution starts the record" kicker in CTA
- **Status**: draft (ready for implementation)

## MY3YE Landing Page — Scroll Copy v3 (2026-03-28, per Mev directive)
- **DB ID**: 0e1b9c85-d8b5-4de3-baa0-9e106f99ed85
- **Commit**: 1fd6d30
- **Angle**: Sparse axioms. Old angle told a story (narrative arc). New angle states facts.
- **Hero**: "Earn your weight." / "Nothing else buys in." — river metaphor removed from hero entirely; it lives in articles/whitepaper now.
- **Sub**: "No snapshot. No founder's share. / Contribution compounds. Capital does not."
- **Manifesto title**: "Nothing Is Given." (was "The River Does Not Ask Permission")
- **Manifesto sub**: "The protocol runs whether or not you are watching."
- **Stanzas**: 7 (was 12). ~40 words total (was ~75). No narrative arc — each stanza is a standalone fact.
- **Arc**: Entry → Accounting → Law → Mechanism → Design → Builders → Close
- **Outro**: "We built it for us." (stripped from longer original)
- **What NOT to repeat**: narrative arc across stanzas, river metaphor in hero, "watching/seeing" frame, "Every platform/governance/committee..." triptych pattern

## ONEON
### Identity Is the First Layer (e071b473)
- **Angle**: Identity as infrastructure — sovereign identity before network

### The Network Is Not a Service. It Is a Commons. (35aacd26)
- **Angle**: ONEON as commons infrastructure

## Tusita
### The Parallel Civilization (2c60ca97)
- **Angle**: Physical sovereign communities as parallel civilization

### The Place You Can Actually Live (ac0e39b6)
- **Angle**: Tusita as destination and lifestyle

## Otto AI
### Intelligence That Works for You (7b8062df)
- **Angle**: AI as servant not master

### The Machine Is Already Running (bfe5167e)
- **Angle**: Compounding memory — corporate AI forgets by design, Otto compounds. Evidence not pitch. Phase 1 live (single VM, AgentOS, dual heartbeat). Phase 3/4 in development/planned.
- **Story beat**: The Mission
- **Status**: draft
- **File**: /mnt/media/projects/my3ye-web/content/blog/the-machine-is-already-running.mdx

### Otto: Agent OS Pink Paper (9abcdba3) — 2026-04-11
- **DB ID**: 9abcdba3-e45c-439d-b761-f537ba7ec0cb
- **Angle**: Technical pink paper — full architectural account of Otto from inside the system. AgentOS kernel (IVT/RIC/S-MMU), 6-layer memory, 5 self-improvement systems, two heartbeats/hour, DAG task engine, honest lessons from 6 weeks in production. On-chain features (LaborAttestation, ContributionRegistry, GovernanceWeight) all future/conditional tense — not deployed.
- **Story beat**: Law + Frame
- **Status**: draft
- **File**: DB only
- **What NOT to repeat**: AgentOS/IVT/RIC/S-MMU technical breakdown, five-strategy retrieval stack, RL2F 40% accuracy stat, mass-archival incidents, rate-limit trap incident, goldfish memory bug, dual heartbeat structure, DAG task engine detail, 5 self-improvement systems enumeration

### We've Been Building an AI OS. Here's How It Compares to What Else Exists. (45407c6d) ← LinkedIn 2026-04-05, v3 harness section added
- **DB ID**: 45407c6d-88db-4e22-805c-13b3ebb5154a
- **Version**: 3 (v3 2026-04-05: AI harness section added — OpenClaw + Symphony; OTel gap updated to "now shipped")
- **Angle**: LinkedIn article — Otto's architecture vs 8 benchmarked frameworks (2026 landscape), honest gap analysis (OTel NOW SHIPPED, multi-LLM underdeveloped, community scale), blockchain roadmap as Phase 3 vision (NOT live — all future tense). Covers: 6-layer memory stack moat, RL2F+MARS+AutoEvolve structured self-improvement (unique across all frameworks), WebAssist as first live product.
- **v3 additions**: New section "category I left out" — AI harnesses (OpenClaw: >150K stars, heartbeat-native, flat-file memory, 5700+ skills; Symphony: BEAM runtime, deterministic runs). OTel gap updated from "building next" to "now shipped". Two gaps remain: multi-LLM routing + community ecosystem scale.
- **Voice**: LinkedIn practitioner, first-person Mev, short paragraphs — NOT MY3YE ecosystem voice
- **Story beat**: Mission + Frame
- **Status**: draft — ready for Mev to publish
- **Review changes (v1→v2)**: Pydantic AI uses Logfire (not LangSmith); "structured self-improvement loops" qualifier; EVM-compatible + smart contracts in blockchain section; comparison matrix links to first comment; closer sharpened to single question "What are you building on?"; 8 frameworks named in opening (added Mastra, OpenAI Agents SDK, AWS Strands); "We are two of three" given visual standalone weight
- **What NOT to repeat**: "agent is a runtime" vs "AI OS" framing, 6-layer memory stack as moat, RL2F+MARS+AutoEvolve as self-improvement moat, OTel as a gap (now resolved — shipped), AI harnesses vs frameworks distinction, OpenClaw as closest Otto parallel, blockchain ownership problem as Phase 3 vision, "two of three" closing structure

## KOINK
### Chaos With Structure. Chaos That Compounds. (9c46d865)
### The Meme Has Always Been a Mirror (e451f538)

## OTTOLABS
### The Workshop Is the Revolution (5892656b)
- **Angle**: Physical manufacturing/R&D arm — digital sovereignty without physical infrastructure is performance
- **Status**: draft (published: true in MDX)

### The Means of Production Belong to the Many (15982c81)
- **Angle**: Comprehensive physical stack — device ecosystem, robotics, energy, manufacturing
- **Status**: draft

### First the Intelligence, Then the Iron (7f9681d0)
- **DB ID**: 7f9681d0-8e7f-4a19-a17d-6b24646ec994
- **Angle**: AI services commercial engine — WebAssist (live), Tech Assist, App Assist, Brand Assist; intelligence → revenue → hardware sequencing; Otto as first proof of Ottolabs
- **Story beat**: The Mission + The Frame
- **Status**: draft
- **File**: /mnt/media/projects/my3ye-web/content/blog/first-the-intelligence-then-the-iron.mdx
- **What NOT to repeat**: services-fund-hardware sequencing, "revenue is the mechanism" framing

## SHAKRAH
### What the Body Knows Before the Protocol Does (f8ab84ff)

### What the Healer Carries (efb65920)
- **DB ID**: efb65920-4cb1-48f8-bb88-a435c3f0e8b0
- **Angle**: Practitioner perspective — corporate wellness extraction vs Shakrah planned practitioner-governed marketplace. Healer narrative entry. Biometric data ownership, community governance, Tusita Sanctuary as physical anchor.
- **Status**: draft — all claims qualified as planned/in development (status=early, no deployed contract)
- **Story beat**: The Mission + The Dream
- **File**: /mnt/media/projects/my3ye-web/content/blog/what-the-healer-carries.mdx
- **What NOT to repeat**: substrate/nervous system angle (f8ab84ff), builders-must-be-whole civilizational angle (b6b478a5), corporate 30-40% take rate as central argument

## Web3 / Blockchain Security

### Trust Is the Attack Surface (d6571c34)
- **DB ID**: d6571c34-44c6-4f0d-b38c-17b7d79ddce0
- **Angle**: Thought leadership — blockchain security failures are architectural not technical; "keeper problem" is the attack surface; audits document the problem, not solve it; MY3YE design principle = minimal trusted surface area; connects to "machine needs no priest" without repeating that article; references Ronin, Wormhole, Nomad exploits
- **Story beat**: The Law ("this is not punishment, this is physics")
- **Status**: draft
- **File**: /mnt/media/projects/my3ye-web/content/blog/trust-is-the-attack-surface.mdx

## DeFi / Web3 Technical

### The Currency That Did Not Ask Permission (1e4021b4)
- **DB ID**: 1e4021b4-5c1e-4b36-b1e8-a606646cc217
- **Angle**: Narrative/human — Venezuela remittance story, stablecoin as permissionless infrastructure, correspondent banking exclusion as structural failure, DeFi as physics not disruption. Composite illustrative character.
- **Story beat**: The Mission
- **Status**: draft
- **File**: /mnt/media/projects/my3ye-web/content/blog/the-currency-that-did-not-ask-permission.mdx

### The Block Is a Battleground (07e384b3)
- **Project**: KOINK
- **Angle**: MEV as the ultimate "lake" system — extraction by proximity not contribution. Three strategies (front-run, sandwich, liquidation). 2026 landscape: PBS, MEV-Share, intent-based, VRF. Koink.fun VRF fair launch as real-world example of encoded anti-extraction.
- **Story beats**: The Law + The Mission
- **Status**: draft

### A Contract That Cannot Lie (de8b2d4b)
- **DB ID**: de8b2d4b-1794-49b2-bcdd-e210d2b657f6
- **Angle**: Beginner explainer — contracts depend on enforcers; smart contracts make enforcement automatic and immutable. Extends vending machine analogy. Honest about limitations (bugs = law, need careful authors). No Solidity required to understand.
- **Story beat**: The Mission
- **File**: /mnt/media/projects/my3ye-web/content/blog/a-contract-that-cannot-lie.mdx
- **Status**: draft

## Web3 Trend Analysis

### What Compounds in the Silence (3f91edff)
- **DB ID**: 3f91edff-d4d4-43be-830a-93d86e6a5373
- **Angle**: Q1 2026 trend analysis — three structural shifts: intent-based execution as standard (not trend), AI exploit discovery operational (defender asymmetry widens), contribution-weighted governance becoming tractable. Frame: absence of speculation reveals genuine physics.
- **Story beat**: The Frame — "This is not punishment. This is physics."
- **Status**: draft
- **File**: /mnt/media/projects/my3ye-web/content/blog/what-compounds-in-the-silence.mdx
- **Note**: Avoids MEV mechanics (Block Is a Battleground) and bridge exploit case studies (Trust Is the Attack Surface)

## PiPi

### The Meme Is the Method (fb979e60)
- **Angle**: PiPi as FUNCTIONAL DESIGN — not mythology or PI framework explainer, but WHY the ecosystem chose a meme character. Culture as engineered trust layer. Meme bypasses skeptic; protocol follows.
- **Story beat**: The Frame
- **Status**: draft
- **File**: /mnt/media/projects/my3ye-web/content/blog/the-meme-is-the-method.mdx
- **What NOT to repeat**: mythology (Three Lives), PI framework explainer (v2 First Meme), Pepe heritage angle, K-k-koink as primary hook

## Otto Music

### What the Algorithm Cannot Hear (edcf8095)
- **Angle**: Discovery algorithm failure + four fronts (Manager/Player/Studio/Events/Festivals) + listener early-believer model + cultural layer (Tusita). PRE-WRITE CONSTRAINT applied — status=concept.
- **Story beat**: The Frame ("This is not punishment. This is physics.")
- **Status**: draft
- **File**: /mnt/media/projects/my3ye-web/content/blog/what-the-algorithm-cannot-hear.mdx
- **Existing article NOT repeated**: 8d15bb5a covers label extraction/royalties/AI tools — this covers discovery + four fronts structure

## MY3YE Manifesto / Lure Piece

### The Last Unfair Advantage ← NEW 2026-03-27
- **DB ID**: 2bb95205-76e2-4ff7-9d40-c1346313e223
- **Angle**: Capital was the moat; AI dissolved the coordination tax; clarity is now the only variable. Window argument — most haven't updated their model yet. Proof: one founder, no team, production system running. Invitation to build.
- **File**: /mnt/media/projects/my3ye-web/content/blog/the-last-unfair-advantage.mdx
- **Status**: draft
- **Story beat**: The Law + The Mission + The Dream
- **What NOT to repeat**: moat → river shift (this piece owns it), "clarity is the variable" frame, "coordination tax dissolved" mechanics, window-closing urgency argument

## Governance Manifesto — SOS / 505 Systems

### The River Has No King ← OPTIMIZED SOS-5 2026-03-30
- **DB ID (original)**: 5e01b2cb-939a-420f-9487-628b67d837c2 (draft source)
- **DB ID (optimized)**: a3ac5242-23a9-457a-83e4-7a58a7adb060 (status=ready)
- **Angle**: Philosophical — the oldest question about power ("are they good or evil?") is made structurally obsolete. Not better leaders but rotating meritocratic councils. The question doesn't get answered, it gets dissolved. Also covers: founder sunset by immutable contract, DPC open path to leadership.
- **File**: /mnt/media/projects/505-systems-web/content/the-river-has-no-king.mdx
- **Status**: ready (optimized for Paragraph publication)
- **Story beat**: The Law + The Mission
- **Optimization changes**: (1) 14 em dashes removed, (2) Phase 0/1/2 descriptions fixed to conditional/future tense, (3) Frontmatter stripped from body, (4) Date updated to 2026-03-30, (5) Negative checklist compliant (505-systems status=early, no contracts)
- **What NOT to repeat**: "are they good or evil?" dissolution argument (this piece owns it), founder sunset framing, rotating seat expiry as central mechanism, "the room" framing

## Founder Positioning Copy

### Why I Am the Best Person to Build This (1a369f23)
- **Content type**: note (not article — it's a copy reference document)
- **Angle covered**: Execution as the qualification — 15 years eng, Supra Oracles Web3 infra lead, solo-built live AI ecosystem, zero external funding. Three versions: short (30–50w), medium (~100w), long (~280w)
- **Status**: draft
- **What NOT to repeat**: "execution is already running" as the core answer, credentials-come-second framing

## Founder Origin Story

### Core Origin Story Narrative (86bb6d97)
- **Content type**: note (personal brand copy, not a published article)
- **Angle covered**: Arc narrative — 15y depth (FE/FS engineering) → Web3 evolution (Supra Oracles, Engineering Lead) → independent execution (built what no company would charter). Key frame: past is context, execution is the qualification.
- **Status**: draft
- **~200 words, first-person voice**
- **What NOT to repeat**: "no company was going to build this" constraint framing, "They are context, not qualification. The qualification is what is already running." as the kicker
- **Related**: 1a369f23 (answers *why best person*) | this answers *how did you get here*

## ONEON Positioning (Strategic Reference)

### ONEON: Four-Primitive Differentiation Positioning (5d18e242)
- **DB ID**: 5d18e242-940c-4a2c-9516-d7c4c94d65f6
- **Content type**: plan (strategic reference, not a public article)
- **Angle covered**: Competitive differentiation — 8-dimension matrix vs 7 protocols, four-primitive gap (identity + comms + governance + encrypted storage), DPC as governance moat, Memory Capsules as data moat, invisible onboarding as growth mechanism, Bluesky contrast as market proof
- **Status**: draft
- **Story beat**: The Frame + The Mission
- **All undeployed features qualified as**: "designed/not deployed" (DPC, Memory Capsules) or "planned" (invisible onboarding Phase 1, LoRa Phase 2)
- **What NOT to repeat**: 4-primitive matrix as core argument, Bluesky 40M vs Web3 45K contrast, "the gap no protocol occupies" frame, $240M raised / <100K DAU as the verdict

## PiPi (continued)

### Polkadot Forum — The chain that saw it first still has no face ← NEW 2026-03-28
- **DB ID**: 8a96c772-60e3-4105-8e84-3bc08aa4f17f
- **Content type**: social_post (forum post for forum.polkadot.network)
- **Angle covered**: Community discussion post — Polkadot's culture gap, prophet archetype fits DOT's real history (built multi-chain before buzzword, OpenGov before anyone else), PiPi as a built character with that narrative. Invites genuine discussion, not a formal pitch.
- **Tone**: First-person as Mev, community member raising a question
- **Status**: draft
- **Story beat**: The Frame
- **What NOT to repeat**: "chain that saw it first has no face" framing, prophet-archetype-fits-history argument, five-layer PI meaning intro

## OTTOLABS Capital Strategy (continued)

### Ottolabs Capital Raise Strategy & Pitch Narrative (1915511d)
- **DB ID**: 1915511d-a504-4861-9764-2f0b801093d3
- **Content type**: plan (strategic reference document, not a public article)
- **Angle covered**: Full 3-phase capital raise strategy: Phase 1 (grants + WebAssist + $KOIN, $75K-$200K, no dilution), Phase 2 (Lemnos P0 hardware VC + UNDP Tusita green bond, $500K-$2M), Phase 3 (Kembara + ADB + PPP, $5M-$20M). Pitch narratives for three audiences: hardware investors, development finance, Web3/DePIN.
- **Status**: draft — Mev review required
- **Story beat**: The Mission
- **Status qualifier applied**: All Ottolabs hardware/devices/contracts = PLANNED (pre-prototype). WebAssist = live. Otto AI = operational on one VM. No deployed contracts stated as fact.
- **What NOT to repeat**: 3-phase sequencing with exact milestone tables, RaaS framing as institutional preference, Lemnos as P0, Kembara as Phase 3, "Capital cannot make this real. Contribution does." kicker sentiment
- **Critical unknowns documented**: EIC Sri Lanka eligibility (unverified), EIB geographic mandate (unverified)

## LinkedIn Profile Bio (Job Market Positioning)

### LinkedIn Profile Bio — Mev (EM / Senior FE / AI Consulting) ← REVISED v2 2026-04-08
- **DB ID**: 5af8bf90-7e10-42c6-ae08-9bb7f8e4ac70
- **Content type**: note (LinkedIn About section copy)
- **Angle covered**: Three-audience positioning (EM / Senior FE / AI Readiness Consultant). Jobs-first structure: track record → current work (Ottolabs/Otto/WebAssist) → skills bullets → open-to signal → MY3YE mission closer
- **Voice**: LinkedIn practitioner voice (NOT ecosystem voice) — first-person Mev, short paragraphs, no river metaphor, no ecosystem brand lines
- **Status**: draft — Mev review/publish
- **Word count**: ~330 (v2 after review manifest applied)
- **Constraint applied**: Revenue claim softened (Stripe-pending). "AI operating system" overclaim fixed → "autonomous operations platform". LinkedIn plain-text formatting (no **, no → arrows). Headcount for Supra Oracles NOT confirmed — Mev to add actual team size for EM signal.
- **v2 changes**: 7 manifest entries applied (2 HIGH, 3 MEDIUM, 2 LOW) — see reviewer memory for detail
- **What NOT to repeat**: jobs-first → proof → open-to structure with Ottolabs/Otto/WebAssist as proof points; MY3YE as mission closer framing; "autonomous operations platform" as Otto descriptor

## Campaign Reference Documents

### Campaign Messaging Bible — Open System vs Empire ← NEW 2026-03-28
- **DB ID**: 50ebad1d-af8f-4592-886a-52111c3deb4e
- **Content type**: plan (strategic reference, feeds all downstream content)
- **Core line**: "Will you support the open system or the empire?"
- **What it defines**: Two sides (empire = closed AI/platform incumbents, open system = MY3YE ecosystem); 5 variations for Twitter/X, long-form, investor pitch, community onboarding, editorial/press; companion lines; vocabulary rules; usage guide
- **Key rule**: Do not name the empire as evil — the architecture is the argument, not the founders. Do not paraphrase the question.
- **What NOT to repeat**: The question's analytical explanation (defined here — articles just USE the question, not explain it)

## Investor Letter

### To the Investor Who Is Still Asking the Right Questions ← NEW 2026-03-28
- **DB ID**: dc1548f5-5afa-433c-bcd0-e55c513bf4b3
- **File**: ~/otto/docs/investor-letter.md
- **Content type**: article (founder letter / investor document)
- **Angle covered**: Full investor letter using empire framing as opening hook. Thesis: open systems win structurally (river vs lake metaphor throughout). Entities section: Ottolabs (open physical layer), Tusita (the address), full ecosystem reference. Capital paths: Phase 1 ($75K-$200K grants+revenue, no dilution), Phase 2 ($500K-$2M hardware VC + UNDP + PPP, Month 6-18), Phase 3 ($5M-$20M infrastructure fund, Month 18-36). Anti-extraction architecture: milestone gates on-chain, CET labor equity, 30% agent tax, governance non-concentration. Closes with the question.
- **Register**: Variation 3 from messaging bible (investor/analytical) + founder letter warmth — not a deck, not a consultant memo
- **Story beat**: The Frame + The Mission
- **Word count**: 2166
- **What NOT to repeat**: The exact three-phase capital sequencing with these numbers, the lake/river metaphor as the central structural frame for capital allocation, "Will you support the open system or the empire?" as the closing question (this letter owns the full investor close)

### High-Calibre Peer-to-Peer Investor Letter ← NEW 2026-03-28
- **DB ID**: fb4faa36-22db-4682-8207-473e88e52b77
- **Content type**: article (founder letter — compact, peer-to-peer, high-calibre)
- **Angle covered**: Short-form (430 words) invitation for top-tier investors. Not a pitch — evidence. Structure: contrarian opener (Otto running now, not on TechCrunch), base-layer capture physics (infrastructure transition pattern), physical layer window still open, Ethereum-at-$1 pattern recognition, close with canonical question.
- **Key line**: "This letter is itself evidence. Otto drafted it."
- **Register**: Peer-to-peer. The kind of letter a Sequoia partner forwards without being asked.
- **Story beat**: The Law + The Frame + The Mission
- **Word count**: ~430
- **What NOT to repeat**: "Otto drafted it" self-referential proof line (this owns it), Ethereum-at-$1 pattern recognition framing for this specific context, "operating continuously in production while every other AI company is still writing decks"

## MY3YE Ecosystem / Live Organism

### One Current, Every Bank ← NEW 2026-03-29 / REVISED Step 2
- **DB ID**: bc92f58f-1ffe-40e0-9fd2-6f362860bcc0
- **File**: /mnt/media/projects/my3ye-web/content/blog/one-current-every-bank.mdx
- **Angle**: Vertical scenario playbook — the Otto Loop running across 6 contributor types NOT covered in "Every Hand That Touched This": architect (dome spec → per-build royalty), chef (recipe → per-meal earnings), coder (governance module → integration revenue), curator (discovery on Otto Music → discovery residuals), data annotator (labels → Redistribution Pool), physical builder at Tusita (labor attestation → perpetual booking revenue).
- **Step 2 revisions**: Opening changed to inversion declaration ("The loop does not run in one vertical."); closing architecture anchor added before river closing line ("Same current. Every vertical. That is not a metaphor. It is the architecture.")
- **What NOT to repeat**: These 6 specific scenarios. "Different banks, one current" universality frame. "The river does not forget what it owes." kicker. "This is not generosity. It is accounting." line. "Same current. Every vertical. That is not a metaphor. It is the architecture." closing anchor.
- **Status**: draft (Step 2 complete)
- **Story beat**: The Law + The Dream
- **Word count**: ~780
- **Tense note**: All planned features in conditional/future ("designed to", "would be in the chain")

### Five Trades. One Law. ← NEW 2026-03-29 / REVISED Step 2
- **DB ID**: f1f5156a-4984-4c5c-bba7-712ed5014fc7
- **Angle**: Companion playbook to "Every Hand That Touched This" (438df147) and "One Current, Every Bank" (bc92f58f). Five verticals from an INDUSTRY/SECTOR perspective: furniture designer (design), musician (music), educator (SOS/education), farmer (Tusita/agriculture), developer (code/protocol). Each scenario walks the full Otto Loop from submission to governance weight. Companion to One Current's labor-role perspective.
- **Step 2 revisions**: Musician section — "she is also designed to earn" → "she also earns" (human action must use present tense per voice rule); Farmer section — "A small farm" → "A farmer" (wrong subject — person records, not place).
- **File**: /mnt/media/projects/my3ye-web/content/blog/five-trades-one-law.mdx
- **Status**: draft (Step 2 complete)
- **Story beat**: The Law + The Frame
- **Word count**: ~1,060
- **Tense discipline**: Full PRE-WRITE CONSTRAINT — all mechanisms use "designed to" / "planned to"; human actions use present tense
- **What NOT to repeat**: Five specific industry scenarios (design/music/education/agriculture/code), "Same eight stages in every one of them" central device, "That is not a promise. It is architecture." kicker, "The river does not care which valley it runs through." closing line

## TUSITA

### Let's Build a Better Island ← NEW 2026-03-29
- **DB ID**: 56316016-2fe2-4b0f-bc1c-31dd6987ce45
- **Angle**: Islands as sovereignty without accountability — private islands reflect their builders because there is no external check. The architecture determines whose argument wins. Tusita as the designed alternative: contribution-governed, on-chain rules, no single override authority.
- **Cultural subtext**: Extremely subtle Epstein Island resonance (files recently released) — never named; purely architectural argument works on two reading levels
- **Story beat**: The Law + The Frame
- **Status**: draft
- **File**: /mnt/media/projects/my3ye-web/content/blog/lets-build-a-better-island.mdx
- **What NOT to repeat**: "the island reflects its builder" frame, accountability-is-structural argument, "the design flaw IS the design" line, Tusita as accountability inversion
- **Tense discipline**: All Tusita features in "designed to" / "being built" — not operational

### The Loop Remembers ← OPTIMIZED SOS-2 2026-03-30
- **DB ID (original)**: 9e01c26c-9986-48e8-b027-f61069e28854 (draft)
- **DB ID (source for optimization)**: cc7a28cd-feb6-4537-8c04-5d54c8e56d85 (draft, partial prior optimization)
- **DB ID (optimized)**: 062609e0-cf49-45c2-bc14-2a42b977e1bc (status=ready)
- **Angle**: SOS inception article — island metaphor (private sovereignty vs contribution-governed) as entry frame; agents already earning on-chain as urgency hook (softened from $43M Bittensor stat); furniture loop (8-stage Otto Loop) as the concrete model; solo founder + AI as the working proof; SOS governance requirement (DPC mechanics included); automation liberation thesis; call to founding cohort
- **Story beat**: The Law + The Mission + The Frame + The Dream (all four)
- **File**: /mnt/media/projects/505-systems-web/content/the-loop-remembers-optimized.mdx
- **Status**: ready (optimized for Paragraph publication)
- **Word count**: ~1,040 (minus frontmatter)
- **Multi-Audience Review**: d3de345e — NEEDS_CHANGES 7.5/10. Applied all 6 fixes.
- **Optimizations**: (1) Bittensor $43M→tens of millions, (2) governance immutability→rules no single actor can rewrite, (3) SOS Systems is being built as the answer, (4) running without interruption→continuously in production, (5) 6 prose em dashes removed (2 canonical brand lines kept), (6) CTA strengthened with admin@otto.lk, (7) name reveal moved to parenthetical at first mention, (8) thousands of agents→a growing number
- **Negative checklist**: COMPLIANT — 505-systems status=early, no deployed contracts. All product claims use conditional/design tense.
- **What NOT to repeat**: island-reflects-builder frame, "when the agent earns, who earns?" as entry hook, furniture loop as central concrete example, "Not as a metaphor. As a fact." proof section structure, "The threat is an automated economy with no governance backbone." line, "This is not generosity. This is accounting." in loop context, automation-as-liberation-not-threat thesis arc

## Sri Lanka Movement

### The Island Does Not Have to Bow ← NEW 2026-03-29
- **DB ID**: 97015b04-6e99-49d7-a82c-8e6ba81e5e54
- **Angle**: Movement manifesto + community whitepaper for the Sri Lanka proposal. Entry: 2022 Sri Lanka crisis as concrete grounding (not abstract). Makes the case for WHY Sri Lanka (NPP alignment, $98M digital budget, SL-UDI operational, Port City crypto licensing live, 4.97% crypto penetration). What SOS Systems + Tusita are building (DPC governance, education ladder, dome communities). How the crypto community participates ($TUSITA tiers, $KOIN, Port City registration, DPC smart contract building). Dream: SL 2030 with on-chain contribution records, 50K digital jobs, Tusita ecotourism funding governance loop.
- **Story beat**: The Law + The Mission + The Frame + The Dream (all four)
- **File**: /mnt/media/projects/505-systems-web/content/the-island-does-not-have-to-bow.mdx
- **Status**: draft
- **Word count**: ~2,100
- **Commit**: 566f8b2
- **What NOT to repeat**: 2022 crisis as entry frame, "island does not have to bow" sovereignty framing, the five-tier $TUSITA participation model as CTA, SL-UDI + Port City + $98M budget as the three proof-of-window facts, "the first country that got it right" as the dream frame, "The record cannot be forged. It cannot be bought. It can only be earned." accountability line
- **Tone note**: Closest to a political manifesto of anything written. Register is higher stakes than normal articles. Canonical brand lines used at close. "For the ones who were handed nothing — we built this for us." placed in What We Are Building section.

## LinkedIn AI Consulting Series (for Mev's consulting positioning)

### Why Most AI Transformations Fail (And What Actually Works)
- **DB ID**: 0857eeb6-6bfc-4d9e-a96d-aceaa355c954
- **Content type**: article (LinkedIn long-form)
- **Project**: OTTOLABS (Mev consulting)
- **Angle covered**: Three hidden prerequisites of AI implementation (data readiness, process definition, change management). Failure is upstream of the tool. Incentive misalignment in vendor/consulting ecosystem. What the 10% who succeed actually do.
- **Series**: LinkedIn AI consulting Article 1 of 5
- **Target persona**: Burned Founder, Cautious Operator
- **Story beat**: The Frame
- **Status**: draft
- **Word count**: ~750
- **CTA**: Comment "READY" / DM for 90-min AI Readiness Diagnostic
- **Voice note**: LINKEDIN B2B PRACTITIONER VOICE — not MY3YE ecosystem voice. First-person Mev. Short paragraphs. No river metaphor. No ecosystem brand lines.
- **Data used**: Forrester 25% spend deferred; "research suggests ~90% failure" (directional, not hard stat)
- **What NOT to repeat**: three-prerequisites framing (data/process/change), "failure is upstream of the tool" as core argument, "20% technology / 80% people and process" ratio, pilot-works-but-scale-fails as entry observation, Forrester 25% deferral as closing data point

## Mev AI Consulting LinkedIn Series

### The Hidden Cost of Not Automating (A Business Case) ← LinkedIn Article 3 / 2026-04-03
- **DB ID**: bd5a4b2c-bb0d-4b92-b5d4-693565f06ed0
- **Content type**: article (LinkedIn long-form)
- **Project**: OTTOLABS (Mev consulting positioning)
- **Series**: Mev AI & Automation Consulting LinkedIn Series, Article 3 of 5
- **Target persona**: CFO Skeptic / Burned Founder
- **Angle**: Opportunity cost of NOT automating — flips the standard pitch by making the status quo feel expensive. Three hidden costs (productivity tax, error rate, speed gap), CFO math (40% efficiency, 6-month payback), risk framing, internal case-making guide.
- **CTA keyword**: "CASE" (triggers DM script)
- **Status**: draft — Step 3 COMPLETE (v2, 2026-04-03)
- **Word count**: ~840 (after review additions)
- **Voice**: Authoritative practitioner (NOT MY3YE brand voice — this is Mev's personal consulting LinkedIn)
- **Story beat**: N/A (consulting series, not MY3YE ecosystem)
- **DB-only**: No MDX file — LinkedIn article does not belong in my3ye-web blog
- **Review changes applied (v2)**: (1) "permanently"→"for good" [error rate section], (2) 40% efficiency attribution fixed to "implementations I have run with SMB and mid-market clients", (3) 6-month payback attribution fixed to "based on engagements I have run", (4) Single-point-of-failure strengthened: "The process dies with the person. And the replacement spends their first 30 days learning what the previous person never documented.", (5) Forrester 25% AI spend deferral stat added to "What Not Yet Actually Costs" section
- **What NOT to repeat**: "productivity tax" framing, "invisible competitive moat" line, "Not automating is a risk position, not just an efficiency position" close, the 4-hour vs 3-day inquiry response example, "before-and-after with your own numbers" as the CFO activation move, Forrester deferral stat (used here)

### The 90-Day AI & Automation Roadmap for Any Business ← LinkedIn Article 5 / 2026-04-03
- **DB ID**: cb240798-67e0-42c1-b743-4e2b61b63bb4
- **Content type**: article (LinkedIn long-form)
- **Project**: MEV_CONSULTING
- **Series**: Mev AI & Automation Consulting LinkedIn Series, Article 5 of 5
- **Target persona**: Burned Founder / Overwhelmed Leader (decision-ready)
- **Angle**: 90-day phased approach vs failed 18-month transformations. Three phases: Diagnose+Win Small (Days 1-30), Operationalize (Days 31-60), Build the System (Days 61-90). Organizational muscle argument — the most valuable outcome is the team's ability to iterate without external help.
- **CTA keyword**: "ROADMAP"
- **Status**: draft — Step 0 COMPLETE (2026-04-03)
- **Word count**: ~973
- **Voice**: Authoritative practitioner (NOT MY3YE brand voice)
- **Story beat**: N/A (consulting series, not MY3YE ecosystem)
- **DB-only**: No MDX file — LinkedIn article
- **What NOT to repeat**: 18-month-fails-from-scope-overload as entry argument, three-phase (30/60/90) day structure, "organizational muscle" as the true outcome, "systems compound in a way that projects do not" line, "proof is worth more than strategy at this stage" line, "ROADMAP" CTA keyword

### How to Build an AI-First Culture Without Losing Your Team ← LinkedIn Article 4 / 2026-04-03
- **DB ID**: 5f08f11f-1497-4c84-97cb-b40209094216
- **Content type**: article (LinkedIn long-form)
- **Project**: OTTOLABS (Mev consulting positioning)
- **Series**: Mev AI & Automation Consulting LinkedIn Series, Article 4 of 5
- **Target persona**: The Builder / People-First Leader / Operations-focused Founder
- **Angle**: Culture as the hardest operational variable in AI implementation. Core insight: resistance comes from fear of losing value (not fear of tech). The fix: involve people in designing the change. Three specific leader mistakes: skip job security talk, measure adoption too early, train enthusiasts instead of skeptics. Success signal: team owns and improves the system.
- **CTA keyword**: "CULTURE"
- **Status**: draft — Step 0 COMPLETE (2026-04-03)
- **Word count**: ~855
- **Voice**: Authoritative practitioner (NOT MY3YE brand voice)
- **Story beat**: N/A (consulting series, not MY3YE ecosystem)
- **DB-only**: No MDX file — LinkedIn article
- **What NOT to repeat**: "tool doesn't resist, team does" opener, the value-loss fear framing (vs. tech fear), "built with them not handed to them" line, "you don't announce your way to AI-first culture, you demonstrate it", train skeptics first insight, "CULTURE" CTA keyword

### Note on LinkedIn Series Voice
- This 5-article series uses Mev's personal consulting voice — NOT MY3YE brand voice
- Short paragraphs (2-3 lines), direct and practitioner-grounded, no hype, no jargon walls
- Every article ends with a keyword CTA (READY / AUDIT / CASE / CULTURE / ROADMAP)
- Series strategy document at: ~/otto/logs/tasks/72e029a4-e73f-4646-a7b1-fffd2934965e/linkedin_strategy.md

## zkPresence Open Source Documentation (2026-04-11)

### zkPresence README
- **DB ID**: bd3ef86a-fa73-41ac-b53b-4f5861167d2f
- **File**: /home/web3relic/otto/zkpresence/README.md
- **Content type**: note (open-source project docs)
- **Angle**: Developer-facing README — problem framing (surveillance receipt), architecture diagram, attestation modes table, security properties, honest status warning (alpha, circuit in-development), contribution CTA
- **Status**: draft
- **Voice**: Developer-first technical precision; brand voice in problem framing section only; no ecosystem jargon
- **Negative checklist**: Applied. No deployed contracts stated as fact. Circuit SHA-256/ECDSA described as "in active development." All TypeScript packages described as "planned" or "scaffold."

### zkPresence ROADMAP
- **DB ID**: 7909fd14-42c2-4095-bc8e-386b47174ed4
- **File**: /home/web3relic/otto/zkpresence/ROADMAP.md
- **Content type**: roadmap
- **Angle**: Phase 0 → 1 → 2 → 3 structure. Phase 0 complete. Phase 1 = precompile wiring + Base Sepolia deploy. Phase 2 = SDK + organizer tool. Phase 3 = production, ecosystem integrations (Otto Music, Tusita), sybil resistance research.
- **Status**: draft
- **Voice**: Clinical, table-driven, future tense throughout for all planned items

### zkPresence CONTRIBUTING
- **DB ID**: a37a3023-c611-4be9-8c8b-6a91bcb3bfc5
- **File**: /home/web3relic/otto/zkpresence/CONTRIBUTING.md
- **Content type**: note (open-source project docs)
- **Angle**: Practical developer guide. Leads with SP1 precompile wiring (SHA-256 via sha2 crate, ECDSA via k256 crate), Foundry test priorities, TypeScript SDK stubs. Includes security section, PR workflow, code style.
- **Status**: draft

### zkPresence QUICK_START
- **DB ID**: a51066e9-2c2f-4a57-bd61-83ae5f862be2
- **File**: /home/web3relic/otto/zkpresence/docs/QUICK_START.md
- **Content type**: note (documentation)
- **Angle**: End-to-end flow — build → prove (mock mode) → deploy → submit proof → verify. Proof time table (mock/local/network). Clear status note about circuit development state.
- **Status**: draft (review feedback applied 2026-04-11, commit 122416b)

### Review Feedback Applied (2026-04-11)
- Critical: ECDSA simultaneous-wiring warning added to CONTRIBUTING.md (Before You Start + SHA-256 section end). Circuit bogus-API fix was pre-applied in commit 18a61e7.
- Critical: QUICK_START Step 3 output comment replaced with sha256 panic warning
- Warning: Gas estimate anchored (~0.001 gwei, basefees.net)
- Warning: Otto Music/Tusita reframed as generic platform examples (not internal brand names)
- Warning: ARCHITECTURE.md geohash contradiction annotated (6-char storage, 5-char prefix match)
- Suggestions: SP1 v6.1.0 pinned, Phase 1 target 2026-05-02, GitHub Discussions link, PR sequencing note

## Angles NOT yet taken
- Personal founder motivation/story — WHY Mev cares (the *why*, not the *what*) — flagged still missing: the mission narrative / seeker / meditation / abundance worldview
- SOS integrity layer deep dive (offline mesh, displaced communities, auditable aid) — referenced but not centered in new piece; could be its own article
- Deep DPC mechanics walkthrough (reserved for Pink Paper)
- Solo founder + AI as a *how-to* or *model* article (partially started in rewrite)
- Otto AI inception article (7b8062fd is a version but may need rewrite)
- MEV redistribution model: how anti-MEV protocols return value to LPs (extension of The Block Is a Battleground)
- Q1 2026 angles remaining: AI+Web3 convergence (deeper), L2 ecosystem maturation, developer credentialing shift
- Sri Lanka: government response article (for when the proposal gets traction)
- Sri Lanka: diaspora-specific piece (more emotional, less technical — for the WhatsApp groups)

## Mev Job Search Materials — Resume Variants (2026-04-06)

### Resume — Senior Frontend Engineer (e12c5b92)
- **Content type**: note (personal document, not a published article)
- **File**: /mnt/media/projects/mev-personal/resume-senior-frontend-engineer-2026.md
- **DB ID**: e12c5b92-f1ee-46ba-996d-4e371f3bc132
- **Target role**: Senior Frontend Engineer at Web3, AI lab, or high-craft product companies
- **Key positioning**: "Infrastructure engineer who builds products" — WebAssist as showcase project, Otto as full-stack depth signal, Supra Oracles as Web3 credibility anchor
- **ATS keywords loaded**: TypeScript, Next.js 15, React 18, Tailwind, Supabase, Vercel, Stripe, FastAPI, pgvector, Docker, systemd, Claude API, Gemini, WebSocket, VAD, WCAG 2.2, Core Web Vitals, wagmi, ethers.js
- **Needs from Mev**: Supra Oracles dates, prior employment (2010–Supra), education, contact info
- **Status**: draft

### Resume — Engineering Lead / Tech Lead (98572a29)
- **Content type**: note (personal document, not a published article)
- **File**: /mnt/media/projects/mev-personal/resume-engineering-lead-2026.md
- **DB ID**: 98572a29-59f7-40f6-ac79-fa59347ee959
- **Target role**: Engineering Lead / Tech Lead at Web3 infra, AI product, or blockchain companies
- **Key positioning**: Solo architect of 21-agent autonomous team = demonstrated engineering leadership depth without requiring traditional management context. Supra Oracles establishes the prior lead pedigree.
- **Key reframe**: 21 specialist Otto sub-agents directed = engineering team led. DAG task queue = sprint/dependency management. Workflow engine = CI/CD pipeline ownership. All real, technically credible.
- **Leadership approach section**: included — covers AI workflow leadership, architecture decision philosophy, code review as mentoring. Mev should review and adjust voice.
- **Needs from Mev**: Supra Oracles team size, dates, specific wins; prior employment; education; contact info
- **Status**: draft
