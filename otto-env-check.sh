#!/usr/bin/env bash
# otto-env-check.sh — New-environment authentication checklist
#
# Checks all external services and CLIs that require re-authentication
# after a VM restore or fresh deploy. Outputs structured JSON.
#
# Usage: ./otto-env-check.sh [--json | --human]
# Returns: exit 0 if all checks pass, exit 1 if any fail
#
# Triggered automatically by otto-restore.sh after a restore.

set -uo pipefail

FORMAT="${1:---json}"  # --json (default) or --human
USER="${SUDO_USER:-web3relic}"
HOME_DIR="/home/${USER}"
MEMORY_ENV="${HOME_DIR}/memory/.env"
MARKER_FILE="/tmp/otto-env-restored"

# ── Helpers ────────────────────────────────────────────────────────────────

check_result() {
  local name="$1" status="$2" detail="$3"
  echo "{\"name\":\"${name}\",\"status\":\"${status}\",\"detail\":$(printf '%s' "${detail}" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')}"
}

cmd_exists() { command -v "$1" &>/dev/null; }

# ── Checks ────────────────────────────────────────────────────────────────

checks=()

# 1. GitHub CLI
if cmd_exists gh; then
  gh_status=$(gh auth status 2>&1 | head -3 | tr '\n' ' ')
  if echo "${gh_status}" | grep -q "Logged in"; then
    gh_user=$(gh api user --jq .login 2>/dev/null || echo "unknown")
    checks+=("$(check_result "github_cli" "pass" "Logged in as ${gh_user}")")
  else
    checks+=("$(check_result "github_cli" "fail" "Not authenticated. Run: gh auth login")")
  fi
else
  checks+=("$(check_result "github_cli" "fail" "gh CLI not installed")")
fi

# 2. Vercel CLI
if cmd_exists vercel; then
  vercel_out=$(vercel whoami 2>&1 | head -1)
  if echo "${vercel_out}" | grep -qv -e "Error" -e "not found" -e "login" -e "Forbidden"; then
    checks+=("$(check_result "vercel_cli" "pass" "Logged in: ${vercel_out}")")
  else
    checks+=("$(check_result "vercel_cli" "fail" "Not authenticated. Run: vercel login")")
  fi
else
  checks+=("$(check_result "vercel_cli" "warn" "vercel CLI not installed (npm i -g vercel)")")
fi

# 3. GCP / gcloud
if cmd_exists gcloud; then
  gcloud_out=$(gcloud auth list --format="value(account,status)" 2>/dev/null | head -3 | tr '\n' ' ')
  if [[ -n "${gcloud_out}" ]] && ! echo "${gcloud_out}" | grep -qi "no credentialed accounts"; then
    checks+=("$(check_result "gcp_auth" "pass" "Active accounts: ${gcloud_out}")")
  else
    checks+=("$(check_result "gcp_auth" "fail" "Not authenticated. Run: gcloud auth login")")
  fi
else
  checks+=("$(check_result "gcp_auth" "warn" "gcloud CLI not installed")")
fi

# 4. npm / registry token
if cmd_exists npm; then
  npm_user=$(npm whoami 2>/dev/null)
  if [[ -n "${npm_user}" ]]; then
    checks+=("$(check_result "npm_auth" "pass" "Logged in as ${npm_user}")")
  else
    # Check ~/.npmrc for token (not logged in but token may be set)
    if [[ -f "${HOME_DIR}/.npmrc" ]] && grep -q "authToken" "${HOME_DIR}/.npmrc" 2>/dev/null; then
      checks+=("$(check_result "npm_auth" "pass" "Auth token present in ~/.npmrc")")
    else
      checks+=("$(check_result "npm_auth" "warn" "No npm auth. Run: npm login (if private packages needed)")")
    fi
  fi
else
  checks+=("$(check_result "npm_auth" "warn" "npm not installed")")
fi

# 5. Claude Code CLI
if cmd_exists claude; then
  # Claude Code doesn't have a "whoami" — check if config/credentials exist
  claude_creds="${HOME_DIR}/.claude/credentials.json"
  if [[ -f "${claude_creds}" ]] && python3 -c "import json; d=json.load(open('${claude_creds}')); exit(0 if d else 1)" 2>/dev/null; then
    checks+=("$(check_result "claude_cli" "pass" "Credentials file present")")
  else
    checks+=("$(check_result "claude_cli" "warn" "No credentials file found. Run: claude and follow login prompt")")
  fi
else
  checks+=("$(check_result "claude_cli" "fail" "claude CLI not installed")")
fi

# 6. WhatsApp session
WHATSAPP_AUTH="${HOME_DIR}/interfaces/whatsapp/auth_state"
if [[ -d "${WHATSAPP_AUTH}" ]] && [[ $(find "${WHATSAPP_AUTH}" -name "*.json" 2>/dev/null | wc -l) -gt 2 ]]; then
  session_files=$(find "${WHATSAPP_AUTH}" -name "*.json" | wc -l)
  checks+=("$(check_result "whatsapp_session" "pass" "Auth state present (${session_files} files)")")
else
  checks+=("$(check_result "whatsapp_session" "fail" "No auth state — re-pair required. Run: node ~/interfaces/whatsapp/login.mjs")")
