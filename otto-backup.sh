#!/usr/bin/env bash
# otto-backup.sh — Full encrypted backup of Otto's entire state
# Creates a timestamped, GPG-encrypted archive ready for restore on a fresh VM
#
# Usage: ./otto-backup.sh [output_dir]
# Output: /mnt/media/backups/otto-backup-YYYYMMDD-HHMMSS.tar.gz.gpg
# Restore: ./otto-restore.sh <archive.tar.gz.gpg>
#
# Encryption: AES-256 via GPG symmetric. Passphrase stored in ~/memory/.backup-key
# If the key file doesn't exist, one is generated and displayed.

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
ENCRYPTED_NAME="${ARCHIVE_NAME}.gpg"
ARCHIVE_PATH="${OUTPUT_BASE}/${ARCHIVE_NAME}"
ENCRYPTED_PATH="${OUTPUT_BASE}/${ENCRYPTED_NAME}"
KEY_FILE="${MEMORY_DIR}/.backup-key"
WORK_DIR=$(mktemp -d /tmp/otto-backup-XXXXXX)

# ── Helpers ──────────────────────────────────────────────────────────────────
log()  { echo "[$(date '+%H:%M:%S')] $*"; }
warn() { echo "[$(date '+%H:%M:%S')] WARN: $*" >&2; }
die()  { echo "[$(date '+%H:%M:%S')] ERROR: $*" >&2; exit 1; }

cleanup() { rm -rf "${WORK_DIR}"; rm -f "${ARCHIVE_PATH}"; }
trap cleanup EXIT

log "Otto Backup — ${TIMESTAMP}"
log "Staging to: ${WORK_DIR}"

mkdir -p "${OUTPUT_BASE}"
mkdir -p \
  "${WORK_DIR}/otto" \
  "${WORK_DIR}/memory" \
  "${WORK_DIR}/interfaces" \
  "${WORK_DIR}/systemd" \
  "${WORK_DIR}/docker-volumes" \
  "${WORK_DIR}/system" \
  "${WORK_DIR}/nginx" \
  "${WORK_DIR}/ssh" \
  "${WORK_DIR}/claude" \
  "${WORK_DIR}/projects-manifest"

# ── Encryption key ──────────────────────────────────────────────────────────
if [[ ! -f "${KEY_FILE}" ]]; then
  PASSPHRASE=$(openssl rand -base64 32)
  echo "${PASSPHRASE}" > "${KEY_FILE}"
  chmod 600 "${KEY_FILE}"
  chown "${USER}:${USER}" "${KEY_FILE}" 2>/dev/null || true
  log ""
  log "╔══════════════════════════════════════════════════════════════╗"
  log "║  NEW BACKUP ENCRYPTION KEY GENERATED                        ║"
  log "║  Stored at: ${KEY_FILE}"
  log "║                                                              ║"
  log "║  Key: ${PASSPHRASE}"
  log "║                                                              ║"
  log "║  SAVE THIS KEY SOMEWHERE SAFE (password manager, etc.)       ║"
  log "║  You need it to restore backups. Lost key = lost backup.     ║"
  log "╚══════════════════════════════════════════════════════════════╝"
  log ""
else
  PASSPHRASE=$(cat "${KEY_FILE}")
  log "Using existing backup key from ${KEY_FILE}"
fi

# ── 1. Otto agent core ────────────────────────────────────────────────────
log "[1/13] Backing up ~/otto ..."
tar -C "${HOME_DIR}" \
  --exclude='otto/logs/*.log' \
  --exclude='otto/logs/tasks/*.log' \
  --exclude='otto/__pycache__' \
  --exclude='otto/**/__pycache__' \
  --exclude='otto/*.pyc' \
  --exclude='otto/.venv' \
  --exclude='otto/node_modules' \
  --exclude='otto/memory/.venv' \
  -cf - otto 2>/dev/null | tar -xf - -C "${WORK_DIR}/" || true

