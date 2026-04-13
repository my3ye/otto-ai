"""File manager routes — browse/upload/download/edit files on /mnt/media."""
import logging
import os
import mimetypes
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

log = logging.getLogger("otto.files")

router = APIRouter(prefix="/files", tags=["files"])

MEDIA_ROOT = Path("/mnt/media")


ALLOWED_ABSOLUTE_ROOTS = (
    Path("/var/www"),
    Path("/mnt/media"),
    Path("/home/web3relic"),
)

LANGUAGE_MAP: dict[str, str] = {
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".py": "python",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "css",
    ".sass": "css",
    ".less": "css",
    ".json": "json",
    ".md": "markdown",
    ".mdx": "markdown",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".sql": "sql",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".svg": "xml",
    ".env": "plaintext",
    ".txt": "plaintext",
    ".log": "plaintext",
    ".conf": "plaintext",
    ".ini": "plaintext",
    ".rs": "rust",
    ".go": "go",
    ".rb": "ruby",
    ".php": "php",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".cs": "csharp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".r": "r",
    ".tf": "terraform",
    ".Dockerfile": "dockerfile",
}

MAX_READ_SIZE = 2 * 1024 * 1024  # 2 MB
BINARY_SNIFF_BYTES = 1024


def _safe_path(path_str: str) -> Path:
    """Resolve path safely within MEDIA_ROOT. Raises 400 on traversal."""
    # Normalise and strip leading slash so Path doesn't treat it as absolute
    clean = path_str.lstrip("/")
    resolved = (MEDIA_ROOT / clean).resolve()
    try:
        resolved.relative_to(MEDIA_ROOT.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Path outside media root")
    return resolved


def _safe_absolute_path(path_str: str) -> Path:
    """Resolve an absolute path, restricting to ALLOWED_ABSOLUTE_ROOTS."""
    resolved = Path(path_str).resolve()
    for allowed in ALLOWED_ABSOLUTE_ROOTS:
        try:
            resolved.relative_to(allowed.resolve())
            return resolved
        except ValueError:
            continue
    allowed_str = ", ".join(str(r) for r in ALLOWED_ABSOLUTE_ROOTS)
    raise HTTPException(
        status_code=400,
        detail=f"Absolute path must be under one of: {allowed_str}",
    )


def _resolve_path(path_str: str, root: str) -> tuple[Path, str]:
    """
    Resolve path according to root mode.
    Returns (resolved_path, display_path).
    """
    if root == "absolute":
        resolved = _safe_absolute_path(path_str)
        display = path_str.lstrip("/")
    else:
        resolved = _safe_path(path_str)
        display = str(resolved.relative_to(MEDIA_ROOT))
    return resolved, display


def _detect_language(path: Path) -> str:
    """Return a language identifier from the file extension."""
    suffix = path.suffix.lower()
    if path.name == "Dockerfile":
        return "dockerfile"
    return LANGUAGE_MAP.get(suffix, "plaintext")


def _is_binary(path: Path) -> bool:
    """Return True if the file appears to be binary (null bytes in first 1 KB)."""
    try:
        with path.open("rb") as fh:
            chunk = fh.read(BINARY_SNIFF_BYTES)
        return b"\x00" in chunk
    except OSError:
        return False


class WriteRequest(BaseModel):
    path: str
    content: str
    root: Literal["media", "absolute"] = "media"


class CreateRequest(BaseModel):
    path: str
    is_dir: bool = False
    root: Literal["media", "absolute"] = "media"


class FileEntry(BaseModel):
    name: str
    path: str  # relative to /mnt/media
    is_dir: bool
    size: int | None
    modified: float | None
    mime: str | None


@router.get("/list", response_model=list[FileEntry])
async def list_directory(path: str = Query(default="")):
    """List directory contents at /mnt/media/{path}."""
    target = _safe_path(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    entries: list[FileEntry] = []
    try:
        items = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    for item in items:
        try:
            stat = item.stat()
            rel = str(item.relative_to(MEDIA_ROOT))
            mime = None if item.is_dir() else (mimetypes.guess_type(item.name)[0])
            entries.append(FileEntry(
                name=item.name,
                path=rel,
                is_dir=item.is_dir(),
                size=None if item.is_dir() else stat.st_size,
                modified=stat.st_mtime,
                mime=mime,
            ))
        except (PermissionError, OSError):
            continue  # skip unreadable entries

    return entries


@router.get("/download")
async def download_file(path: str = Query(...)):
    """Download a file from /mnt/media/{path}."""
    target = _safe_path(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if not target.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")
    return FileResponse(
        path=str(target),
        filename=target.name,
        media_type=mimetypes.guess_type(target.name)[0] or "application/octet-stream",
    )


@router.post("/upload")
async def upload_file(
    path: str = Query(default=""),
    file: UploadFile = File(...),
):
    """Upload a file into /mnt/media/{path}/."""
    target_dir = _safe_path(path)
    if not target_dir.exists():
        raise HTTPException(status_code=404, detail="Target directory not found")
    if not target_dir.is_dir():
        raise HTTPException(status_code=400, detail="Target path is not a directory")

    # Sanitise filename
    filename = Path(file.filename or "upload").name
    if not filename or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")

    dest = target_dir / filename
    try:
        content = await file.read()
        dest.write_bytes(content)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    rel = str(dest.relative_to(MEDIA_ROOT))
    return {"path": rel, "name": filename, "size": len(content)}


@router.get("/read")
async def read_file(
    path: str = Query(...),
    root: Literal["media", "absolute"] = Query(default="media"),
):
    """
    Read a text file and return its content for editing.

    - root="media"    — path is relative to /mnt/media (default)
    - root="absolute" — path is absolute, restricted to allowed directories
    """
    target, display = _resolve_path(path, root)

    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if not target.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    stat = target.stat()

    if stat.st_size > MAX_READ_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large to edit ({stat.st_size} bytes; max {MAX_READ_SIZE})",
        )

    if _is_binary(target):
        raise HTTPException(status_code=400, detail="Binary file cannot be edited")

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Read error: {exc}")

    return {
        "content": content,
        "path": display,
        "language": _detect_language(target),
        "size": stat.st_size,
        "readonly": not os.access(target, os.W_OK),
    }


@router.put("/write")
async def write_file(body: WriteRequest):
    """
    Write text content to a file, creating parent directories as needed.

    - root="media"    — path is relative to /mnt/media (default)
    - root="absolute" — path is absolute, restricted to allowed directories
    """
    target, display = _resolve_path(body.path, body.root)

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body.content, encoding="utf-8")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Write error: {exc}")

    return {"path": display, "size": target.stat().st_size, "message": "File saved"}


@router.post("/create")
async def create_file_or_dir(body: CreateRequest):
    """
    Create a new empty file or directory.

    - root="media"    — path is relative to /mnt/media (default)
    - root="absolute" — path is absolute, restricted to allowed directories
    """
    target, display = _resolve_path(body.path, body.root)

    if target.exists():
        raise HTTPException(
            status_code=409,
            detail=f"{'Directory' if body.is_dir else 'File'} already exists",
        )

    try:
        if body.is_dir:
            target.mkdir(parents=True, exist_ok=False)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch()
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Create error: {exc}")

    kind = "Directory" if body.is_dir else "File"
    return {"path": display, "message": f"{kind} created"}


class AIEditRequest(BaseModel):
    path: str
    content: str
    instruction: str
    root: Literal["media", "absolute"] = "media"


@router.post("/ai-edit")
async def ai_edit_file(body: AIEditRequest):
    """Use LLM to edit file content based on a natural language instruction.

    Returns the modified content and an explanation of changes.
    """
    import google.generativeai as genai
    from ..config import settings

    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="AI editing unavailable — no API key configured")

    if len(body.content) > MAX_READ_SIZE:
        raise HTTPException(status_code=400, detail="File content too large for AI editing")

    # Detect language for context
    try:
        target, _ = _resolve_path(body.path, body.root)
        lang = _detect_language(target)
    except Exception:
        lang = "plaintext"

    filename = body.path.split("/")[-1] if "/" in body.path else body.path

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""You are a code editor assistant. The user has a file open and wants you to modify it.

