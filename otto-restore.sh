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
log "[1/18] Installing system packages ..."
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
log "[2/18] Ensuring user ${TARGET_USER} exists ..."
if ! id "${TARGET_USER}" &>/dev/null; then
  useradd -m -s /bin/bash "${TARGET_USER}"
  usermod -aG sudo,docker "${TARGET_USER}"
  log "  Created user ${TARGET_USER}"
else
  usermod -aG docker "${TARGET_USER}" 2>/dev/null || true
fi

# ── Step 3: Restore ~/otto ──────────────────────────────────────────────────
log "[3/18] Restoring ~/otto ..."
mkdir -p "${OTTO_DIR}"
cp -a "${WORK_DIR}/otto/." "${OTTO_DIR}/"
chown -R "${TARGET_USER}:${TARGET_USER}" "${OTTO_DIR}"
chmod +x "${OTTO_DIR}"/*.sh 2>/dev/null || true
chmod +x "${OTTO_DIR}/tools/"*.sh 2>/dev/null || true
log "  ~/otto restored"

# ── Step 4: Restore ~/memory ────────────────────────────────────────────────
log "[4/18] Restoring ~/memory config ..."
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
log "[5/18] Restoring ~/interfaces ..."
mkdir -p "${INTERFACES_DIR}"

# WhatsApp
if [[ -d "${WORK_DIR}/interfaces/whatsapp" ]]; then
  mkdir -p "${INTERFACES_DIR}/whatsapp"
  cp -a "${WORK_DIR}/interfaces/whatsapp/." "${INTERFACES_DIR}/whatsapp/"
  log "  WhatsApp interface restored"
fi

# Athena WhatsApp
if [[ -d "${WORK_DIR}/interfaces/athena-whatsapp" ]]; then
  mkdir -p "${INTERFACES_DIR}/athena-whatsapp"
  cp -a "${WORK_DIR}/interfaces/athena-whatsapp/." "${INTERFACES_DIR}/athena-whatsapp/"
  log "  Athena WhatsApp interface restored"
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
log "[6/18] Restoring nginx configs ..."
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
log "[7/18] Restoring SSH keys ..."
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
log "[8/18] Restoring Claude Code + git config ..."
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
log "[9/18] Restoring Docker volumes ..."

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
restore_volume "graphiti_neo4j_data.tar.gz" "graphiti_neo4j_data"
restore_volume "projects_postgres_data.tar.gz" "projects-db_projects-postgres-data"
restore_volume "projects_leads_log.tar.gz" "projects-db_projects-leads-log"

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
log "[10/18] Installing systemd units ..."
if [[ -d "${WORK_DIR}/systemd" ]]; then
  cp "${WORK_DIR}/systemd/"*.service "${WORK_DIR}/systemd/"*.timer \
    /etc/systemd/system/ 2>/dev/null || true
  systemctl daemon-reload

  # Enable all units that were enabled on the source machine
  if [[ -f "${WORK_DIR}/systemd/enabled-units.txt" ]]; then
    while read -r unit state vendor; do
      systemctl enable "${unit}" 2>/dev/null || true
    done < "${WORK_DIR}/systemd/enabled-units.txt"
    log "  Units enabled from source state"
  else
    # Fallback: enable known critical units
    for unit in \
      otto-heartbeat.timer \
      otto-reflection.timer \
      otto-maintenance.timer \
      otto-memory.service \
      otto-email-listener.service \
      whatsapp.service \
      athena-whatsapp.service \
      projects-db.service \
      service-monitor.timer; do
      systemctl enable "${unit}" 2>/dev/null || true
    done
  fi
  log "  Units installed + enabled"
else
  warn "  No systemd units in backup"
fi

# ── Step 11: Start memory stack ─────────────────────────────────────────────
log "[11/18] Starting memory infrastructure ..."
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
log "[12/18] Starting Otto services ..."

# Setup Python venv for Memory API if missing
if [[ ! -d "${OTTO_DIR}/memory/.venv" ]]; then
  log "  Creating Memory API venv ..."
  as_user python3 -m venv "${OTTO_DIR}/memory/.venv"
  as_user "${OTTO_DIR}/memory/.venv/bin/pip" install -q -r "${OTTO_DIR}/memory/requirements.txt" 2>/dev/null || true
fi

# Setup Python venv for Alpha paper trader if missing
if [[ -f "${OTTO_DIR}/projects/alpha/requirements.txt" && ! -d "${OTTO_DIR}/projects/alpha/.venv" ]]; then
  log "  Creating Alpha venv ..."
  as_user python3 -m venv "${OTTO_DIR}/projects/alpha/.venv"
  as_user "${OTTO_DIR}/projects/alpha/.venv/bin/pip" install -q -r "${OTTO_DIR}/projects/alpha/requirements.txt" 2>/dev/null || true
fi

# Setup Node.js deps for WhatsApp if missing
if [[ -f "${INTERFACES_DIR}/whatsapp/package.json" && ! -d "${INTERFACES_DIR}/whatsapp/node_modules" ]]; then
  log "  Installing WhatsApp node_modules ..."
  cd "${INTERFACES_DIR}/whatsapp" && as_user npm install --production 2>/dev/null || true
fi

# Setup Node.js deps for Athena WhatsApp if missing
if [[ -f "${INTERFACES_DIR}/athena-whatsapp/package.json" && ! -d "${INTERFACES_DIR}/athena-whatsapp/node_modules" ]]; then
  log "  Installing Athena WhatsApp node_modules ..."
  cd "${INTERFACES_DIR}/athena-whatsapp" && as_user npm install --production 2>/dev/null || true
fi

# Setup OMS deps if missing
if [[ -f "${INTERFACES_DIR}/web-next/package.json" && ! -d "${INTERFACES_DIR}/web-next/node_modules" ]]; then
  log "  Installing OMS node_modules ..."
  cd "${INTERFACES_DIR}/web-next" && as_user pnpm install 2>/dev/null || true
  as_user pnpm build 2>/dev/null || true
fi

# Start all services
systemctl start otto-memory 2>/dev/null && log "  otto-memory started" || warn "  otto-memory failed"
systemctl start whatsapp 2>/dev/null && log "  whatsapp started" || warn "  whatsapp failed"
systemctl start athena-whatsapp 2>/dev/null && log "  athena-whatsapp started" || warn "  athena-whatsapp failed"
systemctl start otto-email-listener 2>/dev/null && log "  email-listener started" || warn "  email-listener failed"
systemctl start otto-heartbeat.timer 2>/dev/null || true
systemctl start otto-reflection.timer 2>/dev/null || true
systemctl start otto-maintenance.timer 2>/dev/null || true
systemctl start service-monitor.timer 2>/dev/null || true

# ── Step 13: Clone project repos from manifest ──────────────────────────────
log "[13/18] Restoring project repos ..."
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

  # Restore uncommitted changes (dirty state)
  if [[ -d "${WORK_DIR}/projects-manifest/dirty" ]]; then
    log "  Restoring uncommitted project changes ..."
    for dirty_dir in "${WORK_DIR}/projects-manifest/dirty"/*/; do
      name=$(basename "${dirty_dir}")
      repo_path="${PROJECTS_DIR}/${name}"
      if [[ -d "${repo_path}" ]]; then
        # Apply patch (staged + unstaged diffs)
        if [[ -s "${dirty_dir}/changes.patch" ]]; then
          as_user git -C "${repo_path}" apply --allow-empty "${dirty_dir}/changes.patch" 2>/dev/null && \
            log "    ${name}: patch applied" || warn "    ${name}: patch failed (may need manual merge)"
        fi
        # Extract untracked files
        if [[ -f "${dirty_dir}/untracked.tar" ]]; then
          as_user tar -xf "${dirty_dir}/untracked.tar" -C "${repo_path}" 2>/dev/null && \
            log "    ${name}: untracked files restored" || warn "    ${name}: untracked restore failed"
        fi
      fi
    done
  fi
