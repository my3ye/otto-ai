#!/usr/bin/env python3
"""Create 4 high-value workflow templates for Otto."""
import json
import urllib.request
import urllib.error

API_BASE = "http://localhost:8100"


def post_template(template):
    data = json.dumps(template).encode()
    req = urllib.request.Request(
        f"{API_BASE}/workflows/templates",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()}


TEMPLATES = [
    # -------------------------------------------------------------------------
    # 1. outbound-sales-pipeline (P10 — WebAssist revenue)
    # -------------------------------------------------------------------------
    {
        "name": "outbound-sales-pipeline",
        "description": "Research prospects, qualify via signal intelligence, draft personalized outreach sequences, review, and finalize. Used to generate WebAssist leads.",
        "tags": ["sales", "outbound", "webassist", "leads"],
        "default_priority": 10,
        "steps": [
            {
                "position": 0,
                "name": "ICP & Signal Research",
                "agent_type": "researcher",
                "max_budget_usd": 4.0,
                "max_turns": 40,
                "timeout_seconds": 900,
                "on_failure": "retry_once",
                "review_mode": "auto",
                "prompt_template": (
                    "Research the ideal customer profile and buying signals for this outbound campaign:\n\n"
                    "Target Industry: {target_industry}\n"
                    "ICP: {icp_description}\n"
                    "Service: {service_offer}\n\n"
                    "Tasks:\n"
                    "1. Search semantic memory for existing prospect data: POST http://localhost:8100/semantic/search "
                    '{{"query": "{target_industry} prospects leads"}}\n'
                    "2. Research the industry: company size, tech stack patterns, hiring signals, funding activity\n"
                    "3. Identify TOP 3 buying signals most predictive of converting to {service_offer}\n"
                    "4. Map common objections and how to handle them\n"
                    "5. Identify best channels and timing for this ICP\n\n"
                    "Output: Structured ICP profile with signal taxonomy. Max 2000 tokens."
                )
            },
            {
                "position": 1,
                "name": "Prospect Qualification & List",
                "agent_type": "outbound-strategist",
                "max_budget_usd": 4.0,
                "max_turns": 40,
                "timeout_seconds": 900,
                "on_failure": "retry_once",
                "review_mode": "auto",
                "prompt_template": (
                    "You are Outbound Strategist. Using the ICP research below, build a qualified prospect list "
                    "and signal-triggered outreach strategy.\n\n"
                    "ICP Research:\n{prev_output}\n\n"
                    "Service: {service_offer}\n"
                    "Channel: {outreach_channel}\n"
                    "Target Count: {num_prospects}\n\n"
                    "Tasks:\n"
                    "1. Define the precise ICP criteria from the research\n"
                    "2. List {num_prospects} specific prospect targets (company + role + signal detected)\n"
                    "3. Assign signal tier (Tier 1/2/3) to each prospect\n"
                    "4. Design the outreach sequence structure: touchpoints, timing, channel mix\n"
                    "5. Write the core value proposition angle for this ICP\n\n"
                    "Output: Prospect list (JSON) + sequence architecture. "
                    "Store top prospects via POST http://localhost:8100/semantic/remember with category=\"lead\"."
                )
            },
            {
                "position": 2,
                "name": "Sequence Draft",
                "agent_type": "content-creator",
                "max_budget_usd": 4.0,
                "max_turns": 40,
                "timeout_seconds": 900,
                "on_failure": "retry_once",
                "review_mode": "auto",
                "prompt_template": (
                    "Draft personalized outreach sequences for these prospects.\n\n"
                    "Prospects and sequence architecture:\n{prev_output}\n\n"
                    "ICP Research:\n{step_0_output}\n\n"
                    "Service: {service_offer}\n"
                    "Channel: {outreach_channel}\n\n"
                    "Tasks:\n"
                    "1. Write 3-touchpoint sequences for each prospect tier (T1, T2, T3)\n"
                    "2. Touchpoint 1: cold outreach (reference their specific signal)\n"
                    "3. Touchpoint 2: follow-up (add value, not just checking in)\n"
                    "4. Touchpoint 3: final attempt (clear CTA or graceful close)\n"
                    "5. Keep each message under 100 words for {outreach_channel}\n\n"
                    "Output: Complete sequences in structured format. One sequence per tier, "
                    "personalized hooks for each prospect."
                )
            },
            {
                "position": 3,
                "name": "Sequence Review",
                "agent_type": "reviewer",
                "max_budget_usd": 2.0,
                "max_turns": 25,
                "timeout_seconds": 600,
                "on_failure": "skip",
                "review_mode": "auto",
                "prompt_template": (
                    "Review these outreach sequences for quality, signal alignment, and conversion potential.\n\n"
                    "Sequences:\n{prev_output}\n\n"
                    "Evaluate:\n"
                    "1. Signal alignment — do touchpoints reference the actual buying signals detected?\n"
                    "2. Personalization quality — generic or genuinely specific?\n"
                    "3. Value clarity — is the offer clear and compelling within 5 seconds?\n"
                    "4. CTA strength — is there one clear next step per touchpoint?\n"
                    "5. Compliance — no spam trigger words, appropriate length for channel\n\n"
                    "Score each sequence 0-10. Flag specific improvements. Recommend approve/revise."
                )
            },
            {
                "position": 4,
                "name": "Refine & Finalize",
                "agent_type": "content-creator",
                "max_budget_usd": 3.0,
                "max_turns": 30,
                "timeout_seconds": 600,
                "on_failure": "retry_once",
                "review_mode": "auto",
                "prompt_template": (
                    "Apply the review feedback to finalize the outreach sequences.\n\n"
                    "Original sequences:\n{step_2_output}\n\n"
                    "Review feedback:\n{prev_output}\n\n"
                    "Apply every actionable improvement. Maintain signal-based selling principles throughout.\n"
                    "Store finalized sequences via POST http://localhost:8100/semantic/remember "
                    "with category=\"outreach_sequence\".\n\n"
                    "Output: Final sequences ready for deployment + brief implementation notes."
                )
            },
            {
                "position": 5,
                "name": "Notify",
                "agent_type": None,
                "action": "notify",
                "max_budget_usd": 0.5,
                "max_turns": 5,
                "timeout_seconds": 60,
                "on_failure": "skip",
                "review_mode": "auto",
                "notify_template": (
                    "✅ Outbound sales pipeline complete for {target_industry}. "
                    "Finalized sequences stored in semantic memory (category=outreach_sequence). "
                    "Pipeline: researcher → outbound-strategist → content-creator → reviewer → content-creator"
                )
            },
        ]
    },

    # -------------------------------------------------------------------------
    # 2. smart-contract-pipeline (P9 — Koink/Web3)
    # -------------------------------------------------------------------------
    {
        "name": "smart-contract-pipeline",
        "description": "Design, implement, security-audit, and fix EVM smart contracts. Used for Koink.fun $KOINK standard, ONEON token, and any chain deployments.",
        "tags": ["web3", "solidity", "smart-contract", "security"],
        "default_priority": 9,
        "steps": [
            {
                "position": 0,
                "name": "Contract Architecture",
                "agent_type": "architect",
                "max_budget_usd": 3.0,
                "max_turns": 30,
                "timeout_seconds": 600,
                "on_failure": "retry_once",
                "review_mode": "auto",
                "prompt_template": (
                    "Design the smart contract architecture for: {contract_type}\n\n"
                    "Target chains: {chain}\n"
                    "Requirements: {requirements}\n"
                    "Repo: {repo_path}\n\n"
                    "Produce:\n"
                    "1. Contract architecture diagram (text-based)\n"
                    "2. Interface definitions (all public/external functions)\n"
                    "3. State variables and storage layout\n"
                    "4. Access control model\n"
                    "5. Upgrade strategy (if applicable)\n"
                    "6. Gas optimization priorities\n"
                    "7. Known risks and mitigations\n\n"
                    "Output a complete architecture spec ready for Solidity implementation."
                )
            },
            {
                "position": 1,
                "name": "Implementation",
                "agent_type": "solidity-smart-contract-engineer",
                "max_budget_usd": 8.0,
                "max_turns": 60,
                "timeout_seconds": 1800,
                "on_failure": "retry_once",
                "review_mode": "auto",
                "prompt_template": (
                    "Implement the smart contract based on this architecture:\n\n"
                    "{prev_output}\n\n"
                    "Requirements: {requirements}\n"
                    "Target chains: {chain}\n"
                    "Repo: {repo_path}\n\n"
                    "You are a battle-hardened Solidity engineer. Write secure, gas-optimized contracts:\n"
                    "1. Follow checks-effects-interactions for all state changes\n"
                    "2. Use custom errors (not require strings)\n"
                    "3. Include NatSpec documentation on all public functions\n"
                    "4. Write Foundry tests covering happy path + key edge cases + attack vectors\n"
                    "5. Commit to {repo_path} with meaningful commit messages\n\n"
                    "Output: Implementation summary with file paths, function inventory, and test coverage report."
                )
            },
            {
                "position": 2,
                "name": "Security Audit",
                "agent_type": "blockchain-security-auditor",
                "max_budget_usd": 4.0,
                "max_turns": 40,
                "timeout_seconds": 900,
                "on_failure": "pause",
                "review_mode": "human_approval",
                "prompt_template": (
                    "Perform a comprehensive security audit of this smart contract implementation.\n\n"
                    "Architecture spec:\n{step_0_output}\n\n"
                    "Implementation:\n{prev_output}\n\n"
                    "Read the actual contract files at {repo_path}. Audit for:\n"
                    "1. Reentrancy vulnerabilities (checks-effects-interactions)\n"
                    "2. Integer overflow/underflow\n"
                    "3. Access control bypasses\n"
                    "4. Front-running vulnerabilities\n"
                    "5. Economic attack vectors (price manipulation, flash loans)\n"
                    "6. Centralization risks\n"
                    "7. Denial of service vectors\n"
                    "8. Compliance with stated architecture\n\n"
                    "Rate each finding: CRITICAL / HIGH / MEDIUM / LOW / INFORMATIONAL\n"
                    "Output: Structured audit report with findings, exploit scenarios, and recommended fixes."
                )
            },
            {
                "position": 3,
                "name": "Fix Audit Issues",
                "agent_type": "solidity-smart-contract-engineer",
                "max_budget_usd": 6.0,
                "max_turns": 50,
                "timeout_seconds": 1200,
                "on_failure": "pause",
                "review_mode": "auto",
                "prompt_template": (
                    "Fix ALL findings from the security audit.\n\n"
                    "Audit report:\n{prev_output}\n\n"
                    "Original implementation:\n{step_1_output}\n\n"
                    "Fix every CRITICAL, HIGH, and MEDIUM finding. For LOW/INFORMATIONAL:\n"
                    "- Fix if trivial (< 5 lines)\n"
                    "- Document as accepted risk with rationale if complex\n\n"
                    "Update the actual files at {repo_path}. Re-run tests after fixes. "
                    "Commit with message referencing the audit fix.\n\n"
                    "Output: Fix summary listing each finding, action taken, and confirmation of passing tests."
                )
            },
            {
                "position": 4,
                "name": "Final Review",
                "agent_type": "reviewer",
                "max_budget_usd": 2.0,
                "max_turns": 25,
                "timeout_seconds": 600,
                "on_failure": "skip",
                "review_mode": "auto",
                "prompt_template": (
                    "Final review of the smart contract after security fixes.\n\n"
                    "Fix summary:\n{prev_output}\n\n"
                    "Architecture spec:\n{step_0_output}\n\n"
                    "Review for: architecture compliance, NatSpec completeness, test coverage, "
                    "deployment readiness.\n"
                    "Output: READY FOR DEPLOYMENT or list of blockers with specific fixes required."
                )
            },
            {
                "position": 5,
                "name": "Notify",
                "agent_type": None,
                "action": "notify",
                "max_budget_usd": 0.5,
                "max_turns": 5,
                "timeout_seconds": 60,
                "on_failure": "skip",
                "review_mode": "auto",
                "notify_template": (
                    "✅ Smart contract pipeline complete for {contract_type} on {chain}. "
                    "Security audit passed. Code at {repo_path}. "
                    "Pipeline: architect → solidity-engineer → security-audit → fix → reviewer"
                )
            },
        ]
    },

    # -------------------------------------------------------------------------
    # 3. grant-application-pipeline (P9 — Capital raising)
    # -------------------------------------------------------------------------
    {
        "name": "grant-application-pipeline",
        "description": "Research grant requirements, synthesize scoring criteria, draft application, review from evaluator perspective, refine, and deliver. Used for Gitcoin GG24, W3F grants, ecosystem bounties.",
        "tags": ["grants", "fundraising", "capital", "writing"],
        "default_priority": 9,
        "steps": [
            {
                "position": 0,
                "name": "Grant Research",
                "agent_type": "researcher",
                "max_budget_usd": 5.0,
                "max_turns": 50,
                "timeout_seconds": 900,
                "on_failure": "retry_once",
                "review_mode": "auto",
                "prompt_template": (
                    "Research the grant requirements and winning application patterns for: {grant_name}\n\n"
                    "Grant Program: {grant_program}\n"
                    "Project: {project_name}\n"
                    "Amount: {grant_amount}\n"
                    "Deadline: {deadline}\n\n"
                    "Research tasks:\n"
                    '1. WebSearch: "{grant_name} application requirements scoring criteria 2026"\n'
                    '2. WebSearch: "{grant_program} successful grant applications examples"\n'
                    "3. WebFetch grant program website for current round details\n"
                    "4. Search semantic memory: POST http://localhost:8100/semantic/search "
                    '{{"query": "{grant_name} {grant_program}"}}\n'
                    "5. Identify: evaluation criteria (weighted), common rejection reasons, "
                    "preferred narrative frames, required deliverables\n\n"
                    "Output raw multi-source findings. Include grant deadline, word limits, "
                    "required sections, and evaluation rubric."
                )
            },
            {
                "position": 1,
                "name": "Synthesis & Brief",
                "agent_type": "research-synthesizer",
                "max_budget_usd": 2.0,
                "max_turns": 20,
                "timeout_seconds": 600,
                "on_failure": "retry_once",
                "review_mode": "auto",
                "prompt_template": (
                    "You are research-synthesizer. Synthesize these grant research findings into a structured "
                    "application brief.\n\n"
                    "Raw findings:\n{prev_output}\n\n"
                    "Grant: {grant_name} | Project: {project_name}\n\n"
                    "Produce:\n"
                    "1. SCORING CRITERIA (weighted list, most important first)\n"
                    "2. REQUIRED SECTIONS (exact sections evaluators expect)\n"
                    "3. NARRATIVE FRAME (what angle wins this grant)\n"
                    "4. EVIDENCE NEEDED (what proof points to include)\n"
                    "5. RED FLAGS TO AVOID (common rejection reasons)\n"
                    "6. WORD/FORMAT CONSTRAINTS\n\n"
                    "Output: Compact application brief. Max 1500 tokens. No prose — structured bullets only."
                )
            },
            {
                "position": 2,
                "name": "Draft Application",
                "agent_type": "content-creator",
                "max_budget_usd": 6.0,
                "max_turns": 50,
                "timeout_seconds": 1200,
                "on_failure": "retry_once",
                "review_mode": "auto",
                "prompt_template": (
                    "Write a complete grant application for {grant_name}.\n\n"
                    "Application Brief:\n{prev_output}\n\n"
                    "Research:\n{step_0_output}\n\n"
                    "Project: {project_name}\n"
                    "Description: {project_description}\n"
                    "Amount Requested: {grant_amount}\n\n"
                    "Read the project's existing content from semantic memory:\n"
                    "POST http://localhost:8100/semantic/search "
                    '{{"query": "{project_name} mission architecture roadmap"}}\n\n'
                    "Write the full application following the required sections and narrative frame exactly. "
                    "Use MY3YE brand voice: calm authority, short declarations, poetic but clear. "
                    "Back every claim with evidence from our actual shipped work.\n\n"
                    "Save draft via POST http://localhost:8100/semantic/remember with category=\"grant_application\"."
                )
            },
            {
                "position": 3,
                "name": "Evaluator Review",
                "agent_type": "reviewer",
                "max_budget_usd": 3.0,
                "max_turns": 30,
                "timeout_seconds": 600,
                "on_failure": "skip",
                "review_mode": "auto",
                "prompt_template": (
                    "Review this grant application as a skeptical evaluator for {grant_name}.\n\n"
                    "Application:\n{prev_output}\n\n"
                    "Scoring criteria:\n{step_1_output}\n\n"
                    "Evaluate as the grant committee would:\n"
                    "1. Does it address every scoring criterion explicitly?\n"
                    "2. Are claims backed by evidence (not promises)?\n"
                    "3. Is the ask reasonable relative to deliverables?\n"
                    "4. Are there any red flags that would trigger rejection?\n"
                    "5. Is the narrative compelling for this specific grant's mission?\n\n"
                    "Score each section 0-10. Provide specific edits for each weakness."
                )
            },
            {
                "position": 4,
                "name": "Refine",
                "agent_type": "content-creator",
                "max_budget_usd": 4.0,
                "max_turns": 40,
                "timeout_seconds": 900,
                "on_failure": "retry_once",
                "review_mode": "auto",
                "prompt_template": (
                    "Revise the grant application based on evaluator feedback.\n\n"
                    "Original application:\n{step_2_output}\n\n"
                    "Evaluator feedback:\n{prev_output}\n\n"
                    "Address every critique. Strengthen weak sections. Do not weaken strong ones.\n"
                    "Update the DB record via the content API or re-store via semantic/remember.\n\n"
                    "Output: Final application text + list of changes made."
                )
            },
            {
                "position": 5,
                "name": "Notify",
                "agent_type": None,
                "action": "notify",
                "max_budget_usd": 0.5,
                "max_turns": 5,
                "timeout_seconds": 60,
                "on_failure": "skip",
                "review_mode": "auto",
                "notify_template": (
                    "✅ Grant application ready: {grant_name} for {project_name}. "
                    "Target amount: {grant_amount}. Deadline: {deadline}. "
                    "Draft saved to semantic memory (category=grant_application). "
                    "Pipeline: researcher → synthesizer → content-creator → reviewer → content-creator"
                )
            },
        ]
    },

    # -------------------------------------------------------------------------
    # 4. product-sprint-pipeline (P8 — Product delivery)
    # -------------------------------------------------------------------------
    {
        "name": "product-sprint-pipeline",
        "description": "Execute a focused product sprint: plan scope, design architecture, implement, verify reality, code review, fix issues, and ship. More complete than feature-development — includes sprint prioritization and functional verification.",
        "tags": ["product", "sprint", "development", "planning"],
        "default_priority": 8,
        "steps": [
            {
                "position": 0,
                "name": "Sprint Planning",
                "agent_type": "sprint-prioritizer",
                "max_budget_usd": 3.0,
                "max_turns": 30,
                "timeout_seconds": 600,
                "on_failure": "retry_once",
                "review_mode": "auto",
                "prompt_template": (
                    "Plan this product sprint.\n\n"
                    "Sprint Goal: {sprint_goal}\n"
                    "Backlog Items: {backlog_items}\n"
                    "Priority Filter: {priority_filter}\n"
                    "Constraints: {constraints}\n\n"
                    "Tasks:\n"
                    "1. GET pending tasks from task queue: GET http://localhost:8100/tasks?status=pending\n"
                    "2. Review backlog items against the sprint goal\n"
                    "3. Score each item: impact x confidence / effort (ICE score)\n"
                    "4. Select top items that fit within {constraints}\n"
                    "5. Define explicit acceptance criteria for each selected item\n"
                    "6. Flag dependencies and risks\n\n"
                    "Output: Sprint plan with prioritized items, ICE scores, acceptance criteria, and risk flags."
                )
            },
            {
                "position": 1,
                "name": "Architecture",
                "agent_type": "architect",
                "max_budget_usd": 3.0,
                "max_turns": 30,
                "timeout_seconds": 600,
                "on_failure": "retry_once",
                "review_mode": "auto",
                "prompt_template": (
                    "Design the technical architecture for this sprint.\n\n"
                    "Sprint Plan:\n{prev_output}\n\n"
                    "Sprint Goal: {sprint_goal}\n"
                    "Working Directory: {working_directory}\n\n"
                    "For each sprint item:\n"
                    "1. Identify affected files and components\n"
                    "2. Design the change (data model, API contract, UI spec as applicable)\n"
                    "3. Sequence implementation steps (what to build in what order)\n"
                    "4. Identify tests needed\n\n"
                    "Output: Complete implementation plan. Be specific — name actual files, "
                    "functions, endpoints."
                )
            },
            {
                "position": 2,
                "name": "Implementation",
                "agent_type": "coder",
                "max_budget_usd": 8.0,
                "max_turns": 60,
                "timeout_seconds": 1800,
                "on_failure": "retry_once",
                "review_mode": "auto",
                "prompt_template": (
                    "Implement the sprint based on the architecture plan.\n\n"
                    "Architecture:\n{prev_output}\n\n"
                    "Sprint Plan:\n{step_0_output}\n\n"
                    "Working Directory: {working_directory}\n\n"
                    "Follow the plan. Commit after each item. Keep commits atomic and descriptive.\n"
                    "Run existing tests after each commit. Stop if a commit breaks tests — fix before proceeding.\n\n"
                    "Output: Implementation log with each item completed, files changed, and test results."
                )
            },
            {
                "position": 3,
                "name": "Reality Check",
                "agent_type": "reality-checker",
                "max_budget_usd": 2.0,
                "max_turns": 25,
                "timeout_seconds": 600,
                "on_failure": "skip",
                "review_mode": "auto",
                "prompt_template": (
                    "Verify the sprint implementation actually works.\n\n"
                    "Implementation log:\n{prev_output}\n\n"
                    "Sprint acceptance criteria:\n{step_0_output}\n\n"
                    "You are Reality Checker. For each implemented item:\n"
                    "1. Read the actual code — don't trust the implementation log alone\n"
                    "2. Verify it satisfies its acceptance criterion\n"
                    "3. Test edge cases the implementer likely missed\n"
                    "4. Check for regressions in adjacent functionality\n\n"
                    "Output: Reality check report — PASS/FAIL per item with evidence. "
                    "Flag any FAIL with specific reproduction steps."
                )
            },
            {
                "position": 4,
                "name": "Code Review",
                "agent_type": "reviewer",
                "max_budget_usd": 3.0,
                "max_turns": 30,
                "timeout_seconds": 600,
                "on_failure": "skip",
                "review_mode": "auto",
                "prompt_template": (
                    "Review the sprint implementation for code quality and consistency.\n\n"
                    "Reality check:\n{prev_output}\n\n"
                    "Implementation:\n{step_2_output}\n\n"
                    "Architecture plan:\n{step_1_output}\n\n"
                    "Review for: code quality, security, consistency with codebase conventions, test coverage gaps.\n"
                    "Focus on items that PASSED the reality check — reality failures will be fixed separately.\n\n"
                    "Output: Review findings with severity (critical/major/minor) and specific fix suggestions."
                )
            },
            {
                "position": 5,
                "name": "Fix Issues",
                "agent_type": "debugger",
                "max_budget_usd": 4.0,
                "max_turns": 40,
                "timeout_seconds": 900,
                "on_failure": "pause",
                "review_mode": "auto",
                "prompt_template": (
                    "Fix all issues from reality check and code review.\n\n"
                    "Reality check failures:\n{step_3_output}\n\n"
                    "Code review issues:\n{prev_output}\n\n"
                    "Working Directory: {working_directory}\n\n"
                    "Fix every CRITICAL and MAJOR issue. Minor issues: fix if quick, document as tech debt if complex.\n"
                    "Re-run tests after fixes. Commit with 'fix(sprint): [description]' messages.\n\n"
                    "Output: Fix summary with each issue resolved and final test status."
                )
            },
            {
                "position": 6,
                "name": "Notify",
                "agent_type": None,
                "action": "notify",
                "max_budget_usd": 0.5,
                "max_turns": 5,
                "timeout_seconds": 60,
                "on_failure": "skip",
                "review_mode": "auto",
                "notify_template": (
                    "✅ Product sprint complete: {sprint_goal}. "
                    "All items implemented, reality-checked, reviewed, and fixed. "
                    "Code at {working_directory}. "
                    "Pipeline: sprint-prioritizer → architect → coder → reality-checker → reviewer → debugger"
                )
            },
        ]
    },
]


def main():
    print(f"Creating {len(TEMPLATES)} workflow templates...\n")
    created = []
    for t in TEMPLATES:
        print(f"Creating: {t['name']}")
        result = post_template(t)
        if "error" in result:
            print(f"  ERROR: {result['error'][:200]}")
        elif "id" in result:
            print(f"  OK: id={result['id']}")
            created.append(result)
        else:
            print(f"  Response: {json.dumps(result)[:200]}")

    print(f"\nDone. {len(created)}/{len(TEMPLATES)} templates created.")
    return created


if __name__ == "__main__":
    main()
