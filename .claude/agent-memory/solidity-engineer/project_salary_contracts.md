---
name: Contributor Salary System
description: Three-contract salary system for MY3YE ecosystem — ContributorRegistry, TreasuryGate, ContributorSalary. Deployed to /home/web3relic/otto/contracts/salary/. Integrates with OPRLP on Polygon zkEVM.
type: project
---

Three contracts written at /home/web3relic/otto/contracts/salary/ on 2026-03-29.

**Why:** Mev's directive: founder salary of 9k USDC/month from treasury reserve, same structure for all future contributors. Terms locked and public on-chain from day one.

**Contracts:**
- ContributorRegistry.sol — contributor management, roles, allocation BPS per contributor
- TreasuryGate.sol — floor enforcement, period snapshots, pre/post payout checks
- ContributorSalary.sol — claim processing, payout math, reentrancy guard, emergency recovery

**Key invariants locked in:**
- GLOBAL_SALARY_CAP = 9_000e6 (constant, not configurable by governance)
- MAX_ALLOCATION_BPS = 500 (5% per contributor)
- MAX_TOTAL_ALLOCATION_BPS = 2000 (20% aggregate)
- ABSOLUTE_MINIMUM_FLOOR = 10_000e6 (10k USDC — governance cannot zero the floor)
- All contributors get identical structure — no special founder treatment in the code

**Payout math:** min(allocationBps × eligiblePool / 10000, hardCapUsd)
Where eligiblePool = periodOpeningBalance - floor (snapshot anchored at first claim per period)

**Security patterns used:**
- Checks-Effects-Interactions strictly followed
- ReentrancyGuard on claim() and claimFor()
- SafeERC20 for all transfers
- Pre AND post floor checks (belt + suspenders)
- Period snapshot prevents flash-loan eligible-pool inflation
- USDC goes to registered wallet, never to msg.sender (prevents operator redirection)

**OPRLP integration:** DPCRegistry address pattern matched. Same AccessControl + Pausable base. Same OpenZeppelin import paths and solc 0.8.24.

**Not yet implemented:** DPC-gated contributor registration (optional, noted in architecture doc). Gnosis Safe module pattern is handled operationally, not in-contract.

**How to apply:** When deploying, grant SALARY_CONTRACT_ROLE on both TreasuryGate and ContributorRegistry to the ContributorSalary address. Fund ContributorSalary with USDC each period (or grant allowance). Set up Gnosis Safe to push-fund monthly.
