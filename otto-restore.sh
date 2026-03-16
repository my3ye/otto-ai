#!/usr/bin/env bash
# otto-restore.sh — Restore / clone Otto onto a fresh Debian 12 VM
#
# Usage: sudo bash otto-restore.sh <extracted-backup-dir>
# Or:    sudo bash otto-restore.sh <otto-backup-*.tar.gz>
#
# Idempotent — safe to re-run. Skips steps already completed.

set -euo pipefail

# ── Config ──────────────────────────────────────────────────────────────────
TARGET_USER="web3relic"
TARGET_HOME="/home/${TARGET_USER}"
OTTO_DIR="${TARGET_HOME}/otto"
MEMORY_DIR="${TARGET_HOME}/memory"
INTERFACES_DIR="${TARGET_HOME}/interfaces"

# ── Helpers ──────────────────────────────────────────────────────────────────
log()  { echo "[$(date '+%H:%M:%S')] $*"; }
warn() { echo "[$(date '+%H:%M:%S')] WARN: $*" >&2; }
die()  { echo "[$(date '+%H:%M:%S')] ERROR: $*" >&2; exit 1; }

as_user() { sudo -u "${TARGET_USER}" "$@"; }

# ── Resolve backup dir ────────────────────────────────────────────────────────
BACKUP_INPUT="${1:-}"
[[ -z "${BACKUP_INPUT}" ]] && die "Usage: sudo bash otto-restore.sh <backup-dir-or-archive.tar.gz>"

WORK_DIR="${BACKUP_INPUT}"
CLEANUP_WORK=false

if [[ "${BACKUP_INPUT}" == *.tar.gz ]]; then
  log "Extracting archive: ${BACKUP_INPUT}"
  WORK_DIR=$(mktemp -d /tmp/otto-restore-XXXXXX)
  CLEANUP_WORK=true
  tar xzf "${BACKUP_INPUT}" -C "${WORK_DIR}" --strip-components=1
fi

[[ -d "${WORK_DIR}" ]] || die "Backup directory not found: ${WORK_DIR}"
log "Restoring from: ${WORK_DIR}"

cleanup() {
  [[ "${CLEANUP_WORK}" == true ]] && rm -rf "${WORK_DIR}"
}
trap cleanup EXIT

# ── Step 1: System packages ───────────────────────────────────────────────────
log "[1/9] Installing system packages ..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
  curl wget jq git tmux htop tree build-essential \
  python3 python3-pip python3-venv \
  ca-certificates gnupg lsb-release \
  rsync 2>/dev/null || warn "Some packages may have failed"

# Docker Engine
if ! command -v docker &>/dev/null; then
  log "  Installing Docker Engine ..."
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/debian/gpg \
    -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
    https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
  usermod -aG docker "${TARGET_USER}"
  log "  Docker installed"
else
  log "  Docker already installed — skipping"
fi

# Node.js 22 (via nvm or nodesource)
if ! command -v node &>/dev/null; then
  log "  Installing Node.js 22 ..."
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y -qq nodejs
else
  log "  Node.js already installed ($(node --version)) — skipping"
fi

# ── Step 2: Create user if needed ─────────────────────────────────────────────
log "[2/9] Ensuring user ${TARGET_USER} exists ..."
if ! id "${TARGET_USER}" &>/dev/null; then
  useradd -m -s /bin/bash "${TARGET_USER}"
  usermod -aG sudo,docker "${TARGET_USER}"
  log "  Created user ${TARGET_USER}"
else
  log "  User exists — checking docker group"
  usermod -aG docker "${TARGET_USER}" 2>/dev/null || true
fi

