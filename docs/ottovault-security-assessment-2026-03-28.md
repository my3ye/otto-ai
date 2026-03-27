# OttoVault Security Assessment — Pre-Build Audit

**Date**: 2026-03-28
**Scope**: OttoVault AI-Driven Regime-Adaptive USDC Vault (Solana/Voltr)
**TVL Target**: Up to $1M (hackathon seed capital)
**Architecture**: Off-chain TypeScript keeper + Voltr SDK (no custom Anchor program)
**Risk Rating**: MEDIUM-HIGH (real TVL, off-chain keeper has fund-moving authority)

---

## 1. Architecture Security Profile

### What We Control (Attack Surface)

| Component | Type | Risk Level | Reason |
|-----------|------|------------|--------|
| **Manager keypair** | Off-chain secret | **CRITICAL** | Full authority to move vault funds between strategies |
| **Keeper service** (`src/index.ts`) | Off-chain process | **HIGH** | Makes all rebalance decisions — compromise = fund drain |
| **Signal collectors** | Off-chain data ingestion | **MEDIUM** | Manipulated signals → bad regime classification → losses |
| **Circuit breakers** | Off-chain logic | **MEDIUM** | Bypass = remove safety rails |
| **Monitoring/alerting** | Off-chain | **LOW** | Failure = delayed detection, not direct loss |

### What We Don't Control (Trust Dependencies)

| Component | Trust Level | Risk |
|-----------|-------------|------|
| **Voltr Vault Program** (`vVoLTR...`) | HIGH — audited, production | Voltr bugs could affect all vaults |
| **Adaptor Programs** (Drift, Kamino, Jupiter, Save) | HIGH — audited by respective teams | CPI bugs in adaptors |
| **Underlying protocols** (Drift, Kamino, etc.) | HIGH — billions in TVL | Protocol exploits drain strategy positions |
| **Pyth Oracle** | HIGH — industry standard | Oracle manipulation is the #1 DeFi attack vector |
| **Solana RPC (Helius)** | MEDIUM | RPC manipulation or downtime |

---

## 2. Attack Vectors — Ranked by Severity

### CRITICAL — Manager Key Compromise

**Vector**: The manager keypair has full authority to call `createDepositStrategyIx()` and `createWithdrawStrategyIx()` on the Voltr vault. If this key is compromised, an attacker can:
- Withdraw all vault capital from strategies back to the vault
- Potentially redirect funds if Voltr allows manager withdrawals to arbitrary addresses (needs verification)
- Register malicious adaptors and deposit to attacker-controlled programs

**Likelihood**: MEDIUM (single key on a cloud VM)
**Impact**: TOTAL LOSS ($1M)

**Mitigations Required**:
- [ ] **M1**: Store keypair in encrypted file (not plaintext `.env`). Use `solana-keygen` with password protection.
- [ ] **M2**: Use a dedicated hot wallet with ONLY the keypair for vault management — no other assets.
- [ ] **M3**: Set up a 2-of-3 multisig as vault admin (Squads Protocol) if Voltr supports admin transfer. Manager key is then a hot operator key with limited authority.
- [ ] **M4**: Implement IP allowlisting on the Helius RPC endpoint.
- [ ] **M5**: File permissions: `chmod 600` on keypair file, owned by dedicated service user.
- [ ] **M6**: Never commit keypair to git. Add to `.gitignore` explicitly.
- [ ] **M7**: Rotate keypair if VM is ever accessed by unauthorized parties.

---

### CRITICAL — Oracle Manipulation / Stale Data

**Vector**: The regime classifier depends on Pyth prices and Drift funding rates. Manipulated or stale oracle data causes:
- **False TRENDING detection** → vault opens basis trades in a ranging/stress market → losses
- **False STRESS detection** → vault exits profitable positions prematurely → opportunity cost
- **Stale prices during rebalance** → vault sells/buys at wrong valuations

**Likelihood**: LOW for Pyth manipulation (requires significant capital), MEDIUM for staleness (Solana congestion events)
**Impact**: HIGH (5-20% loss depending on regime misclassification)

