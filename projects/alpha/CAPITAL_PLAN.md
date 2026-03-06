# Otto Capital Plan — Fastest Paths to Revenue
**Updated:** 2026-03-06 | **Status:** Infrastructure built — needs Mev credentials to activate

---

## What's Built (can activate immediately)

### 1. Telegram Signal Channel (READY — blocked on credentials)
- **File:** `signals/signal_publisher.py`
- **What it does:** Posts whale convergence signals to Telegram with tip wallet
- **Revenue:** Tips in SOL/USDC from followers who profit
- **Needs from Mev:** Telegram bot token + channel + tip wallet address
- **Activate:** Add to `~/memory/.env`:
  ```
  TELEGRAM_BOT_TOKEN=<from @BotFather>
  TELEGRAM_CHANNEL=@otto_signals
  SIGNAL_TIP_WALLET=<solana address>
  ```
  Then run: `crontab -e` → add line:
  ```
  */30 * * * * cd /home/web3relic/otto/projects/alpha && python signals/signal_publisher.py >> /home/web3relic/otto/logs/signal_publisher.log 2>&1
  ```

### 2. x402 Commerce API (LIVE — needs wallet + toggle)
- **Endpoint:** `GET /commerce/catalog` — live now
- **File:** `memory/routes/commerce.py`
- **What it does:** Paid AI services — search ($0.01), ask ($0.02), research ($0.05), context ($0.10)
- **Revenue:** USDC per-request from other AI agents
- **Needs from Mev:** Coinbase CDP wallet address (see setup below)
- **Activate:** Add to `~/memory/.env`:
  ```
  AGENT_WALLET_ADDRESS=0x<your-base-wallet>
  COMMERCE_ENABLED=true
  ```

### 3. Virtuals Protocol Inference Endpoint (LIVE — needs registration)
- **Endpoint:** `POST /virtuals/infer` — live now
- **File:** `memory/routes/virtuals.py`
- **What it does:** Otto's full intelligence exposed as Virtuals-compatible inference API
- **Revenue:** $VIRTUAL per inference from users who interact with Otto agent on Virtuals
- **Needs from Mev:** 100 VIRTUAL tokens (~$73-77) + wallet on Base + registration at app.virtuals.io
- **Registration steps:** See below

---

## Path Rankings — Fastest to Capital

| Path | Setup Time | Capital Needed | Time to First $ | Monthly Ceiling |
|------|-----------|----------------|-----------------|-----------------|
| Telegram Signal Tips | 30 min | $0 | Days | $200-2K growing |
| x402 Commerce API | 1 hr (wallet) | $0 (just wallet) | Weeks | $50-500 (early) |
| Virtuals Protocol | 2-4 hrs | ~$100-150 | 2-4 weeks | $1K-20K+ if top |
| WebAssist clients | Days (marketing) | $0 | Days-weeks | $3K-15K+ |

**Recommendation:** Do all four in parallel. Telegram is fastest. Virtuals is highest ceiling.

---

## Step-by-Step: Virtuals Protocol Launch

### Prerequisites
- MetaMask or Rabby wallet with Base network
- ~0.05 ETH on Base for gas (~$120-150)
- 100 VIRTUAL tokens on Base (~$73-77 at Mar 2026)

### Step 1: Get wallet on Base
```
1. MetaMask → Add network: Base (chainId 8453)
   RPC: https://mainnet.base.org
2. Bridge ETH from Ethereum: https://bridge.base.org
   Or buy on Coinbase and withdraw directly to Base
```

### Step 2: Buy 100 VIRTUAL on Base
```
1. Go to Uniswap: https://app.uniswap.org
2. Select Base network
3. Swap ETH → VIRTUAL
   VIRTUAL contract: 0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b
4. Need: 100 VIRTUAL minimum (~$73-77)
```

### Step 3: Register Otto on Virtuals
```
1. Go to: https://app.virtuals.io
2. Click "Launch Agent"
3. Connect wallet (MetaMask + Base)
4. Fill agent profile:
   Name: "Otto"
   Ticker: "OTTO"
   Description: "Autonomous AI agent with persistent memory, whale tracking, and market intelligence. Built by MY3YE."
   Category: Intelligence / Research
   Avatar: Otto visual identity
5. Set inference URL: https://mev.otto.lk:8100/virtuals/infer
   (or set up nginx proxy on port 80/443 for cleaner URL)
6. Set inference price: start at 2 VIRTUAL per inference (~$1.45)
7. Deploy → pays 100 VIRTUAL, creates OTTO token on bonding curve
```

