# Workflow Templates Architecture — 2026-03-22

## Design: 4 High-Value Workflow Templates from Agent Directory

---

### Problem

Otto has 138 specialist agents in the agency-agents repo but only uses ~14 of them across 4 workflow templates. High-priority operational needs (WebAssist outbound sales, Web3 smart contracts, grant applications, product sprints) have no dedicated workflow templates, requiring ad-hoc tasks with no pipeline structure, reuse, or evolutionary improvement.

---

### Current State

**Active agents** (14): content-creator, researcher, coder, debugger, reviewer, architect, memory-curator, landing-page, growth-hacker, twitter-engager, social-media-strategist, security-audit, research-synthesizer

**Existing templates** (4):
| Template | Steps | Fitness |
|---|---|---|
| feature-development | architect → coder → reviewer → debugger → notify | 0.82 |
| content-publishing-pipeline | content-creator → reviewer → content-creator → coder → notify | 0.79 |
| research-pipeline | researcher → research-synthesizer → reviewer → researcher → notify | — |
| social-content-pipeline | social-media-strategist → twitter-engager → reviewer → content-creator → notify | — |

**Gap**: No pipelines for outbound sales, smart contracts, grants, or product sprints.

---

### 4 New Templates

---

## Template 1: outbound-sales-pipeline

**Priority**: P10 (WebAssist revenue — highest priority)
**Tags**: sales, outbound, webassist, leads

**Purpose**: Research target prospects, qualify via signal intelligence, draft personalized outreach sequences, review quality, and notify. Used to generate WebAssist leads.

**Agents to activate**: `outbound-strategist` (from sales/sales-outbound-strategist.md)

### Steps

| # | Name | Agent | Budget | Turns | Timeout | On Failure |
|---|---|---|---|---|---|---|
| 0 | ICP & Signal Research | researcher | $4 | 40 | 900s | retry_once |
| 1 | Prospect Qualification & List | outbound-strategist | $4 | 40 | 900s | retry_once |
| 2 | Sequence Draft | content-creator | $4 | 40 | 900s | retry_once |
| 3 | Sequence Review | reviewer | $2 | 25 | 600s | skip |
| 4 | Refine & Finalize | content-creator | $3 | 30 | 600s | retry_once |
| 5 | Notify | (action=notify) | — | — | — | — |

### Variables
- `target_industry` — industry to target (e.g. "SaaS startups needing websites")
- `icp_description` — ideal customer profile description
- `service_offer` — what we're selling (e.g. "WebAssist — $2,995 complete website")
- `outreach_channel` — email / linkedin / twitter (default: email)
- `num_prospects` — target prospect count (default: 10)

### Step 0 Prompt Template
```
Research the ideal customer profile and buying signals for this outbound campaign:

Target Industry: {target_industry}
ICP: {icp_description}
Service: {service_offer}

Tasks:
1. Search semantic memory for existing prospect data: POST http://localhost:8100/semantic/search {"query": "{target_industry} prospects leads"}
2. Research the industry: company size, tech stack patterns, hiring signals, funding activity
3. Identify TOP 3 buying signals most predictive of converting to {service_offer}
4. Map common objections and how to handle them
5. Identify best channels and timing for this ICP

Output: Structured ICP profile with signal taxonomy. Max 2000 tokens.
```

### Step 1 Prompt Template
```
You are Outbound Strategist. Using the ICP research below, build a qualified prospect list and signal-triggered outreach strategy.

ICP Research:
{prev_output}

Service: {service_offer}
Channel: {outreach_channel}
Target Count: {num_prospects}

Tasks:
1. Define the precise ICP criteria from the research
2. List {num_prospects} specific prospect targets (company + role + signal detected)
3. Assign signal tier (Tier 1/2/3) to each prospect
4. Design the outreach sequence structure: touchpoints, timing, channel mix
5. Write the core value proposition angle for this ICP

Output: Prospect list (JSON) + sequence architecture. Store top prospects via POST http://localhost:8100/semantic/remember with category="lead".
```