**Mitigations Required**:
- [ ] **M8**: Oracle staleness check: reject ANY signal with `slot_age > 20 slots` (~8 seconds). Architecture doc says 5 minutes — **this is too loose for $1M TVL**. Tighten to 30 seconds max.
- [ ] **M9**: Cross-validate Pyth prices against Drift mark price and DEX spot (Jupiter). If >1% divergence, halt rebalancing.
- [ ] **M10**: Never use a single oracle source for any critical decision. Require 2-of-3 agreement (Pyth, Drift mark, Jupiter spot).
- [ ] **M11**: Add a `CONFIDENCE_THRESHOLD` for Pyth price feeds — reject prices with confidence interval > 2%.
- [ ] **M12**: Log all oracle readings. If retroactive manipulation is suspected, have audit trail.

---

### HIGH — Keeper Service Compromise / Logic Bug

**Vector**: The keeper is an off-chain TypeScript process with full rebalance authority. Risks:
- **Code injection**: Dependency supply chain attack (npm packages) injects malicious rebalance calls
- **Logic bug**: Regime classifier error → perpetual TRENDING → overleveraged basis trades → liquidation
- **Infinite loop**: Rebalance thrashing between strategies burns transaction fees and creates slippage
- **Race condition**: Multiple keeper instances running simultaneously issue conflicting rebalances

**Likelihood**: MEDIUM (npm supply chain risk is real, logic bugs are common in new code)
**Impact**: HIGH (gradual drain through bad trades or fee burn)

**Mitigations Required**:
- [ ] **M13**: Lock all npm dependencies with exact versions in `package-lock.json`. Run `npm audit` before every deploy.
- [ ] **M14**: Single-instance enforcement: use a PID lockfile or on-chain nonce to prevent concurrent keepers.
- [ ] **M15**: Maximum transaction value per cycle: cap any single rebalance at 25% of vault equity. Never move >25% in one 15-minute cycle.
- [ ] **M16**: Rate limiter: max 10 rebalance transactions per hour (already in architecture — enforce it).
- [ ] **M17**: Sanity check on all signal values before classification: reject if any value is `NaN`, `Infinity`, negative where impossible, or >10x historical range.
- [ ] **M18**: Add a `KILL_SWITCH` environment variable that, when set, halts all rebalancing immediately.

---

### HIGH — Drift Perpetual Position Risks

**Vector**: Basis trades on Drift involve short perpetual positions. Specific risks:
- **Liquidation**: If SOL/BTC price moves sharply against the short and collateral is insufficient
- **Funding rate flip**: Short pays funding instead of receiving it — position bleeds
- **Oracle lag**: Drift mark price diverges from spot → unfavorable liquidation price
- **Insurance fund shortfall**: Drift insurance fund depleted → socialized losses

**Likelihood**: MEDIUM (crypto vol events happen regularly)
**Impact**: HIGH (up to 50% of vault in basis trades per architecture)

**Mitigations Required**:
- [ ] **M19**: Hard health factor floor: if Drift account health drops below 1.20 (not 1.10 as in architecture), reduce leverage immediately. 1.10 is one bad candle from liquidation.
- [ ] **M20**: Funding rate monitoring: if funding flips sign AND magnitude > 0.01%/h, close basis position within 1 cycle (15 min). Don't wait for the regime classifier.
- [ ] **M21**: Maximum leverage cap: 1.5x, not 1.8x as proposed. At $1M TVL, the 0.3x difference is $300K of additional risk exposure for marginal yield improvement.
- [ ] **M22**: Pre-calculate liquidation prices for every basis position and alert if current price is within 15% of liquidation.
- [ ] **M23**: Never have >40% of vault in basis trades (architecture says 50% max — reduce to 40%).

---

### HIGH — Rebalance Front-Running / MEV

**Vector**: When the keeper sends rebalance transactions to the Solana network:
- **Sandwich attacks**: MEV bots see the keeper's pending deposit/withdraw and front-run with opposing trades
- **Transaction reordering**: Solana validators can reorder within a block, though Solana's continuous block production reduces this vs Ethereum

