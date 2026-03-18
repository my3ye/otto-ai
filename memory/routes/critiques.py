"""Persona Critique Agent Pipeline.

Runs each article/post through 6 audience-specific critique agents,
each embodied by an influential figure persona. Logs all suggestions,
surfaces them on OMS, and provides a synthesis endpoint that produces
a revised document incorporating all critique suggestions.

Personas:
  - Web3 Native     → Vitalik Buterin (crypto/decentralization lens)
  - Startup Founder → Paul Graham (startup/product/growth lens)
  - Social Impact   → Malala Yousafzai (humanity/equity/access lens)
  - Developer       → DHH (pragmatic engineering/builder lens)
  - Wellness/Spirit → Thich Nhat Hanh (mindfulness/well-being lens)
  - Mainstream Skep → Kara Swisher (skeptical journalist/accountability lens)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from ..db import get_pool
from ..llm import llm_chat

log = logging.getLogger("otto.critiques")

router = APIRouter(prefix="/critiques", tags=["critiques"])

# ── Persona definitions ────────────────────────────────────────────────────

PERSONAS = [
    {
        "id": "web3_native",
        "audience": "Web3 Native",
        "figure": "Vitalik Buterin",
        "figure_bio": "Ethereum co-founder, decentralization philosopher, deep thinker on crypto economics, governance, and the intersection of technology and society.",
        "lens": "decentralization, trustlessness, on-chain mechanics, token design, community ownership, open protocols",
        "system_prompt": """You are critiquing content as Vitalik Buterin — Ethereum co-founder, systems thinker, and decentralization philosopher.

Your lens: Does this content resonate with someone deep in Web3? You care about:
- Genuine decentralization vs theater
- On-chain mechanics and trustless systems
- Token economic incentives and game theory
- Community ownership and governance
- Open protocols vs closed ecosystems
- Technical accuracy and intellectual honesty
- Whether the vision is actually achievable on-chain

Be direct, intellectually rigorous, and constructive. Point out where claims are vague, technically dubious, or where centralization risks are being glossed over. Also highlight what resonates strongly with the Web3-native audience.""",
    },
    {
        "id": "startup_founder",
        "audience": "Startup Founder",
        "figure": "Paul Graham",
        "figure_bio": "Y Combinator co-founder, essayist, startup philosopher. Deeply skeptical of complexity, loves clarity, shipping, and talking to users.",
        "lens": "product-market fit, traction, simplicity, user value, growth mechanics, avoiding premature optimization",
        "system_prompt": """You are critiquing content as Paul Graham — Y Combinator co-founder and startup essayist.

Your lens: Does this content make sense to a founder who ships products and talks to users? You care about:
- Is the core insight genuinely valuable or just restated conventional wisdom?
- Does this help founders understand what to build and why?
- Is the writing clear and precise? (You hate jargon)
- Does it pass the "make something people want" test?
- Is this talking about real user problems or intellectual abstractions?
- Growth mechanics and path to revenue
- What's the actual differentiator vs existing solutions?

Be direct and specific. Call out where things are too vague to act on, where the market insight is weak, or where the complexity is unnecessary. Also highlight where the content lands correctly for founders.""",
    },
    {
        "id": "social_impact",
        "audience": "Social Impact",
        "figure": "Malala Yousafzai",
        "figure_bio": "Nobel Peace Prize laureate, education advocate, global speaker on equity, access, and the power of education to transform lives.",
        "lens": "access and equity, real-world impact on underserved communities, genuine empowerment vs extractive systems",
        "system_prompt": """You are critiquing content as Malala Yousafzai — Nobel laureate and global advocate for education, equity, and human dignity.

Your lens: Does this content genuinely serve people who need it most? You care about:
- Does this create real access for underserved communities?
- Is the impact measurable and concrete, or vague aspiration?
- Who benefits and who might be excluded?
- Does this reinforce existing inequalities or disrupt them?
- Is the language inclusive and accessible?
- Are the people being served treated as agents or just beneficiaries?
- What systemic changes does this create vs surface-level help?

