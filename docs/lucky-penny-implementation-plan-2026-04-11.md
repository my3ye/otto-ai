# Lucky Penny ($PENNY) — Implementation Plan
**Date:** 2026-04-11 | **For:** Solidity Engineer Agent (Step 1)  
**Architecture Spec:** ~/otto/docs/lucky-penny-token-architecture-2026-04-11.md  
**Status:** Ready for implementation

---

## Prerequisites (must be done before writing contracts)

### 1. Install Foundry
```bash
curl -L https://foundry.paradigm.xyz | bash
source ~/.bashrc
foundryup
```

### 2. Create Project
```bash
mkdir -p /mnt/media/projects/lucky-penny-contracts
cd /mnt/media/projects/lucky-penny-contracts
forge init --no-git
```

### 3. Install Dependencies
```bash
cd /mnt/media/projects/lucky-penny-contracts
forge install OpenZeppelin/openzeppelin-contracts@v5.1.0 --no-git
```

### 4. Configure foundry.toml
```toml
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
solc = "0.8.28"
optimizer = true
optimizer_runs = 200
via_ir = false
evm_version = "cancun"

[profile.default.fmt]
line_length = 120
tab_width = 4
bracket_spacing = false

remappings = [
    "@openzeppelin/contracts/=lib/openzeppelin-contracts/contracts/",
]

[fuzz]
runs = 256
max_test_rejects = 65536

[invariant]
runs = 256
depth = 15
```

---

## Implementation Order (4 contracts, 5 test files)

### Contract 1: LuckyPenny.sol (~80 lines)

**File:** `src/LuckyPenny.sol`  
**Inherits:** `ERC20, Ownable2Step, ERC20Permit`  
**Import from:** `@openzeppelin/contracts/`

**State variables:**
```
bool public tradingEnabled
uint256 public maxWalletAmount  // default 10_000 (1% of 1M)
uint256 public launchBlock
uint256 public constant SNIPE_BLOCKS = 43_200  // ~24h on Base @ 2s
mapping(address => bool) public isExempt
mapping(address => uint256) public lastBuyBlock
```

**Constructor:** Takes 4 addresses (treasury, team, liquidityLocker, luckyDrops). Mints:
- treasury: 500,000 (community 300K + treasury 200K combined)
- team: 100,000
- liquidityLocker: 300,000
- luckyDrops: 100,000

Mark all 4 recipient addresses as exempt. Set maxWalletAmount = 10_000.

**Key functions:**
- `decimals()` → returns 0 (pure override)
- `_update(from, to, value)` — override with:
  - Trading gate: if !tradingEnabled, require from or to is exempt
  - Anti-whale: if maxWalletAmount > 0 && !isExempt[to], require balanceOf(to) + value <= maxWalletAmount
  - Anti-sniper: if block.number < launchBlock + SNIPE_BLOCKS && !isExempt[to] && from != address(0), require block.number > lastBuyBlock[to] + 5, set lastBuyBlock[to] = block.number
  - Call super._update(from, to, value)
- `enableTrading()` — onlyOwner, sets tradingEnabled=true, launchBlock=block.number
- `setMaxWallet(uint256)` — onlyOwner
- `setExempt(address, bool)` — onlyOwner
- `renounceWithMaxWallet()` — onlyOwner, sets maxWalletAmount=0 then calls renounceOwnership()

**NO mint(), NO burn(), NO pause(), NO blacklist.**

**Events:**
- `TradingEnabled(uint256 blockNumber)`
- `MaxWalletUpdated(uint256 newAmount)`
- `ExemptUpdated(address indexed account, bool exempt)`

---

### Contract 2: WrappedPenny.sol (~50 lines)

**File:** `src/WrappedPenny.sol`  
**Inherits:** `ERC20, ERC20Permit`  
**No Ownable — fully autonomous.**

**State:**
```
LuckyPenny public immutable penny;
```

**Constructor:** Takes address of LuckyPenny. No special minting.

**Functions:**
- `decimals()` → returns 18 (pure override)
- `wrap(uint256 amount)` — transferFrom(msg.sender, address(this), amount), _mint(msg.sender, amount * 1e18)
- `unwrap(uint256 pennyAmount)` — _burn(msg.sender, pennyAmount * 1e18), penny.transfer(msg.sender, pennyAmount)
- `pennyBalance(address)` → balanceOf(account) / 1e18

