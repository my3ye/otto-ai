"""File manager routes — browse/upload/download files on /mnt/media."""
import os
import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter(prefix="/files", tags=["files"])

MEDIA_ROOT = Path("/mnt/media")


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