Be compassionate but rigorous. Call out where rhetoric doesn't match reality, where impact claims are overstated, or where structural barriers are being ignored. Also highlight where the content genuinely addresses real human needs.""",
    },
    {
        "id": "developer",
        "audience": "Developer",
        "figure": "DHH (David Heinemeier Hansson)",
        "figure_bio": "Rails creator, Basecamp/Hey co-founder. Pragmatic builder, skeptic of complexity and hype, advocate for calm, profitable, independent software.",
        "lens": "technical practicality, developer experience, avoiding over-engineering, independence over VC-dependency",
        "system_prompt": """You are critiquing content as DHH (David Heinemeier Hansson) — Rails creator and pragmatic software builder.

Your lens: Does this content actually make sense to engineers who build and ship software? You care about:
- Is the technical architecture sane and practical?
- Does this avoid the trap of complexity for complexity's sake?
- Can a small team actually build and maintain this?
- Is this sustainable without VC dependency?
- What's the developer experience like?
- Are the open-source/community mechanics sound?
- Does this pass the "just ship it" test?

Be blunt and practical. Call out over-engineering, unrealistic scalability claims, or where the system requires more infrastructure than the problem justifies. Also highlight where the technical approach is sound and pragmatic.""",
    },
    {
        "id": "wellness_spiritual",
        "audience": "Wellness & Spiritual",
        "figure": "Thich Nhat Hanh",
        "figure_bio": "Vietnamese Buddhist monk, peace activist, prolific author on mindfulness, interconnectedness, and compassionate action in the modern world.",
        "lens": "human flourishing, mindfulness, interconnectedness, well-being, community, slowing down in a fast world",
        "system_prompt": """You are critiquing content as Thich Nhat Hanh — Zen master, peace activist, and teacher of mindfulness and compassionate action.

Your lens: Does this content serve the whole person and nourish human flourishing? You care about:
- Does this reduce suffering or add to it?
- Does it honor the interconnectedness of all beings?
- Does it create space for reflection, or does it accelerate mindless consumption?
- Is there genuine community and belonging, or just another platform?
- Does this serve human well-being, or does it extract from it?
- Can this coexist with a contemplative, intentional life?
- What is the deeper purpose beneath the technology?

Speak with warmth and gentleness but with clear insight. Call out where systems create anxiety, division, or exploitation even if unintentionally. Also highlight where the content genuinely serves peace, community, and human dignity.""",
    },
    {
        "id": "mainstream_skeptic",
        "audience": "Mainstream Skeptic",
        "figure": "Kara Swisher",
        "figure_bio": "Veteran tech journalist, podcast host (On with Kara Swisher), known for sharp accountability journalism and skepticism of tech utopian claims.",
        "lens": "accountability, realistic critique of tech promises, consumer protection, power dynamics, media literacy",
        "system_prompt": """You are critiquing content as Kara Swisher — veteran tech journalist and accountability reporter.

Your lens: Does this hold up to a skeptical, informed mainstream audience? You care about:
- Are the claims realistic or classic tech utopian overclaiming?
- Who holds power in this system and who doesn't?
- What are the accountability mechanisms when things go wrong?
- Is this crypto/Web3 use case actually necessary, or could it be done better without it?
- What are the consumer protection implications?
- Is the language accessible to a non-technical audience?
- What's the honest failure mode of this?

Be sharp and direct — like you'd be in an interview. Call out vague promises, missing accountability structures, and where the tech complexity obscures what's actually being proposed. Also acknowledge where the vision is credible and the critique would be unfair.""",
    },
]

PERSONA_MAP = {p["id"]: p for p in PERSONAS}

# ── DB Schema ──────────────────────────────────────────────────────────────

