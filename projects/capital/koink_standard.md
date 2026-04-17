# The $KOINK Standard
## A Fork-Ready Tokenomics Template for Fair, Contribution-Governed Token Launches

**Version:** 1.0
**Published:** 2026-03-17
**Author:** MY3YE / Koink.fun
**Status:** Open Standard (publish, fork, deploy)
**License:** Open Copyright — use freely, contribute back

---

## Abstract

The $KOINK Standard is an open tokenomics template designed to fix the most common failures in token launches:

1. **Snipers capture launch value** before real users arrive
2. **Whales dominate governance** through capital concentration
3. **Dumps tank price** in the critical early period
4. **Treasury gets drained** by insiders or captured by a single faction
5. **Long-term believers have no more power** than 5-minute holders

Any project can adopt the $KOINK Standard. It is chain-agnostic, open-source, and battle-tested in the Koink.fun ecosystem. This document defines the 5 principles, provides a Solana/Anchor reference implementation, and explains how to deploy on Base and Polkadot.

---

## The 5 Principles

```
┌──────────────────────────────────────────────────────────┐
│               THE $KOINK STANDARD PRINCIPLES              │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  1. FAIR LAUNCH        No snipers. No insider edge.       │
│                        VRF-based slot assignment.         │
│                                                           │
│  2. MERIT DISTRIBUTION Tokens earned via contribution,    │
│                        not just purchased.                │
│                                                           │
│  3. ANTI-WHALE         Hard caps + graduated sell tax.    │
│     MECHANICS          Capital can't buy governance.      │
│                                                           │
│  4. CONTRIBUTION       Weight = time + actions taken.     │
│     GOVERNANCE         Not token balance alone.           │
│                                                           │
│  5. COMMUNITY          20% of sell taxes to DAO.         │
│     TREASURY           Community-governed, transparent.   │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

A project that implements all 5 principles is a **$KOINK Standard compliant** deployment. Projects may implement a subset (e.g., just Principle 1 + 3), but full compliance is the recommended path.

---

## Principle 1: Fair Launch

### The Problem

MEV bots, insider tip-offs, and mempool monitoring give certain actors a head start at every token launch. By the time real community members can buy, the supply is already concentrated in extractive hands.

### The Solution: VRF-Based Slot Assignment

**Verifiable Random Functions (VRF)** generate cryptographically provable random numbers on-chain. No one — not the deployer, not validators, not bots — can predict or influence the output.

**Mechanism:**

```
Every wallet that registers intent to participate receives a random launch slot.
No two wallets share the same slot. No one knows their slot until the block arrives.

Registration Period         Launch Window
      │                          │
      │   Wallet A  ──► VRF ──►  Slot 1247  (Block 1247 ± 3)
      │   Wallet B  ──► VRF ──►  Slot 0892  (Block 0892 ± 3)
      │   Wallet C  ──► VRF ──►  Slot 2031  (Block 2031 ± 3)
      │
      └── No wallet can buy before its assigned slot
```

**Key properties:**
- Registration is open and permissionless
- Slot assignments are on-chain and publicly verifiable
- The ±3 block tolerance accommodates normal network variance
- No wallet can participate in another wallet's slot

**Block-based time (not timestamp):**
All timing uses block height, not `block.timestamp`. Validators can manipulate `block.timestamp` by ±30 seconds — enough to game time-sensitive mechanics. Block height is immutable once finalized.

---

## Principle 2: Merit-Based Distribution

### The Problem

Most token distributions reward early buyers and insiders. The community gets the smallest allocation and the worst price.

### The Solution: Earned Allocation

The majority allocation (40% in the reference implementation) is **earned**, not sold.

**Earning mechanisms:**
- Code contributions (merged to official repo)
- Content creation (verified reach/impact)
- Governance participation (voting, proposing)
- Community building (verified onboarding)
- Long-term holding (Diamond Hands Multiplier)

**Verification layer:**
Contribution scoring must be:
- On-chain verifiable (or anchored to immutable proof)
- Transparent (anyone can audit the methodology)
- Not gameable by the team (DPC-governed scoring rules)

**Reference distribution:**
```
Community (earned)    40%   ████████████████
Treasury (DAO)        20%   ████████
Team (2yr vest)       15%   ██████
LP (locked)           15%   ██████
Ecosystem Grants      10%   ████
```

Adopt or adjust proportions — but the community allocation must be the largest.

---

## Principle 3: Anti-Whale Mechanics

### The Problem

Whales accumulate 5-20% of supply in the first hour. Price pumps, they dump, community bagholders are left holding worthless tokens.

### The Solution: Caps + Graduated Tax

**Hard buy caps (launch period):**
```
First 24 hours:   max 0.1% of total supply per wallet
First 7 days:     max 0.3% of total supply per wallet
After 7 days:     uncapped (organic accumulation)
```

This is enforced at contract level — no override, no exception.

**Graduated sell tax:**
```
Days 0-1:    0%   (grace period — no penalty for immediate exit)
Days 2-7:    5%   (early sellers pay moderate cost)
Days 8-14:   8%
Days 15-21:  12%
Days 22-30:  15%  (peak discouragement of early dump)
Days 31+:    Decay → 3% stable rate
```

**Sell tax split:**
```
Sell Tax
   │
   ├── 20% ──► Community Treasury
   ├── 50% ──► LP Reinforcement
   └── 30% ──► Burn (permanent)
