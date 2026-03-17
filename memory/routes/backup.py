"""
System Backup / Restore — /backup routes

Provides:
  GET  /backup/list        — list all backup archives on disk
  POST /backup/run         — trigger otto-backup.sh as a background process
  GET  /backup/status      — is a backup currently running?
  GET  /backup/instructions — return restore instructions as text
  GET  /backup/env-check   — run new-environment auth checklist
"""

import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

log = logging.getLogger("otto.backup")
router = APIRouter(prefix="/backup", tags=["backup"])

BACKUP_DIR = Path("/mnt/media/backups")
BACKUP_SCRIPT = Path("/home/web3relic/otto/otto-backup.sh")
RESTORE_SCRIPT = Path("/home/web3relic/otto/otto-restore.sh")
LOCK_FILE = Path("/tmp/otto-backup.lock")
ENV_CHECK_SCRIPT = Path("/home/web3relic/otto/otto-env-check.sh")


# ── Models ─────────────────────────────────────────────────────────────────

class BackupEntry(BaseModel):
    filename: str
    path: str
    size_bytes: int
    size_human: str
    created_at: str  # ISO8601


class BackupListResponse(BaseModel):
    backups: list[BackupEntry]
    count: int
    backup_dir: str


class BackupStatusResponse(BaseModel):
    running: bool
    pid: int | None = None
    started_at: str | None = None


class BackupRunResponse(BaseModel):
    status: str
    message: str
    pid: int | None = None


class BackupInstructionsResponse(BaseModel):
    script_path: str
    restore_script_path: str
    backup_dir: str
    run_backup_command: str
    run_restore_command: str
    steps: list[str]


# ── Helpers ────────────────────────────────────────────────────────────────

def _human_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def _get_running_backup() -> tuple[bool, int | None, str | None]:
    """Return (is_running, pid, started_at) from lock file."""
    if not LOCK_FILE.exists():
        return False, None, None
    try:
        contents = LOCK_FILE.read_text().strip().splitlines()
        pid = int(contents[0]) if contents else None
        started_at = contents[1] if len(contents) > 1 else None
        # Verify the process is actually alive
        if pid and not _pid_alive(pid):
            LOCK_FILE.unlink(missing_ok=True)
            return False, None, None
        return True, pid, started_at
    except Exception:
        return False, None, None


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/list", response_model=BackupListResponse)
async def list_backups():
    """List all backup archives found in the backup directory."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    entries: list[BackupEntry] = []

    for entry in sorted(BACKUP_DIR.iterdir(), reverse=True):
        if entry.name.startswith("otto-backup-") and entry.name.endswith(".tar.gz"):
            stat = entry.stat()
            created_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            entries.append(BackupEntry(
                filename=entry.name,
                path=str(entry),
                size_bytes=stat.st_size,
                size_human=_human_size(stat.st_size),
                created_at=created_at,
            ))

    return BackupListResponse(
        backups=entries,
        count=len(entries),
        backup_dir=str(BACKUP_DIR),
    )


@router.get("/status", response_model=BackupStatusResponse)
async def backup_status():
    """Check whether a backup is currently running."""
    running, pid, started_at = _get_running_backup()
    return BackupStatusResponse(running=running, pid=pid, started_at=started_at)


@router.post("/run", response_model=BackupRunResponse)
async def run_backup():
    """Trigger otto-backup.sh as a background process. Only one backup may run at a time."""
    if not BACKUP_SCRIPT.exists():
        raise HTTPException(status_code=500, detail=f"Backup script not found: {BACKUP_SCRIPT}")

    running, pid, _ = _get_running_backup()
    if running:
        return BackupRunResponse(
            status="already_running",
            message=f"A backup is already running (PID {pid}). Wait for it to complete.",
            pid=pid,
        )

    # Launch backup as detached background process
    log.info("Triggering otto-backup.sh")
    started_at = datetime.now(tz=timezone.utc).isoformat()
    try:
        proc = subprocess.Popen(
            ["bash", str(BACKUP_SCRIPT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # detach from this process group
        )
        pid = proc.pid
        # Write lock file with pid + start time
        LOCK_FILE.write_text(f"{pid}\n{started_at}\n")
        log.info(f"Backup started — PID {pid}")
        return BackupRunResponse(
            status="started",
            message=f"Backup started in background (PID {pid}). Check /backup/list when done.",
            pid=pid,
        )
    except Exception as e:
        log.error(f"Failed to start backup: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start backup: {e}")


@router.get("/instructions", response_model=BackupInstructionsResponse)
async def backup_instructions():
    """Return backup/restore instructions and script paths."""
    return BackupInstructionsResponse(
        script_path=str(BACKUP_SCRIPT),
        restore_script_path=str(RESTORE_SCRIPT),
        backup_dir=str(BACKUP_DIR),
        run_backup_command="bash /home/web3relic/otto/otto-backup.sh",
        run_restore_command="sudo bash /home/web3relic/otto/otto-restore.sh <archive.tar.gz>",
        steps=[
            "Run backup: bash /home/web3relic/otto/otto-backup.sh",
            "Archive saved to: /mnt/media/backups/otto-backup-YYYYMMDD-HHMMSS.tar.gz",
            "Copy to target VM: scp otto-backup-*.tar.gz web3relic@<TARGET>:~/",
            "On target VM — extract & restore: sudo bash otto-restore.sh otto-backup-*.tar.gz",
            "Run env-check after restore: bash /home/web3relic/otto/otto-env-check.sh --human",
            "OMS env checklist: mev.otto.lk/environment",
        ],
    )


# ── Env Check ──────────────────────────────────────────────────────────────

class EnvCheckItem(BaseModel):
    name: str
    status: str  # "pass" | "fail" | "warn"
    detail: str


class EnvCheckResponse(BaseModel):
    overall: str  # "pass" | "fail" | "warn"
    pass_count: int
    fail_count: int
    warn_count: int
    total_count: int
    is_restored: bool
    checks: list[EnvCheckItem]
    ran_at: str


@router.get("/env-check", response_model=EnvCheckResponse)
async def env_check():
    """
    Run the new-environment auth checklist (otto-env-check.sh).
    Returns structured pass/fail/warn results for each auth service.
    """
    if not ENV_CHECK_SCRIPT.exists():
        raise HTTPException(status_code=500, detail=f"Env check script not found: {ENV_CHECK_SCRIPT}")

    try:
        result = subprocess.run(
            ["bash", str(ENV_CHECK_SCRIPT), "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Script exits 1 on failures — that's fine, we still parse JSON
        data: dict[str, Any] = json.loads(result.stdout)
        checks = [EnvCheckItem(**c) for c in data.get("checks", [])]
        return EnvCheckResponse(
            overall=data.get("overall", "fail"),
            pass_count=data.get("pass_count", 0),
            fail_count=data.get("fail_count", 0),
            warn_count=data.get("warn_count", 0),
            total_count=data.get("total_count", 0),
            is_restored=data.get("is_restored", False),
            checks=checks,
            ran_at=datetime.now(tz=timezone.utc).isoformat(),
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Env check timed out (30s)")
    except json.JSONDecodeError as e:
        log.error(f"Env check JSON parse error: {e}\nOutput: {result.stdout[:500]}")
        raise HTTPException(status_code=500, detail=f"Failed to parse env check output: {e}")
    except Exception as e:
        log.error(f"Env check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Env check failed: {e}")