**Likelihood**: MEDIUM (Solana MEV is growing, Jito bundles are used for sandwich attacks)
**Impact**: MEDIUM (slippage on each rebalance, compounds over time — 1-5% annual drag)

**Mitigations Required**:
- [ ] **M24**: Use Jito bundles for rebalance transactions to ensure atomic execution and prevent sandwich attacks.
- [ ] **M25**: Gradual rebalancing (25% per cycle) is already designed — this naturally limits MEV extraction per transaction.
- [ ] **M26**: Set strict slippage limits on all swaps: max 0.5% for USDC pairs.
- [ ] **M27**: Add transaction simulation before submission — if simulated output differs from expected by >1%, abort.
- [ ] **M28**: Voltr's `lockedProfitDegradation` (24h linear unlock) already mitigates deposit-side sandwich. Verify this is working.

---

### MEDIUM — Flash Loan Attack Surface

**Vector**: Classic flash loan attacks borrow large amounts within a single transaction to manipulate prices/rates, then repay.

**Assessment for OttoVault**: **LOW direct risk** because:
1. The keeper is off-chain — it reads state across multiple transactions, not within one
2. No custom Anchor program = no on-chain logic to exploit atomically
3. Voltr's vault program likely has re-entrancy guards (needs verification)

**Residual risk**: Flash loans can manipulate the *inputs* the keeper reads:
- Temporarily spike Drift funding rates
- Temporarily distort lending utilization rates
- These manipulated readings could trigger a bad regime classification

**Mitigations Required**:
- [ ] **M29**: Use TWAP/EMA for all signal inputs, not spot values. Minimum 15-minute EMA for funding rates, 1-hour EMA for volatility. Single-block readings are manipulable.
- [ ] **M30**: Require regime changes to persist for ≥2 consecutive readings (30 minutes) before acting. Prevents flash-loan-induced false regime transitions.

---

### MEDIUM — Lending Protocol Risks

**Vector**: USDC deposited into Kamino, Jupiter Lend, Save, and Marginfi faces:
- **Protocol exploit**: Smart contract bug drains lending pool
- **Utilization spike**: All borrowers exit → high utilization → cannot withdraw
- **Bad debt**: Undercollateralized loans default, socializing losses to lenders
- **Protocol upgrade**: Unexpected migration or parameter change

**Likelihood**: LOW per protocol (audited, high TVL), but MEDIUM across 4 protocols (4x exposure surface)
**Impact**: MEDIUM-HIGH (up to 40% loss if one protocol is exploited while holding 25% max allocation)

**Mitigations Required**:
- [ ] **M31**: Maximum 25% concentration per lending protocol (already in architecture — enforce strictly).
- [ ] **M32**: Monitor withdrawal liquidity: before depositing, verify `available_liquidity > 2x deposit amount`. If not, skip that protocol.
- [ ] **M33**: Maintain 20% minimum in the most battle-tested protocol (Kamino, $3.5B TVL) as a reserve floor.
- [ ] **M34**: Monitor protocol governance for upgrade proposals. If a protocol announces a migration, withdraw preemptively.

---

### MEDIUM — RPC Provider Dependency

**Vector**: The keeper relies on Helius RPC to read on-chain state and submit transactions. If Helius:
- Goes down → keeper is blind and cannot rebalance
- Returns stale data → keeper makes decisions on outdated state
- Is compromised → keeper receives manipulated data

**Likelihood**: LOW (Helius is reliable), but single point of failure
**Impact**: MEDIUM (keeper paralysis during market events when rebalancing matters most)

**Mitigations Required**:
- [ ] **M35**: Configure a fallback RPC provider (e.g., Triton, public Solana RPC) for reads if primary fails.
- [ ] **M36**: Health check RPC before every keeper cycle — verify slot is current (within 10 of tip).
- [ ] **M37**: If RPC is unreachable for >2 cycles (30 min), alert via WhatsApp and halt rebalancing.

---

### LOW — Keeper Service Availability

**Vector**: The keeper runs on otto-machine (single GCP VM). If the VM goes down:
- Existing positions stay open (Drift shorts continue, lending continues earning)
- No rebalancing occurs — positions drift from target allocation
- In a stress event, no circuit breakers fire

