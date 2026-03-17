#!/usr/bin/env python3
"""
roadmap_sync.py — Sync universe roadmaps with task queue.

Reads roadmap .md files, parses phases/milestones, queries the task queue DB
for related tasks, and outputs a dependency report JSON.

Usage:
    python3 roadmap_sync.py [--output PATH]

Output JSON structure:
    {
      "generated_at": "ISO timestamp",
      "summary": { "total_milestones": N, "completed": N, ... },
      "projects": {
        "project_id": {
          "title": "...",
          "status": "live|in-progress|planned",
          "layers": [...],
          "phases": [
            {
              "name": "Phase 1 — ...",
              "goal": "...",
              "milestones": [
                {
                  "name": "...",
                  "status": "completed|in-progress|pending|blocked",
                  "related_tasks": [
                    { "id": "...", "title": "...", "status": "completed", "completed_at": "..." }
                  ],
                  "blocking_tasks": []   # pending/running tasks that must finish before this milestone
                }
              ]
            }
          ]
        }
      }
    }
"""

import re
import json
import os
import sys
import asyncio
import asyncpg
from datetime import datetime, timezone
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
ROADMAPS_DIR = Path("/home/web3relic/otto/universe/roadmaps")
OUTPUT_PATH  = Path("/home/web3relic/otto/projects/capital/roadmap_dependencies.json")

# DB settings (matches ~/memory/.env)
DB_DSN = "postgresql://otto:LldgQBV1hiPejrKn6UlPQvX76pBqMB@localhost:5432/memory"

# Files to skip
SKIP_FILES = {"README.md", "master-dependency-map.md", "polkadot-bd-pitch.md"}

# ── Layer map (from master-dependency-map.md) ───────────────────────────────
PROJECT_LAYERS = {
    "03-oneon":          {"layer": 0, "name": "ONEON",           "hard_deps": [],                           "blocks": ["Otto AI", "Panik", "ONEON identity/comms"]},
    "14-505-systems":    {"layer": 0, "name": "S0S Systems",     "hard_deps": [],                           "blocks": ["Governance", "DAOs", "tokens", "Koink"]},
    "14-otto-ai":        {"layer": 1, "name": "Otto AI",         "hard_deps": ["ONEON"],                    "blocks": ["OMS", "Broadcast", "all AI agents"]},
    "15-ottolabs":       {"layer": 1, "name": "Ottolabs",        "hard_deps": ["S0S Systems"],              "blocks": ["Tusita physical", "Properties"]},
    "01-webassist":      {"layer": 2, "name": "WebAssist",       "hard_deps": [],                           "blocks": ["First revenue stream"]},
    "02-oms":            {"layer": 2, "name": "OMS",             "hard_deps": ["Otto AI"],                  "blocks": ["Mev visibility/control"]},
    "11-koink-koin":     {"layer": 3, "name": "Koink/KOIN",      "hard_deps": ["S0S Systems"],              "blocks": ["Community funding", "PiPi"]},
    "19-pipi":           {"layer": 3, "name": "PiPi",            "hard_deps": ["Koink"],                    "blocks": []},
    "12-pipi":           {"layer": 3, "name": "PiPi",            "hard_deps": ["Koink"],                    "blocks": []},
    "06-otto-music":     {"layer": 3, "name": "Otto Music",      "hard_deps": ["ONEON", "S0S Systems"],     "blocks": []},
    "10-panik":          {"layer": 3, "name": "Panik App",       "hard_deps": ["ONEON"],                    "blocks": []},
    "09-shakrah":        {"layer": 3, "name": "Shakrah",         "hard_deps": ["ONEON", "Ottolabs"],        "blocks": []},
    "04-tusita":         {"layer": 4, "name": "Tusita",          "hard_deps": ["ONEON", "S0S", "Ottolabs", "Shakrah"], "blocks": ["Properties"]},
    "08-otto-properties":{"layer": 4, "name": "Otto Properties", "hard_deps": ["ONEON", "S0S", "Ottolabs", "Tusita"],  "blocks": []},
    "05-otto-travel":    {"layer": 5, "name": "Otto Travel",     "hard_deps": ["ONEON", "Tusita", "Properties"], "blocks": []},
    "07-otto-market":    {"layer": 5, "name": "Otto Market",     "hard_deps": ["ONEON", "S0S"],             "blocks": []},
    "12-my3ye":          {"layer": 0, "name": "MY3YE",           "hard_deps": [],                           "blocks": ["All"]},
    "13-s0s-systems":    {"layer": 0, "name": "S0S Systems",     "hard_deps": [],                           "blocks": []},
    "16-otto-ui":        {"layer": 1, "name": "Otto UI",         "hard_deps": [],                           "blocks": []},
    "17-otto-cars":      {"layer": 3, "name": "Otto Cars",       "hard_deps": ["ONEON", "Ottolabs"],        "blocks": []},
    "18-otto-billboards":{"layer": 3, "name": "Otto Billboards", "hard_deps": ["ONEON"],                    "blocks": []},
}