```

**Why 0% on Day 0-1?**
This prevents a perverse incentive where "I'll just buy and immediately sell to capture the 0% window" becomes a dominant strategy. The 0% grace period acknowledges that some early buyers will change their mind — and that's fine. The sell tax is for discouraging prolonged speculation, not punishing genuine mistakes.

---

## Principle 4: Contribution Governance

### The Problem

Token-weighted governance = plutocracy. The biggest bag wins every vote.

### The Solution: Contribution-Weighted Votes

**Governance weight formula:**

```
weight = token_balance
       × diamond_hands_multiplier
       × contribution_score_multiplier
       × alignment_score_multiplier

Where:
  diamond_hands_multiplier  = 1.0 + (months_held / 12) × 2.0
                              (1x at launch → 3x at 12 months)

  contribution_score_mult   = 0.5 + (contribution_points / max_points) × 1.5
                              (0.5x floor → 2x ceiling)

  alignment_score_mult      = 0.8 + (alignment_score / 100) × 0.4
                              (0.8x floor → 1.2x ceiling, measured on-chain)
```

**Diamond Hands Multiplier:**
```
┌──────────────┬──────────────────────────────────────────┐
│ Hold Duration│ Governance Weight                        │
├──────────────┼──────────────────────────────────────────┤
│ Launch       │ 1.0x ████                                │
│ 3 months     │ 1.5x ██████                              │
│ 6 months     │ 2.0x ████████                            │
│ 9 months     │ 2.5x ██████████                          │
│ 12 months    │ 3.0x ████████████                        │
└──────────────┴──────────────────────────────────────────┘
  Non-transferable. Resets on full position exit.
  Partial sells (<20%) do not reset the multiplier.
```

**Why non-transferable?**
The multiplier is a function of commitment, not capital. If it were transferable, whales would buy multiplied wallets instead of earning them.

---

## Principle 5: Community Treasury

### The Problem

Protocol revenue accumulates in team multisigs. Community has no ownership over the value they helped create.

### The Solution: On-Chain Treasury with DPC Governance

**Treasury funding:**
- 20% of all sell taxes
- Protocol fees (optional per implementation)
- Ecosystem partnership fees

**Governance:**
- Any holder may propose an allocation
- Voting uses contribution-weighted weight (Principle 4)
- Quorum: 10% of circulating supply
- Approval: 60% yes vote
- Time-lock: 48 hours after approval before execution

**Transparency requirements for $KOINK Standard compliance:**
- All treasury transactions on-chain
- Monthly summary published (IPFS-anchored)
- Audit trail linkable to individual proposal IDs

---

## Reference Implementation: Solana / Anchor

The following pseudocode outlines the core contracts. Full implementation is in the Koink.fun GitHub.

### Account Structures

```rust
// Solana / Anchor pseudocode

#[account]
pub struct TokenConfig {
    pub total_supply: u64,           // 1_000_000_000 * 10^9 (lamports)
    pub sell_tax_bps: u16,           // Current sell tax (basis points)
    pub launch_block: u64,           // Block height of launch
    pub hard_cap_24h_bps: u16,       // Max buy per wallet first 24h (bps of supply)
    pub hard_cap_7d_bps: u16,        // Max buy per wallet first 7d (bps of supply)
    pub treasury: Pubkey,            // PDA for community treasury
    pub dpc_authority: Pubkey,       // 505 Systems DPC multisig
    pub admin: Pubkey,               // Deployer (limited post-launch powers)
}