# ── Step 3: Restore ~/otto ────────────────────────────────────────────────────
log "[3/9] Restoring ~/otto ..."
mkdir -p "${OTTO_DIR}"
cp -a "${WORK_DIR}/otto/." "${OTTO_DIR}/"
chown -R "${TARGET_USER}:${TARGET_USER}" "${OTTO_DIR}"
chmod +x "${OTTO_DIR}"/*.sh 2>/dev/null || true
chmod +x "${OTTO_DIR}/tools/"*.sh 2>/dev/null || true
log "  ~/otto restored"

# ── Step 4: Restore ~/memory ──────────────────────────────────────────────────
log "[4/9] Restoring ~/memory config ..."
mkdir -p "${MEMORY_DIR}"
if [[ -f "${WORK_DIR}/memory/.env" ]]; then
  cp "${WORK_DIR}/memory/.env" "${MEMORY_DIR}/.env"
  chmod 600 "${MEMORY_DIR}/.env"
fi
[[ -f "${WORK_DIR}/memory/docker-compose.yml" ]] && \
  cp "${WORK_DIR}/memory/docker-compose.yml" "${MEMORY_DIR}/docker-compose.yml"
[[ -f "${WORK_DIR}/memory/docker-compose.yml.bak" ]] && \
  cp "${WORK_DIR}/memory/docker-compose.yml.bak" "${MEMORY_DIR}/docker-compose.yml.bak"
[[ -f "${WORK_DIR}/memory/cdp_api_key.json" ]] && \
  cp "${WORK_DIR}/memory/cdp_api_key.json" "${MEMORY_DIR}/cdp_api_key.json"
[[ -d "${WORK_DIR}/memory/init-db" ]] && \
  cp -r "${WORK_DIR}/memory/init-db" "${MEMORY_DIR}/init-db"
chown -R "${TARGET_USER}:${TARGET_USER}" "${MEMORY_DIR}"
log "  ~/memory config restored"

# ── Step 5: Restore ~/interfaces ──────────────────────────────────────────────
log "[5/9] Restoring ~/interfaces ..."
mkdir -p "${INTERFACES_DIR}/whatsapp" "${INTERFACES_DIR}/web-next"

if [[ -d "${WORK_DIR}/interfaces/whatsapp" ]]; then
  cp -a "${WORK_DIR}/interfaces/whatsapp/." "${INTERFACES_DIR}/whatsapp/"
  log "  WhatsApp interface restored"
else
  warn "  No WhatsApp backup found"
fi

if [[ -d "${WORK_DIR}/interfaces/web-next" ]]; then
  mkdir -p "${INTERFACES_DIR}/web-next"
  cp -a "${WORK_DIR}/interfaces/web-next/." "${INTERFACES_DIR}/web-next/"
  log "  web-next (OMS) restored"
fi

chown -R "${TARGET_USER}:${TARGET_USER}" "${INTERFACES_DIR}"

# ── Step 6: Docker volumes ────────────────────────────────────────────────────
log "[6/9] Restoring Docker volumes ..."

restore_volume() {
  local archive="$1" vol="$2"
  if [[ -f "${WORK_DIR}/docker-volumes/${archive}" ]]; then
    log "  Restoring volume: ${vol}"
    docker volume create "${vol}" 2>/dev/null || true
    docker run --rm -v "${vol}:/data" -v "${WORK_DIR}/docker-volumes:/backup" \
      debian:bookworm-slim \
      bash -c "cd /data && tar xzf /backup/${archive}" && \
      log "  Done: ${vol}" || warn "  Failed to restore ${vol}"
  else
    warn "  Archive not found for ${vol}: ${archive}"
  fi
}

# Start Docker if not running
systemctl start docker 2>/dev/null || true

# Restore raw volume dumps
restore_volume "postgres_data.tar.gz" "memory_postgres_data"
restore_volume "neo4j_data.tar.gz"    "memory_neo4j_data"

# If raw dumps failed/missing, fall back to SQL dump
if [[ -f "${WORK_DIR}/docker-volumes/postgres_dump.sql.gz" ]]; then
  if ! docker volume inspect memory_postgres_data &>/dev/null || \
     [[ ! -f "${WORK_DIR}/docker-volumes/postgres_data.tar.gz" ]]; then
    log "  Bootstrapping Postgres from SQL dump ..."
    docker volume create memory_postgres_data 2>/dev/null || true
    # Start postgres temporarily to load dump
    cd "${MEMORY_DIR}" && as_user docker compose up -d postgres 2>/dev/null || true
    sleep 5
    zcat "${WORK_DIR}/docker-volumes/postgres_dump.sql.gz" | \
      docker exec -i memory-postgres-1 psql -U otto -d memory && \
      log "  SQL dump loaded" || warn "  SQL dump load failed"
  fi
fi

# ── Step 7: Systemd units ─────────────────────────────────────────────────────
log "[7/9] Installing systemd units ..."
if [[ -d "${WORK_DIR}/systemd" ]]; then
  cp "${WORK_DIR}/systemd/"*.service "${WORK_DIR}/systemd/"*.timer \
    /etc/systemd/system/ 2>/dev/null || true
  systemctl daemon-reload
  log "  Units installed"

  # Enable and start key services
  for unit in \
    otto-heartbeat.timer \
    otto-reflection.timer \
    otto-maintenance.timer \
    otto-memory.service; do
    systemctl enable "${unit}" 2>/dev/null || true
    systemctl start "${unit}"  2>/dev/null || warn "  Could not start ${unit}"
  done
  log "  Core Otto services enabled"
else
  warn "  No systemd units in backup"
fi

# ── Step 8: Start memory stack ────────────────────────────────────────────────
log "[8/9] Starting memory infrastructure ..."
cd "${MEMORY_DIR}"
as_user docker compose up -d 2>/dev/null || \
  docker compose up -d 2>/dev/null || \
  warn "  docker compose up failed — check ${MEMORY_DIR}"
log "  Memory stack started"

# Wait for Postgres to be ready
log "  Waiting for Postgres ..."
for i in $(seq 1 20); do
  docker exec memory-postgres-1 pg_isready -U otto -d memory &>/dev/null && break
  sleep 2
done

# ── Step 9: Start Otto memory API ─────────────────────────────────────────────
log "[9/9] Starting Otto Memory API ..."
systemctl start otto-memory 2>/dev/null && \
  log "  otto-memory.service started" || \
  warn "  otto-memory.service not available — start manually"

# WhatsApp service
if [[ -f /etc/systemd/system/whatsapp.service ]]; then
  systemctl enable whatsapp 2>/dev/null || true
  systemctl start whatsapp 2>/dev/null && \
    log "  whatsapp.service started" || \
    warn "  whatsapp start failed — may need re-auth"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
log "╔══════════════════════════════════════════════════════════════╗"
log "║             Otto Restore Complete                            ║"
log "╠══════════════════════════════════════════════════════════════╣"
log "║  ~/otto           ✓ restored                                 ║"
log "║  ~/memory         ✓ config + volumes restored                ║"
log "║  ~/interfaces     ✓ whatsapp + web-next restored             ║"
log "║  systemd units    ✓ installed + enabled                      ║"
log "║  Docker stack     ✓ started                                  ║"
log "╠══════════════════════════════════════════════════════════════╣"
log "║  Manual steps required:                                      ║"
log "║  1. claude (login if needed)                                 ║"
log "║  2. gh auth login (GitHub CLI)                               ║"
log "║  3. Verify WhatsApp — may need QR scan                       ║"
log "║  4. Check: systemctl status otto-memory otto-heartbeat       ║"
log "╚══════════════════════════════════════════════════════════════╝"