FILE: {filename}
LANGUAGE: {lang}

CURRENT CONTENT:
```{lang}
{body.content}
```

USER INSTRUCTION: {body.instruction}

Respond with EXACTLY this JSON format (no markdown fencing, just raw JSON):
{{
  "explanation": "Brief description of what you changed",
  "modified_content": "The complete modified file content"
}}

Rules:
- Return the COMPLETE file content, not just the changed parts
- Make only the changes requested — do not add unsolicited improvements
- Preserve existing code style, indentation, and formatting
- If the instruction is unclear, make your best interpretation and explain in the explanation"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Strip markdown fencing if present
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]  # remove opening fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]  # remove closing fence
            text = "\n".join(lines)

        import json
        result = json.loads(text)

        return {
            "explanation": result.get("explanation", "Changes applied"),
            "modified_content": result.get("modified_content", body.content),
        }
    except json.JSONDecodeError:
        log.warning("AI edit returned non-JSON response, attempting to extract content")
        # If the LLM didn't return valid JSON, return the raw text as explanation
        return {
            "explanation": "I processed your request but couldn't structure the response properly. Please try again with a more specific instruction.",
            "modified_content": None,
        }
    except Exception as exc:
        log.error(f"AI edit failed: {exc}")
        raise HTTPException(status_code=500, detail=f"AI edit failed: {exc}")
