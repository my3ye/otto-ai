#!/usr/bin/env bash
# wire_solana_tracker.sh — Store Solana Tracker API key and verify connection
#
# Usage:
#   ./wire_solana_tracker.sh <api_key>
#
# What it does:
#   1. Adds SOLANA_TRACKER_API_KEY to ~/memory/.env
#   2. Tests the API connection
#   3. Logs confirmation to Otto memory API

set -euo pipefail

ENV_FILE="$HOME/memory/.env"
ALPHA_DIR="$HOME/otto/projects/alpha"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <solana_tracker_api_key>"
  exit 1
fi

API_KEY="$1"

echo "[wire] Storing SOLANA_TRACKER_API_KEY in $ENV_FILE..."

# Remove existing entry if present, then append fresh
if grep -q "SOLANA_TRACKER_API_KEY" "$ENV_FILE" 2>/dev/null; then
  # Update in place
  sed -i "s|^SOLANA_TRACKER_API_KEY=.*|SOLANA_TRACKER_API_KEY=${API_KEY}|" "$ENV_FILE"
  echo "[wire] Updated existing SOLANA_TRACKER_API_KEY entry."
else
  echo "" >> "$ENV_FILE"
  echo "# Solana Tracker (wallet PnL / re-qualification)" >> "$ENV_FILE"
  echo "SOLANA_TRACKER_API_KEY=${API_KEY}" >> "$ENV_FILE"
  echo "[wire] Added SOLANA_TRACKER_API_KEY to .env"
fi

chmod 600 "$ENV_FILE"

echo "[wire] Testing connection..."
cd "$ALPHA_DIR"
if [[ -d ".venv" ]]; then
  source .venv/bin/activate
fi

export SOLANA_TRACKER_API_KEY="$API_KEY"
python3 -c "
import sys, os
sys.path.insert(0, '${ALPHA_DIR}')
os.environ['SOLANA_TRACKER_API_KEY'] = '${API_KEY}'
from solana_tracker_client import test_connection
ok = test_connection()
if ok:
    print('[wire] Connection: OK — Solana Tracker API is live')
    sys.exit(0)
else:
    print('[wire] Connection: FAILED — check key or network')
    sys.exit(1)
"

echo "[wire] Logging to Otto memory..."
curl -s -X POST http://localhost:8100/semantic/remember \
  -H 'Content-Type: application/json' \
  -d "{
    \"content\": \"Solana Tracker API key registered and verified. SOLANA_TRACKER_API_KEY stored in ~/memory/.env. Integration ready: solana_tracker_client.py provides get_wallet_pnl() and score_wallet_st() replacing Birdeye for wallet re-qualification (free tier: 500K credits/month, 10 RPS).\",
    \"category\": \"infrastructure\",
    \"confidence\": 0.95
  }" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'[wire] Memory logged: {d.get(\"id\",\"?\")}' )" 2>/dev/null || true

echo ""
echo "Done. Next steps:"
echo "  1. Run wallet re-qualification: cd ${ALPHA_DIR} && python3 birdeye_requalification.py --score-only"
echo "     (update it to use solana_tracker_client instead of birdeye_client for wallet scoring)"
echo "  2. Start paper trader: python3 paper_trader.py --daemon"
