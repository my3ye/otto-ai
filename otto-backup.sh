#!/usr/bin/env bash
# otto-backup.sh — One-command full backup of Otto's state
# Creates a timestamped archive ready for restore/clone on a fresh VM
#
# Usage: ./otto-backup.sh [output_dir]
# Output: /mnt/media/backups/otto-backup-YYYYMMDD-HHMMSS.tar.gz
# Restore: ./otto-restore.sh <archive>

set -euo pipefail

# ── Config ──────────────────────────────────────────────────────────────────
USER="${SUDO_USER:-web3relic}"
HOME_DIR="/home/${USER}"
OTTO_DIR="${HOME_DIR}/otto"
MEMORY_DIR="${HOME_DIR}/memory"
INTERFACES_DIR="${HOME_DIR}/interfaces"
OUTPUT_BASE="${1:-/mnt/media/backups}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
ARCHIVE_NAME="otto-backup-${TIMESTAMP}.tar.gz"
ARCHIVE_PATH="${OUTPUT_BASE}/${ARCHIVE_NAME}"
WORK_DIR=$(mktemp -d /tmp/otto-backup-XXXXXX)

# ── Helpers ──────────────────────────────────────────────────────────────────
log()  { echo "[$(date '+%H:%M:%S')] $*"; }
warn() { echo "[$(date '+%H:%M:%S')] WARN: $*" >&2; }
die()  { echo "[$(date '+%H:%M:%S')] ERROR: $*" >&2; exit 1; }

cleanup() { rm -rf "${WORK_DIR}"; }
trap cleanup EXIT

log "Otto Backup — ${TIMESTAMP}"
log "Staging to: ${WORK_DIR}"
log "Output:     ${ARCHIVE_PATH}"

mkdir -p "${OUTPUT_BASE}"
mkdir -p \
  "${WORK_DIR}/otto" \
  "${WORK_DIR}/memory" \
  "${WORK_DIR}/interfaces" \
  "${WORK_DIR}/systemd" \
  "${WORK_DIR}/docker-volumes" \
  "${WORK_DIR}/system"

# ── 1. Otto agent core ────────────────────────────────────────────────────────
log "[1/8] Backing up ~/otto ..."
# Use tar + extract to support exclusions without rsync
# Allow exit 1 (file-changed-as-we-read-it warnings) — non-fatal
tar -C "${HOME_DIR}" \
  --exclude='otto/logs/*.log' \
  --exclude='otto/logs/tasks/*.log' \
  --exclude='otto/__pycache__' \
  --exclude='otto/*.pyc' \
  --exclude='otto/.venv' \
  --exclude='otto/node_modules' \
  -cf - otto 2>/dev/null | tar -xf - -C "${WORK_DIR}/" || true

# ── 2. Memory infrastructure config ──────────────────────────────────────────
log "[2/8] Backing up ~/memory config ..."
cp "${MEMORY_DIR}/.env" "${WORK_DIR}/memory/.env"
cp "${MEMORY_DIR}/docker-compose.yml" "${WORK_DIR}/memory/docker-compose.yml"
[[ -f "${MEMORY_DIR}/docker-compose.yml.bak" ]] && \
  cp "${MEMORY_DIR}/docker-compose.yml.bak" "${WORK_DIR}/memory/docker-compose.yml.bak"
[[ -f "${MEMORY_DIR}/cdp_api_key.json" ]] && \
  cp "${MEMORY_DIR}/cdp_api_key.json" "${WORK_DIR}/memory/cdp_api_key.json"
[[ -d "${MEMORY_DIR}/init-db" ]] && \
  cp -r "${MEMORY_DIR}/init-db" "${WORK_DIR}/memory/init-db"

# ── 3. WhatsApp session ───────────────────────────────────────────────────────
log "[3/8] Backing up WhatsApp auth state ..."
if [[ -d "${INTERFACES_DIR}/whatsapp/auth_state" ]]; then
  mkdir -p "${WORK_DIR}/interfaces/whatsapp"
  cp -r "${INTERFACES_DIR}/whatsapp/auth_state" "${WORK_DIR}/interfaces/whatsapp/"
  cp "${INTERFACES_DIR}/whatsapp/package.json" "${WORK_DIR}/interfaces/whatsapp/" 2>/dev/null || true
  cp "${INTERFACES_DIR}/whatsapp/service.mjs"  "${WORK_DIR}/interfaces/whatsapp/" 2>/dev/null || true
  cp "${INTERFACES_DIR}/whatsapp/login.mjs"    "${WORK_DIR}/interfaces/whatsapp/" 2>/dev/null || true
else
  warn "No WhatsApp auth_state found — skipping"
fi