### Step 2 Prompt Template
```
Draft personalized outreach sequences for these prospects.

Prospects and sequence architecture:
{prev_output}

ICP Research:
{step_0_output}

Service: {service_offer}
Channel: {outreach_channel}

Tasks:
1. Write 3-touchpoint sequences for each prospect tier (T1, T2, T3)
2. Touchpoint 1: cold outreach (reference their specific signal)
3. Touchpoint 2: follow-up (add value, not just "checking in")
4. Touchpoint 3: final attempt (clear CTA or graceful close)
5. Keep each message under 100 words for {outreach_channel}

Output: Complete sequences in structured format. One sequence per tier, personalized hooks for each prospect.
```

### Step 3 Prompt Template
```
Review these outreach sequences for quality, signal alignment, and conversion potential.

Sequences:
{prev_output}

Evaluate:
1. Signal alignment — do touchpoints reference the actual buying signals detected?
2. Personalization quality — generic or genuinely specific?
3. Value clarity — is the offer clear and compelling within 5 seconds?
4. CTA strength — is there one clear next step per touchpoint?
5. Compliance — no spam trigger words, appropriate length for channel

Score each sequence 0-10. Flag specific improvements. Recommend approve/revise.
```

### Step 4 Prompt Template
```
Apply the review feedback to finalize the outreach sequences.

Original sequences:
{step_2_output}

Review feedback:
{prev_output}

Apply every actionable improvement. Maintain signal-based selling principles throughout.
Store finalized sequences via POST http://localhost:8100/semantic/remember with category="outreach_sequence".

Output: Final sequences ready for deployment + brief implementation notes.
```

---

## Template 2: smart-contract-pipeline

**Priority**: P9 (Koink.fun, ONEON token, Web3 infrastructure)
**Tags**: web3, solidity, smart-contract, security

**Purpose**: Design, implement, security-audit, and fix EVM smart contracts. Used for Koink.fun $KOINK standard, ONEON token, any chain deployments.

**Agents to activate**: `solidity-smart-contract-engineer` (engineering/engineering-solidity-smart-contract-engineer.md), `blockchain-security-auditor` (specialized/blockchain-security-auditor.md)

### Steps

| # | Name | Agent | Budget | Turns | Timeout | On Failure |
|---|---|---|---|---|---|---|
| 0 | Contract Architecture | architect | $3 | 30 | 600s | retry_once |
| 1 | Implementation | solidity-smart-contract-engineer | $8 | 60 | 1800s | retry_once |
| 2 | Security Audit | blockchain-security-auditor | $4 | 40 | 900s | pause |
| 3 | Fix Audit Issues | solidity-smart-contract-engineer | $6 | 50 | 1200s | pause |
| 4 | Final Review | reviewer | $2 | 25 | 600s | skip |
| 5 | Notify | (action=notify) | — | — | — | — |

### Variables
- `contract_type` — e.g. "ERC-20 token", "meme token with $KOINK Standard", "NFT collection"
- `chain` — target chain(s) (e.g. "Ethereum mainnet, Base, Polygon")
- `requirements` — specific functional requirements
- `repo_path` — where to write the contract (default: /mnt/media/projects/koink-fun)

### Step 0 Prompt Template
```
Design the smart contract architecture for: {contract_type}

Target chains: {chain}
Requirements: {requirements}
Repo: {repo_path}

Produce:
1. Contract architecture diagram (text-based)
2. Interface definitions (all public/external functions)
3. State variables and storage layout
4. Access control model
5. Upgrade strategy (if applicable)
6. Gas optimization priorities
7. Known risks and mitigations

Output a complete architecture spec ready for Solidity implementation.
```

### Step 1 Prompt Template
```
Implement the smart contract based on this architecture:

{prev_output}

Requirements: {requirements}
Target chains: {chain}
Repo: {repo_path}

You are a battle-hardened Solidity engineer. Write secure, gas-optimized contracts:
1. Follow checks-effects-interactions for all state changes
2. Use custom errors (not require strings)
3. Include NatSpec documentation on all public functions
4. Write Foundry tests covering happy path + key edge cases + attack vectors
5. Commit to {repo_path} with meaningful commit messages

Output: Implementation summary with file paths, function inventory, and test coverage report.
```

