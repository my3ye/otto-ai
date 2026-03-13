"""
Universe Context Loader — loads project and persona context for Otto.

Usage:
    from universe.loader import load_project, load_persona, search_projects, get_context_for_mention

The primary function is get_context_for_mention(text) which scans text for
project/persona references and returns relevant context for injection into
Otto's conversation.
"""

import yaml
from pathlib import Path
from typing import Optional

UNIVERSE_DIR = Path(__file__).parent
PROJECTS_DIR = UNIVERSE_DIR / "projects"
PERSONAS_DIR = UNIVERSE_DIR / "personas"
REGISTRY_PATH = UNIVERSE_DIR / "registry.yaml"

# Cache
_registry_cache: dict | None = None
_project_cache: dict = {}
_persona_cache: dict = {}


def _load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def get_registry() -> dict:
    global _registry_cache
    if _registry_cache is None:
        _registry_cache = _load_yaml(REGISTRY_PATH)
    return _registry_cache


def load_project(project_id: str) -> dict | None:
    """Load a project YAML by its ID."""
    if project_id in _project_cache:
        return _project_cache[project_id]

    path = PROJECTS_DIR / f"{project_id}.yaml"
    if not path.exists():
        return None

    data = _load_yaml(path)
    _project_cache[project_id] = data
    return data


def load_persona(persona_id: str) -> dict | None:
    """Load a persona YAML by its ID."""
    if persona_id in _persona_cache:
        return _persona_cache[persona_id]

    path = PERSONAS_DIR / f"{persona_id}.yaml"
    if not path.exists():
        return None

    data = _load_yaml(path)
    _persona_cache[persona_id] = data
    return data


def list_projects() -> list[dict]:
    """List all projects with basic info from registry."""
    reg = get_registry()
    return [
        {"id": pid, **info}
        for pid, info in reg.get("projects", {}).items()
    ]


def list_personas() -> list[dict]:
    """List all personas with basic info from registry."""
    reg = get_registry()
    return [
        {"id": pid, **info}
        for pid, info in reg.get("personas", {}).items()
    ]


def search_projects(query: str) -> list[dict]:
    """Search projects by name, ID, or one-liner."""
    query_lower = query.lower()
    results = []
    for proj in list_projects():
        searchable = f"{proj['id']} {proj.get('one_liner', '')}".lower()
        if query_lower in searchable:
            results.append(proj)
    return results


# ── Mention Detection & Context Injection ─────────────────────────────────────

# Map of keywords/aliases -> project IDs
_PROJECT_ALIASES: dict[str, str] = {
    "my3ye": "my3ye",
    "the eye": "my3ye",
    "maitrieye": "my3ye",
    "otto": "otto",
    "ottoassist": "otto",
    "otto assist": "otto",
    "oneon": "oneon",
    "the network": "oneon",
    "tusita": "tusita",
    "the civilization": "tusita",
    "505 systems": "505-systems",
    "505systems": "505-systems",
    "sos systems": "505-systems",
    "sos": "505-systems",
    "the umbrella": "505-systems",
    "ottolabs": "ottolabs",
    "otto labs": "ottolabs",
    "the workshop": "ottolabs",
    "otto puck": "ottolabs",
    "otto phone": "ottolabs",
    "otto band": "ottolabs",
    "otto buds": "ottolabs",
    "otto home": "ottolabs",
    "otto tower": "ottolabs",
    "otto satellites": "ottolabs",
    "otto music": "otto-music",
    "the frequency": "otto-music",
    "otto travel": "otto-travel",
    "experience ceylon": "otto-travel",
    "otto market": "otto-market",
    "the exchange": "otto-market",
    "otto properties": "otto-properties",
    "the land": "otto-properties",
    "shakrah": "shakrah",
    "the balance": "shakrah",
    "wellness": "shakrah",
    "panik": "panik",
    "panik app": "panik",
    "the shield": "panik",
    "koink": "koink",
    "koink.fun": "koink",
    "koinkfun": "koink",
    "the money printer": "koink",
    "quantum koinkulator": "koink",
    "pipi": "pipi",
    "perspicacious": "pipi",
    "pink pepe pig": "pipi",
    "the first meme": "pipi",
    "assistive tech": "assistive-tech",
    "assistive technologies": "assistive-tech",
    "webassist": "assistive-tech",
    "techassist": "assistive-tech",
    "brandassist": "assistive-tech",
    "appassist": "assistive-tech",
    "just assist it": "assistive-tech",
}


