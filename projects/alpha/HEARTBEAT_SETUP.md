# Project Alpha — 30-Minute Heartbeat Setup

**Status: READY — awaiting Mev approval to activate**

## What Was Created

### 1. `/etc/systemd/system/otto-alpha-heartbeat.timer`
Fires every 30 minutes (`OnCalendar=*:0/30`), with up to 60 seconds of jitter.
Persistent=true means it catches up missed runs after a reboot.

### 2. `/etc/systemd/system/otto-alpha-heartbeat.service`
Runs as `web3relic`, depends on `otto-memory.service`, 5-minute timeout.
Calls the runner script below.

### 3. `/home/web3relic/otto/projects/alpha/alpha_heartbeat.sh`
Shell runner — same pattern as the hourly heartbeat. Uses a lock file to prevent overlaps.
Calls Claude Code CLI with `--agent alpha_heartbeat`, budget capped at **$0.30/cycle**.

### 4. `/home/web3relic/otto/.claude/agents/alpha_heartbeat.md`
The agent prompt. Each 30-minute cycle it will:
- Load wallet list from `projects/alpha/wallets.json`
- Scan up to 10 wallets via Helius RPC (last 20 txns each, filtered to past 30 min)
- Score signals: HIGH / MEDIUM / LOW
- Log all findings to memory (`/episodic/events`)
- Append raw signals to `projects/alpha/signals.jsonl`
- Send WhatsApp alert to Mev **only** for HIGH signals

## Cost Estimate

| Metric | Value |
|---|---|
| Budget per cycle | $0.30 (Sonnet) |
| Cycles per day | 48 |
| Max daily cost | ~$14.40 |
| Typical daily cost | ~$4–8 (most cycles will be fast) |

> Note: Actual cost depends on how active the wallet list is. Consider setting a daily cap once live.

## Activation Instructions (for Mev)

When ready to go live, run:
```bash
sudo systemctl enable --now otto-alpha-heartbeat.timer
systemctl list-timers | grep alpha
```

To check logs:
```bash
ls -t ~/otto/logs/alpha-heartbeat-*.log | head -1 | xargs cat
```

To stop:
```bash
sudo systemctl stop otto-alpha-heartbeat.timer
sudo systemctl disable otto-alpha-heartbeat.timer
```

## Prerequisite: Wallet List

The agent requires a wallet list before it can scan anything:
```
/home/web3relic/otto/projects/alpha/wallets.json
```

Expected format:
```json
[
  {"address": "wallet_pubkey_here", "label": "Known Alpha Whale 1", "priority": 10},
  {"address": "wallet_pubkey_here", "label": "Top Solana Trader", "priority": 8}
]
```

Without this file, the agent will log a warning and skip scanning gracefully.

## Prerequisite: Helius API Key

The agent reads `HELIUS_API_KEY` from `~/memory/.env`. Confirm this key is present before enabling the timer.

```bash
grep HELIUS_API_KEY ~/memory/.env
```

If missing, add it:
```bash
echo 'HELIUS_API_KEY=your_key_here' >> ~/memory/.env
```

## What's NOT Done Yet (Needs Mev Input)

1. **Wallet list** — no smart money wallets loaded yet. Need Mev to provide initial list or approve auto-discovery approach.
2. **Signal thresholds** — currently hardcoded at $10k+ for HIGH. Adjust in agent prompt if needed.
3. **Timer activation** — intentionally not enabled. Mev must run `enable --now`.

---
*Setup completed by Otto task queue, 2026-02-19.*