# ── Roadmap parser ───────────────────────────────────────────────────────────

def parse_roadmap(path: Path) -> dict:
    """Parse a roadmap .md file into structured data."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    project_id = path.stem  # e.g. "01-webassist"
    meta = PROJECT_LAYERS.get(project_id, {})

    result = {
        "id": project_id,
        "title": _extract_title(lines),
        "subtitle": _extract_subtitle(lines),
        "layer": meta.get("layer", -1),
        "hard_deps": meta.get("hard_deps", []),
        "blocks": meta.get("blocks", []),
        "current_status": _extract_current_status(text),
        "phases": _extract_phases(text),
    }
    return result


def _extract_title(lines: list) -> str:
    for ln in lines:
        if ln.startswith("# "):
            return ln[2:].strip()
    return "Unknown"


def _extract_subtitle(lines: list) -> str:
    for ln in lines:
        ln = ln.strip()
        if ln.startswith("*") and ln.endswith("*") and len(ln) > 2:
            return ln.strip("*").strip()
    return ""


def _extract_current_status(text: str) -> str:
    m = re.search(r"\*\*(?:LIVE|Status)[:\s—-]+(.*?)\*\*", text)
    if m:
        return m.group(1).strip()
    if "**LIVE**" in text:
        return "live"
    if "**PLANNED**" in text:
        return "planned"
    return "in-progress"


def _extract_phases(text: str) -> list:
    """Extract Phase sections with their milestones."""
    phases = []

    # Split on Phase headings: ## Phase N — ...
    phase_blocks = re.split(r"(?m)^## Phase \d+", text)

    for i, block in enumerate(phase_blocks[1:], 1):
        # Get phase heading line
        heading_match = re.search(r"^[^\n]*", block)
        heading = f"Phase {i}" + (heading_match.group(0).strip() if heading_match else "")

        # Goal line
        goal_m = re.search(r"\*\*Goal[:\s]*\*\*[:\s]*(.*)", block)
        goal = goal_m.group(1).strip() if goal_m else ""

        # Extract milestones from numbered lists under ### Milestones
        milestones = _extract_milestones(block)

        phases.append({
            "name": heading,
            "goal": goal,
            "milestones": milestones,
        })

    return phases


def _extract_milestones(phase_text: str) -> list:
    """Extract milestone names from a phase block."""
    milestones = []

    # Look for ### Milestones section
    m_section = re.search(r"###\s+Milestones\s*\n(.*?)(?:\n###|\n---|\Z)", phase_text, re.DOTALL)
    if not m_section:
        m_section_text = phase_text
    else:
        m_section_text = m_section.group(1)

    # Pattern 1: numbered list: 1. **Title** — description
    for match in re.finditer(r"^\d+\.\s+\*\*(.*?)\*\*", m_section_text, re.MULTILINE):
        name = match.group(1).strip()
        if name and len(name) > 2:
            milestones.append({"name": name, "description": ""})

    # Pattern 2: **N.N — Title** (Otto AI style) OR **MN — Title** (Ottolabs style)
    if not milestones:
        for match in re.finditer(r"^\*\*(?:\d+\.\d+|M\d+)\s*[—-]\s*(.*?)\*\*", m_section_text, re.MULTILINE):
            name = match.group(1).strip()
            if name and len(name) > 2:
                milestones.append({"name": name, "description": ""})

    # Pattern 3: bare numbered list: 1. Title — description (without bold)
    if not milestones:
        for match in re.finditer(r"^\d+\.\s+(.+?)(?:\s*—|\s*-|\s*:|\s*$)", m_section_text, re.MULTILINE):
            name = match.group(1).strip().strip("*")
            if name and len(name) > 3 and not name.startswith("["):
                milestones.append({"name": name, "description": ""})

    return milestones


# ── Task matcher ─────────────────────────────────────────────────────────────

def build_search_terms(project: dict) -> list[str]:
    """Build keyword search terms from project title and milestone names."""
    terms = []
    # Project-level terms
    proj_name = project["title"].lower()
    # Extract core words (2+ chars, not stopwords)
    stopwords = {"the", "a", "an", "and", "or", "for", "with", "in", "on", "at", "to", "of",
                 "is", "are", "be", "build", "create", "update", "fix", "add", "improve"}
    words = [w for w in re.findall(r"[a-z]{3,}", proj_name) if w not in stopwords]
    terms.extend(words)
    return list(set(terms))


def match_tasks_to_milestone(milestone_name: str, project_title: str, all_tasks: list) -> tuple[list, list]:
    """Return (related_tasks, blocking_tasks) for a milestone."""
    # Build search words from milestone name + project name
    name_lower = milestone_name.lower()
    proj_lower = project_title.lower()

    # Keywords: significant words from both
    stopwords = {"the", "a", "an", "and", "or", "for", "with", "in", "on", "at", "to", "of",
                 "is", "are", "be", "build", "create", "update", "fix", "add", "improve",
                 "design", "write", "research", "implement", "system", "all", "new"}

    milestone_words = set(w for w in re.findall(r"[a-z]{3,}", name_lower) if w not in stopwords)
    project_words = set(w for w in re.findall(r"[a-z]{3,}", proj_lower) if w not in stopwords)

    # Must match at least 1 project word AND 1 milestone word (or 2+ milestone words)
    related = []
    blocking = []

    for task in all_tasks:
        title_lower = task["title"].lower()
        task_words = set(re.findall(r"[a-z]{3,}", title_lower))

        proj_overlap = len(project_words & task_words)
        milestone_overlap = len(milestone_words & task_words)

        # Score: weighted overlap
        score = (proj_overlap * 2) + (milestone_overlap * 3)

        if score >= 4:  # meaningful match threshold
            task_entry = {
                "id": task["id"][:8],
                "full_id": task["id"],
                "title": task["title"],
                "status": task["status"],
                "created_at": task.get("created_at", ""),
                "completed_at": task.get("completed_at", ""),
                "score": score,
            }
            related.append(task_entry)
            if task["status"] in ("running", "pending"):
                blocking.append(task_entry)

    # Sort by score desc
    related.sort(key=lambda x: x["score"], reverse=True)
    return related[:5], blocking  # cap at 5 most relevant


def infer_milestone_status(milestone: dict, related_tasks: list, blocking_tasks: list) -> str:
    """Infer milestone completion status from related tasks."""
    if not related_tasks:
        return "pending"

    completed = [t for t in related_tasks if t["status"] == "completed"]
    if blocking_tasks:
        return "blocked"
    if completed:
        return "completed"
    running = [t for t in related_tasks if t["status"] == "running"]
    if running:
        return "in-progress"
    return "pending"


# ── DB fetch ─────────────────────────────────────────────────────────────────

async def fetch_all_tasks() -> list:
    """Fetch all tasks from DB."""
    conn = await asyncpg.connect(DB_DSN)
    try:
        rows = await conn.fetch(
            """
            SELECT id::text, title, status, created_at, completed_at, priority
            FROM tasks
            ORDER BY created_at DESC
            """
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


# ── Main ─────────────────────────────────────────────────────────────────────

async def main(output_path: Path = OUTPUT_PATH):
    print(f"[roadmap_sync] Loading tasks from DB...")
    all_tasks = await fetch_all_tasks()
    print(f"[roadmap_sync] Loaded {len(all_tasks)} tasks")

    # Normalize task dates to strings
    for t in all_tasks:
        for f in ("created_at", "completed_at"):
            if t[f] is not None:
                t[f] = t[f].isoformat() if hasattr(t[f], "isoformat") else str(t[f])

    print(f"[roadmap_sync] Parsing roadmap files...")
    roadmap_files = sorted(
        [f for f in ROADMAPS_DIR.glob("*.md") if f.name not in SKIP_FILES]
    )
    print(f"[roadmap_sync] Found {len(roadmap_files)} roadmap files")

    projects = {}
    total_milestones = 0
    status_counts = {"completed": 0, "in-progress": 0, "pending": 0, "blocked": 0}

    for rf in roadmap_files:
        project = parse_roadmap(rf)
        pid = project["id"]

        enriched_phases = []
        for phase in project["phases"]:
            enriched_milestones = []
            for ms in phase["milestones"]:
                related, blocking = match_tasks_to_milestone(
                    ms["name"], project["title"], all_tasks
                )
                ms_status = infer_milestone_status(ms, related, blocking)
                status_counts[ms_status] = status_counts.get(ms_status, 0) + 1
                total_milestones += 1

                enriched_milestones.append({
                    "name": ms["name"],
                    "status": ms_status,
                    "related_tasks": [
                        {k: v for k, v in t.items() if k != "score"}
                        for t in related
                    ],
                    "blocking_tasks": [
                        {k: v for k, v in t.items() if k != "score"}
                        for t in blocking
                    ],
                })

            enriched_phases.append({
                "name": phase["name"],
                "goal": phase["goal"],
                "milestones": enriched_milestones,
            })

        projects[pid] = {
            "title": project["title"],
            "subtitle": project["subtitle"],
            "current_status": project["current_status"],
            "layer": project["layer"],
            "hard_deps": project["hard_deps"],
            "blocks": project["blocks"],
            "phases": enriched_phases,
            "phase_count": len(enriched_phases),
            "milestone_count": sum(len(p["milestones"]) for p in enriched_phases),
        }
        print(f"  [{pid}] {project['title']} — {len(enriched_phases)} phases, "
              f"{sum(len(p['milestones']) for p in enriched_phases)} milestones")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_projects": len(projects),
            "total_milestones": total_milestones,
            "total_tasks_in_queue": len(all_tasks),
            "milestone_status_breakdown": status_counts,
            "pct_complete": round(status_counts.get("completed", 0) / max(total_milestones, 1) * 100, 1),
        },
        "dependency_layers": {
            "layer_0_foundations": ["ONEON", "S0S Systems"],
            "layer_1_intelligence": ["Otto AI", "Ottolabs"],
            "layer_2_revenue": ["WebAssist", "OMS"],
            "layer_3_community": ["Koink/KOIN", "PiPi", "Otto Music", "Panik App", "Shakrah"],
            "layer_4_physical": ["Tusita", "Otto Properties"],
            "layer_5_commerce": ["Otto Travel", "Otto Market"],
        },
        "projects": projects,
    }

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print(f"\n[roadmap_sync] ✓ Report written to {output_path}")
    print(f"[roadmap_sync] Summary:")
    print(f"  Projects:   {report['summary']['total_projects']}")
    print(f"  Milestones: {report['summary']['total_milestones']}")
    print(f"  Tasks:      {report['summary']['total_tasks_in_queue']}")
    print(f"  Completed:  {status_counts.get('completed', 0)} ({report['summary']['pct_complete']}%)")
    print(f"  In-progress:{status_counts.get('in-progress', 0)}")
    print(f"  Pending:    {status_counts.get('pending', 0)}")
    print(f"  Blocked:    {status_counts.get('blocked', 0)}")

    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sync roadmaps with task queue")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="Output JSON path")
    args = parser.parse_args()
    asyncio.run(main(args.output))