### Step 2 Prompt Template
```
Perform a comprehensive security audit of this smart contract implementation.

Architecture spec:
{step_0_output}

Implementation:
{prev_output}

Read the actual contract files at {repo_path}. Audit for:
1. Reentrancy vulnerabilities (checks-effects-interactions)
2. Integer overflow/underflow
3. Access control bypasses
4. Front-running vulnerabilities
5. Economic attack vectors (price manipulation, flash loans)
6. Centralization risks
7. Denial of service vectors
8. Compliance with stated architecture

Rate each finding: CRITICAL / HIGH / MEDIUM / LOW / INFORMATIONAL
Output: Structured audit report with findings, exploit scenarios, and recommended fixes.
```

### Step 3 Prompt Template
```
Fix ALL findings from the security audit.

Audit report:
{prev_output}

Original implementation:
{step_1_output}

Fix every CRITICAL, HIGH, and MEDIUM finding. For LOW/INFORMATIONAL:
- Fix if trivial (< 5 lines)
- Document as accepted risk with rationale if complex

Update the actual files at {repo_path}. Re-run tests after fixes. Commit with message referencing the audit fix.

Output: Fix summary listing each finding, action taken, and confirmation of passing tests.
```

---

## Template 3: grant-application-pipeline

**Priority**: P9 (Capital raising — Gitcoin, W3F, ecosystem grants)
**Tags**: grants, fundraising, capital, writing

**Purpose**: Research grant requirements, synthesize scoring criteria, draft application, review from evaluator perspective, refine, and deliver. Used for Gitcoin GG24, W3F grants, ecosystem bounties.

**Agents to activate**: None new required (uses researcher, research-synthesizer, content-creator, reviewer — all active)

### Steps

| # | Name | Agent | Budget | Turns | Timeout | On Failure |
|---|---|---|---|---|---|---|
| 0 | Grant Research | researcher | $5 | 50 | 900s | retry_once |
| 1 | Synthesis & Brief | research-synthesizer | $2 | 20 | 600s | retry_once |
| 2 | Draft Application | content-creator | $6 | 50 | 1200s | retry_once |
| 3 | Evaluator Review | reviewer | $3 | 30 | 600s | skip |
| 4 | Refine | content-creator | $4 | 40 | 900s | retry_once |
| 5 | Notify | (action=notify) | — | — | — | — |

### Variables
- `grant_name` — e.g. "Gitcoin GG24", "W3F General Grant Level 1"
- `grant_program` — grantor organization
- `project_name` — which MY3YE project to apply for
- `project_description` — brief description of the project
- `grant_amount` — target funding amount
- `deadline` — application deadline

### Step 0 Prompt Template
```
Research the grant requirements and winning application patterns for: {grant_name}

Grant Program: {grant_program}
Project: {project_name}
Amount: {grant_amount}
Deadline: {deadline}

Research tasks:
1. WebSearch: "{grant_name} application requirements scoring criteria 2026"
2. WebSearch: "{grant_program} successful grant applications examples"
3. WebFetch grant program website for current round details
4. Search semantic memory: POST http://localhost:8100/semantic/search {"query": "{grant_name} {grant_program}"}
5. Identify: evaluation criteria (weighted), common rejection reasons, preferred narrative frames, required deliverables

Output raw multi-source findings. Include grant deadline, word limits, required sections, and evaluation rubric.
```

### Step 1 Prompt Template
```
You are research-synthesizer. Synthesize these grant research findings into a structured application brief.

Raw findings:
{prev_output}

Grant: {grant_name} | Project: {project_name}

Produce:
1. SCORING CRITERIA (weighted list, most important first)
2. REQUIRED SECTIONS (exact sections evaluators expect)
3. NARRATIVE FRAME (what angle wins this grant)
4. EVIDENCE NEEDED (what proof points to include)
5. RED FLAGS TO AVOID (common rejection reasons)
6. WORD/FORMAT CONSTRAINTS

Output: Compact application brief. Max 1500 tokens. No prose — structured bullets only.
```