fi

# ── Step 14: Restore projects-db ────────────────────────────────────────────
log "[14/18] Restoring projects-db ..."
PROJECTSDB_DIR="${TARGET_HOME}/projects-db"
if [[ -d "${WORK_DIR}/projects-db" ]]; then
  mkdir -p "${PROJECTSDB_DIR}"
  cp -a "${WORK_DIR}/projects-db/." "${PROJECTSDB_DIR}/"
  chown -R "${TARGET_USER}:${TARGET_USER}" "${PROJECTSDB_DIR}"
  # Start projects-db compose stack
  cd "${PROJECTSDB_DIR}" && as_user docker compose up -d 2>/dev/null && \
    log "  projects-db started" || warn "  projects-db compose failed"
  systemctl start projects-db 2>/dev/null || true
fi

# ── Step 15: Restore CLI configs ────────────────────────────────────────────
log "[15/18] Restoring CLI configs ..."
if [[ -d "${WORK_DIR}/cli-configs" ]]; then
  # Gemini
  if [[ -d "${WORK_DIR}/cli-configs/gemini" ]]; then
    mkdir -p "${TARGET_HOME}/.gemini"
    cp -a "${WORK_DIR}/cli-configs/gemini/." "${TARGET_HOME}/.gemini/"
    chown -R "${TARGET_USER}:${TARGET_USER}" "${TARGET_HOME}/.gemini"
    log "  Gemini config restored"
  fi
  # Kimi
  if [[ -d "${WORK_DIR}/cli-configs/kimi" ]]; then
    mkdir -p "${TARGET_HOME}/.kimi"
    cp -a "${WORK_DIR}/cli-configs/kimi/." "${TARGET_HOME}/.kimi/"
    chown -R "${TARGET_USER}:${TARGET_USER}" "${TARGET_HOME}/.kimi"
    log "  Kimi config restored"
  fi
  # Vercel
  if [[ -d "${WORK_DIR}/cli-configs/vercel" ]]; then
    mkdir -p "${TARGET_HOME}/.local/share"
    cp -r "${WORK_DIR}/cli-configs/vercel" "${TARGET_HOME}/.local/share/com.vercel.cli"
    chown -R "${TARGET_USER}:${TARGET_USER}" "${TARGET_HOME}/.local/share/com.vercel.cli"
    log "  Vercel config restored"
  fi