# ── 2. Memory infrastructure config ────────────────────────────────────────
log "[2/13] Backing up ~/memory config ..."
cp "${MEMORY_DIR}/.env" "${WORK_DIR}/memory/.env"
cp "${MEMORY_DIR}/docker-compose.yml" "${WORK_DIR}/memory/docker-compose.yml"
[[ -f "${MEMORY_DIR}/docker-compose.yml.bak" ]] && \
  cp "${MEMORY_DIR}/docker-compose.yml.bak" "${WORK_DIR}/memory/docker-compose.yml.bak"
[[ -f "${MEMORY_DIR}/cdp_api_key.json" ]] && \
  cp "${MEMORY_DIR}/cdp_api_key.json" "${WORK_DIR}/memory/cdp_api_key.json"
[[ -d "${MEMORY_DIR}/init-db" ]] && \
  cp -r "${MEMORY_DIR}/init-db" "${WORK_DIR}/memory/init-db"
# Backup key itself (so restore can decrypt future backups with same key)
cp "${KEY_FILE}" "${WORK_DIR}/memory/.backup-key"

# ── 3. WhatsApp session + service ──────────────────────────────────────────
log "[3/13] Backing up WhatsApp interface ..."
if [[ -d "${INTERFACES_DIR}/whatsapp" ]]; then
  mkdir -p "${WORK_DIR}/interfaces/whatsapp"
  cp -r "${INTERFACES_DIR}/whatsapp/auth_state" "${WORK_DIR}/interfaces/whatsapp/" 2>/dev/null || true
  cp "${INTERFACES_DIR}/whatsapp/package.json" "${WORK_DIR}/interfaces/whatsapp/" 2>/dev/null || true
  cp "${INTERFACES_DIR}/whatsapp/service.mjs"  "${WORK_DIR}/interfaces/whatsapp/" 2>/dev/null || true
  cp "${INTERFACES_DIR}/whatsapp/login.mjs"    "${WORK_DIR}/interfaces/whatsapp/" 2>/dev/null || true
else
  warn "No WhatsApp interface found"
fi

# ── 4. Email interface ───────────────────────────────────────────────────────
log "[4/13] Backing up email interface ..."
if [[ -d "${INTERFACES_DIR}/email" ]]; then
  mkdir -p "${WORK_DIR}/interfaces/email"
  cp "${INTERFACES_DIR}/email/"*.py "${WORK_DIR}/interfaces/email/" 2>/dev/null || true
  cp "${INTERFACES_DIR}/email/"*.md "${WORK_DIR}/interfaces/email/" 2>/dev/null || true
  cp "${INTERFACES_DIR}/email/"*.yml "${WORK_DIR}/interfaces/email/" 2>/dev/null || true
  cp "${INTERFACES_DIR}/email/"*.env "${WORK_DIR}/interfaces/email/" 2>/dev/null || true
else
  warn "No email interface found"
fi

# ── 5. Web-next (OMS) interface ──────────────────────────────────────────────
log "[5/13] Backing up ~/interfaces/web-next ..."
if [[ -d "${INTERFACES_DIR}/web-next" ]]; then
  mkdir -p "${WORK_DIR}/interfaces"
  tar -C "${INTERFACES_DIR}" \
    --exclude='web-next/node_modules' \
    --exclude='web-next/.next' \
    --exclude='web-next/out' \
    --exclude='web-next/out.bak' \
    -cf - web-next | tar -xf - -C "${WORK_DIR}/interfaces/"
else
  warn "~/interfaces/web-next not found"
fi

# ── 6. Nginx configs ────────────────────────────────────────────────────────
log "[6/13] Backing up nginx configs ..."
if [[ -d /etc/nginx ]]; then
  cp /etc/nginx/nginx.conf "${WORK_DIR}/nginx/" 2>/dev/null || true
  cp -r /etc/nginx/sites-available "${WORK_DIR}/nginx/sites-available" 2>/dev/null || true
  cp -r /etc/nginx/sites-enabled "${WORK_DIR}/nginx/sites-enabled" 2>/dev/null || true
  # SSL certs (Let's Encrypt)
  if [[ -d /etc/letsencrypt ]]; then
    tar -C /etc -cf - letsencrypt 2>/dev/null | tar -xf - -C "${WORK_DIR}/nginx/" || true
    log "  SSL certificates included"
  fi
else
  warn "No nginx found"
fi