fi

# 7. .env secrets validation
if [[ -f "${MEMORY_ENV}" ]]; then
  missing_vars=()
  required_vars=("OPENAI_API_KEY" "POSTGRES_PASSWORD" "NEO4J_PASSWORD" "GEMINI_API_KEY")
  for var in "${required_vars[@]}"; do
    val=$(grep "^${var}=" "${MEMORY_ENV}" 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'")
    if [[ -z "${val}" ]] || [[ "${val}" == "your_key_here" ]] || [[ "${val}" == "REPLACE_ME" ]]; then
      missing_vars+=("${var}")
    fi
  done
  if [[ ${#missing_vars[@]} -eq 0 ]]; then
    checks+=("$(check_result "env_secrets" "pass" "All ${#required_vars[@]} required vars present in ~/memory/.env")")
  else
    checks+=("$(check_result "env_secrets" "fail" "Missing/empty vars: ${missing_vars[*]}. Edit ~/memory/.env")")
  fi
else
  checks+=("$(check_result "env_secrets" "fail" "~/memory/.env not found — restore failed or incomplete")")
fi

# 8. Systemd services
declare -A SERVICES=(
  ["otto-memory"]="Memory API (:8100)"
  ["otto-heartbeat.timer"]="Orchestrator timer"
  ["otto-reflection.timer"]="Reflection timer"
  ["whatsapp"]="WhatsApp interface"
)

failed_services=()
running_services=()
for svc in "${!SERVICES[@]}"; do
  if systemctl is-active --quiet "${svc}" 2>/dev/null; then
    running_services+=("${svc}")
  else
    failed_services+=("${svc}")
  fi
done

if [[ ${#failed_services[@]} -eq 0 ]]; then
  checks+=("$(check_result "systemd_services" "pass" "All ${#running_services[@]} key services running")")
else
  checks+=("$(check_result "systemd_services" "fail" "Services not running: ${failed_services[*]}. Run: sudo systemctl start <name>")")
fi

# 9. Docker / memory services
if cmd_exists docker; then
  containers=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -E "memory-(postgres|neo4j|graphiti)" | tr '\n' ' ')
  container_count=$(echo "${containers}" | tr ' ' '\n' | grep -c . || true)
  if [[ "${container_count}" -ge 2 ]]; then
    checks+=("$(check_result "docker_services" "pass" "Memory containers running: ${containers}")")
  else
    checks+=("$(check_result "docker_services" "fail" "Memory containers not running. Run: cd ~/memory && docker compose up -d")")
  fi
else
  checks+=("$(check_result "docker_services" "fail" "Docker not installed or not accessible")")
fi

# ── Output ─────────────────────────────────────────────────────────────────

# Count pass/fail/warn
pass_count=0; fail_count=0; warn_count=0
for c in "${checks[@]}"; do
  status=$(echo "${c}" | python3 -c 'import sys,json; d=json.loads(sys.stdin.read()); print(d["status"])')
  case "${status}" in
    pass) ((pass_count++)) ;;
    fail) ((fail_count++)) ;;
    warn) ((warn_count++)) ;;
  esac
done

total_count=${#checks[@]}
overall="pass"
[[ "${fail_count}" -gt 0 ]] && overall="fail"
[[ "${fail_count}" -eq 0 && "${warn_count}" -gt 0 ]] && overall="warn"

# Is this a post-restore environment?
is_restored="false"
[[ -f "${MARKER_FILE}" ]] && is_restored="true"

if [[ "${FORMAT}" == "--human" ]]; then
  # Human-readable output
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  Otto New-Environment Auth Checklist"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  [[ "${is_restored}" == "true" ]] && echo "  ⚠ Restored environment detected"
  echo ""

  for c in "${checks[@]}"; do
    name=$(echo "${c}" | python3 -c 'import sys,json; d=json.loads(sys.stdin.read()); print(d["name"])')
    status=$(echo "${c}" | python3 -c 'import sys,json; d=json.loads(sys.stdin.read()); print(d["status"])')
    detail=$(echo "${c}" | python3 -c 'import sys,json; d=json.loads(sys.stdin.read()); print(d["detail"])')
    case "${status}" in
      pass) icon="✓" ;;
      fail) icon="✗" ;;
      warn) icon="⚠" ;;
    esac
    printf "  %s  %-22s  %s\n" "${icon}" "${name}" "${detail}"
  done

  echo ""
  echo "  Result: ${pass_count}/${total_count} pass, ${fail_count} fail, ${warn_count} warn"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
else
  # JSON output
  checks_json="["
  for i in "${!checks[@]}"; do
    [[ "${i}" -gt 0 ]] && checks_json+=","
    checks_json+="${checks[$i]}"
  done
  checks_json+="]"

  python3 -c "
import json, sys
checks = json.loads(sys.argv[1])
result = {
  'overall': '${overall}',
  'pass_count': ${pass_count},
  'fail_count': ${fail_count},
  'warn_count': ${warn_count},
  'total_count': ${total_count},
  'is_restored': ${is_restored},
  'checks': checks
}
print(json.dumps(result, indent=2))
" "${checks_json}"
fi

# Exit with non-zero if any failures
[[ "${fail_count}" -gt 0 ]] && exit 1
exit 0