fi

# ── Step 16: Restore shell profile + dotfiles ───────────────────────────────
log "[16/18] Restoring shell profile ..."
if [[ -d "${WORK_DIR}/dotfiles" ]]; then
  [[ -f "${WORK_DIR}/dotfiles/.bashrc" ]] && \
    cp "${WORK_DIR}/dotfiles/.bashrc" "${TARGET_HOME}/.bashrc"
  [[ -f "${WORK_DIR}/dotfiles/.profile" ]] && \
    cp "${WORK_DIR}/dotfiles/.profile" "${TARGET_HOME}/.profile"
  [[ -f "${WORK_DIR}/dotfiles/.bash_aliases" ]] && \
    cp "${WORK_DIR}/dotfiles/.bash_aliases" "${TARGET_HOME}/.bash_aliases"
  # Cargo env
  if [[ -f "${WORK_DIR}/dotfiles/cargo-env" ]]; then
    mkdir -p "${TARGET_HOME}/.cargo"
    cp "${WORK_DIR}/dotfiles/cargo-env" "${TARGET_HOME}/.cargo/env"
  fi
  chown -R "${TARGET_USER}:${TARGET_USER}" "${TARGET_HOME}/.bashrc" "${TARGET_HOME}/.profile" 2>/dev/null || true
  chown -R "${TARGET_USER}:${TARGET_USER}" "${TARGET_HOME}/.cargo" 2>/dev/null || true
  log "  Shell profile restored"
  # Install Rust + Foundry if they were present
  if [[ -f "${WORK_DIR}/system-extras/rust-version.txt" ]]; then
    log "  Installing Rust toolchain ..."
    as_user bash -c 'curl --proto "=https" --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y' 2>/dev/null && \
      log "  Rust installed" || warn "  Rust install failed"
  fi
  if [[ -f "${WORK_DIR}/system-extras/foundry-version.txt" ]]; then
    log "  Installing Foundry ..."
    as_user bash -c 'curl -L https://foundry.paradigm.xyz | bash && source ~/.bashrc && foundryup' 2>/dev/null && \
      log "  Foundry installed" || warn "  Foundry install failed"
  fi
fi

