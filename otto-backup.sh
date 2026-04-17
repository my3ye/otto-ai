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
log "[1/19] Backing up ~/otto ..."
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
log "[2/19] Backing up ~/memory config ..."
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
log "[3/19] Backing up WhatsApp interfaces ..."
if [[ -d "${INTERFACES_DIR}/whatsapp" ]]; then
  mkdir -p "${WORK_DIR}/interfaces/whatsapp"
  cp -r "${INTERFACES_DIR}/whatsapp/auth_state" "${WORK_DIR}/interfaces/whatsapp/" 2>/dev/null || true
  cp "${INTERFACES_DIR}/whatsapp/package.json" "${WORK_DIR}/interfaces/whatsapp/" 2>/dev/null || true
  cp "${INTERFACES_DIR}/whatsapp/service.mjs"  "${WORK_DIR}/interfaces/whatsapp/" 2>/dev/null || true
  cp "${INTERFACES_DIR}/whatsapp/login.mjs"    "${WORK_DIR}/interfaces/whatsapp/" 2>/dev/null || true
else
  warn "No WhatsApp interface found"
fi
# Athena WhatsApp (second WhatsApp interface)
if [[ -d "${INTERFACES_DIR}/athena-whatsapp" ]]; then
  mkdir -p "${WORK_DIR}/interfaces/athena-whatsapp"
  cp -a "${INTERFACES_DIR}/athena-whatsapp/." "${WORK_DIR}/interfaces/athena-whatsapp/" 2>/dev/null || true
  # Exclude node_modules if present
  rm -rf "${WORK_DIR}/interfaces/athena-whatsapp/node_modules" 2>/dev/null || true
  log "  Athena WhatsApp interface included"
fi

# ── 4. Email interface ───────────────────────────────────────────────────────
log "[4/19] Backing up email interface ..."
if [[ -d "${INTERFACES_DIR}/email" ]]; then
  mkdir -p "${WORK_DIR}/interfaces/email"
  cp "${INTERFACES_DIR}/email/"*.py "${WORK_DIR}/interfaces/email/" 2>/dev/null || true
  cp "${INTERFACES_DIR}/email/"*.md "${WORK_DIR}/interfaces/email/" 2>/dev/null || true
  cp "${INTERFACES_DIR}/email/"*.yml "${WORK_DIR}/interfaces/email/" 2>/dev/null || true
  cp "${INTERFACES_DIR}/email/"*.env "${WORK_DIR}/interfaces/email/" 2>/dev/null || true
  # Email server data (bind mounts: mail-data, mail-state, config, postfixadmin DB)
  if [[ -d "${INTERFACES_DIR}/email/data" ]]; then
    cp -r "${INTERFACES_DIR}/email/data" "${WORK_DIR}/interfaces/email/data"
    log "  Email server data included (mail-data, config, postfixadmin)"
  fi
else
  warn "No email interface found"
fi

# ── 5. Web-next (OMS) interface ──────────────────────────────────────────────
log "[5/19] Backing up ~/interfaces/web-next ..."
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
log "[6/19] Backing up nginx configs ..."
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
log "[7/19] Backing up SSH keys ..."
if [[ -d "${HOME_DIR}/.ssh" ]]; then
  cp -r "${HOME_DIR}/.ssh" "${WORK_DIR}/ssh/dot-ssh"
  chmod 700 "${WORK_DIR}/ssh/dot-ssh"
  chmod 600 "${WORK_DIR}/ssh/dot-ssh/"* 2>/dev/null || true
else
  warn "No SSH keys found"
fi

# ── 8. Claude Code config ────────────────────────────────────────────────────
log "[8/19] Backing up Claude Code config ..."
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

# ── 9. Systemd units (ALL custom units) ──────────────────────────────────────
log "[9/19] Backing up systemd units ..."
for f in /etc/systemd/system/otto-*.service \
         /etc/systemd/system/otto-*.timer \
         /etc/systemd/system/whatsapp.service \
         /etc/systemd/system/athena-whatsapp.service \
         /etc/systemd/system/projects-db.service \
         /etc/systemd/system/code-tunnel.service \
         /etc/systemd/system/alpha-paper-trader.service \
         /etc/systemd/system/service-monitor.service \
         /etc/systemd/system/service-monitor.timer; do
  [[ -f "$f" ]] && cp "$f" "${WORK_DIR}/systemd/"
done
# Record which units are currently enabled
systemctl list-unit-files --state=enabled --no-pager 2>/dev/null | grep -E "^(otto-|whatsapp|athena|projects-db|code-tunnel|alpha|service-monitor)" \
  > "${WORK_DIR}/systemd/enabled-units.txt" 2>/dev/null || true
