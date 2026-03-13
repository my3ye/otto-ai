"""
Universe API routes — MY3YE Universe System.

Manages YAML files in ~/otto/universe/ for projects and personas.
Supports read, partial update, and conversational (LLM-driven) edits.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import asyncio
import json

from ..llm import llm_chat, extract_json

log = logging.getLogger("otto.universe")

router = APIRouter(prefix="/universe", tags=["universe"])

# ── Paths ──────────────────────────────────────────────────────────────────────

UNIVERSE_DIR = Path("/home/web3relic/otto/universe")
PROJECTS_DIR = UNIVERSE_DIR / "projects"
PERSONAS_DIR = UNIVERSE_DIR / "personas"
REGISTRY_PATH = UNIVERSE_DIR / "registry.yaml"
CHANGELOG_PATH = UNIVERSE_DIR / "changelog.md"


# ── Helpers ────────────────────────────────────────────────────────────────────

def deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, returning a new dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _read_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _write_yaml(path: Path, data: dict) -> None:
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def append_changelog(entry: str) -> None:
    with open(CHANGELOG_PATH, "a") as f:
        f.write(f"\n- {datetime.now().strftime('%Y-%m-%d %H:%M')}: {entry}")


def _changed_fields(old: dict, new: dict, prefix: str = "") -> list[str]:
    """Return a list of dot-notation keys that differ between old and new."""
    changed = []
    all_keys = set(old.keys()) | set(new.keys())
    for k in all_keys:
        full_key = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
        if k not in old:
            changed.append(f"+{full_key}")
        elif k not in new:
            changed.append(f"-{full_key}")
        elif isinstance(old[k], dict) and isinstance(new[k], dict):
            changed.extend(_changed_fields(old[k], new[k], prefix=full_key))
        elif old[k] != new[k]:
            changed.append(full_key)
    return changed


# ── Pydantic models ────────────────────────────────────────────────────────────

def _clear_loader_cache():
    """Clear the universe loader's in-memory cache after writes."""
    try:
        import sys
        sys.path.insert(0, str(UNIVERSE_DIR.parent))
        from universe.loader import clear_cache
        clear_cache()
    except Exception as e:
        log.warning(f"clear_cache failed (non-fatal): {e}")


CLAUDE_CLI = "/home/web3relic/.local/bin/claude"


async def _claude_edit(yaml_text: str, user_message: str, entity_label: str, entity_id: str) -> dict | None:
    """Use Claude CLI to parse natural language edit into JSON fields."""
    prompt = (
        f"You are editing a {entity_label} YAML file ('{entity_id}'). "
        f"Current content:\n```yaml\n{yaml_text}```\n\n"
        f"User wants: {user_message}\n\n"
        "Return ONLY a JSON object with the fields to update. Use the same nested structure as the YAML. "
        "Only include changed fields. Example: {\"identity\": {\"tagline\": \"new value\"}}"
    )
    try:
        proc = await asyncio.create_subprocess_exec(
            CLAUDE_CLI, "-p", "--model", "haiku", "--max-turns", "1",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(prompt.encode()),
            timeout=90,
        )
        if proc.returncode == 0 and stdout:
            return extract_json(stdout.decode())
        log.warning(f"Claude CLI edit failed: code={proc.returncode} err={stderr.decode()[:200]}")
    except asyncio.TimeoutError:
        log.warning("Claude CLI edit timed out")
        try:
            proc.kill()
        except Exception:
            pass
    except Exception as e:
        log.warning(f"Claude CLI edit error: {e}")
    return None


class EditRequest(BaseModel):
    message: str
    target_type: str  # "project" or "persona"
    target_id: str


# ── Project endpoints ──────────────────────────────────────────────────────────

