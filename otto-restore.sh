#!/usr/bin/env bash
# otto-restore.sh — Restore / clone Otto onto a fresh Debian 12 VM
#
# Usage: sudo bash otto-restore.sh <otto-backup-*.tar.gz.gpg>
#    or: sudo bash otto-restore.sh <otto-backup-*.tar.gz>  (unencrypted)
#    or: sudo bash otto-restore.sh <extracted-backup-dir>
#
# For encrypted archives, set BACKUP_KEY env var or it will prompt.
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

# ── Resolve backup input ────────────────────────────────────────────────────
BACKUP_INPUT="${1:-}"
[[ -z "${BACKUP_INPUT}" ]] && die "Usage: sudo bash otto-restore.sh <backup-archive-or-dir>"

WORK_DIR="${BACKUP_INPUT}"
CLEANUP_WORK=false

# Handle encrypted .gpg archive
if [[ "${BACKUP_INPUT}" == *.gpg ]]; then
  log "Decrypting archive: ${BACKUP_INPUT}"
  DECRYPTED=$(mktemp /tmp/otto-backup-XXXXXX.tar.gz)
  CLEANUP_WORK=true

  if [[ -n "${BACKUP_KEY:-}" ]]; then
    gpg --batch --yes --passphrase "${BACKUP_KEY}" -d "${BACKUP_INPUT}" > "${DECRYPTED}"
  else
    echo "Enter backup decryption key (from ~/memory/.backup-key):"
    read -rs BACKUP_KEY
    gpg --batch --yes --passphrase "${BACKUP_KEY}" -d "${BACKUP_INPUT}" > "${DECRYPTED}" || \
      die "Decryption failed — wrong key?"
  fi
  log "Decrypted successfully"
  BACKUP_INPUT="${DECRYPTED}"
fi

# Handle .tar.gz archive
if [[ "${BACKUP_INPUT}" == *.tar.gz ]]; then
  log "Extracting archive: ${BACKUP_INPUT}"
  WORK_DIR=$(mktemp -d /tmp/otto-restore-XXXXXX)
  CLEANUP_WORK=true
  tar xzf "${BACKUP_INPUT}" -C "${WORK_DIR}" --strip-components=1
fi

[[ -d "${WORK_DIR}" ]] || die "Backup directory not found: ${WORK_DIR}"
log "Restoring from: ${WORK_DIR}"

cleanup() {
  [[ "${CLEANUP_WORK}" == true ]] && rm -rf "${WORK_DIR}" "${DECRYPTED:-}" 2>/dev/null || true
}
trap cleanup EXIT

# ── Step 1: System packages ─────────────────────────────────────────────────
log "[1/12] Installing system packages ..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
  curl wget jq git tmux htop tree build-essential \
  python3 python3-pip python3-venv \
  ca-certificates gnupg lsb-release \
  rsync nginx certbot python3-certbot-nginx \
  2>/dev/null || warn "Some packages may have failed"

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

# Node.js 22
if ! command -v node &>/dev/null; then
  log "  Installing Node.js 22 ..."
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y -qq nodejs
else
  log "  Node.js already installed ($(node --version)) — skipping"
fi

# pnpm
if ! command -v pnpm &>/dev/null; then
  npm install -g pnpm 2>/dev/null || true
fi

# ── Step 2: Create user if needed ───────────────────────────────────────────
log "[2/12] Ensuring user ${TARGET_USER} exists ..."
if ! id "${TARGET_USER}" &>/dev/null; then
  useradd -m -s /bin/bash "${TARGET_USER}"
  usermod -aG sudo,docker "${TARGET_USER}"
  log "  Created user ${TARGET_USER}"
else
  usermod -aG docker "${TARGET_USER}" 2>/dev/null || true
fi