**Events:**
- `Wrapped(address indexed user, uint256 pennyAmount, uint256 wPennyAmount)`
- `Unwrapped(address indexed user, uint256 pennyAmount, uint256 wPennyAmount)`

**Invariant:** `totalSupply() <= penny.balanceOf(address(this)) * 1e18` — ALWAYS.

---

### Contract 3: PennyVesting.sol (~70 lines)

**File:** `src/PennyVesting.sol`  
**Inherits:** `Ownable2Step`

**State:**
```
IERC20 public immutable penny;
struct VestingSchedule {
    uint256 totalAmount;
    uint256 claimed;
    uint256 startTime;
    uint256 cliffDuration;
    uint256 vestingDuration;
}
mapping(address => VestingSchedule) public schedules;
```

**Constructor:** Takes penny address + initial owner.

**Functions:**
- `addSchedule(address beneficiary, uint256 totalAmount, uint256 cliffDuration, uint256 vestingDuration)` — onlyOwner, requires schedules[beneficiary].totalAmount == 0 (no overwrite), sets startTime = block.timestamp
- `claim()` — calculates vested, subtracts claimed, transfers delta. Uses integer math (floor division). Emits `Claimed(beneficiary, amount)`.
- `vestedAmount(address)` → public view. If block.timestamp < startTime + cliffDuration → 0. Else: min(totalAmount, totalAmount * elapsed / vestingDuration) where elapsed = block.timestamp - startTime - cliffDuration. Integer division rounds DOWN.
- `claimable(address)` → vestedAmount - claimed

**Critical edge case:** 0-decimal tokens mean vesting math must NOT produce fractional results. Since Solidity integer division floors naturally, this is handled — but the test suite must verify the remainder (totalAmount - sum of all claims) is eventually claimable.

---

### Contract 4: LuckyDrops.sol (~45 lines)

**File:** `src/LuckyDrops.sol`  
**Inherits:** `Ownable2Step`

**State:**
```
IERC20 public immutable penny;
bytes32 public merkleRoot;
uint256 public dropId;
mapping(uint256 => mapping(address => bool)) public claimed;
```

**Constructor:** Takes penny address + initial owner.

**Functions:**
- `setDrop(bytes32 root)` — onlyOwner, increments dropId, sets merkleRoot. Emits `DropCreated(dropId, root)`.
- `findPenny(uint256 amount, bytes32[] calldata proof)` — requires !claimed[dropId][msg.sender], verifies Merkle proof against leaf = keccak256(abi.encodePacked(msg.sender, amount)), marks claimed, transfers. Emits `PennyFound(dropId, msg.sender, amount)`.
- `isClaimed(uint256 _dropId, address user)` → view

**Note:** Uses `dropId` instead of `merkleRoot` as mapping key — cleaner for multiple drop rounds.

**Import:** `@openzeppelin/contracts/utils/cryptography/MerkleProof.sol`

---

## Test Files

### Test 1: LuckyPenny.t.sol
- Total supply is exactly 1,000,000
- Decimals returns 0
- Constructor distributes correctly (500K + 100K + 300K + 100K)
- Transfers blocked before enableTrading (non-exempt)
- Transfers allowed for exempt addresses before trading
- enableTrading enables transfers for all
- maxWallet blocks transfers exceeding 10,000 to non-exempt
- maxWallet does not block exempt addresses
- Anti-sniper cooldown blocks rapid buys in first SNIPE_BLOCKS
- Anti-sniper cooldown allows buys after block gap
- Anti-sniper inactive after SNIPE_BLOCKS elapsed
- renounceWithMaxWallet removes cap and renounces
- Ownable2Step two-step transfer works
- ERC20Permit works with valid signature

### Test 2: WrappedPenny.t.sol
- Decimals returns 18
- wrap(n) mints n*1e18 wPENNY
- wrap requires prior approval
- unwrap(n) burns n*1e18 wPENNY, returns n PENNY
- unwrap reverts if insufficient wPENNY balance
- Round-trip: wrap(n) then unwrap(n) returns exact amount
- Dust: wrap(1) → transfer 0.5*1e18 wPENNY → recipient can't unwrap → dust stays
- pennyBalance returns floor(balance / 1e18)
- Invariant: totalSupply <= penny.balanceOf(wrapper) * 1e18

