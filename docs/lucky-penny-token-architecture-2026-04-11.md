# Lucky Penny ($PENNY) — Token Architecture & Contract Specification
**Date:** 2026-04-11 | **Status:** Design Complete | **Author:** Architect Agent  
**Prerequisites:** Research brief (0-decimal ERC-20 mechanics), Lore Bible (Lucky Cooper narrative)  
**Target:** Solidity engineer can implement directly from this spec

---

## Design: Lucky Penny Non-Divisible Token

### Problem

$PENNY is the conviction/speculation layer of the Koink.fun brand stack (PiPi → Koink.fun → $PENNY). The narrative demands 0 decimals — "a penny cannot be split." But 0-decimal ERC-20 tokens have well-documented DEX incompatibilities: integer-only pricing on AMMs, coarse-grained concentrated liquidity, wallet display bugs, and crowdsale math pitfalls.

The challenge: build a token that is genuinely non-divisible on-chain (honoring the narrative) while remaining tradeable on Uniswap V2/V3 and compatible with Base L2 infrastructure.

### Approach

**Two-contract architecture**: a 0-decimal core token (`LuckyPenny.sol`) and an 18-decimal AMM wrapper (`WrappedPenny.sol`). Users hold $PENNY. Traders use wPENNY. Same underlying asset, different interfaces — like stETH/wstETH.

Deploy on **Base L2** (confirmed as Phase 1 chain target: Chainlink VRF support, Coinbase Ventures prereq, EVM expertise alignment).

---

## 1. Token Identity

| Property | Value |
|---|---|
| **Name** | Lucky Penny |
| **Symbol** | PENNY |
| **Decimals** | 0 |
| **Standard** | ERC-20 (OpenZeppelin v5) |
| **Chain** | Base (Mainnet) |
| **Wrapper Name** | Wrapped Penny |
| **Wrapper Symbol** | wPENNY |
| **Wrapper Decimals** | 18 |

---

## 2. Supply Mechanics

### 2.1 Total Supply

**1,000,000 $PENNY (one million)**