### Step 2 Prompt Template
```
Write a complete grant application for {grant_name}.

Application Brief:
{prev_output}

Research:
{step_0_output}

Project: {project_name}
Description: {project_description}
Amount Requested: {grant_amount}

Read the project's existing content from semantic memory:
POST http://localhost:8100/semantic/search {"query": "{project_name} mission architecture roadmap"}

Write the full application following the required sections and narrative frame exactly. Use MY3YE brand voice: calm authority, short declarations, poetic but clear. Back every claim with evidence from our actual shipped work.

Save draft via POST http://localhost:8100/semantic/remember with category="grant_application".
```

### Step 3 Prompt Template
```
Review this grant application as a skeptical evaluator for {grant_name}.

Application:
{prev_output}

Scoring criteria:
{step_1_output}

Evaluate as the grant committee would:
1. Does it address every scoring criterion explicitly?
2. Are claims backed by evidence (not promises)?
3. Is the ask reasonable relative to deliverables?
4. Are there any red flags that would trigger rejection?
5. Is the narrative compelling for this specific grant's mission?

Score each section 0-10. Provide specific edits for each weakness.
```

### Step 4 Prompt Template
```
Revise the grant application based on evaluator feedback.

Original application:
{step_2_output}

Evaluator feedback:
{prev_output}

Address every critique. Strengthen weak sections. Do not weaken strong ones.
Update the DB record via the content API.

Output: Final application text + list of changes made.
```

---

## Template 4: product-sprint-pipeline

**Priority**: P8 (Continuous product delivery)
**Tags**: product, sprint, development, planning

**Purpose**: Execute a focused product sprint: plan scope → design → implement → verify → review → ship. More complete than feature-development — includes sprint prioritization and functional verification.

**Agents to activate**: `sprint-prioritizer` (product/product-sprint-prioritizer.md), `reality-checker` (testing/testing-reality-checker.md)

### Steps

| # | Name | Agent | Budget | Turns | Timeout | On Failure |
|---|---|---|---|---|---|---|
| 0 | Sprint Planning | sprint-prioritizer | $3 | 30 | 600s | retry_once |
| 1 | Architecture | architect | $3 | 30 | 600s | retry_once |
| 2 | Implementation | coder | $8 | 60 | 1800s | retry_once |
| 3 | Reality Check | reality-checker | $2 | 25 | 600s | skip |
| 4 | Code Review | reviewer | $3 | 30 | 600s | skip |
| 5 | Fix Issues | debugger | $4 | 40 | 900s | pause |
| 6 | Notify | (action=notify) | — | — | — | — |

### Variables
- `sprint_goal` — the sprint objective
- `backlog_items` — comma-separated list of items to consider
- `priority_filter` — min priority to include (e.g. "P7 and above")
- `working_directory` — project repo path
- `constraints` — budget, timeline, tech constraints

### Step 0 Prompt Template
```
Plan this product sprint.

Sprint Goal: {sprint_goal}
Backlog Items: {backlog_items}
Priority Filter: {priority_filter}
Constraints: {constraints}

Tasks:
1. GET pending tasks from task queue: GET http://localhost:8100/tasks?status=pending
2. Review backlog items against the sprint goal
3. Score each item: impact × confidence ÷ effort (ICE score)
4. Select top items that fit within {constraints}
5. Define explicit acceptance criteria for each selected item
6. Flag dependencies and risks

Output: Sprint plan with prioritized items, ICE scores, acceptance criteria, and risk flags.
```

### Step 1 Prompt Template
```
Design the technical architecture for this sprint.

Sprint Plan:
{prev_output}

Sprint Goal: {sprint_goal}
Working Directory: {working_directory}

For each sprint item:
1. Identify affected files and components
2. Design the change (data model, API contract, UI spec as applicable)
3. Sequence implementation steps (what to build in what order)
4. Identify tests needed

Output: Complete implementation plan. Be specific — name actual files, functions, endpoints.
```

### Step 2 Prompt Template
```
Implement the sprint based on the architecture plan.

Architecture:
{prev_output}

Sprint Plan:
{step_0_output}

Working Directory: {working_directory}

Follow the plan. Commit after each item. Keep commits atomic and descriptive.
Run existing tests after each commit. Stop if a commit breaks tests — fix before proceeding.

Output: Implementation log with each item completed, files changed, and test results.
```