#[account]
pub struct WalletState {
    pub owner: Pubkey,
    pub balance: u64,
    pub launch_slot: u64,            // VRF-assigned launch slot
    pub hold_since_block: u64,       // Block when current position started
    pub contribution_score: u32,     // Contribution points (0-10000)
    pub alignment_score: u8,         // Alignment score (0-100)
    pub total_purchased_24h: u64,    // Tracks hard cap compliance
    pub total_purchased_7d: u64,
    pub last_sell_block: u64,        // For partial-sell multiplier protection
}

#[account]
pub struct VrfResult {
    pub wallet: Pubkey,
    pub assigned_slot: u64,          // Block height for this wallet's launch window
    pub fulfilled: bool,             // Has VRF been fulfilled?
    pub randomness: [u8; 32],        // Raw VRF output (verifiable)
}
```

### Core Functions

```rust
// Fair launch: assign VRF slot
pub fn register_for_launch(ctx: Context<Register>) -> Result<()> {
    // Request VRF from Switchboard oracle
    let vrf_account = &ctx.accounts.vrf;
    let request_params = VrfRequestRandomnessParams {
        authority: ctx.accounts.authority.key(),
        // ... vrf params
    };

    // Store pending VRF result — slot assigned on callback
    let wallet_state = &mut ctx.accounts.wallet_state;
    wallet_state.owner = ctx.accounts.owner.key();
    wallet_state.launch_slot = 0; // Set on VRF callback

    emit!(LaunchRegistered {
        wallet: ctx.accounts.owner.key(),
        requested_at: Clock::get()?.slot,
    });
    Ok(())
}

// VRF callback: assign actual slot
pub fn vrf_fulfill_callback(ctx: Context<VrfFulfill>, result: [u8; 32]) -> Result<()> {
    let vrf_result = &mut ctx.accounts.vrf_result;
    vrf_result.randomness = result;
    vrf_result.fulfilled = true;

    // Derive launch slot from VRF output
    // Spread across a 7-day window (current_block + 0 to ~300000 blocks)
    let slot_offset = u64::from_le_bytes(result[..8].try_into().unwrap())
        % LAUNCH_WINDOW_BLOCKS;
    let launch_slot = Clock::get()?.slot + MIN_DELAY_BLOCKS + slot_offset;

    let wallet_state = &mut ctx.accounts.wallet_state;
    wallet_state.launch_slot = launch_slot;

    emit!(SlotAssigned {
        wallet: vrf_result.wallet,
        assigned_slot: launch_slot,
    });
    Ok(())
}

// Buy: enforce caps and slot
pub fn buy(ctx: Context<Buy>, amount: u64) -> Result<()> {
    let wallet_state = &mut ctx.accounts.wallet_state;
    let config = &ctx.accounts.token_config;
    let current_slot = Clock::get()?.slot;

    // Check slot assignment
    require!(
        current_slot >= wallet_state.launch_slot
        && current_slot <= wallet_state.launch_slot + SLOT_WINDOW,
        KoinkError::OutsideLaunchWindow
    );

    // Enforce hard cap (24h)
    let slots_since_launch = current_slot - config.launch_block;
    if slots_since_launch < SLOTS_PER_24H {
        let max_buy_24h = (config.total_supply as u128
            * config.hard_cap_24h_bps as u128 / 10000) as u64;
        require!(
            wallet_state.total_purchased_24h + amount <= max_buy_24h,
            KoinkError::ExceedsHardCap
        );
        wallet_state.total_purchased_24h += amount;
    }

    // ... transfer logic
    Ok(())
}

// Sell: apply graduated tax, distribute
pub fn sell(ctx: Context<Sell>, amount: u64) -> Result<()> {
    let config = &ctx.accounts.token_config;
    let current_slot = Clock::get()?.slot;

    // Calculate current sell tax
    let slots_since_launch = current_slot - config.launch_block;
    let tax_bps = calculate_sell_tax(slots_since_launch);

    let tax_amount = (amount as u128 * tax_bps as u128 / 10000) as u64;
    let seller_receives = amount - tax_amount;

    // Distribute tax
    let treasury_share = tax_amount * 20 / 100;    // 20% to treasury
    let lp_share = tax_amount * 50 / 100;          // 50% to LP
    let burn_share = tax_amount - treasury_share - lp_share; // 30% burned

    transfer_to_treasury(ctx, treasury_share)?;
    transfer_to_lp(ctx, lp_share)?;
    burn_tokens(ctx, burn_share)?;

    // Transfer net amount to seller
    transfer_to_seller(ctx, seller_receives)?;

    Ok(())
}

