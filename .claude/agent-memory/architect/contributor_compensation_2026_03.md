---
name: Contributor Compensation Contract
description: Treasury-gated salary system — Gnosis Safe module, 50bp + $9K cap, $100K floor, monthly claim. Composes with OPRLP + Core Value Loop. Immutable contract. 3 phases ~$16-21.
type: project
---

Contributor Compensation Contract system designed (2026-03-29). Gnosis Safe module pattern — ContributorCompensation.sol as the only automated withdrawal path from Movement Treasury.

**Key design:** allocationBps (% of eligible pool) + hardCapUsd (absolute monthly cap). Mev initial config: 50bp, $9K cap, FOUNDER role. Full $9K activates at $1.9M treasury. $100K floor is sacred — never breached by payouts.

**Why:** Mev directive: 9K/month from reserve, treasury-gated, same structure for all contributors. % + cap hybrid chosen over fixed salary (scales with treasury health) or pure % (unbounded).

**How to apply:** This is the operating salary layer. Distinct from CET revenue-share (EquityTreasury) and provenance splits (SplitEngine). Contributors can earn BOTH salary + CET. Phase 2 adds DPC-gated registration and InvestmentLock module. Phase 3 migrates governance to DAO.

Full spec at ~/otto/docs/contributor-compensation-contract-architecture-2026-03-29.md.