### Step 3 Prompt Template
```
Verify the sprint implementation actually works.

Implementation log:
{prev_output}

Sprint acceptance criteria:
{step_0_output}

You are Reality Checker. For each implemented item:
1. Read the actual code — don't trust the implementation log alone
2. Verify it satisfies its acceptance criterion
3. Test edge cases the implementer likely missed
4. Check for regressions in adjacent functionality

Output: Reality check report — PASS/FAIL per item with evidence. Flag any FAIL with specific reproduction steps.
```

### Step 4 Prompt Template
```
Review the sprint implementation for code quality and consistency.

Reality check:
{prev_output}

Implementation:
{step_2_output}

Architecture plan:
{step_1_output}

Review for: code quality, security, consistency with codebase conventions, test coverage gaps.
Focus on items that PASSED the reality check — reality failures will be fixed separately.

Output: Review findings with severity (critical/major/minor) and specific fix suggestions.
```

### Step 5 Prompt Template
```
Fix all issues from reality check and code review.

Reality check failures:
{step_3_output}

Code review issues:
{prev_output}

Working Directory: {working_directory}

Fix every CRITICAL and MAJOR issue. Minor issues: fix if quick, document as tech debt if complex.
Re-run tests after fixes. Commit with "fix(sprint): [description]" messages.

Output: Fix summary with each issue resolved and final test status.
```

---

### Agents to Activate

These agents must be activated before templates can run:

| Agent Name | Source Path | Used In |
|---|---|---|
| outbound-strategist | /mnt/media/projects/agency-agents/sales/sales-outbound-strategist.md | outbound-sales-pipeline (step 1) |
| Solidity Smart Contract Engineer | /mnt/media/projects/agency-agents/engineering/engineering-solidity-smart-contract-engineer.md | smart-contract-pipeline (steps 1, 3) |
| Blockchain Security Auditor | /mnt/media/projects/agency-agents/specialized/blockchain-security-auditor.md | smart-contract-pipeline (step 2) |
| Sprint Prioritizer | /mnt/media/projects/agency-agents/product/product-sprint-prioritizer.md | product-sprint-pipeline (step 0) |
| Reality Checker | /mnt/media/projects/agency-agents/testing/testing-reality-checker.md | product-sprint-pipeline (step 3) |

Note: grant-application-pipeline requires NO new agent activations (all agents already active).

---

### Implementation Plan

**Step 1 (next workflow step)**: Activate agents + create templates

1. Activate 5 agents via `POST /workflows/agents/activate`:
   - outbound-strategist
   - solidity-smart-contract-engineer (agent_type slug from "Solidity Smart Contract Engineer")
   - blockchain-security-auditor
   - sprint-prioritizer
   - reality-checker

2. POST 4 workflow templates to `POST /workflows/templates`:
   - outbound-sales-pipeline
   - smart-contract-pipeline
   - grant-application-pipeline
   - product-sprint-pipeline

3. Verify all 4 templates appear in `GET /workflows/templates`

4. Store semantic memory confirming new templates created

**Total estimated cost**: ~$0.50 (API calls only, no task execution)

---

### Key Decisions

- **4 templates, not 5**: Dropped technical-docs-pipeline (nice-to-have) to stay focused on P9/P10 directives. Can add later.
- **No new agent writes**: All templates use agents from the existing agency-agents repo (activate, don't write). Faster, lower risk.
- **grant-application-pipeline reuses existing agents**: Only template with zero new activations. Good quick win.
- **smart-contract-pipeline pauses on audit**: `on_failure: pause` for security audit step — never skip or auto-retry a security audit finding. Mev should review.
- **product-sprint-pipeline replaces ad-hoc tasks**: The existing feature-development template is good but doesn't include sprint planning or functional verification. This is a superset.

---

### Risks

- **Agent activation API**: `POST /workflows/agents/activate` — need to verify the exact agent_type slug it assigns. Slug confirmed: "Solidity Smart Contract Engineer" → "solidity-smart-contract-engineer". All template references updated accordingly.
- **solidity-smart-contract-engineer fallback**: The coder agent is a fallback if activation fails.
- **sprint-prioritizer file path**: Verify `product/product-sprint-prioritizer.md` exists before activation.

---

*Document created: 2026-03-22*
*Author: architect agent*
*Next step: Implementation (activate agents + POST templates)*
