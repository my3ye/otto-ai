#!/usr/bin/env bash
# Otto Alpha Signal Launcher
# Checks wallet + Telegram config, then runs the signal publisher
#
# Usage:
#   ./alpha_signal_launcher.sh            # Publish new signals
#   ./alpha_signal_launcher.sh --test     # Post a test message
#   ./alpha_signal_launcher.sh --dry-run  # Print without posting
#   ./alpha_signal_launcher.sh --status   # Show config status only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$HOME/memory/.env"
PUBLISHER="$SCRIPT_DIR/signals/signal_publisher.py"

# Load env
if [[ -f "$ENV_FILE" ]]; then
    set -a
    # Only load key=value lines, handle multi-line PEM keys
    while IFS='=' read -r key val; do
        [[ "$key" =~ ^#.*$ ]] && continue
        [[ -z "$key" ]] && continue
        [[ "$key" != *"BEGIN"* ]] && export "$key"="$val" 2>/dev/null || true
    done < <(grep -v "^#" "$ENV_FILE" | grep -v "^$" | grep "^[A-Z_]*=")
    set +a
fi

MODE="${1:-}"

# ── Status check ───────────────────────────────────────────────
echo "=== Otto Alpha Signal Status ==="
echo ""

WALLET="${AGENT_WALLET_ADDRESS:-}"
TIP="${SIGNAL_TIP_WALLET:-}"
BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
CHANNEL="${TELEGRAM_CHANNEL:-}"

# Wallet
if [[ -n "$WALLET" ]]; then
    ETH_BAL=$(curl -s -X POST https://mainnet.base.org \
        -H "Content-Type: application/json" \
        -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_getBalance\",\"params\":[\"$WALLET\",\"latest\"],\"id\":1}" \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{int(d.get(\"result\",\"0x0\"),16)/1e18:.6f}')" 2>/dev/null || echo "0.000000")
    echo "Wallet:   $WALLET"
    echo "Network:  base-mainnet"
    echo "ETH bal:  $ETH_BAL ETH"
    echo "Explorer: https://basescan.org/address/$WALLET"
else
    echo "Wallet:   NOT CONFIGURED"
fi

echo ""

# Telegram
if [[ -n "$BOT_TOKEN" ]]; then
    echo "Telegram: CONFIGURED"
    echo "Channel:  ${CHANNEL:-not set}"
    echo "Bot:      @OttoTgBot (t.me/OttoTgBot)"
else
    echo "Telegram: NOT CONFIGURED"
    echo "  Set TELEGRAM_BOT_TOKEN in $ENV_FILE"
    echo "  Get token from: @BotFather on Telegram → /mybots → @OttoTgBot → API Token"
fi

echo ""

# ── Exit if just checking status ────────────────────────────────
if [[ "$MODE" == "--status" ]]; then
    exit 0
fi

# ── Abort if Telegram not configured ────────────────────────────
if [[ -z "$BOT_TOKEN" ]]; then
    echo "ERROR: TELEGRAM_BOT_TOKEN not set. Cannot post signals."
    echo ""
    echo "To configure:"
    echo "  1. Open Telegram → @BotFather"
    echo "  2. Send: /mybots"
    echo "  3. Select @OttoTgBot"
    echo "  4. API Token"
    echo "  5. Copy the token and add to $ENV_FILE:"
    echo "     TELEGRAM_BOT_TOKEN=<your-token>"
    echo ""
    echo "  Also create the channel:"
    echo "  1. Telegram → New Channel → Name: Otto Signals → @otto_signals"
    echo "  2. Add @OttoTgBot as administrator"
    exit 1
fi

# ── Run publisher ───────────────────────────────────────────────
echo "=== Running Signal Publisher ==="
python3 "$PUBLISHER" $MODE
