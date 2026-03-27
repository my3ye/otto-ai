---
name: ranger_vault_architecture
description: OttoVault AI-driven regime-adaptive USDC vault for Ranger Build-A-Bear Hackathon (deadline April 6 2026). Voltr SDK, no custom Anchor. 3-phase 9-day build.
type: project
---

OttoVault architecture designed (2026-03-28) for Ranger Build-A-Bear Hackathon.

**Key decisions:**
- Voltr SDK + existing adaptors (Drift, Kamino, Jupiter, Save) — NOT custom Anchor program. Reason: no Rust/Solana toolchain on otto-machine, 9-day deadline impossible with custom program.
- TypeScript keeper service (not Python) — entire Solana/DeFi SDK ecosystem is TS-first.
- Market regime detection (TRENDING/RANGING/STRESS) as novel differentiator — no Solana vault does strategy-type switching.
- Rule-based classifier (not ML) — auditable, no training data needed, hackathon judges can verify.
- Existing alpha pipeline (paper_trader, live_watcher) NOT reusable — meme-token focused, confirmed by validation review.

**Why:** $1M prize (TVL seeding), AI-driven explicitly eligible, Otto has genuine edge via regime detection + persistent memory.

**How to apply:** All vault implementation tasks should reference ~/otto/docs/ranger-vault-architecture-2026-03-28.md. Critical blocker: funded Solana wallet for mainnet deploy (Mev decision needed).

**Phase budget: ~$25.50 total across 3 phases.**