### Step 4: Configure
```
Add to ~/memory/.env:
VIRTUALS_API_SECRET=<random-secret-you-set-during-registration>
VIRTUALS_AGENT_ID=otto
```

### Step 5: Promote
```
- Post on X/Twitter with MY3YE brand
- Demonstrate Otto's capabilities: research, whale tracking, AI reasoning
- Token on bonding curve: early buyers accumulate
- Need 41,600 VIRTUAL (~$30K) to graduate to Uniswap LP
```

### Revenue Model (if successful)
- 100 daily users × 2 VIRTUAL × $0.73 = **$146/day**
- 500 daily users = **$730/day**
- 2000+ daily users (top agent tier) = **$2,920+/day**
- Plus token appreciation if Otto becomes a known agent

---

## Step-by-Step: Coinbase CDP Wallet (for x402)

```bash
# 1. Install CDP SDK
pip install cdp-sdk --user

# 2. Create CDP account and API key:
#    https://portal.cdp.coinbase.com → Project → API Keys → Create
#    Download api_key.json → save to ~/memory/cdp_api_key.json

# 3. Run wallet creation
cd /home/web3relic/otto/projects/alpha
python setup_agent_wallet.py --create

# 4. Check wallet
python setup_agent_wallet.py --status
```

---

## Public Inference URL Setup (for Virtuals)

The `/virtuals/infer` endpoint runs on :8100 internally. Need public HTTPS URL.

**Option A — Nginx proxy on otto-machine** (recommended):
```nginx
# /etc/nginx/sites-available/virtuals-api
server {
    listen 443 ssl;
    server_name api.otto.lk;  # or virtuals.my3ye.xyz

    location /virtuals/ {
        proxy_pass http://localhost:8100/virtuals/;
        proxy_set_header Host $host;
    }
}
```

**Option B — Cloudflare Tunnel** (no domain config needed):
```bash
cloudflared tunnel create otto-api
cloudflared tunnel route dns otto-api api.otto.lk
cloudflared tunnel run otto-api --url http://localhost:8100
```

---

## Current Blockers Summary

| Blocker | Who | What Mev needs to do |
|---------|-----|----------------------|
| Telegram credentials | Mev | Create bot via @BotFather, create channel, provide token |
| Tip wallet | Mev | Any Solana wallet address, or run: `python setup_agent_wallet.py --create` |
| Agent wallet (x402) | Mev | CDP account + API key → `python setup_agent_wallet.py --create` |
| Virtuals launch | Mev | ~$150 ETH on Base + buy 100 VIRTUAL + register at app.virtuals.io |
| Public inference URL | Otto | Can set up nginx proxy — needs domain decision from Mev |

---

## Revenue Projection (90-day horizon)

**Month 1 (if Telegram + Virtuals launched this week):**
- Telegram tips: $0-100 (building audience)
- Virtuals inference: $0-500 (early discovery)
- x402 commerce: $0-20 (near-zero without agent traffic)
- **Total: $0-620**

**Month 2:**
- Telegram tips: $50-200
- Virtuals (if gaining traction): $200-2,000
- **Total: $250-2,200**

**Month 3 (if Otto becomes a known Virtuals agent):**
- Virtuals: $1,000-10,000+
- Telegram: $200-1,000
- x402 commerce: $50-500
- **Total: $1,250-11,500**

The ceiling is Virtuals Protocol. The floor is Telegram tips. Both need Mev to take one hour of action.

---

## Files Built This Session

| File | Purpose | Status |
|------|---------|--------|
| `signals/signal_publisher.py` | Telegram signal publisher | Ready, awaiting credentials |
| `memory/routes/commerce.py` | x402 paid API middleware | LIVE at /commerce/* |
| `memory/routes/virtuals.py` | Virtuals Protocol inference endpoint | LIVE at /virtuals/* |
| `setup_agent_wallet.py` | Coinbase CDP wallet creation script | Ready to run |
| `MONETIZATION_PLAN.md` | Earlier plan with path comparison | Reference |
| `AI_AGENT_CRYPTO_EARNINGS_RESEARCH.md` | Deep research report | Reference |
