#!/usr/bin/env bash
# dns_healer.sh — Auto-heal DNS A records when VM external IP changes
# Managed subdomains: mev, alpha (otto.lk)
set -euo pipefail

DOMAIN="otto.lk"
SUBDOMAINS=("mev" "alpha")
LOG="/home/web3relic/otto/logs/dns_healer.log"
VERCEL="/usr/bin/vercel"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }

# Get current VM external IP
CURRENT_IP=$(curl -sf --max-time 10 https://api.ipify.org) || {
  log "ERROR: Failed to fetch external IP"
  exit 1
}

CHANGED=0

for SUB in "${SUBDOMAINS[@]}"; do
  FQDN="${SUB}.${DOMAIN}"
  DNS_IP=$(dig +short "$FQDN" A 2>/dev/null | head -1)

  if [[ -z "$DNS_IP" ]]; then
    log "WARN: No A record found for $FQDN — adding $CURRENT_IP"
  elif [[ "$DNS_IP" == "$CURRENT_IP" ]]; then
    continue
  else
    log "MISMATCH: $FQDN points to $DNS_IP, VM is $CURRENT_IP — fixing"
  fi

  # Find and remove stale A records for this subdomain (parse text output)
  RECORD_IDS=$($VERCEL dns ls "$DOMAIN" 2>/dev/null \
    | awk -v sname="$SUB" '$2 == sname && $3 == "A" { print $1 }') || true

  for RID in $RECORD_IDS; do
    log "Removing old record $RID for $FQDN"
    echo 'y' | $VERCEL dns rm "$RID" >> "$LOG" 2>&1 || log "WARN: Failed to remove $RID"
  done

  # Add new A record
  log "Adding A record: $FQDN -> $CURRENT_IP"
  $VERCEL dns add "$DOMAIN" "$SUB" A "$CURRENT_IP" >> "$LOG" 2>&1 || {
    log "ERROR: Failed to add A record for $FQDN"
    continue
  }

  CHANGED=1
  log "OK: $FQDN now points to $CURRENT_IP"
done

if [[ "$CHANGED" -eq 0 ]]; then
  log "CHECK: All subdomains already point to $CURRENT_IP — no changes needed"
fi