### Test 3: PennyVesting.t.sol
- addSchedule creates schedule correctly
- addSchedule reverts for existing beneficiary
- claim returns 0 before cliff
- claim returns correct amount after cliff
- Linear vesting: claims at 25%, 50%, 75%, 100% of duration
- Integer math: 100 tokens / 12 months, verify remainder claimable at end
- Full claim after vesting complete
- Cannot claim more than total
- Only owner can add schedules

### Test 4: LuckyDrops.t.sol
- setDrop updates root and increments dropId
- findPenny with valid proof succeeds
- findPenny with invalid proof reverts
- Double-claim reverts
- New drop (new dropId) resets claims
- Multiple recipients can claim same drop

### Test 5: Integration.t.sol
- Full deployment flow: deploy all 4 contracts
- Token distribution verification
- Wrap → LP simulation (approve + wrap 300K)
- Enable trading → transfer flow
- Vesting: team claims after cliff
- Lucky Drop: create drop, claim
- Anti-whale: verify max wallet during trading

---

## File Structure (Final)

```
/mnt/media/projects/lucky-penny-contracts/
├── src/
│   ├── LuckyPenny.sol
│   ├── WrappedPenny.sol
│   ├── PennyVesting.sol
│   └── LuckyDrops.sol
├── test/
│   ├── LuckyPenny.t.sol
│   ├── WrappedPenny.t.sol
│   ├── PennyVesting.t.sol
│   ├── LuckyDrops.t.sol
│   └── Integration.t.sol
├── script/
│   └── Deploy.s.sol
├── foundry.toml
├── remappings.txt
└── README.md
```

---

## Deployment Script (Deploy.s.sol)

The deploy script should:
1. Deploy LuckyPenny with 4 allocation addresses
2. Deploy WrappedPenny pointing to LuckyPenny
3. Deploy PennyVesting pointing to LuckyPenny
4. Deploy LuckyDrops pointing to LuckyPenny
5. Set wrapper address as exempt on LuckyPenny
6. Set vesting contract as exempt on LuckyPenny
7. Set drops contract as exempt on LuckyPenny
8. Transfer 300K community tokens from treasury to vesting contract
9. Add vesting schedules (team: 6mo cliff + 12mo, community: 0 cliff + 24mo)
10. Log all deployed addresses

---

## Critical Implementation Notes

1. **OZ v5 uses `_update` not `_beforeTokenTransfer`** — the override pattern changed in v5.
2. **`Ownable2Step` constructor in OZ v5 takes `address initialOwner`** — pass msg.sender.
3. **For `ERC20Permit` + `ERC20` + `Ownable2Step`**: order matters. ERC20("Lucky Penny", "PENNY"), ERC20Permit("Lucky Penny"), Ownable(msg.sender).
4. **Anti-sniper `lastBuyBlock` only tracks when `from` is not address(0) and not exempt** — don't track minting or exempt-to-exempt.
5. **The `wrap` function in WrappedPenny needs the user to first `approve`** the WrappedPenny contract to spend their PENNY. The test must include this approval step.
6. **Use `abi.encodePacked` (not `abi.encode`) for Merkle leaves** — standard convention for Merkle proofs.
7. **Solidity 0.8.28** — no need for SafeMath (built-in overflow checks).
8. **All contracts use SPDX: MIT** — standard for open-source tokens.

---

## Budget Estimate

| Item | Estimated Cost |
|---|---|
| Foundry setup + config | $0.50 |
| LuckyPenny.sol + tests | $1.50 |
| WrappedPenny.sol + tests | $1.00 |
| PennyVesting.sol + tests | $1.00 |
| LuckyDrops.sol + tests | $0.75 |
| Integration tests | $0.75 |
| Deploy script | $0.50 |
| **Total** | **~$6.00** |

---

## Open Questions for Mev (flagged in architecture)

1. **Burn/tax policy**: Recommended zero-fee, no burn (Cooper Law). Awaiting confirmation.
2. **Initial price target**: Recommended $0.01/PENNY (1 ETH initial LP). Awaiting confirmation.
3. **Ownership model**: Recommended renounce core + multisig drops. Awaiting confirmation.

**Implementation proceeds with recommended defaults.** All 3 are isolated to config constants — easy to change before deployment without contract rewrite.