// Governance weight calculation (view function)
pub fn get_governance_weight(wallet_state: &WalletState, current_block: u64) -> u64 {
    let months_held = (current_block - wallet_state.hold_since_block)
        / BLOCKS_PER_MONTH;

    // Diamond Hands Multiplier: 1x → 3x over 12 months
    let dhm = (100 + months_held.min(12) * 200 / 12) as u128; // 100 = 1x

    // Contribution multiplier: 0.5x → 2x
    let contrib_mult = (50 + wallet_state.contribution_score as u128 * 150 / 10000);

    // Alignment multiplier: 0.8x → 1.2x
    let align_mult = (80 + wallet_state.alignment_score as u128 * 40 / 100);

    (wallet_state.balance as u128 * dhm * contrib_mult * align_mult
        / (100 * 100 * 100)) as u64
}

fn calculate_sell_tax(slots_since_launch: u64) -> u16 {
    // 0% grace (day 0-1), graduated to 15% (day 30), decay to 3%
    match slots_since_launch {
        s if s < SLOTS_PER_24H     => 0,
        s if s < SLOTS_PER_7D     => 500,   // 5%
        s if s < SLOTS_PER_14D    => 800,   // 8%
        s if s < SLOTS_PER_21D    => 1200,  // 12%
        s if s < SLOTS_PER_30D    => 1500,  // 15%
        s => {
            // Decay from 1500 bps toward 300 bps over 90 days
            let decay_slots = s - SLOTS_PER_30D;
            let decay_progress = decay_slots.min(SLOTS_PER_90D) * 1200 / SLOTS_PER_90D;
            (1500 - decay_progress as u16).max(300)
        }
    }
}
```

---

## Deploying on Base (EVM)

Base is EVM-compatible. The $KOINK Standard maps cleanly to Solidity.

### Key differences from Solana:

```solidity
// Solidity / Base adaptation notes

// 1. VRF: Use Chainlink VRF v2+ instead of Switchboard
//    import "@chainlink/contracts/src/v0.8/vrf/VRFConsumerBaseV2Plus.sol";

// 2. Block-based timing: Use block.number (NOT block.timestamp)
//    EVM: ~1 block per 2 seconds on Base → adjust slot constants

// 3. Token standard: ERC-20 with transfer hook for sell tax
//    Override _transfer() to detect sells (to LP pool) and apply tax

// 4. Hard caps: Track per-address in mapping
//    mapping(address => uint256) public purchased24h;
//    mapping(address => uint256) public purchaseWindowStart;

// 5. Governance weight: Off-chain computation with on-chain anchoring
//    OR use snapshot.org integration with custom strategy

// Example: ERC-20 transfer override for sell tax
function _transfer(
    address from,
    address to,
    uint256 amount
) internal override {
    bool isSell = lpPools[to]; // to is a known LP pool

    if (isSell && sellTaxActive) {
        uint256 taxBps = getCurrentSellTax();
        uint256 taxAmount = (amount * taxBps) / 10000;
        uint256 netAmount = amount - taxAmount;

        // Distribute tax
        _distributeSellTax(taxAmount);

        super._transfer(from, to, netAmount);
    } else {
        super._transfer(from, to, amount);
    }
}
```

### Base deployment checklist:
```
□ Deploy token contract (ERC-20 + sell tax hook)
□ Deploy VRF consumer contract (Chainlink VRF v2+)
□ Deploy launch registrar (maps wallets to VRF slots)
□ Deploy treasury vault (multisig or DAO module)
□ Register LP pool addresses for sell detection
□ Fund VRF subscription (LINK tokens)
□ Audit all contracts
□ Lock LP tokens
□ Transfer ownership to DPC multisig
```

---

## Deploying on Polkadot

Polkadot supports $KOINK Standard via two paths:

### Path A: Ink! Smart Contract (Asset Hub or parachain)

```rust
// Ink! / Polkadot pseudocode

#[ink::contract]
mod koink_token {
    use ink::storage::Mapping;

    #[ink(storage)]
    pub struct KoinkToken {
        total_supply: Balance,
        balances: Mapping<AccountId, Balance>,
        launch_block: BlockNumber,
        sell_tax_bps: u16,
        // ... wallet states
    }

    impl KoinkToken {
        // VRF: use substrate-randomness or off-chain worker
        // Block timing: use Self::env().block_number() — reliable
        // Sell tax: hook into transfer logic same as EVM version