# ── 7. SSH keys ──────────────────────────────────────────────────────────────
log "[7/13] Backing up SSH keys ..."
if [[ -d "${HOME_DIR}/.ssh" ]]; then
  cp -r "${HOME_DIR}/.ssh" "${WORK_DIR}/ssh/dot-ssh"
  chmod 700 "${WORK_DIR}/ssh/dot-ssh"
  chmod 600 "${WORK_DIR}/ssh/dot-ssh/"* 2>/dev/null || true
else
  warn "No SSH keys found"
fi

# ── 8. Claude Code config ────────────────────────────────────────────────────
log "[8/13] Backing up Claude Code config ..."
if [[ -d "${HOME_DIR}/.claude" ]]; then
  # Copy settings, credentials, project configs — skip large caches
  mkdir -p "${WORK_DIR}/claude/dot-claude"
  cp "${HOME_DIR}/.claude/"*.json "${WORK_DIR}/claude/dot-claude/" 2>/dev/null || true
  [[ -d "${HOME_DIR}/.claude/projects" ]] && \
    cp -r "${HOME_DIR}/.claude/projects" "${WORK_DIR}/claude/dot-claude/projects" 2>/dev/null || true
  [[ -d "${HOME_DIR}/.claude/agent-memory" ]] && \
    cp -r "${HOME_DIR}/.claude/agent-memory" "${WORK_DIR}/claude/dot-claude/agent-memory" 2>/dev/null || true
fi
# Git global config
cp "${HOME_DIR}/.gitconfig" "${WORK_DIR}/claude/" 2>/dev/null || true

# ── 9. Systemd units ────────────────────────────────────────────────────────
log "[9/13] Backing up systemd units ..."
for f in /etc/systemd/system/otto-*.service /etc/systemd/system/otto-*.timer; do
  [[ -f "$f" ]] && cp "$f" "${WORK_DIR}/systemd/"
done
for f in /etc/systemd/system/whatsapp.service \
          /etc/systemd/system/service-monitor.service \
          /etc/systemd/system/service-monitor.timer; do
  [[ -f "$f" ]] && cp "$f" "${WORK_DIR}/systemd/"
done

# ── 10. Docker volume dumps ──────────────────────────────────────────────────
log "[10/13] Dumping Docker volumes ..."

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

# ── 11. PostgreSQL SQL dump ──────────────────────────────────────────────────
log "[11/13] Creating PostgreSQL SQL dump ..."
if docker ps --format '{{.Names}}' | grep -q "memory-postgres"; then
  docker exec memory-postgres-1 pg_dumpall -U otto 2>/dev/null \
    > "${WORK_DIR}/docker-volumes/postgres_dump.sql" && \
    gzip "${WORK_DIR}/docker-volumes/postgres_dump.sql" && \
    log "  postgres_dump.sql.gz created" || \
    warn "  PostgreSQL dump failed"
else
  warn "  memory-postgres-1 not running — skipping SQL dump"
fi