CREATE_CRITIQUE_RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS critique_runs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    article_id      TEXT,
    article_title   TEXT NOT NULL,
    article_content TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    created_at      TIMESTAMPTZ DEFAULT now(),
    completed_at    TIMESTAMPTZ
);
"""

CREATE_CRITIQUES_TABLE = """
CREATE TABLE IF NOT EXISTS critiques (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id          UUID NOT NULL REFERENCES critique_runs(id) ON DELETE CASCADE,
    persona_id      TEXT NOT NULL,
    persona_name    TEXT NOT NULL,
    persona_figure  TEXT NOT NULL,
    audience        TEXT NOT NULL,
    overall_feedback TEXT,
    suggestions     JSONB DEFAULT '[]',
    strengths       JSONB DEFAULT '[]',
    rating          INTEGER,
    status          TEXT NOT NULL DEFAULT 'pending',
    error           TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    completed_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_critiques_run_id ON critiques(run_id);
CREATE INDEX IF NOT EXISTS idx_critiques_persona_id ON critiques(persona_id);
"""

CREATE_SYNTHESES_TABLE = """
CREATE TABLE IF NOT EXISTS critique_syntheses (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id          UUID NOT NULL REFERENCES critique_runs(id) ON DELETE CASCADE,
    article_title   TEXT NOT NULL,
    original_content TEXT NOT NULL,
    synthesized_content TEXT,
    key_changes     JSONB DEFAULT '[]',
    personas_used   JSONB DEFAULT '[]',
    status          TEXT NOT NULL DEFAULT 'pending',
    error           TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    completed_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_syntheses_run_id ON critique_syntheses(run_id);
"""


async def _ensure_tables(pool):
    await pool.execute(CREATE_CRITIQUE_RUNS_TABLE)
    await pool.execute(CREATE_CRITIQUES_TABLE)
    await pool.execute(CREATE_SYNTHESES_TABLE)


# ── Helper functions ────────────────────────────────────────────────────────

def _run_row(row) -> dict:
    return {
        "id": str(row["id"]),
        "article_id": row["article_id"],
        "article_title": row["article_title"],
        "article_content": row["article_content"],
        "status": row["status"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
    }


def _parse_jsonb(val, default=None):
    """Parse JSONB field — asyncpg may return it as str or already-parsed."""
    if val is None:
        return default if default is not None else []
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, ValueError):
            return default if default is not None else []
    return val


def _critique_row(row) -> dict:
    return {
        "id": str(row["id"]),
        "run_id": str(row["run_id"]),
        "persona_id": row["persona_id"],
        "persona_name": row["persona_name"],
        "persona_figure": row["persona_figure"],
        "audience": row["audience"],
        "overall_feedback": row["overall_feedback"],
        "suggestions": _parse_jsonb(row["suggestions"]),
        "strengths": _parse_jsonb(row["strengths"]),
        "rating": row["rating"],
        "status": row["status"],
        "error": row["error"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
    }


def _synthesis_row(row) -> dict:
    return {
        "id": str(row["id"]),
        "run_id": str(row["run_id"]),
        "article_title": row["article_title"],
        "original_content": row["original_content"],
        "synthesized_content": row["synthesized_content"],
        "key_changes": _parse_jsonb(row["key_changes"]),
        "personas_used": _parse_jsonb(row["personas_used"]),
        "status": row["status"],
        "error": row["error"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
    }


async def _run_single_critique(pool, critique_id: str, persona: dict, article_title: str, article_content: str):
    """Run one persona critique via LLM and store results."""
    try:
        prompt = f"""You are critiquing the following content.

ARTICLE TITLE: {article_title}

ARTICLE CONTENT:
{article_content[:8000]}

Please critique this content from your perspective. Respond in JSON with this exact structure:
{{
  "overall_feedback": "2-3 sentence overall assessment",
  "rating": <integer 1-10, where 10 = excellent for this audience>,
  "strengths": [
    "strength 1",
    "strength 2"
  ],
  "suggestions": [
    {{
      "issue": "what the problem is",
      "suggestion": "specific actionable improvement",
      "priority": "high|medium|low"
    }}
  ]
}}

Provide 2-4 strengths and 3-6 specific, actionable suggestions. Be honest and direct."""

        response = await llm_chat(
            messages=[{"role": "user", "content": prompt}],
            system_instruction=persona["system_prompt"],
            max_tokens=1500,
            temperature=0.3,
        )

        # Parse JSON response
        result = {}
        # Try to extract JSON block
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                result = json.loads(json_match.group())
            except json.JSONDecodeError:
                result = {}

        overall_feedback = result.get("overall_feedback", response[:500] if response else "No feedback generated")
        suggestions = result.get("suggestions", [])
        strengths = result.get("strengths", [])
        rating = result.get("rating")
        if rating is not None:
            try:
                rating = max(1, min(10, int(rating)))
            except (TypeError, ValueError):
                rating = None

        await pool.execute(
            """UPDATE critiques SET
                overall_feedback = $1,
                suggestions = $2::jsonb,
                strengths = $3::jsonb,
                rating = $4,
                status = 'completed',
                completed_at = now()
               WHERE id = $5""",
            overall_feedback,
            json.dumps(suggestions),
            json.dumps(strengths),
            rating,
            critique_id,
        )
        log.info("Critique completed: %s / %s", persona["id"], critique_id)

    except Exception as e:
        log.error("Critique failed for %s: %s", persona["id"], e)
        await pool.execute(
            "UPDATE critiques SET status = 'failed', error = $1 WHERE id = $2",
            str(e)[:500],
            critique_id,
        )


async def _run_all_critiques(run_id: str, article_title: str, article_content: str):
    """Background task: run all 6 persona critiques and update run status."""
    pool = await get_pool()
    try:
        # Get all critique IDs for this run
        rows = await pool.fetch(
            "SELECT id, persona_id FROM critiques WHERE run_id = $1",
            run_id,
        )

        # Run critiques sequentially (to avoid rate limits)
        for row in rows:
            persona = PERSONA_MAP.get(row["persona_id"])
            if persona:
                await _run_single_critique(
                    pool, str(row["id"]), persona, article_title, article_content
                )

        # Check if all critiques completed
        results = await pool.fetch(
            "SELECT status FROM critiques WHERE run_id = $1",
            run_id,
        )
        statuses = [r["status"] for r in results]
        if all(s in ("completed", "failed") for s in statuses):
            failed_count = sum(1 for s in statuses if s == "failed")
            run_status = "failed" if failed_count == len(statuses) else "completed"
            await pool.execute(
                "UPDATE critique_runs SET status = $1, completed_at = now() WHERE id = $2",
                run_status, run_id,
            )
            log.info("Critique run %s finished: %s (%d failed)", run_id, run_status, failed_count)

    except Exception as e:
        log.error("Critique run %s failed: %s", run_id, e)
        await pool.execute(
            "UPDATE critique_runs SET status = 'failed', completed_at = now() WHERE id = $1",
            run_id,
        )


async def _run_synthesis(synthesis_id: str, run_id: str, article_title: str, article_content: str):
    """Background task: synthesize all critique suggestions into a revised document."""
    pool = await get_pool()
    try:
        # Gather all completed critiques for this run
        rows = await pool.fetch(
            """SELECT persona_id, persona_figure, audience, overall_feedback,
                      suggestions, strengths, rating
               FROM critiques
               WHERE run_id = $1 AND status = 'completed'
               ORDER BY persona_id""",
            run_id,
        )

        if not rows:
            raise ValueError("No completed critiques found for synthesis")

        # Build critique summary for LLM
        critique_summary_parts = []
        personas_used = []
        for row in rows:
            suggestions = _parse_jsonb(row["suggestions"])
            strengths = _parse_jsonb(row["strengths"])
            personas_used.append(row["persona_id"])

            critique_summary_parts.append(f"""
## {row['audience']} Perspective ({row['persona_figure']})
**Rating:** {row['rating'] or 'N/A'}/10
**Overall:** {row['overall_feedback'] or 'N/A'}

**Strengths:**
{chr(10).join(f'- {s}' for s in strengths) if strengths else '- None noted'}

**Suggestions:**
{chr(10).join(f'- [{s.get("priority","medium").upper()}] {s.get("issue","")}: {s.get("suggestion","")}' for s in suggestions) if suggestions else '- None'}
""")

        critique_summary = "\n".join(critique_summary_parts)

        synthesis_prompt = f"""You have received critique feedback on the following content from 6 different audience perspectives.

ORIGINAL TITLE: {article_title}

ORIGINAL CONTENT:
{article_content[:6000]}

---

CRITIQUE FEEDBACK FROM ALL PERSPECTIVES:
{critique_summary}

---

Your task: Produce a revised, improved version of this content that thoughtfully incorporates the most important suggestions across all perspectives.

Guidelines:
- Preserve the author's core voice and message
- Address HIGH priority suggestions first
- Where suggestions conflict, find the best synthesis that serves all audiences
- Make the content stronger, clearer, and more resonant across audiences
- Do not become generic — retain specificity and authenticity

Respond in JSON with this structure:
{{
  "synthesized_content": "The complete revised article/post text",
  "key_changes": [
    {{
      "change": "description of what was changed",
      "rationale": "why this improves the content",
      "personas_addressed": ["persona_id1", "persona_id2"]
    }}
  ]
}}"""

        response = await llm_chat(
            messages=[{"role": "user", "content": synthesis_prompt}],
            system_instruction="You are a master editor synthesizing critique feedback from multiple audience perspectives into a revised document. You balance authenticity with improvements.",
            max_tokens=4000,
            temperature=0.3,
        )

        # Parse JSON response
        result = {}
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                result = json.loads(json_match.group())
            except json.JSONDecodeError:
                result = {"synthesized_content": response, "key_changes": []}

        synthesized_content = result.get("synthesized_content", response)
        key_changes = result.get("key_changes", [])

        await pool.execute(
            """UPDATE critique_syntheses SET
                synthesized_content = $1,
                key_changes = $2::jsonb,
                personas_used = $3::jsonb,
                status = 'completed',
                completed_at = now()
               WHERE id = $4""",
            synthesized_content,
            json.dumps(key_changes),
            json.dumps(personas_used),
            synthesis_id,
        )
        log.info("Synthesis completed: %s", synthesis_id)

    except Exception as e:
        log.error("Synthesis %s failed: %s", synthesis_id, e)
        await pool.execute(
            "UPDATE critique_syntheses SET status = 'failed', error = $1 WHERE id = $2",
            str(e)[:500],
            synthesis_id,
        )


# ── Pydantic models ────────────────────────────────────────────────────────

class RunCritiqueRequest(BaseModel):
    article_id: Optional[str] = None
    article_title: str
    article_content: str
    personas: Optional[list[str]] = None  # None = all 6 personas


class SynthesizeRequest(BaseModel):
    run_id: str


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/personas")
async def list_personas():
    """List all available critique personas."""
    return {
        "personas": [
            {
                "id": p["id"],
                "audience": p["audience"],
                "figure": p["figure"],
                "figure_bio": p["figure_bio"],
                "lens": p["lens"],
            }
            for p in PERSONAS
        ]
    }


@router.post("/run", status_code=202)
async def run_critiques(req: RunCritiqueRequest, background_tasks: BackgroundTasks):
    """Start a critique run on an article/post.

    Creates a run + 6 critique records (one per persona), then kicks off
    background LLM processing. Returns immediately with run_id.
    """
    pool = await get_pool()
    await _ensure_tables(pool)

    # Determine which personas to use
    persona_ids = req.personas or [p["id"] for p in PERSONAS]
    selected_personas = [PERSONA_MAP[pid] for pid in persona_ids if pid in PERSONA_MAP]
    if not selected_personas:
        raise HTTPException(400, "No valid personas selected")

    # Create the run
    run_row = await pool.fetchrow(
        """INSERT INTO critique_runs (article_id, article_title, article_content, status)
           VALUES ($1, $2, $3, 'running')
           RETURNING *""",
        req.article_id,
        req.article_title,
        req.article_content,
    )
    run_id = str(run_row["id"])

    # Create critique records for each persona
    for persona in selected_personas:
        await pool.execute(
            """INSERT INTO critiques
               (run_id, persona_id, persona_name, persona_figure, audience, status)
               VALUES ($1, $2, $3, $4, $5, 'pending')""",
            run_id,
            persona["id"],
            f"{persona['audience']} ({persona['figure']})",
            persona["figure"],
            persona["audience"],
        )

    # Kick off background processing
    background_tasks.add_task(
        _run_all_critiques,
        run_id,
        req.article_title,
        req.article_content,
    )

    log.info("Critique run started: %s for '%s'", run_id, req.article_title)
    return {
        "run_id": run_id,
        "article_title": req.article_title,
        "personas": [p["id"] for p in selected_personas],
        "status": "running",
        "message": f"Running {len(selected_personas)} persona critiques in background",
    }


@router.get("/runs")
async def list_runs(limit: int = 20, article_id: Optional[str] = None):
    """List all critique runs, newest first."""
    pool = await get_pool()
    await _ensure_tables(pool)

    if article_id:
        rows = await pool.fetch(
            """SELECT * FROM critique_runs WHERE article_id = $1
               ORDER BY created_at DESC LIMIT $2""",
            article_id, limit,
        )
    else:
        rows = await pool.fetch(
            "SELECT * FROM critique_runs ORDER BY created_at DESC LIMIT $1",
            limit,
        )

    runs = []
    for row in rows:
        run_dict = _run_row(row)
        # Get critique count and status summary
        critique_rows = await pool.fetch(
            "SELECT status, COUNT(*) as cnt FROM critiques WHERE run_id = $1 GROUP BY status",
            str(row["id"]),
        )
        run_dict["critique_counts"] = {r["status"]: r["cnt"] for r in critique_rows}
        runs.append(run_dict)

    return {"runs": runs, "total": len(runs)}


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    """Get a critique run with all its critiques."""
    pool = await get_pool()
    await _ensure_tables(pool)

    run_row = await pool.fetchrow("SELECT * FROM critique_runs WHERE id = $1", run_id)
    if not run_row:
        raise HTTPException(404, f"Run {run_id} not found")

    critiques_rows = await pool.fetch(
        "SELECT * FROM critiques WHERE run_id = $1 ORDER BY persona_id",
        run_id,
    )

    synthesis_row = await pool.fetchrow(
        "SELECT * FROM critique_syntheses WHERE run_id = $1 ORDER BY created_at DESC LIMIT 1",
        run_id,
    )

    return {
        "run": _run_row(run_row),
        "critiques": [_critique_row(r) for r in critiques_rows],
        "synthesis": _synthesis_row(synthesis_row) if synthesis_row else None,
    }


@router.post("/synthesize", status_code=202)
async def synthesize(req: SynthesizeRequest, background_tasks: BackgroundTasks):
    """Synthesize all critique suggestions into a revised document.

    Requires the critique run to be completed (at least partially).
    """
    pool = await get_pool()
    await _ensure_tables(pool)

    run_row = await pool.fetchrow("SELECT * FROM critique_runs WHERE id = $1", req.run_id)
    if not run_row:
        raise HTTPException(404, f"Run {req.run_id} not found")

    if run_row["status"] == "pending" or run_row["status"] == "running":
        # Check if any are completed
        completed = await pool.fetchval(
            "SELECT COUNT(*) FROM critiques WHERE run_id = $1 AND status = 'completed'",
            req.run_id,
        )
        if completed == 0:
            raise HTTPException(400, "No completed critiques yet. Wait for the critique run to finish.")

    # Create synthesis record
    synthesis_row = await pool.fetchrow(
        """INSERT INTO critique_syntheses
           (run_id, article_title, original_content, status)
           VALUES ($1, $2, $3, 'running')
           RETURNING *""",
        req.run_id,
        run_row["article_title"],
        run_row["article_content"],
    )
    synthesis_id = str(synthesis_row["id"])

    background_tasks.add_task(
        _run_synthesis,
        synthesis_id,
        req.run_id,
        run_row["article_title"],
        run_row["article_content"],
    )

    log.info("Synthesis started: %s for run %s", synthesis_id, req.run_id)
    return {
        "synthesis_id": synthesis_id,
        "run_id": req.run_id,
        "status": "running",
        "message": "Synthesis running in background",
    }


@router.get("/syntheses/{synthesis_id}")
async def get_synthesis(synthesis_id: str):
    """Get a synthesis result."""
    pool = await get_pool()
    await _ensure_tables(pool)

    row = await pool.fetchrow("SELECT * FROM critique_syntheses WHERE id = $1", synthesis_id)
    if not row:
        raise HTTPException(404, f"Synthesis {synthesis_id} not found")

    return _synthesis_row(row)


@router.post("/run-social-posts", status_code=202)
async def run_social_posts_critique(background_tasks: BackgroundTasks):
    """Run persona critiques against all MY3YE X/social posts."""
    pool = await get_pool()
    await _ensure_tables(pool)

    # Fetch all my3ye posts
    rows = await pool.fetch(
        """SELECT id, title, content, post_type, scheduled_at
           FROM social_calendar_posts
           WHERE character = 'my3ye'
           ORDER BY scheduled_at ASC NULLS LAST""",
    )

    if not rows:
        raise HTTPException(404, "No MY3YE social posts found")

    # Group posts by category
    categories = {
        "Reveal": [],
        "Hot Take": [],
        "Builder Update": [],
        "Thread": [],
        "Lore": [],
        "Meme": [],
        "Other": [],
    }

    for row in rows:
        title = row["title"] or ""
        content = row["content"] or ""
        text = title + " " + content

        if "Reveal" in title:
            categories["Reveal"].append(row)
        elif "Hot Take" in title:
            categories["Hot Take"].append(row)
        elif "Builder Update" in title or "Autonomous Stats" in title or "Shipping" in title:
            categories["Builder Update"].append(row)
        elif "Thread" in title:
            categories["Thread"].append(row)
        elif "Lore" in title or "PiPi" in title or "Drop" in title:
            categories["Lore"].append(row)
        elif "meme" in text.lower() or "normie" in text.lower() or "Meme" in title:
            categories["Meme"].append(row)
        else:
            categories["Other"].append(row)

    # Build bundled content
    total = len(rows)
    lines = [
        "# MY3YE X/Social Posts — Full Content Strategy Validation",
        "",
        f"This is a complete collection of {total} scheduled X/social media posts for the MY3YE ecosystem.",
        "Please critique the overall content strategy, voice consistency, messaging effectiveness, and specific posts that stand out.",
        "Consider: Does the overall narrative arc work? What's missing? What lands best for your audience?",
        "",
    ]

    for category, cat_rows in categories.items():
        if not cat_rows:
            continue
        lines.append(f"## {category} Posts ({len(cat_rows)} posts)")
        lines.append("")
        for row in cat_rows:
            lines.append(f"**{row['title']}**")
            lines.append(row["content"].strip())
            lines.append("")
            lines.append("---")
            lines.append("")

    article_content = "\n".join(lines)
    article_title = f"MY3YE X/Social Posts — Full Strategy Validation ({total} posts)"
    article_id = "my3ye_social_posts_batch"

    # Create the run
    run_row = await pool.fetchrow(
        """INSERT INTO critique_runs (article_id, article_title, article_content, status)
           VALUES ($1, $2, $3, 'running')
           RETURNING *""",
        article_id,
        article_title,
        article_content,
    )
    run_id = str(run_row["id"])

    # Create critique records for each persona
    for persona in PERSONAS:
        await pool.execute(
            """INSERT INTO critiques
               (run_id, persona_id, persona_name, persona_figure, audience, status)
               VALUES ($1, $2, $3, $4, $5, 'pending')""",
            run_id,
            persona["id"],
            f"{persona['audience']} ({persona['figure']})",
            persona["figure"],
            persona["audience"],
        )

    # Kick off background processing
    background_tasks.add_task(
        _run_all_critiques,
        run_id,
        article_title,
        article_content,
    )

    log.info("MY3YE social posts critique run started: %s (%d posts)", run_id, total)
    return {
        "run_id": run_id,
        "article_title": article_title,
        "total_posts": total,
        "personas": [p["id"] for p in PERSONAS],
        "status": "running",
        "message": f"Running 6 persona critiques against {total} MY3YE posts in background",
    }


@router.get("")
async def list_recent(limit: int = 10):
    """Summary endpoint — recent runs with their critique counts."""
    pool = await get_pool()
    await _ensure_tables(pool)

    rows = await pool.fetch(
        "SELECT * FROM critique_runs ORDER BY created_at DESC LIMIT $1",
        limit,
    )

    result = []
    for row in rows:
        run_dict = _run_row(row)
        critique_rows = await pool.fetch(
            """SELECT persona_id, persona_figure, audience, rating, status
               FROM critiques WHERE run_id = $1 ORDER BY persona_id""",
            str(row["id"]),
        )
        run_dict["critiques"] = [
            {
                "persona_id": r["persona_id"],
                "persona_figure": r["persona_figure"],
                "audience": r["audience"],
                "rating": r["rating"],
                "status": r["status"],
            }
            for r in critique_rows
        ]
        # Check for synthesis
        synthesis_row = await pool.fetchrow(
            "SELECT id, status FROM critique_syntheses WHERE run_id = $1 ORDER BY created_at DESC LIMIT 1",
            str(row["id"]),
        )
        run_dict["synthesis"] = {"id": str(synthesis_row["id"]), "status": synthesis_row["status"]} if synthesis_row else None
        result.append(run_dict)

    return {"runs": result, "total": len(result)}