@router.get("/projects")
async def list_projects():
    """List all projects from the registry with basic info."""
    if not REGISTRY_PATH.exists():
        raise HTTPException(status_code=404, detail="registry.yaml not found")
    reg = _read_yaml(REGISTRY_PATH)
    projects = [
        {"id": pid, **info}
        for pid, info in reg.get("projects", {}).items()
    ]
    return {"projects": projects, "count": len(projects)}


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get a full project YAML as JSON."""
    path = PROJECTS_DIR / f"{project_id}.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return _read_yaml(path)


@router.put("/projects/{project_id}")
async def update_project(project_id: str, body: dict):
    """Partial update a project. Deep-merges body into existing YAML, logs to changelog."""
    path = PROJECTS_DIR / f"{project_id}.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    existing = _read_yaml(path)
    updated = deep_merge(existing, body)
    _write_yaml(path, updated)

    changed = _changed_fields(existing, updated)
    description = f"fields changed: {', '.join(changed)}" if changed else "no-op update"
    append_changelog(f"Updated project '{project_id}' — {description}")

    _clear_loader_cache()

    return {"ok": True, "project_id": project_id, "changed_fields": changed, "content": updated}


# ── Persona endpoints ──────────────────────────────────────────────────────────

@router.get("/personas")
async def list_personas():
    """List all personas from the registry with basic info."""
    if not REGISTRY_PATH.exists():
        raise HTTPException(status_code=404, detail="registry.yaml not found")
    reg = _read_yaml(REGISTRY_PATH)
    personas = [
        {"id": pid, **info}
        for pid, info in reg.get("personas", {}).items()
    ]
    return {"personas": personas, "count": len(personas)}


@router.get("/personas/{persona_id}")
async def get_persona(persona_id: str):
    """Get a full persona YAML as JSON."""
    path = PERSONAS_DIR / f"{persona_id}.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found")
    return _read_yaml(path)


@router.put("/personas/{persona_id}")
async def update_persona(persona_id: str, body: dict):
    """Partial update a persona. Deep-merges body into existing YAML, logs to changelog."""
    path = PERSONAS_DIR / f"{persona_id}.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found")

    existing = _read_yaml(path)
    updated = deep_merge(existing, body)
    _write_yaml(path, updated)

    changed = _changed_fields(existing, updated)
    description = f"fields changed: {', '.join(changed)}" if changed else "no-op update"
    append_changelog(f"Updated persona '{persona_id}' — {description}")

    _clear_loader_cache()

    return {"ok": True, "persona_id": persona_id, "changed_fields": changed, "content": updated}


# ── Registry & changelog ───────────────────────────────────────────────────────

@router.get("/registry")
async def get_registry():
    """Get the full registry.yaml as JSON."""
    if not REGISTRY_PATH.exists():
        raise HTTPException(status_code=404, detail="registry.yaml not found")
    return _read_yaml(REGISTRY_PATH)


@router.get("/changelog")
async def get_changelog():
    """Get the changelog as plain text."""
    if not CHANGELOG_PATH.exists():
        return {"changelog": ""}
    return {"changelog": CHANGELOG_PATH.read_text()}


# ── Conversational edit ────────────────────────────────────────────────────────

@router.post("/edit")
async def conversational_edit(req: EditRequest):
    """LLM-driven conversational edit.

    Sends current YAML content + user message to the LLM, which returns
    the exact fields to update. Applies via deep merge and logs to changelog.
    """
    target_type = req.target_type.lower()
    if target_type not in ("project", "persona"):
        raise HTTPException(status_code=400, detail="target_type must be 'project' or 'persona'")

    if target_type == "project":
        path = PROJECTS_DIR / f"{req.target_id}.yaml"
        entity_label = "project"
    else:
        path = PERSONAS_DIR / f"{req.target_id}.yaml"
        entity_label = "persona"

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"{entity_label.capitalize()} '{req.target_id}' not found",
        )

    existing = _read_yaml(path)
    yaml_text = yaml.dump(existing, default_flow_style=False, allow_unicode=True)

    system_prompt = (
        "You are a YAML editor for the MY3YE Universe system. "
        "The user will describe a change they want to make to a YAML document. "
        "Return ONLY a JSON object with the exact fields to update — no explanation, no markdown. "
        "Use the same nested key structure as the original YAML. "
        "Only include the fields that need to change, not the entire document."
    )

    user_message = (
        f"Here is the current {entity_label} YAML for '{req.target_id}':\n\n"
        f"```yaml\n{yaml_text}```\n\n"
        f"User request: {req.message}\n\n"
        "Return a JSON object with only the fields that should be updated."
    )

    # Try Kimi/primary LLM first
    llm_response = await llm_chat(
        messages=[{"role": "user", "content": user_message}],
        system_instruction=system_prompt,
        max_tokens=1000,
        temperature=0.0,
    )

    changes = extract_json(llm_response) if llm_response else None

    # Fallback: Claude CLI with explicit JSON prompt
    if not changes:
        log.info("Primary LLM failed for universe edit, trying Claude CLI directly")
        changes = await _claude_edit(yaml_text, req.message, entity_label, req.target_id)

    if not changes:
        raise HTTPException(
            status_code=502,
            detail="Both LLM backends failed to produce a valid edit. Try a simpler instruction or use the PUT endpoint directly.",
        )

    updated = deep_merge(existing, changes)
    _write_yaml(path, updated)

    changed_fields = _changed_fields(existing, updated)
    description = f"via conversational edit: \"{req.message[:80]}\""
    append_changelog(f"Updated {entity_label} '{req.target_id}' — {description}")

    _clear_loader_cache()

    log.info(f"Conversational edit applied to {entity_label} '{req.target_id}': {changed_fields}")

    return {
        "changes": changes,
        "message": f"Applied: {req.message}",
        "changed_fields": changed_fields,
        "new_content": updated,
    }