def detect_mentions(text: str) -> list[str]:
    """Detect project mentions in text. Returns list of project IDs."""
    text_lower = text.lower()
    found = set()

    # Sort aliases by length (longest first) to match multi-word phrases first
    sorted_aliases = sorted(_PROJECT_ALIASES.keys(), key=len, reverse=True)

    for alias in sorted_aliases:
        if alias in text_lower:
            found.add(_PROJECT_ALIASES[alias])

    return list(found)


def get_context_for_mention(text: str, max_projects: int = 3) -> str:
    """
    Scan text for project/persona mentions and return formatted context
    suitable for injection into Otto's system prompt or conversation.

    Returns empty string if no projects mentioned.
    """
    project_ids = detect_mentions(text)
    if not project_ids:
        return ""

    # Limit to prevent context bloat
    project_ids = project_ids[:max_projects]

    blocks = []
    for pid in project_ids:
        proj = load_project(pid)
        if not proj:
            continue

        identity = proj.get("identity", {})
        brand = proj.get("brand", {})
        technical = proj.get("technical", {})
        ecosystem = proj.get("ecosystem", {})
        questions = proj.get("open_questions", [])

        block = f"## {proj.get('name', pid)}\n"
        block += f"**Archetype:** {proj.get('archetype', '')}\n"

        if identity.get("what_it_is"):
            block += f"**What it is:** {identity['what_it_is'].strip()}\n"
        if identity.get("what_it_is_not"):
            block += f"**What it is NOT:** {identity['what_it_is_not'].strip()}\n"
        if identity.get("key_quote"):
            block += f"**Key quote:** \"{identity['key_quote']}\"\n"

        if brand.get("domain"):
            block += f"**Domain:** {brand['domain']}\n"
        if technical.get("status"):
            block += f"**Status:** {technical['status']}\n"
        if technical.get("repo"):
            block += f"**Repo:** {technical['repo']}\n"

        if ecosystem.get("provides"):
            block += f"**Provides:** {', '.join(ecosystem['provides'])}\n"

        if questions:
            block += f"**Open questions:** {'; '.join(questions[:3])}\n"

        blocks.append(block)

    if not blocks:
        return ""

    header = "--- PROJECT CONTEXT (from ~/otto/universe/) ---\n"
    return header + "\n".join(blocks) + "--- END PROJECT CONTEXT ---\n"


def get_persona_context(persona_id: str) -> str:
    """Load a persona and return formatted context for agent use."""
    persona = load_persona(persona_id)
    if not persona:
        return ""

    voice = persona.get("voice", {})
    behavior = persona.get("behavior", {})
    examples = persona.get("post_examples", [])
    never_say = persona.get("never_say", [])
    never_do = persona.get("never_do", [])

    block = f"## Persona: {persona.get('name', persona_id)}\n"
    block += f"**Role:** {persona.get('role', '')}\n"

    if persona.get("identity", {}).get("bio"):
        block += f"**Bio:** {persona['identity']['bio'][0]}\n"
    if voice.get("tone"):
        block += f"**Tone:** {voice['tone']}\n"
    if voice.get("sentence_length"):
        block += f"**Length:** {voice['sentence_length']}\n"

    if examples:
        block += "\n**Example posts:**\n"
        for ex in examples[:8]:
            block += f"- \"{ex}\"\n"

    if never_say:
        block += f"\n**Never say:** {', '.join(never_say[:10])}\n"
    if never_do:
        block += f"\n**Never do:**\n"
        for nd in never_do[:5]:
            block += f"- {nd}\n"

    return block


# ── Clear caches (useful after edits) ─────────────────────────────────────────

def clear_cache():
    global _registry_cache, _project_cache, _persona_cache
    _registry_cache = None
    _project_cache.clear()
    _persona_cache.clear()