# ── 4. Web-next (OMS) interface ───────────────────────────────────────────────
log "[4/8] Backing up ~/interfaces/web-next ..."
if [[ -d "${INTERFACES_DIR}/web-next" ]]; then
  mkdir -p "${WORK_DIR}/interfaces"
  tar -C "${INTERFACES_DIR}" \
    --exclude='web-next/node_modules' \
    --exclude='web-next/.next' \
    --exclude='web-next/out' \
    -cf - web-next | tar -xf - -C "${WORK_DIR}/interfaces/"
else
  warn "~/interfaces/web-next not found — skipping"
fi

# ── 5. Systemd units ──────────────────────────────────────────────────────────
log "[5/8] Backing up systemd units ..."
for f in /etc/systemd/system/otto-*.service /etc/systemd/system/otto-*.timer; do
  [[ -f "$f" ]] && cp "$f" "${WORK_DIR}/systemd/"
done
# Also capture whatsapp and service-monitor units if present
for f in /etc/systemd/system/whatsapp.service \
          /etc/systemd/system/service-monitor.service \
          /etc/systemd/system/service-monitor.timer; do
  [[ -f "$f" ]] && cp "$f" "${WORK_DIR}/systemd/"
done

# ── 6. Docker volume dumps ────────────────────────────────────────────────────
log "[6/8] Dumping Docker volumes ..."

dump_volume() {
  local vol="$1" name="$2"
  if docker volume inspect "${vol}" &>/dev/null; then
    log "  Dumping volume: ${vol}"
    docker run --rm -v "${vol}:/data:ro" -v "${WORK_DIR}/docker-volumes:/backup" \
      debian:bookworm-slim \
      tar czf "/backup/${name}.tar.gz" -C /data . 2>/dev/null && \
      log "  Done: ${name}.tar.gz" || warn "  Failed to dump ${vol}"
  else
    warn "  Volume not found: ${vol}"
  fi
}

dump_volume "memory_postgres_data" "postgres_data"
dump_volume "memory_neo4j_data"    "neo4j_data"

# ── 7. PostgreSQL SQL dump (portable backup) ──────────────────────────────────
log "[7/8] Creating PostgreSQL SQL dump ..."
if docker ps --format '{{.Names}}' | grep -q "memory-postgres"; then
  docker exec memory-postgres-1 pg_dumpall -U otto 2>/dev/null \
    > "${WORK_DIR}/docker-volumes/postgres_dump.sql" && \
    gzip "${WORK_DIR}/docker-volumes/postgres_dump.sql" && \
    log "  postgres_dump.sql.gz created" || \
    warn "  PostgreSQL dump failed"
else
  warn "  memory-postgres-1 not running — skipping SQL dump"
fi

# ── 8. System manifest ────────────────────────────────────────────────────────
log "[8/8] Writing system manifest ..."
{
  echo "# Otto Backup Manifest"
  echo "timestamp: ${TIMESTAMP}"
  echo "hostname: $(hostname)"
  echo "os: $(cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '"')"
  echo "kernel: $(uname -r)"
  echo "user: ${USER}"
  echo "---"
  echo "# Installed packages (apt)"
  dpkg --get-selections 2>/dev/null
} > "${WORK_DIR}/system/manifest.txt"

# Capture pip packages per venv
for venv in "${OTTO_DIR}"/.venv "${INTERFACES_DIR}"/.venv; do
  [[ -f "${venv}/bin/pip" ]] && \
    "${venv}/bin/pip" freeze > "${WORK_DIR}/system/pip-$(basename $(dirname ${venv})).txt" 2>/dev/null || true
done

# ── Write restore instructions ────────────────────────────────────────────────
cat > "${WORK_DIR}/RESTORE.md" << 'RESTORE_EOF'
# Otto Restore / Clone Instructions

## Prerequisites on target VM
- Debian 12
- User: web3relic (with sudo)
- Docker Engine installed
- Git installed

## Steps
1. Copy archive to target VM:
   scp otto-backup-*.tar.gz web3relic@<TARGET>:~/

2. On target VM:
   tar xzf otto-backup-*.tar.gz
   sudo bash otto-restore.sh ./otto-backup-*/

3. Authenticate services manually:
   - WhatsApp: if auth_state restored, it may reconnect automatically
   - GitHub: gh auth login
   - Anthropic: ensure ANTHROPIC_API_KEY in memory/.env is valid
   - Claude Code: claude (login prompt if needed)
RESTORE_EOF

# ── Final archive ─────────────────────────────────────────────────────────────
log "Creating archive: ${ARCHIVE_PATH}"
tar czf "${ARCHIVE_PATH}" -C "$(dirname ${WORK_DIR})" "$(basename ${WORK_DIR})"

ARCHIVE_SIZE=$(du -sh "${ARCHIVE_PATH}" | cut -f1)
log ""
log "✓ Backup complete!"
log "  Archive: ${ARCHIVE_PATH}"
log "  Size:    ${ARCHIVE_SIZE}"
log "  Restore: ./otto-restore.sh ${ARCHIVE_PATH}"