**Likelihood**: LOW (GCP VMs are reliable)
**Impact**: MEDIUM in stress events, LOW otherwise

**Mitigations Required**:
- [ ] **M38**: External uptime monitor (UptimeRobot or similar) pinging `:8200/status` endpoint.
- [ ] **M39**: Systemd service with auto-restart on crash.
- [ ] **M40**: If keeper is down >1 hour during high volatility, manually trigger STRESS regime via `/force-rebalance`.

---

## 3. Voltr-Specific Security Considerations

### Authority & Signer Model

The Voltr vault has a **manager** authority that controls:
- Adding/removing adaptors
- Depositing/withdrawing from strategies
- Fee configuration

**Critical verification needed before build**:
- [ ] **V1**: Can the manager withdraw vault funds to an arbitrary address, or only between strategies? If arbitrary withdrawal is possible, the manager key effectively controls all TVL.
- [ ] **V2**: Does Voltr support admin transfer / timelock on manager changes?
- [ ] **V3**: Is there a withdrawal delay for vault depositors? (Needed to prevent bank-run scenarios.)
- [ ] **V4**: Does Voltr enforce any per-transaction limits, or is the manager fully trusted?
- [ ] **V5**: Verify that `lockedProfitDegradation` (24h linear unlock) cannot be bypassed by the manager.

### Adaptor Trust Model

Each adaptor is a separate Solana program that the vault CPIs into. The vault trusts adaptors to:
- Correctly report position values (via `set_return_data()`)
- Not steal deposited funds
- Handle edge cases (zero liquidity, protocol paused, etc.)

**Risk**: A malicious or buggy adaptor can report inflated position values → vault believes it has more assets than it does → new deposits are diluted → existing depositors lose value.

**Mitigation**:
- [ ] **V6**: Only use Voltr's official, audited adaptors (Drift: `EBN93...`, Kamino: `to6Eti...`, Jupiter: `EW35UR...`, Save/Solend: `aVoLTR...`). Never add unaudited third-party adaptors.
- [ ] **V7**: Cross-validate adaptor-reported values against independent on-chain state reads. If adaptor says position = $100K but independent read says $90K, alert and investigate.

---

## 4. Security Checklist — Pre-Deployment

### Phase 1 (Foundation) — Must Complete Before Any Funds

- [ ] Manager keypair generated securely, stored encrypted, `chmod 600`
- [ ] `.gitignore` includes `*.json` keypairs, `.env`, any secret files
- [ ] All npm dependencies pinned to exact versions, `npm audit` clean
- [ ] Single-instance lockfile mechanism implemented
- [ ] RPC health check before every keeper cycle
- [ ] Basic logging of all keeper decisions and transactions

### Phase 2 (Strategy) — Must Complete Before Devnet Testing

- [ ] Oracle staleness check: reject data >30 seconds old
- [ ] Signal sanity validation: reject NaN, Infinity, out-of-range values
- [ ] Regime change requires 2 consecutive readings (30-min persistence)
- [ ] All signal inputs use EMA/TWAP, not raw spot values
- [ ] Per-cycle rebalance cap: max 25% of vault equity moved
- [ ] Rate limiter: max 10 rebalance txs per hour
- [ ] Drift health factor floor: 1.20 (not 1.10)
- [ ] Maximum leverage: 1.5x (not 1.8x)
- [ ] Maximum basis trade allocation: 40% (not 50%)
- [ ] Transaction simulation before submission
- [ ] Slippage limits: 0.5% max on all operations

### Phase 3 (Production) — Must Complete Before Mainnet with Real TVL

- [ ] Verify Voltr manager authority model (V1-V5 above)
- [ ] Cross-validate adaptor position values against independent reads
- [ ] Jito bundle integration for MEV protection
- [ ] Fallback RPC provider configured
- [ ] External uptime monitoring on keeper
- [ ] Kill switch tested and documented
- [ ] WhatsApp alerting on all circuit breaker activations
- [ ] 24h devnet soak test with simulated stress scenarios
- [ ] Drawdown limits tested: -3%, -5%, -8% triggers verified
- [ ] Full keeper cycle load test (100+ cycles without drift or memory leak)