Rationale:
- Small enough that each penny feels real and scarce (vs $KOIN's 1 billion)
- Large enough for meaningful distribution across community, LP, and treasury
- At $0.01/token, market cap = $10K (approachable). At $1/token, market cap = $1M.
- 1 million pennies is a narratively resonant number — "a million pennies" is a real cultural reference
- With 0 decimals, this gives exactly 1,000,000 transferable units

### 2.2 Supply Policy

**Fixed at genesis. No mint function. No inflation.**

The contract has no `mint()` function exposed post-deployment. All 1,000,000 tokens are minted to the deployer in the constructor, then distributed per the allocation table. The `_mint` internal function is only called once, in the constructor.

This is non-negotiable per the Cooper Law: *"Never split it."* Minting new pennies would dilute the meaning. Pennies are found, not made.

### 2.3 Distribution

| Allocation | Amount | % | Vesting | Purpose |
|---|---|---|---|---|
| **Liquidity Pool** | 300,000 | 30% | Locked 12 months | Initial wPENNY/ETH pool on Uniswap V2 |
| **Community Rewards** | 300,000 | 30% | Linear 24 months | Koink.fun participation, contributions, Lucky Drops |
| **Treasury** | 200,000 | 20% | Multisig controlled | Ecosystem growth, partnerships, future LP |
| **Team** | 100,000 | 10% | 6-month cliff + 12-month linear | Core contributors |
| **Lucky Drops** | 100,000 | 10% | Event-driven | Random distribution events ("find a penny") |

**Lucky Drops** are the narrative-aligned distribution mechanism: random airdrops to active wallets, Koink.fun users, or event attendees. "Find one. Keep it." — the act of receiving a Lucky Drop is "finding" a penny.

---

## 3. Contract Architecture

### 3.1 LuckyPenny.sol (Core Token)

```
LuckyPenny : ERC20, Ownable2Step, ERC20Permit
```

**Key overrides:**
```solidity
function decimals() public pure override returns (uint8) {
    return 0;
}
```

**Constructor:**
```solidity
constructor(address treasury, address team, address liquidityLocker, address luckyDrops)
    ERC20("Lucky Penny", "PENNY")
    ERC20Permit("Lucky Penny")
    Ownable(msg.sender)
{
    _mint(treasury, 500_000);      // Treasury + Community Rewards (split later)
    _mint(team, 100_000);          // Team (behind vesting)
    _mint(liquidityLocker, 300_000); // LP allocation
    _mint(luckyDrops, 100_000);    // Lucky Drops pool
}
```

**Transfer hooks (anti-whale, launch protection):**
```solidity
// State
bool public tradingEnabled;
uint256 public maxWalletAmount;    // anti-whale cap (default: 10,000 = 1%)
mapping(address => bool) public isExempt; // LP, treasury, team vesting exempt

function _update(address from, address to, uint256 value) internal override {
    // Block transfers until trading enabled (except from deployer/exempt)
    if (!tradingEnabled) {
        require(isExempt[from] || isExempt[to], "Trading not enabled");
    }
    
    // Anti-whale: max wallet check on buys (skip exempt addresses)
    if (maxWalletAmount > 0 && !isExempt[to]) {
        require(balanceOf(to) + value <= maxWalletAmount, "Exceeds max wallet");
    }
    
    super._update(from, to, value);
}
```

**Owner functions (minimal):**
```solidity
function enableTrading() external onlyOwner { tradingEnabled = true; }
function setMaxWallet(uint256 amount) external onlyOwner { maxWalletAmount = amount; }
function setExempt(address addr, bool exempt) external onlyOwner { isExempt[addr] = exempt; }
function renounceWithMaxWallet() external onlyOwner {
    maxWalletAmount = 0; // Remove cap permanently
    renounceOwnership();
}
```

**What the contract does NOT have:**
- No `mint()` — supply is fixed
- No `burn()` — see Section 4 for rationale
- No transfer tax — pennies circulate freely (see Section 4)
- No pause — deliberate. Once deployed, it runs forever. Cooper Law: the penny endures.
- No blacklist — philosophical choice: pennies don't discriminate

### 3.2 WrappedPenny.sol (DEX Adapter)

```
WrappedPenny : ERC20, ERC20Permit
```

The wrapper is a trustless, permissionless contract that converts $PENNY ↔ wPENNY at a fixed 1:1e18 ratio.

**Core mechanics:**
```solidity
LuckyPenny public immutable penny;

constructor(address _penny)
    ERC20("Wrapped Penny", "wPENNY")
    ERC20Permit("Wrapped Penny")
{
    penny = LuckyPenny(_penny);
}

function decimals() public pure override returns (uint8) {
    return 18;
}

/// @notice Deposit whole pennies, receive wPENNY at 1:1e18 ratio
/// @param amount Number of whole $PENNY to wrap
function wrap(uint256 amount) external {
    penny.transferFrom(msg.sender, address(this), amount);
    _mint(msg.sender, amount * 1e18);
}

/// @notice Burn wPENNY, receive whole $PENNY back
/// @param pennyAmount Number of whole $PENNY to unwrap (not wPENNY amount)
/// @dev Burns pennyAmount * 1e18 wPENNY, returns pennyAmount $PENNY
function unwrap(uint256 pennyAmount) external {
    _burn(msg.sender, pennyAmount * 1e18);
    penny.transfer(msg.sender, pennyAmount);
}

/// @notice How many whole $PENNY are redeemable for a wPENNY balance
function pennyBalance(address account) external view returns (uint256) {
    return balanceOf(account) / 1e18;
}
```

**Why this works:**
- AMMs see wPENNY as a standard 18-decimal token — no quirks
- Price discovery happens on wPENNY/ETH pairs with full precision
- 1 wPENNY (1e18 units) = 1 $PENNY always — the peg is enforced by the wrap/unwrap mechanism
- The wrapper holds $PENNY as reserves; wPENNY is fully backed 1:1
- Sub-unit wPENNY (fractional pennies in AMM terms) exist in the wrapper but cannot be unwrapped — only whole units unwrap
- Dust wPENNY (< 1e18) stays in the wrapper forever — a feature, not a bug (pennies can't be split)

**Security considerations for wrapper:**
- No owner, no admin — fully autonomous after deployment
- No reentrancy risk (CEI pattern, no external calls in state changes)
- `transferFrom` on $PENNY checked before mint (pull, not push)
- wPENNY total supply ≤ PENNY.balanceOf(wrapper) × 1e18 always (invariant)

### 3.3 PennyVesting.sol (Team + Community Vesting)

```
PennyVesting : Ownable2Step
```

Standard linear vesting with cliff. Handles team (6mo cliff + 12mo linear) and community (no cliff, 24mo linear) schedules.

```solidity
struct VestingSchedule {
    uint256 totalAmount;
    uint256 claimed;
    uint256 startTime;
    uint256 cliffDuration;
    uint256 vestingDuration;
}

mapping(address => VestingSchedule) public schedules;

function claim() external {
    VestingSchedule storage s = schedules[msg.sender];
    uint256 vested = _vestedAmount(s);
    uint256 claimable = vested - s.claimed;
    require(claimable > 0, "Nothing to claim");
    s.claimed = vested;
    penny.transfer(msg.sender, claimable);
}
```

No fractional vesting edge case: since tokens are 0-decimal, `_vestedAmount` must use integer math that rounds DOWN. A beneficiary with 100 tokens over 12 months gets ~8 tokens/month. Remainder (100 - 96 = 4) vests in the final month.

### 3.4 LuckyDrops.sol (Airdrop Distribution)

```
LuckyDrops : Ownable2Step
```

Batch airdrop contract for "find a penny" events. Uses Merkle proofs for gas-efficient claims.

```solidity
bytes32 public merkleRoot;
mapping(bytes32 => mapping(address => bool)) public claimed;

function setDrop(bytes32 root) external onlyOwner {
    merkleRoot = root;
}

function findPenny(uint256 amount, bytes32[] calldata proof) external {
    require(!claimed[merkleRoot][msg.sender], "Already found");
    bytes32 leaf = keccak256(abi.encodePacked(msg.sender, amount));
    require(MerkleProof.verify(proof, merkleRoot, leaf), "Not lucky");
    claimed[merkleRoot][msg.sender] = true;
    penny.transfer(msg.sender, amount);
}
```

The function is named `findPenny` — not `claim`. Narrative in the contract.

---

## 4. Burn Mechanics

### Decision: No Burn

The Cooper Law: *"Find one. Keep it. Pass it down. Never spend it."*

Burning = destroying pennies. The lore explicitly says pennies are kept and passed down, not destroyed. A burn mechanic contradicts the founding narrative.

**Deflationary pressure comes from:**
1. **Lost pennies** — tokens sent to `address(0)` or lost wallets. Natural attrition.
2. **Wrapper dust** — sub-unit wPENNY that accumulates in AMM trades and can never be unwrapped. Effectively locked forever.
3. **Fixed supply** — no inflation means any lost token is permanently deflationary.

**Alternative considered:** 1-2% transfer tax with burn. Rejected because:
- Contradicts "pass it down" (passing shouldn't cost you)
- Adds gas overhead to every transfer
- Makes $PENNY less composable with DeFi
- The wrapper dust mechanic already provides soft deflation

[NEEDS_MEV_INPUT]
{"question": "Should $PENNY have any burn mechanism or transfer tax, or should it be zero-fee transfers as designed (letting natural loss + wrapper dust provide deflation)?", "options": ["Zero-fee transfers, no burn (recommended — fits Cooper Law narrative)", "Small transfer tax (1-2%) to treasury for ecosystem funding", "Voluntary burn function (holder can choose to destroy their pennies)"], "recommendation": 0, "context": "The lore says 'pass it down, never spend it' which argues against forced fees. Fixed supply + natural loss provides soft deflation. Transfer taxes add complexity and contradict the simplicity narrative."}
[/NEEDS_MEV_INPUT]

---

## 5. LP Pairing Strategy

### 5.1 Primary Pool: wPENNY/ETH on Uniswap V2 (Base)

**Why V2, not V3:**
- V3 concentrated liquidity is wasted on a meme/culture token — LPs won't actively manage ranges
- V2 constant product is simpler, more predictable, and the full-range default
- V2 has better bot/aggregator coverage for low-cap tokens
- V3 tick granularity issues (from research) are avoided entirely by using the wrapper

**Initial liquidity:**
- 300,000 wPENNY (= 300,000 $PENNY wrapped)
- Paired with ETH at target initial price

**Initial price calculation:**
- If target price = $0.01/PENNY and ETH = $3,000:
  - 300,000 wPENNY needs 300,000 × $0.01 / $3,000 = 1 ETH
- If target price = $0.10/PENNY:
  - 300,000 wPENNY needs 300,000 × $0.10 / $3,000 = 10 ETH
  
[NEEDS_MEV_INPUT]
{"question": "What should the initial $PENNY price target be? This determines how much ETH goes into the initial LP.", "options": ["$0.01 per PENNY (~1 ETH for 300K LP — extremely cheap entry, meme-tier)", "$0.05 per PENNY (~5 ETH for 300K LP — mid-range, accessible)", "$0.10 per PENNY (~10 ETH for 300K LP — more 'premium' positioning)"], "recommendation": 0, "context": "$0.01 = the price of a real penny. Narratively perfect. Market cap at launch = $10K. This is a meme/culture token with a conviction narrative, not a utility token — low entry encourages 'finding' pennies. Price discovery will handle the rest."}
[/NEEDS_MEV_INPUT]

### 5.2 LP Lock

LP tokens from the initial pool are locked for 12 months in a timelock contract (or via a service like Unicrypt/Team Finance on Base). After 12 months, LP tokens go to the treasury multisig.

### 5.3 The Wrapper Dust Effect

When users trade wPENNY on the AMM, fractional wPENNY accumulates:
- Buy 1.7 wPENNY → can unwrap 1 $PENNY, 0.7 wPENNY remains as dust
- This dust is permanently trapped (cannot be unwrapped without accumulating to 1e18)
- Over thousands of trades, meaningful amounts of wPENNY become permanently locked
- This is a natural, narrative-aligned deflationary mechanism: "pennies get lost in the couch cushions"

---

## 6. Anti-Bot & Launch Protection

### 6.1 Launch Sequence

```
1. Deploy LuckyPenny.sol (trading disabled)
2. Deploy WrappedPenny.sol (pointing to LuckyPenny)
3. Deploy PennyVesting.sol
4. Deploy LuckyDrops.sol
5. Distribute tokens per allocation table
6. Owner wraps 300,000 $PENNY → wPENNY
7. Owner creates Uniswap V2 wPENNY/ETH pool
8. Lock LP tokens (12 months)
9. Set maxWalletAmount = 10,000 (1% of supply)
10. Set exempt addresses (LP pair, vesting, drops, wrapper, treasury)
11. Call enableTrading() — LIVE
12. After 48h: reduce maxWallet to 20,000 (2%) or remove
13. After 7d: consider renouncing ownership (remove max wallet first)
```

### 6.2 Anti-Whale

**Max wallet: 1% of supply (10,000 $PENNY) at launch.**

- Applies to $PENNY transfers only (not wPENNY — the wrapper is exempt)
- The Uniswap pair address, wrapper, vesting, and drops contracts are exempt
- After the initial 48-hour snipe window, owner can relax to 2% or remove entirely
- wPENNY has NO max wallet — this is intentional. Anti-whale on the underlying $PENNY is the real protection; wPENNY is just the trading wrapper.

### 6.3 Anti-Sniper (First 24 Hours)

**Block-based cooldown** in the first 24 hours (~43,200 blocks on Base at 2s/block):

```solidity
uint256 public launchBlock;
uint256 public constant SNIPE_BLOCKS = 43_200; // ~24h on Base
mapping(address => uint256) public lastBuyBlock;

// Inside _update, for buys from LP:
if (block.number < launchBlock + SNIPE_BLOCKS && !isExempt[to]) {
    require(block.number > lastBuyBlock[to] + 5, "Cooldown");
    lastBuyBlock[to] = block.number;
}
```

This means: in the first 24 hours, each wallet can only buy once every ~10 seconds. After 24 hours, the cooldown expires permanently. No ongoing gas tax.

### 6.4 What We Don't Do

- **No blacklist** — philosophical: pennies don't discriminate. Also avoids centralization FUD.
- **No dynamic tax** — too complex for a token whose narrative is simplicity. "Zero decimals. Zero doubt."
- **No honeypot mechanics** — all sells always enabled once trading is on.

---

## 7. Ownership Model

### 7.1 Progressive Decentralization

**Phase 1 (Launch → 7 days):** Owner = deployer EOA (Mev)
- Enable trading, set max wallet, manage exempt list
- Emergency response capability

**Phase 2 (7 days → 30 days):** Owner = deployer EOA
- Remove max wallet cap
- Monitor for issues

**Phase 3 (30+ days):** Owner = renounced OR transferred to multisig
- `renounceWithMaxWallet()` — removes max wallet cap AND renounces in one tx
- Alternatively, transfer ownership to a Gnosis Safe multisig for long-term governance

[NEEDS_MEV_INPUT]
{"question": "Should ownership be renounced (fully immutable, strongest trust signal) or transferred to a multisig (retains emergency power)?", "options": ["Renounce after 30 days (immutable — strongest community trust signal)", "Transfer to 2/3 Gnosis Safe multisig (retains upgrade path for future needs)", "Renounce core token, keep multisig on LuckyDrops only (hybrid)"], "recommendation": 2, "context": "LuckyPenny itself has no admin functions worth keeping post-launch (max wallet removed, trading enabled). But LuckyDrops needs ongoing management to set new Merkle roots for future drop events. Renouncing the core token while keeping drops admin is the cleanest split."}
[/NEEDS_MEV_INPUT]

### 7.2 Contract Ownership Summary

| Contract | Owner at Launch | Final Owner |
|---|---|---|
| LuckyPenny | Deployer EOA | **Renounced** (after max wallet removed) |
| WrappedPenny | None (no owner) | None (immutable from deploy) |
| PennyVesting | Deployer EOA | Renounced (after all schedules set) |
| LuckyDrops | Deployer EOA | Gnosis Safe multisig |

---

## 8. Relationship to $KOIN

$PENNY and $KOIN are distinct tokens serving different roles:

| Dimension | $KOIN | $PENNY |
|---|---|---|
| **Purpose** | Governance + utility | Conviction + culture |
| **Supply** | 1,000,000,000 (1B) | 1,000,000 (1M) |
| **Decimals** | 18 (or 9 on Solana) | 0 |
| **Tradeable** | Yes (native) | Yes (via wPENNY wrapper) |
| **Burn** | Deflationary via fee burn | No burn (natural loss only) |
| **Governance** | DHM-weighted voting | None (pure cultural asset) |
| **Narrative** | "The coordination layer" | "Find one. Keep it." |

### 8.1 Cross-Token Synergies (Future)

- **$PENNY as DHM Booster**: Holding ≥1 $PENNY could provide a 1.1x multiplier on $KOIN DHM (reward the believers)
- **Lucky Drops eligibility**: $KOIN holders above threshold are eligible for $PENNY Lucky Drop events
- **Dual-token LP**: Future wPENNY/$KOIN pool as a pure-ecosystem pair
- These are Phase 2+ features — not in initial contracts

---

## 9. Contract File Structure (Foundry)

```
contracts/
├── src/
│   ├── LuckyPenny.sol          # Core 0-decimal ERC-20
│   ├── WrappedPenny.sol         # 18-decimal DEX wrapper
│   ├── PennyVesting.sol         # Linear vesting with cliff
│   └── LuckyDrops.sol           # Merkle-proof airdrop
├── test/
│   ├── LuckyPenny.t.sol         # Core token tests
│   ├── WrappedPenny.t.sol       # Wrap/unwrap + dust tests
│   ├── PennyVesting.t.sol       # Vesting schedule tests
│   ├── LuckyDrops.t.sol         # Merkle claim tests
│   └── Integration.t.sol        # Full flow: deploy → wrap → LP → trade
├── script/
│   ├── Deploy.s.sol             # Full deployment script
│   └── CreatePool.s.sol         # Uniswap V2 pool creation
├── foundry.toml
└── remappings.txt
```

**Dependencies:**
- OpenZeppelin Contracts v5.x (`@openzeppelin/contracts`)
- Forge Std (`forge-std`)
- Uniswap V2 interfaces (for pool creation script only)

---

## 10. Key Decisions Summary

| Decision | Chosen | Rationale | Alternative Rejected |
|---|---|---|---|
| **Decimals** | 0 | Non-negotiable — the entire narrative | 18 with UI formatting |
| **Supply** | 1,000,000 fixed | Scarce, narratively resonant, no inflation | 1B (too similar to $KOIN), 10K (too scarce for distribution) |
| **DEX strategy** | wPENNY wrapper (18 dec) | Solves AMM compatibility without compromising core token | Direct LP with 0-dec (research shows broken), no DEX (kills price discovery), bonding curve (custom, unaudited) |
| **AMM** | Uniswap V2 on Base | Simpler, full-range, better bot coverage | V3 (concentrated liquidity wasted on meme token) |
| **Burn** | None | Cooper Law says keep and pass down | Transfer tax burn (contradicts lore), voluntary burn (unnecessary) |
| **Anti-whale** | 1% max wallet, 24h cooldown | Simple, effective, temporary | Dynamic tax (complex), blacklist (centralization risk) |
| **Ownership** | Progressive renouncement | Strongest trust signal for core token | Permanent multisig (unnecessary admin surface) |
| **Chain** | Base | Aligned with Koink Phase 1, CbV prereq, Chainlink VRF | Solana (Phase 2), Mainnet (expensive) |

---

## 11. Implementation Plan

### Phase 1: Core Contracts (~$3-5)

1. **LuckyPenny.sol** — 0-decimal ERC-20 with anti-whale hooks (~80 lines)
2. **WrappedPenny.sol** — Trustless 18-decimal wrapper (~50 lines)
3. **Full test suite** — Edge cases: 0-decimal transfers, wrap/unwrap invariants, max wallet, cooldown
4. **Local fork testing** — Fork Base mainnet, simulate Uniswap V2 pool creation + trades

### Phase 2: Distribution Contracts (~$2-3)

5. **PennyVesting.sol** — Linear vesting with cliff, integer-safe math (~70 lines)
6. **LuckyDrops.sol** — Merkle-based airdrop with `findPenny()` (~40 lines)
7. **Deploy script** — Full deployment + pool creation in one script

### Phase 3: Launch (~$1-2)

8. **Base testnet deployment** — Full rehearsal on Base Sepolia
9. **Verify all contracts on Basescan**
10. **Mainnet deployment** — Execute launch sequence (Section 6.1)

**Total estimated cost: $6-10** (agent time, no audit budget — see Risks)

---

## 12. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| **Wrapper introduces smart contract risk** | HIGH | Keep wrapper minimal (~50 LOC), full test coverage, invariant: wPENNY.totalSupply ≤ PENNY.balanceOf(wrapper) × 1e18 |
| **MetaMask display bug** (shows "0 tokens" for 0-decimal transfers) | MEDIUM | Known issue (#18139). Users can verify on Basescan. Document in FAQ. Most interaction is via wPENNY anyway. |
| **Low initial liquidity** | MEDIUM | Start with modest ETH pairing. Add treasury ETH as market develops. LP lock prevents rug. |
| **No audit** | HIGH | Contracts are simple (<250 LOC total). Full test suite with fuzz testing. Use OZ battle-tested base contracts. Consider lightweight audit ($2-5K) before mainnet. |
| **Regulatory** | LOW | $PENNY is a culture/meme token, not a security. No revenue sharing, no governance, no promises of returns. No ICO/presale. Fair launch only. |
| **Wrapper adoption friction** | MEDIUM | Build wrap/unwrap into Koink.fun UI. Most users never touch $PENNY directly — they buy wPENNY on DEX and can optionally unwrap. |

---

## 13. Invariants (for testing)

These MUST hold at all times:

```
1. PENNY.totalSupply() == 1_000_000 (always, forever)
2. wPENNY.totalSupply() <= PENNY.balanceOf(address(wrapper)) * 1e18
3. For all addresses a: PENNY.balanceOf(a) == floor(PENNY.balanceOf(a)) (always integer)
4. wrap(n) increases wPENNY supply by exactly n * 1e18
5. unwrap(n) decreases wPENNY supply by exactly n * 1e18
6. unwrap(wrap(n)) == n (round-trip preserves amount)
7. No address can hold > maxWalletAmount $PENNY (when maxWallet > 0 and !exempt)
8. After renounceOwnership: no state-changing admin functions callable
```

---

## Appendix A: Gas Estimates (Base L2)

| Operation | Estimated Gas | Estimated Cost (Base) |
|---|---|---|
| Deploy LuckyPenny | ~800K | ~$0.08 |
| Deploy WrappedPenny | ~600K | ~$0.06 |
| Transfer $PENNY | ~55K | ~$0.005 |
| wrap() | ~75K | ~$0.008 |
| unwrap() | ~65K | ~$0.007 |
| findPenny() (Merkle claim) | ~80K | ~$0.008 |
| Create Uniswap V2 pool | ~300K | ~$0.03 |

Gas costs on Base are ~100x cheaper than L1. Total deployment cost: < $0.50 in ETH.

---

## Appendix B: Interface Signatures

```solidity
// LuckyPenny.sol
interface ILuckyPenny {
    function decimals() external pure returns (uint8);           // 0
    function tradingEnabled() external view returns (bool);
    function maxWalletAmount() external view returns (uint256);
    function isExempt(address) external view returns (bool);
    function enableTrading() external;                           // onlyOwner
    function setMaxWallet(uint256) external;                     // onlyOwner
    function setExempt(address, bool) external;                  // onlyOwner
    function renounceWithMaxWallet() external;                   // onlyOwner
}

// WrappedPenny.sol
interface IWrappedPenny {
    function penny() external view returns (address);
    function decimals() external pure returns (uint8);           // 18
    function wrap(uint256 amount) external;
    function unwrap(uint256 pennyAmount) external;
    function pennyBalance(address account) external view returns (uint256);
}

// PennyVesting.sol
interface IPennyVesting {
    function schedules(address) external view returns (uint256 total, uint256 claimed, uint256 start, uint256 cliff, uint256 duration);
    function vestedAmount(address beneficiary) external view returns (uint256);
    function claim() external;
    function addSchedule(address beneficiary, uint256 total, uint256 cliff, uint256 duration) external; // onlyOwner
}

// LuckyDrops.sol
interface ILuckyDrops {
    function merkleRoot() external view returns (bytes32);
    function claimed(bytes32 root, address user) external view returns (bool);
    function setDrop(bytes32 root) external;                     // onlyOwner
    function findPenny(uint256 amount, bytes32[] calldata proof) external;
}
```