# ── Step 17: Restore media disk extras ──────────────────────────────────────
log "[17/18] Restoring media disk extras ..."
if [[ -d "${WORK_DIR}/media-extras" ]]; then
  [[ -f "${WORK_DIR}/media-extras/prompts.md" ]] && \
    cp "${WORK_DIR}/media-extras/prompts.md" /mnt/media/ && log "  prompts.md"
  [[ -d "${WORK_DIR}/media-extras/research" ]] && \
    cp -r "${WORK_DIR}/media-extras/research" /mnt/media/ && log "  research/"
  [[ -d "${WORK_DIR}/media-extras/documents" ]] && \
    cp -r "${WORK_DIR}/media-extras/documents" /mnt/media/ && log "  documents/"
  [[ -d "${WORK_DIR}/media-extras/hf_cache" ]] && \
    cp -r "${WORK_DIR}/media-extras/hf_cache" /mnt/media/ && log "  hf_cache/"
  chown -R "${TARGET_USER}:${TARGET_USER}" /mnt/media/prompts.md /mnt/media/research /mnt/media/documents /mnt/media/hf_cache 2>/dev/null || true
fi

# ── Step 18: Restore UFW + symlinks + fstab ─────────────────────────────────
log "[18/18] Restoring UFW + symlinks ..."
# UFW rules
if [[ -d "${WORK_DIR}/ufw" ]]; then
  apt-get install -y -qq ufw 2>/dev/null || true
  [[ -f "${WORK_DIR}/ufw/user.rules" ]] && cp "${WORK_DIR}/ufw/user.rules" /etc/ufw/user.rules
  [[ -f "${WORK_DIR}/ufw/user6.rules" ]] && cp "${WORK_DIR}/ufw/user6.rules" /etc/ufw/user6.rules
  ufw --force enable 2>/dev/null || true
  log "  UFW rules restored"
fi
# Recreate symlinks
if [[ -f "${WORK_DIR}/system-extras/symlinks.txt" ]]; then
  while IFS=' -> ' read -r name target; do
    [[ -n "${name}" && -n "${target}" ]] && \
      ln -sf "${target}" "${TARGET_HOME}/${name}" 2>/dev/null || true
  done < "${WORK_DIR}/system-extras/symlinks.txt"
  log "  Symlinks restored"
fi
# fstab media mount
if [[ -f "${WORK_DIR}/system-extras/fstab-custom.txt" ]]; then
  if ! grep -q "/mnt/media" /etc/fstab 2>/dev/null; then
    grep "/mnt/media" "${WORK_DIR}/system-extras/fstab-custom.txt" >> /etc/fstab 2>/dev/null || true
    mkdir -p /mnt/media
    mount -a 2>/dev/null || true
    log "  fstab media mount added"
  fi
fi

# ── Summary ─────────────────────────────────────────────────────────────────
echo ""
log "╔══════════════════════════════════════════════════════════════╗"
log "║             Otto Restore Complete                            ║"
log "╠══════════════════════════════════════════════════════════════╣"
log "║  ~/otto           restored (agent core, API, tools)          ║"
log "║  ~/memory         restored (config, volumes, DB)             ║"
log "║  ~/interfaces     restored (whatsapp, athena, email, OMS)    ║"
log "║  ~/projects-db    restored (compose, API, postgres)          ║"
log "║  Nginx + SSL      restored (configs + certificates)          ║"
log "║  SSH keys         restored (~/.ssh)                          ║"
log "║  Claude Code      restored (~/.claude config)                ║"
log "║  CLI configs      restored (gemini, kimi, vercel)            ║"
log "║  Shell profile    restored (.bashrc, .profile, cargo)        ║"
log "║  Systemd units    installed + enabled (all units)            ║"
log "║  Docker stack     started (Postgres, Neo4j, Graphiti)        ║"
log "║  Project repos    cloned + dirty state applied               ║"
log "║  Media extras     restored (prompts, research, documents)    ║"
log "║  UFW firewall     rules restored                             ║"
log "║  Symlinks + fstab restored                                   ║"
log "║  Rust + Foundry   installed (if present in source)           ║"
log "╠══════════════════════════════════════════════════════════════╣"
log "║  Manual steps that may be needed:                            ║"
log "║  1. claude (login if credentials expired)                    ║"
log "║  2. gh auth login (GitHub CLI — up to 3 accounts)            ║"
log "║  3. Verify WhatsApp — may need QR scan                       ║"
log "║  4. Verify DNS points to this VM's IP                        ║"
log "║  5. Run: bash ~/otto/otto-env-check.sh --human               ║"
log "╚══════════════════════════════════════════════════════════════╝"