### Post-Deployment — Ongoing Monitoring

- [ ] Daily NAV reconciliation: compare keeper's internal state vs on-chain positions
- [ ] Weekly review of all regime transitions and rebalance decisions
- [ ] Monitor npm advisory feeds for dependency vulnerabilities
- [ ] Track slippage on rebalance transactions — flag if >0.3% average
- [ ] Monitor Voltr governance for program upgrades

---

## 5. Recommended Audit Points (Pre-Competition / Pre-TVL)

If time allows, these are the highest-value audit targets:

1. **Manager key handling code** — verify keypair is never logged, never included in error messages, never sent over network
2. **Rebalance executor** — verify transaction construction is correct, amounts are calculated properly (watch for integer overflow/underflow in u64 arithmetic)
3. **Regime classifier** — fuzz with extreme values, verify no undefined behavior
4. **Circuit breaker logic** — verify breakers cannot be bypassed by rapid sequential calls
5. **Voltr SDK calls** — verify all required accounts are passed correctly (wrong account ordering is a top Solana bug class)

---

## 6. Risk Summary

| Category | Pre-Mitigation | Post-Mitigation | Notes |
|----------|---------------|-----------------|-------|
| Manager key compromise | CRITICAL | HIGH | Multisig would reduce to MEDIUM but adds complexity |
| Oracle manipulation | HIGH | MEDIUM | TWAP + cross-validation + persistence requirement |
| Keeper logic bugs | HIGH | MEDIUM | Sanity checks + caps + single-instance + simulation |
| Drift liquidation | HIGH | MEDIUM | Lower leverage + tighter health floor + faster exit |
| MEV/front-running | MEDIUM | LOW | Jito bundles + gradual rebalancing + slippage limits |
| Flash loan signals | MEDIUM | LOW | EMA inputs + 2-reading persistence |
| Lending protocol risk | MEDIUM | MEDIUM | Diversification helps but can't eliminate protocol risk |
| RPC dependency | MEDIUM | LOW | Fallback provider + health checks |
| Keeper downtime | LOW | LOW | Auto-restart + monitoring |

**Overall assessment**: The architecture is sound for a hackathon submission. The biggest risk is the manager keypair — it's a single hot key on a shared VM with full authority over up to $1M. For hackathon purposes this is acceptable; for production beyond the competition, a multisig or Squads-based authority structure is essential.

The off-chain keeper design actually *reduces* on-chain attack surface compared to a custom Anchor program — there's no on-chain code to exploit. The trade-off is that all trust concentrates in the keeper process and its operator key.

---

## 7. Priority Actions (Ranked)

| Priority | Action | When | Cost |
|----------|--------|------|------|
| **P0** | Secure manager keypair (encrypted, chmod 600, gitignored) | Phase 1 Day 1 | 0 |
| **P0** | Pin npm dependencies, run audit | Phase 1 Day 1 | 0 |
| **P1** | Implement oracle staleness + sanity checks | Phase 2 Day 4 | ~$0.50 |
| **P1** | Add EMA smoothing to all signal inputs | Phase 2 Day 4 | ~$0.50 |
| **P1** | Implement per-cycle rebalance caps | Phase 2 Day 5 | ~$0.25 |
| **P1** | Single-instance lockfile + kill switch | Phase 2 Day 5 | ~$0.25 |
| **P2** | Drift health floor at 1.20 + leverage cap at 1.5x | Phase 2 Day 5 | ~$0.25 |
| **P2** | Transaction simulation before submission | Phase 2 Day 5 | ~$0.50 |
| **P2** | Regime persistence (2 readings before transition) | Phase 2 Day 4 | ~$0.25 |
| **P3** | Jito bundle integration | Phase 3 Day 7 | ~$0.50 |
| **P3** | Fallback RPC + external monitoring | Phase 3 Day 7 | ~$0.25 |
| **P3** | Cross-validate adaptor values | Phase 3 Day 7 | ~$0.50 |

**Total security implementation overhead: ~$3.75** (fits within the $25.50 budget)
