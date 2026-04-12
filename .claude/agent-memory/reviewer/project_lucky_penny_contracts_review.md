---
name: Lucky Penny Contracts Code Review
description: Code review of LuckyPenny.sol, WrappedPenny.sol, PennyVesting.sol, LuckyDrops.sol (83 tests, 4 contracts, 2026-04-12)
type: project
---

Lucky Penny ($PENNY) contract suite review — Step 2 of WF. 83/83 tests pass. All contracts <24KB.

**Why:** Non-divisible 0-decimal ERC-20 for Koink.fun ecosystem. Base L2 deployment.

**Status: NEEDS_CHANGES** — 2 criticals in deploy script, contract logic is solid.

## Critical Issues

1. **`enableTrading()` has no idempotency guard** — `LuckyPenny.sol:83`. Owner can call it twice, resetting `launchBlock` to a later block, extending the anti-sniper window. A sniper who was blocked in the first 24h window now gets a fresh window after the reset. Fix: add `require(!tradingEnabled, "Already enabled")`.

2. **Deploy script double team allocation + LP wrap failure** — `Deploy.s.sol:40-81`. Constructor sends 100K directly to `teamAddr`. Script then funds vesting with another 100K from deployer's allocation. Team ends up with 200K (20%) instead of 100K (10%). Also: deployer starts with 400K (300K LP + 100K drops), transfers 100K to vesting + 100K to drops, leaves only 200K, then tries to wrap 300K for LP → panics/reverts.

## Warnings

3. **`setDrop()` immediately voids previous drop** — `LuckyDrops.sol:29-34`. No grace period. Users who haven't claimed from drop N permanently lose their allocation when drop N+1 is set. Consider adding a deadline timestamp per drop or an archive mechanism.

4. **PennyVesting: no revocation** — `PennyVesting.sol`. If team member is removed, their unvested allocation stays permanently claimable. No `revokeSchedule()` function.

5. **PennyVesting: one schedule per address forever** — `PennyVesting.sol:44`. `totalAmount == 0` guard blocks new schedule even after full vesting + claiming. Can't top up a beneficiary without deploying a new contract.

6. **Anti-sniper bypass via fresh addresses** — `LuckyPenny.sol:74`. Snipers using a new wallet per buy bypass cooldown entirely since `lastBuyBlock[new_addr] == 0` always skips. Documented limitation but imperfect protection.

7. **LP pair exemption required post-deploy** — `Deploy.s.sol` checklist item. If forgotten before `enableTrading()`, DEX router fails max-wallet checks. Should be enforced in deploy script once pair address is known.

8. **No token recovery in LuckyDrops** — `LuckyDrops.sol`. Unclaimed tokens from completed rounds are permanently locked.

## What's Good

- Constructor ordering fix (exempt before mint) is correct and well-commented
- Anti-sniper first-buy fix (skip when `lastBuyBlock == 0`) is clean and correct  
- Double-hash leaf encoding in LuckyDrops is correct OZ second-preimage-resistant pattern
- Trustless WrappedPenny (no owner, no admin) is excellent design
- `renounceWithMaxWallet()` one-tx convenience is elegant
- `Ownable2Step` throughout — safe ownership transfer
- Integer division floor in vesting is correct behavior for 0-decimal tokens
- 83 tests, solid coverage, proper `vm.roll()` + `vm.warp()` pairing

## Patterns Noted

- Deploy scripts for token launches need independent token math verification: sum all mint allocations, subtract all script transfers, verify remaining balance >= final operations
- Multi-state transition functions (enableTrading) need idempotency guards when they have side effects (launchBlock timestamp)
