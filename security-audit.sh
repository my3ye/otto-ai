#!/bin/bash
# Otto Security Audit Runner
# Triggered by otto-security-audit.timer every 3 days.
# Spawns Claude Opus as a security audit agent.

set -euo pipefail

OTTO_DIR="/home/web3relic/otto"
LOCK_FILE="/tmp/otto-security-audit.lock"
LOG_DIR="${OTTO_DIR}/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/security-audit-${TIMESTAMP}.log"
MEMORY_API="http://localhost:8100"

mkdir -p "$LOG_DIR"

# ── Lock: prevent concurrent audits ──────────────────────────────────────────
if [ -f "$LOCK_FILE" ]; then
    LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
    if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
        echo "$(date -Iseconds) Another security audit is running (PID $LOCK_PID), skipping." | tee -a "$LOG_FILE"
        exit 0
    else
        echo "$(date -Iseconds) Stale lock file found, removing." >> "$LOG_FILE"
        rm -f "$LOCK_FILE"
    fi
fi

echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

echo "$(date -Iseconds) ═══════════════════════════════════════════════════" >> "$LOG_FILE"
echo "$(date -Iseconds) Otto Security Audit starting (PID $$)" >> "$LOG_FILE"
echo "$(date -Iseconds) ═══════════════════════════════════════════════════" >> "$LOG_FILE"

# ── Pre-flight: ensure memory API is up ──────────────────────────────────────
if ! curl -sf "${MEMORY_API}/health" > /dev/null 2>&1; then
    echo "$(date -Iseconds) ERROR: Memory API not reachable at ${MEMORY_API}. Aborting audit." >> "$LOG_FILE"
    exit 1
fi

# ── Log audit start as episodic event ────────────────────────────────────────
curl -sf -X POST "${MEMORY_API}/episodic/events" \
    -H "Content-Type: application/json" \
    -d "{\"content\": \"Security audit started at $(date -Iseconds)\", \"event_type\": \"security_audit\", \"importance\": 7, \"metadata\": {\"status\": \"started\", \"log_file\": \"${LOG_FILE}\"}}" \
    > /dev/null 2>&1 || true

# ── Run Claude Opus security audit agent ─────────────────────────────────────
# Budget: $8 / 45 min timeout — comprehensive audit takes time
cd "$OTTO_DIR"
export OTTO_SESSION_TYPE=security_audit

AUDIT_PROMPT="Run the full security audit protocol. Phase 1: trigger vulnerability sync and pull latest threat intel. Phase 2: sweep all 9 system checks (network, SSH, users, secrets, Docker, services, deps, file integrity, updates). Phase 3: produce the structured report. Phase 4: log findings to memory. Be thorough. Do NOT change system state — observe only. Do NOT message Mev. End with a plain text summary of: risk score, top findings, what passed."

timeout 2700s /home/web3relic/.local/bin/claude \
    --print \
    --agent security-audit \
    --dangerously-skip-permissions \
    --model claude-opus-4-5 \
    --max-turns 80 \
    -p "$AUDIT_PROMPT" \
    >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 124 ]; then
    echo "$(date -Iseconds) WARN: Security audit TIMED OUT after 45 minutes." >> "$LOG_FILE"
    # Log timeout as event
    curl -sf -X POST "${MEMORY_API}/episodic/events" \
        -H "Content-Type: application/json" \
        -d "{\"content\": \"Security audit TIMED OUT at $(date -Iseconds). Log: ${LOG_FILE}\", \"event_type\": \"security_audit\", \"importance\": 8, \"metadata\": {\"status\": \"timeout\"}}" \
        > /dev/null 2>&1 || true
elif [ $EXIT_CODE -ne 0 ]; then
    echo "$(date -Iseconds) ERROR: Security audit failed with exit code $EXIT_CODE" >> "$LOG_FILE"
    curl -sf -X POST "${MEMORY_API}/episodic/events" \
        -H "Content-Type: application/json" \
        -d "{\"content\": \"Security audit FAILED at $(date -Iseconds) with exit code ${EXIT_CODE}. Log: ${LOG_FILE}\", \"event_type\": \"security_audit\", \"importance\": 9, \"metadata\": {\"status\": \"failed\", \"exit_code\": ${EXIT_CODE}}}" \
        > /dev/null 2>&1 || true
else
    echo "$(date -Iseconds) Security audit completed successfully." >> "$LOG_FILE"
fi

echo "$(date -Iseconds) Log saved to: ${LOG_FILE}" >> "$LOG_FILE"

# ── Clean up old audit logs (keep last 10) ───────────────────────────────────
ls -t "${LOG_DIR}"/security-audit-*.log 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true

echo "$(date -Iseconds) ═══════════════════════════════════════════════════" >> "$LOG_FILE"