log "  $(ls "${WORK_DIR}/systemd/"*.service "${WORK_DIR}/systemd/"*.timer 2>/dev/null | wc -l) units backed up"

# ── 10. Docker volume dumps ──────────────────────────────────────────────────
log "[10/19] Dumping Docker volumes ..."

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
dump_volume "graphiti_neo4j_data"  "graphiti_neo4j_data"
dump_volume "projects-db_projects-postgres-data" "projects_postgres_data"
dump_volume "projects-db_projects-leads-log" "projects_leads_log"

# ── 11. PostgreSQL SQL dump ──────────────────────────────────────────────────
log "[11/19] Creating PostgreSQL SQL dump ..."
if docker ps --format '{{.Names}}' | grep -q "memory-postgres"; then
  docker exec memory-postgres-1 pg_dumpall -U otto 2>/dev/null \
    > "${WORK_DIR}/docker-volumes/postgres_dump.sql" && \
    gzip "${WORK_DIR}/docker-volumes/postgres_dump.sql" && \
    log "  postgres_dump.sql.gz created" || \
    warn "  PostgreSQL dump failed"
else
  warn "  memory-postgres-1 not running — skipping SQL dump"
fi

# ── 12. Project repos manifest + uncommitted changes ─────────────────────────
log "[12/19] Creating project repos manifest ..."
PROJECTS_DIR="/mnt/media/projects"
if [[ -d "${PROJECTS_DIR}" ]]; then
  for repo in "${PROJECTS_DIR}"/*/; do
    repo_name=$(basename "${repo}")
    if [[ -d "${repo}/.git" ]]; then
      remote=$(git -C "${repo}" remote get-url origin 2>/dev/null || echo "no-remote")
      branch=$(git -C "${repo}" branch --show-current 2>/dev/null || echo "unknown")
      echo "${repo_name}|${remote}|${branch}" >> "${WORK_DIR}/projects-manifest/repos.txt"
      # Capture uncommitted changes as a patch (git diff + untracked files)
      dirty=$(git -C "${repo}" status --porcelain 2>/dev/null | wc -l)
      if [[ "${dirty}" -gt 0 ]]; then
        mkdir -p "${WORK_DIR}/projects-manifest/dirty/${repo_name}"
        # Staged + unstaged diffs
        git -C "${repo}" diff HEAD > "${WORK_DIR}/projects-manifest/dirty/${repo_name}/changes.patch" 2>/dev/null || true
        # List and tar untracked files (new files not in git)
        untracked=$(git -C "${repo}" ls-files --others --exclude-standard 2>/dev/null)
        if [[ -n "${untracked}" ]]; then
          git -C "${repo}" ls-files --others --exclude-standard -z 2>/dev/null | \
            tar -C "${repo}" --null -T - -cf "${WORK_DIR}/projects-manifest/dirty/${repo_name}/untracked.tar" 2>/dev/null || true
        fi
        log "  ${repo_name}: ${dirty} uncommitted changes captured"
      fi
    fi
  done
  log "  $(wc -l < "${WORK_DIR}/projects-manifest/repos.txt" 2>/dev/null || echo 0) repos catalogued"
else
  warn "  /mnt/media/projects not found"
fi

# ── 13. System manifest ──────────────────────────────────────────────────────
log "[13/19] Writing system manifest ..."
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

# ── 14. Projects-DB service ──────────────────────────────────────────────────
log "[14/19] Backing up projects-db ..."
PROJECTSDB_DIR="${HOME_DIR}/projects-db"
if [[ -d "${PROJECTSDB_DIR}" ]]; then
  mkdir -p "${WORK_DIR}/projects-db"
  cp -a "${PROJECTSDB_DIR}/." "${WORK_DIR}/projects-db/"
  rm -rf "${WORK_DIR}/projects-db/api/__pycache__" 2>/dev/null || true
  log "  projects-db backed up"
else
  warn "  ~/projects-db not found"
fi

# ── 15. CLI configs (Gemini, Kimi, Vercel) ───────────────────────────────────
log "[15/19] Backing up CLI configs ..."
mkdir -p "${WORK_DIR}/cli-configs"
# Gemini (oauth tokens, .env, projects — skip large tmp/cache)
if [[ -d "${HOME_DIR}/.gemini" ]]; then
  mkdir -p "${WORK_DIR}/cli-configs/gemini"
  cp "${HOME_DIR}/.gemini/.env" "${WORK_DIR}/cli-configs/gemini/" 2>/dev/null || true
  cp "${HOME_DIR}/.gemini/oauth_creds.json" "${WORK_DIR}/cli-configs/gemini/" 2>/dev/null || true
  cp "${HOME_DIR}/.gemini/projects.json" "${WORK_DIR}/cli-configs/gemini/" 2>/dev/null || true
  cp "${HOME_DIR}/.gemini/mcp-oauth-tokens-v2.json" "${WORK_DIR}/cli-configs/gemini/" 2>/dev/null || true
  log "  Gemini config (oauth + env)"
fi
# Kimi (config + credentials — skip logs/cache)
if [[ -d "${HOME_DIR}/.kimi" ]]; then
  mkdir -p "${WORK_DIR}/cli-configs/kimi"
  cp "${HOME_DIR}/.kimi/config.toml" "${WORK_DIR}/cli-configs/kimi/" 2>/dev/null || true
  cp "${HOME_DIR}/.kimi/device_id" "${WORK_DIR}/cli-configs/kimi/" 2>/dev/null || true
  cp -r "${HOME_DIR}/.kimi/credentials" "${WORK_DIR}/cli-configs/kimi/" 2>/dev/null || true
  log "  Kimi config (credentials + device_id)"
fi
# Vercel
if [[ -d "${HOME_DIR}/.local/share/com.vercel.cli" ]]; then
  cp -r "${HOME_DIR}/.local/share/com.vercel.cli" "${WORK_DIR}/cli-configs/vercel" 2>/dev/null || true
  log "  Vercel config"
fi

# ── 16. Shell profile + dotfiles ─────────────────────────────────────────────
log "[16/19] Backing up shell profile ..."
mkdir -p "${WORK_DIR}/dotfiles"
cp "${HOME_DIR}/.bashrc" "${WORK_DIR}/dotfiles/" 2>/dev/null || true
cp "${HOME_DIR}/.profile" "${WORK_DIR}/dotfiles/" 2>/dev/null || true
cp "${HOME_DIR}/.bash_aliases" "${WORK_DIR}/dotfiles/" 2>/dev/null || true
# Cargo env (sourced in .bashrc)
cp "${HOME_DIR}/.cargo/env" "${WORK_DIR}/dotfiles/cargo-env" 2>/dev/null || true

# ── 17. Media disk non-project files ─────────────────────────────────────────
log "[17/19] Backing up media disk extras ..."
mkdir -p "${WORK_DIR}/media-extras"
[[ -f "/mnt/media/prompts.md" ]] && cp "/mnt/media/prompts.md" "${WORK_DIR}/media-extras/" && log "  prompts.md"
[[ -d "/mnt/media/research" ]] && cp -r "/mnt/media/research" "${WORK_DIR}/media-extras/" && log "  research/"
[[ -d "/mnt/media/documents" ]] && cp -r "/mnt/media/documents" "${WORK_DIR}/media-extras/" && log "  documents/"
[[ -d "/mnt/media/hf_cache" ]] && cp -r "/mnt/media/hf_cache" "${WORK_DIR}/media-extras/" && log "  hf_cache/ ($(du -sh /mnt/media/hf_cache 2>/dev/null | cut -f1))"

# ── 18. UFW firewall rules ──────────────────────────────────────────────────
log "[18/19] Backing up UFW rules ..."
mkdir -p "${WORK_DIR}/ufw"
cp /etc/ufw/user.rules "${WORK_DIR}/ufw/" 2>/dev/null || true
cp /etc/ufw/user6.rules "${WORK_DIR}/ufw/" 2>/dev/null || true
ufw status verbose > "${WORK_DIR}/ufw/status.txt" 2>/dev/null || true

# ── 19. Symlinks + fstab ────────────────────────────────────────────────────
log "[19/19] Backing up symlinks + fstab ..."
mkdir -p "${WORK_DIR}/system-extras"
# Record symlinks
find "${HOME_DIR}" -maxdepth 1 -type l -printf '%f -> %l\n' > "${WORK_DIR}/system-extras/symlinks.txt" 2>/dev/null || true
# fstab media mount
grep -v "^#" /etc/fstab | grep -v "^$" > "${WORK_DIR}/system-extras/fstab-custom.txt" 2>/dev/null || true
# Rust/Foundry install state (just record versions, don't backup 1.8GB of toolchain)
"${HOME_DIR}/.cargo/bin/rustc" --version > "${WORK_DIR}/system-extras/rust-version.txt" 2>/dev/null || true
"${HOME_DIR}/.foundry/bin/forge" --version > "${WORK_DIR}/system-extras/foundry-version.txt" 2>/dev/null || true

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