# ── Step 3: Restore ~/otto ──────────────────────────────────────────────────
log "[3/12] Restoring ~/otto ..."
mkdir -p "${OTTO_DIR}"
cp -a "${WORK_DIR}/otto/." "${OTTO_DIR}/"
chown -R "${TARGET_USER}:${TARGET_USER}" "${OTTO_DIR}"
chmod +x "${OTTO_DIR}"/*.sh 2>/dev/null || true
chmod +x "${OTTO_DIR}/tools/"*.sh 2>/dev/null || true
log "  ~/otto restored"

# ── Step 4: Restore ~/memory ────────────────────────────────────────────────
log "[4/12] Restoring ~/memory config ..."
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
[[ -f "${WORK_DIR}/memory/.backup-key" ]] && \
  cp "${WORK_DIR}/memory/.backup-key" "${MEMORY_DIR}/.backup-key" && \
  chmod 600 "${MEMORY_DIR}/.backup-key"
chown -R "${TARGET_USER}:${TARGET_USER}" "${MEMORY_DIR}"
log "  ~/memory config restored"

# ── Step 5: Restore ~/interfaces ────────────────────────────────────────────
log "[5/12] Restoring ~/interfaces ..."
mkdir -p "${INTERFACES_DIR}"

# WhatsApp
if [[ -d "${WORK_DIR}/interfaces/whatsapp" ]]; then
  mkdir -p "${INTERFACES_DIR}/whatsapp"
  cp -a "${WORK_DIR}/interfaces/whatsapp/." "${INTERFACES_DIR}/whatsapp/"
  log "  WhatsApp interface restored"
fi

# Email
if [[ -d "${WORK_DIR}/interfaces/email" ]]; then
  mkdir -p "${INTERFACES_DIR}/email"
  cp -a "${WORK_DIR}/interfaces/email/." "${INTERFACES_DIR}/email/"
  chmod +x "${INTERFACES_DIR}/email/"*.py 2>/dev/null || true
  log "  Email interface restored"
fi

# Web-next (OMS)
if [[ -d "${WORK_DIR}/interfaces/web-next" ]]; then
  mkdir -p "${INTERFACES_DIR}/web-next"
  cp -a "${WORK_DIR}/interfaces/web-next/." "${INTERFACES_DIR}/web-next/"
  log "  web-next (OMS) restored"
fi

chown -R "${TARGET_USER}:${TARGET_USER}" "${INTERFACES_DIR}"

# ── Step 6: Restore nginx + SSL ─────────────────────────────────────────────
log "[6/12] Restoring nginx configs ..."
if [[ -d "${WORK_DIR}/nginx/sites-available" ]]; then
  cp -r "${WORK_DIR}/nginx/sites-available/"* /etc/nginx/sites-available/ 2>/dev/null || true
  # Re-create symlinks in sites-enabled
  if [[ -d "${WORK_DIR}/nginx/sites-enabled" ]]; then
    for link in "${WORK_DIR}/nginx/sites-enabled/"*; do
      name=$(basename "${link}")
      [[ "${name}" == "default" ]] && continue
      ln -sf "/etc/nginx/sites-available/${name}" "/etc/nginx/sites-enabled/${name}" 2>/dev/null || true
    done
  fi
  [[ -f "${WORK_DIR}/nginx/nginx.conf" ]] && \
    cp "${WORK_DIR}/nginx/nginx.conf" /etc/nginx/nginx.conf
  log "  Nginx configs restored"
fi
if [[ -d "${WORK_DIR}/nginx/letsencrypt" ]]; then
  cp -r "${WORK_DIR}/nginx/letsencrypt" /etc/letsencrypt
  log "  SSL certificates restored"
fi
systemctl enable nginx 2>/dev/null || true
systemctl restart nginx 2>/dev/null || warn "  Nginx restart failed — check configs"

# ── Step 7: Restore SSH keys ────────────────────────────────────────────────
log "[7/12] Restoring SSH keys ..."
if [[ -d "${WORK_DIR}/ssh/dot-ssh" ]]; then
  mkdir -p "${TARGET_HOME}/.ssh"
  cp -a "${WORK_DIR}/ssh/dot-ssh/." "${TARGET_HOME}/.ssh/"
  chown -R "${TARGET_USER}:${TARGET_USER}" "${TARGET_HOME}/.ssh"
  chmod 700 "${TARGET_HOME}/.ssh"
  chmod 600 "${TARGET_HOME}/.ssh/"* 2>/dev/null || true
  chmod 644 "${TARGET_HOME}/.ssh/"*.pub 2>/dev/null || true
  chmod 644 "${TARGET_HOME}/.ssh/known_hosts" 2>/dev/null || true
  chmod 644 "${TARGET_HOME}/.ssh/authorized_keys" 2>/dev/null || true
  log "  SSH keys restored"
else
  warn "  No SSH keys in backup"
fi

# ── Step 8: Restore Claude Code config ───────────────────────────────────────
log "[8/12] Restoring Claude Code + git config ..."
if [[ -d "${WORK_DIR}/claude/dot-claude" ]]; then
  mkdir -p "${TARGET_HOME}/.claude"
  cp -a "${WORK_DIR}/claude/dot-claude/." "${TARGET_HOME}/.claude/"
  chown -R "${TARGET_USER}:${TARGET_USER}" "${TARGET_HOME}/.claude"
  log "  Claude Code config restored"
fi
[[ -f "${WORK_DIR}/claude/.gitconfig" ]] && \
  cp "${WORK_DIR}/claude/.gitconfig" "${TARGET_HOME}/.gitconfig" && \
  chown "${TARGET_USER}:${TARGET_USER}" "${TARGET_HOME}/.gitconfig" && \
  log "  Git config restored"

# ── Step 9: Docker volumes ──────────────────────────────────────────────────
log "[9/12] Restoring Docker volumes ..."

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

systemctl start docker 2>/dev/null || true
restore_volume "postgres_data.tar.gz" "memory_postgres_data"
restore_volume "neo4j_data.tar.gz"    "memory_neo4j_data"

# SQL dump fallback
if [[ -f "${WORK_DIR}/docker-volumes/postgres_dump.sql.gz" ]]; then
  if ! docker volume inspect memory_postgres_data &>/dev/null || \
     [[ ! -f "${WORK_DIR}/docker-volumes/postgres_data.tar.gz" ]]; then
    log "  Bootstrapping Postgres from SQL dump ..."
    docker volume create memory_postgres_data 2>/dev/null || true
    cd "${MEMORY_DIR}" && as_user docker compose up -d postgres 2>/dev/null || true
    sleep 5
    zcat "${WORK_DIR}/docker-volumes/postgres_dump.sql.gz" | \
      docker exec -i memory-postgres-1 psql -U otto -d memory && \
      log "  SQL dump loaded" || warn "  SQL dump load failed"
  fi
fi

# ── Step 10: Systemd units ──────────────────────────────────────────────────
log "[10/12] Installing systemd units ..."
if [[ -d "${WORK_DIR}/systemd" ]]; then
  cp "${WORK_DIR}/systemd/"*.service "${WORK_DIR}/systemd/"*.timer \
    /etc/systemd/system/ 2>/dev/null || true
  systemctl daemon-reload

  for unit in \
    otto-heartbeat.timer \
    otto-reflection.timer \
    otto-maintenance.timer \
    otto-memory.service \
    otto-email-listener.service; do
    systemctl enable "${unit}" 2>/dev/null || true
  done
  log "  Units installed + enabled"
else
  warn "  No systemd units in backup"
fi

# ── Step 11: Start memory stack ─────────────────────────────────────────────
log "[11/12] Starting memory infrastructure ..."
cd "${MEMORY_DIR}"
as_user docker compose up -d 2>/dev/null || \
  docker compose up -d 2>/dev/null || \
  warn "  docker compose up failed"
log "  Memory stack started"

log "  Waiting for Postgres ..."
for i in $(seq 1 20); do
  docker exec memory-postgres-1 pg_isready -U otto -d memory &>/dev/null && break
  sleep 2
done

# ── Step 12: Start services ─────────────────────────────────────────────────
log "[12/12] Starting Otto services ..."

# Setup Python venv for Memory API if missing
if [[ ! -d "${OTTO_DIR}/memory/.venv" ]]; then
  log "  Creating Memory API venv ..."
  as_user python3 -m venv "${OTTO_DIR}/memory/.venv"
  as_user "${OTTO_DIR}/memory/.venv/bin/pip" install -q -r "${OTTO_DIR}/memory/requirements.txt" 2>/dev/null || true
fi

# Setup Node.js deps for WhatsApp if missing
if [[ -f "${INTERFACES_DIR}/whatsapp/package.json" && ! -d "${INTERFACES_DIR}/whatsapp/node_modules" ]]; then
  log "  Installing WhatsApp node_modules ..."
  cd "${INTERFACES_DIR}/whatsapp" && as_user npm install --production 2>/dev/null || true
fi

# Setup OMS deps if missing
if [[ -f "${INTERFACES_DIR}/web-next/package.json" && ! -d "${INTERFACES_DIR}/web-next/node_modules" ]]; then
  log "  Installing OMS node_modules ..."
  cd "${INTERFACES_DIR}/web-next" && as_user pnpm install 2>/dev/null || true
  as_user pnpm build 2>/dev/null || true
fi

systemctl start otto-memory 2>/dev/null && log "  otto-memory started" || warn "  otto-memory failed"
systemctl start whatsapp 2>/dev/null && log "  whatsapp started" || warn "  whatsapp failed"
systemctl start otto-email-listener 2>/dev/null && log "  email-listener started" || warn "  email-listener failed"
systemctl start otto-heartbeat.timer 2>/dev/null || true
systemctl start otto-reflection.timer 2>/dev/null || true

# ── Step 13: Clone project repos from manifest ──────────────────────────────
if [[ -f "${WORK_DIR}/projects-manifest/repos.txt" ]]; then
  PROJECTS_DIR="/mnt/media/projects"
  mkdir -p "${PROJECTS_DIR}" 2>/dev/null || true
  log "  Cloning project repos from manifest ..."
  while IFS='|' read -r name remote branch; do
    if [[ ! -d "${PROJECTS_DIR}/${name}" && "${remote}" != "no-remote" ]]; then
      as_user git clone "${remote}" "${PROJECTS_DIR}/${name}" 2>/dev/null && \
        log "    Cloned: ${name}" || warn "    Failed to clone: ${name}"
    else
      log "    Skipped: ${name} (already exists or no remote)"
    fi
  done < "${WORK_DIR}/projects-manifest/repos.txt"
fi

# ── Summary ─────────────────────────────────────────────────────────────────
echo ""
log "╔══════════════════════════════════════════════════════════════╗"
log "║             Otto Restore Complete                            ║"
log "╠══════════════════════════════════════════════════════════════╣"
log "║  ~/otto           restored (agent core, API, tools)          ║"
log "║  ~/memory         restored (config, volumes, DB)             ║"
log "║  ~/interfaces     restored (whatsapp, email, OMS)            ║"
log "║  Nginx + SSL      restored (configs + certificates)          ║"
log "║  SSH keys         restored (~/.ssh)                          ║"
log "║  Claude Code      restored (~/.claude config)                ║"
log "║  Systemd units    installed + enabled                        ║"
log "║  Docker stack     started (Postgres, Neo4j, Graphiti)        ║"
log "║  Project repos    cloned from manifest                       ║"
log "╠══════════════════════════════════════════════════════════════╣"
log "║  Manual steps that may be needed:                            ║"
log "║  1. claude (login if credentials expired)                    ║"
log "║  2. gh auth login (GitHub CLI — up to 3 accounts)            ║"
log "║  3. Verify WhatsApp — may need QR scan                       ║"
log "║  4. Verify DNS points to this VM's IP                        ║"
log "║  5. Run: bash ~/otto/otto-env-check.sh --human               ║"
log "╚══════════════════════════════════════════════════════════════╝"