        #[ink(message)]
        pub fn governance_weight(&self, account: AccountId) -> u128 {
            // Same formula as Solana — just adapted to Ink! types
            let balance = self.balances.get(account).unwrap_or(0);
            let wallet = self.wallet_states.get(account).unwrap_or_default();
            // ... diamond_hands × contribution × alignment
            balance as u128 * self.compute_multipliers(&wallet) / 100
        }
    }
}
```

### Path B: XCM Asset + Governance Module

For projects that want cross-parachain presence:
1. Issue the token as a cross-chain asset via XCM
2. Use Polkadot OpenGov as the governance layer (compatible with contribution weighting via custom conviction voting)
3. Link to 505 Systems DPC for ecosystem-level decisions

**Polkadot alignment note:** The $KOINK Standard's contribution-weighted governance is philosophically aligned with Polkadot OpenGov's conviction voting — both reward sustained commitment over raw capital. The standard can be presented as a natural extension of OpenGov values.

---

## Compliance Checklist

To be a **$KOINK Standard Compliant** deployment, implement:

```
□ PRINCIPLE 1: Fair Launch
  □ VRF-based slot assignment (Switchboard/Chainlink/substrate-randomness)
  □ No pre-sale advantage for insiders
  □ Block-based timing (not timestamp)
  □ Public, verifiable randomness proof

□ PRINCIPLE 2: Merit Distribution
  □ Community/contributor allocation ≥ 35% of total supply
  □ Earning mechanism documented and on-chain verifiable
  □ No single entity controls community allocation

□ PRINCIPLE 3: Anti-Whale Mechanics
  □ Hard buy caps in first 24h (≤ 0.1% per wallet)
  □ Graduated sell tax active (minimum 30 days)
  □ Buy caps enforced at contract level (not just advisory)

□ PRINCIPLE 4: Contribution Governance
  □ Governance weight formula includes at least time-held component
  □ Pure token-weighted voting disabled or significantly diluted
  □ Diamond Hands Multiplier non-transferable

□ PRINCIPLE 5: Community Treasury
  □ Minimum 15% of sell taxes routed to on-chain treasury
  □ Treasury governed by contribution-weighted DAO
  □ Monthly transparency report (IPFS-anchored)
```

**Partial compliance** is valid — label your deployment as "$KOINK Standard P1+P3" (e.g.) to indicate which principles are implemented.

---

## Why Adopt the $KOINK Standard?

**For builders:**
- Ship with battle-tested tokenomics — don't reinvent the wheel
- Signal trustworthiness to investors and community
- Get ecosystem grants from Koink.fun Treasury for compliant deployments

**For investors:**
- $KOINK Standard compliance = known risk profile
- Anti-whale mechanics protect investment from concentrated dumps
- Contribution governance means the community that builds has governance power

**For users:**
- Fair access from day one
- Loyalty is rewarded, not punished
- Community treasury means the ecosystem reinvests in itself

---

## Ecosystem Grants for Adopters

The Koink.fun Community Treasury allocates a portion of the Ecosystem Grants tranche (10% of $KOIN supply) to projects that:

1. Adopt the $KOINK Standard (full or partial compliance)
2. Deploy on at least one chain not yet covered by Koink.fun
3. Submit a public audit showing compliance

**Grant sizes:**
- Partial compliance (2-3 principles): 50,000-200,000 $KOIN
- Full compliance: 200,000-500,000 $KOIN
- Full compliance + new chain: up to 1,000,000 $KOIN

Apply via the Koink.fun governance portal (launch Q3 2026).

---

## Versioning

The $KOINK Standard uses semantic versioning. This is v1.0.

Future versions may add:
- Privacy-preserving contribution scoring (ZK proofs)
- Cross-standard bridges (for multi-ecosystem holders)
- Reputation portability (DID-based contribution scores)

All version changes require DPC approval and community vote.

---

## Summary

The $KOINK Standard exists because the same mistakes keep getting made in token launches. Fair launches get sniped. Governance gets captured by whales. Treasuries get drained. Communities get left holding bags.

These are not inevitable. They are design choices. The $KOINK Standard is the opposite set of design choices — built into the contracts, not just the marketing.

Fork it. Deploy it. Build on it. The standard only gets stronger with every compliant deployment.

---

*The $KOINK Standard is published under Open Copyright by MY3YE / Koink.fun. Build freely. Contribute back. The civilization is inside.*

*Reference implementation: [Koink.fun GitHub](https://github.com/my3ye)*
*Tokenomics reference: [$KOIN Tokenomics Paper](./koin_tokenomics_paper.md)*
