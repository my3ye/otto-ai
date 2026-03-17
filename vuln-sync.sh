#!/bin/bash
# Vulnerability Intelligence Auto-Sync
# Runs every 6 hours via systemd timer

set -euo pipefail

LOG_FILE="/home/web3relic/otto/logs/vuln-sync-$(date +%Y%m%d-%H%M%S).log"
mkdir -p /home/web3relic/otto/logs

echo "[$(date -Iseconds)] Starting vulnerability sync..." | tee "$LOG_FILE"

# Load env
if [ -f /home/web3relic/memory/.env ]; then
    set -a
    source /home/web3relic/memory/.env 2>/dev/null || true
    set +a
fi

export POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
export POSTGRES_DB="${POSTGRES_DB:-memory}"
export POSTGRES_USER="${POSTGRES_USER:-otto}"

cd /home/web3relic/otto

# Run sync (all sources, 7 days back for NVD, full history for curated)
python3 -c "
import asyncio, sys, json
sys.path.insert(0, '/home/web3relic/otto')
from memory.security.vuln_collector import run_sync
result = asyncio.run(run_sync(days_back=7))
print(json.dumps(result))
" 2>&1 | tee -a "$LOG_FILE"

echo "[$(date -Iseconds)] Sync complete." | tee -a "$LOG_FILE"

# Clean up logs older than 7 days
find /home/web3relic/otto/logs -name "vuln-sync-*.log" -mtime +7 -delete 2>/dev/null || true