# ── 12. Project repos manifest ───────────────────────────────────────────────
log "[12/13] Creating project repos manifest ..."
PROJECTS_DIR="/mnt/media/projects"
if [[ -d "${PROJECTS_DIR}" ]]; then
  for repo in "${PROJECTS_DIR}"/*/; do
    repo_name=$(basename "${repo}")
    if [[ -d "${repo}/.git" ]]; then
      remote=$(git -C "${repo}" remote get-url origin 2>/dev/null || echo "no-remote")
      branch=$(git -C "${repo}" branch --show-current 2>/dev/null || echo "unknown")
      echo "${repo_name}|${remote}|${branch}" >> "${WORK_DIR}/projects-manifest/repos.txt"
    fi
  done
  log "  $(wc -l < "${WORK_DIR}/projects-manifest/repos.txt" 2>/dev/null || echo 0) repos catalogued"
else
  warn "  /mnt/media/projects not found"
fi

# ── 13. System manifest ──────────────────────────────────────────────────────
log "[13/13] Writing system manifest ..."
{
  echo "# Otto Backup Manifest"
  echo "timestamp: ${TIMESTAMP}"
  echo "hostname: $(hostname)"
  echo "os: $(cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '"')"
  echo "kernel: $(uname -r)"
  echo "user: ${USER}"
  echo "node: $(node --version 2>/dev/null || echo 'not installed')"
  echo "python: $(python3 --version 2>/dev/null || echo 'not installed')"
  echo "docker: $(docker --version 2>/dev/null || echo 'not installed')"
  echo "---"
  echo "# Installed packages (apt)"
  dpkg --get-selections 2>/dev/null
} > "${WORK_DIR}/system/manifest.txt"

# Capture pip packages per venv
for venv in "${OTTO_DIR}/memory/.venv" "${INTERFACES_DIR}/.venv"; do
  [[ -f "${venv}/bin/pip" ]] && \
    "${venv}/bin/pip" freeze > "${WORK_DIR}/system/pip-$(basename $(dirname ${venv})).txt" 2>/dev/null || true
done

# ── Write restore instructions ──────────────────────────────────────────────
cat > "${WORK_DIR}/RESTORE.md" << 'RESTORE_EOF'
# Otto Restore / Clone Instructions

## Prerequisites on target VM
- Debian 12
- User: web3relic (with sudo)
- Docker Engine installed
- Git installed

## Steps
1. Copy encrypted archive + key to target VM:
   scp otto-backup-*.tar.gz.gpg web3relic@<TARGET>:~/

2. Decrypt (you need the backup key from ~/memory/.backup-key):
   gpg --batch --yes --passphrase "YOUR_KEY" -d otto-backup-*.tar.gz.gpg > otto-backup.tar.gz

3. On target VM:
   sudo bash otto-restore.sh otto-backup.tar.gz

4. Authenticate services manually:
   - WhatsApp: may reconnect automatically or need QR scan
   - GitHub: gh auth login (for each account)
   - Claude Code: claude (login if needed)

5. Verify: bash otto-env-check.sh --human
RESTORE_EOF

# ── Create archive ──────────────────────────────────────────────────────────
log "Creating archive ..."
tar czf "${ARCHIVE_PATH}" -C "$(dirname ${WORK_DIR})" "$(basename ${WORK_DIR})"

UNENCRYPTED_SIZE=$(du -sh "${ARCHIVE_PATH}" | cut -f1)

# ── Encrypt ──────────────────────────────────────────────────────────────────
log "Encrypting with AES-256 ..."
gpg --batch --yes --symmetric --cipher-algo AES256 \
  --passphrase "${PASSPHRASE}" \
  --output "${ENCRYPTED_PATH}" \
  "${ARCHIVE_PATH}"

# Remove unencrypted archive (cleanup trap will also try, but be explicit)
rm -f "${ARCHIVE_PATH}"

ENCRYPTED_SIZE=$(du -sh "${ENCRYPTED_PATH}" | cut -f1)

log ""
log "╔══════════════════════════════════════════════════════════════╗"
log "║  Backup complete!                                            ║"
log "╠══════════════════════════════════════════════════════════════╣"
log "║  Archive:  ${ENCRYPTED_PATH}"
log "║  Size:     ${ENCRYPTED_SIZE} (uncompressed: ${UNENCRYPTED_SIZE})"
log "║  Encrypted: AES-256 (GPG symmetric)                          ║"
log "║  Key file: ${KEY_FILE}"
log "║                                                              ║"
log "║  Contents:                                                   ║"
log "║    ~/otto (agent core, API, agents, tools)                   ║"
log "║    ~/memory (.env, docker-compose, init-db, backup key)      ║"
log "║    ~/interfaces (whatsapp, email, web-next OMS)              ║"
log "║    Nginx configs + SSL certs                                 ║"
log "║    SSH keys                                                  ║"
log "║    Claude Code config + credentials                          ║"
log "║    Systemd units (services + timers)                         ║"
log "║    Docker volumes (Postgres + Neo4j)                         ║"
log "║    PostgreSQL SQL dump (fallback)                            ║"
log "║    Git config + project repos manifest                       ║"
log "║    System manifest (packages, versions)                      ║"
log "╠══════════════════════════════════════════════════════════════╣"
log "║  Restore: sudo bash otto-restore.sh ${ENCRYPTED_NAME}"
log "╚══════════════════════════════════════════════════════════════╝"
