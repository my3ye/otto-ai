# Coder Agent Memory

## Service & Environment

- otto-memory service venv: `/home/web3relic/otto/memory/.venv/bin/python`
- Run validation with: `/home/web3relic/otto/memory/.venv/bin/python -c "import sys; sys.path.insert(0, '/home/web3relic/otto'); from memory.api import app"`
- DB access (no psql on host): `docker exec memory-postgres-1 psql -U otto -d memory`

## Import Patterns

- Route files live at `memory/routes/*.py`, two levels below `otto/` root
- Relative imports from route files: `from ..llm import llm_chat` (one dot up = memory package)
- To import from `otto/universe/loader.py` inside a route: `from ...universe.loader import clear_cache` (three dots = up to otto/)
- All route files use: `router = APIRouter(prefix="/<name>", tags=["<name>"])`
- Register in `memory/api.py`: add to the import line AND call `app.include_router(<module>.router)`

## Universe System

- Route file: `/home/web3relic/otto/memory/routes/universe.py`
- Loader: `/home/web3relic/otto/universe/loader.py` — provides load_project, load_persona, list_projects, list_personas, search_projects, get_registry, clear_cache
- YAML files: `universe/projects/{id}.yaml`, `universe/personas/{id}.yaml`, `universe/registry.yaml`
- Changelog: `universe/changelog.md` — append-only, format: `- YYYY-MM-DD HH:MM: message`
- After writing YAML, always call clear_cache() so in-memory cache is invalidated

## Management System (web-next)

- Path: `/home/web3relic/interfaces/web-next/`
- Framework: Next.js 15 static export (`output: "export"`)
- Pages: `src/app/{name}/page.tsx` — always `"use client"` at top
- API helper: `apiGet/apiPost/apiPut` from `@/lib/api`, proxied via `/api` to memory API at :8100
- Data hook: `useApi<T>({ fetcher, interval, enabled, deps })` from `@/hooks/use-api`
- UI: shadcn/ui in `src/components/ui/`, custom `DataCard`/`Stat` in `src/components/otto/card`
- Types: `src/lib/api-types.ts` — add new interfaces here
- Sidebar nav: `src/components/layout/app-sidebar.tsx`
- Verify with: `cd /home/web3relic/interfaces/web-next && npx tsc --noEmit && npm run build`
- TypeScript gotcha: `Record<string, unknown>` field access returns `unknown`, not assignable to ReactNode. Use `!!value` in JSX boolean guards instead of bare `{value && <...>}`

## WebAssist / Next.js Gotchas

- **React hooks before early return**: NEVER place hook calls after a conditional `return null`. This violates React's rules of hooks and can crash the root layout. Next.js responds with `html#__next_error__` (no lang/title/main) → A11y score 54/100. Fix: move ALL hooks before early return. Found in `GlobalAthenaButton` (commit 92db7e5).
- **global-error.tsx for root crashes**: Next.js default global error page lacks lang, title, main → A11y failures. Create `app/global-error.tsx` with `<html lang="en">`, `<title>`, `<main>` as safety net.
- **Framer Motion `.get()` anti-pattern**: Using `motionValue.get()` in JSX style props (e.g., `style={{ margin: marginSide.get() + 'px' }}`) captures a STATIC value at render time — it does NOT create a reactive subscription. Pass the MotionValue directly to `motion.*` style props for reactivity: `style={{ margin: marginSide }}`. Discovered in header.tsx nav margin bug (commit 07f42f5, 2026-03-07).
- **Vercel deploys**: Commits must be authored by `ottomev <abraottomev@gmail.com>`. Repo-local git config should be set. Always verify with `git log -1 --format='%an <%ae>'`.
- **Framer Motion ease types**: Tuple casts needed for cubic-bezier arrays in TypeScript (e.g., `ease: [0.4, 0, 0.2, 1] as [number, number, number, number]`). Without cast, TS errors block Vercel build.

## Alpha Signal Pipeline

- `birdeye_client.py` is at `projects/alpha/bot/birdeye_client.py` — must `sys.path.insert(0, 'bot')` from alpha dir
- `compute_wallet_win_rate()` with `use_birdeye_prices=False` returns 0.5 for ALL wallets — useless proxy; Birdeye OHLCV fails for recent/delisted meme tokens
- `compute_wallet_win_rate_from_pairs()`: FIFO buy/sell pair tracking using Helius txs — implemented 2026-03-08 (commit 9190c1b)
  - feePayer filter: only process txs wallet INITIATED (excludes LP wallets)
  - wSOL as currency: modern Solana DEXes use wSOL not native SOL (nativeBalanceChange ≈ 0 for wSOL swaps)
  - JIT LP filter: skip txs where same mint sent/received within 0.5% — catches SM_3/SM_14 bots
  - Token→token rollover: A→B swaps transfer cost basis through intermediate tokens
- **Wallet taxonomy (18 active wallets)**: 17/18 are NOT real directional traders:
  - LP positions (SM_11/12/13/17/18/20): never appear as feePayer — passive pool accounts
  - JIT LP bots (SM_3/SM_14 confirmed, SM_16/SM_19 suspected): atomic roundtrip liquidity
  - MEV bundler (SM_8): fee payer but no own token transfers
  - Only SM_10 is a real directional trader: 83% WR, +0.22 SOL realized from 6 closed trades
- **Window limitation**: 3 pages × 100 = 300 txs max. For active wallets (SM_10 does 70+ trades/day), buys may be outside window — sells show large wSOL recv but skip because no matching holdings
- Results at: `~/otto/projects/alpha/winrate_pair_tracking_results.json` (pair tracking), `~/otto/projects/alpha/requalification_results.json` (old proxy results)
- **CONCLUSION**: Wallet pool fundamentally broken. Need complete rebuild using feePayer-filtered discovery to find real directional traders.
- **FeePayer-filtered discovery (2026-03-08, commit 26edeea)**: New `wallet_discovery.py` at `~/otto/projects/alpha/`. Query trending token's SWAP txs → extract feePayer wallets → score with pair tracking. First run: 7 tokens → 260 candidates → 11 QUALIFIED traders (avg 76% WR vs 30% before). Key insight: querying token mint's txs gives feePayers = real traders (not LP positions).
- **DexScreener endpoint for trending**: `GET /token-boosts/top/v1` then `GET /latest/dex/tokens/{addr}` for pair data. No API key needed.
- **Results file**: `~/otto/projects/alpha/discovered_traders.json` — new discoveries. `winrate_pair_tracking_results.json` — existing pool scoring.
- **Signal quality tier system (2026-03-10)**: `TIER_1_WALLETS = {"SM_10"}` in signal_publisher.py. SM_10 removed from NOISY_WALLETS in whale_convergence.py AND SW_NOISY_WALLETS in signal_publisher.py. `compute_publisher_quality_score()` returns 0-100. Gate: `MIN_PUBLISHER_QUALITY_SCORE = 50`. SM_10=60+bonuses (always passes), 4-wallet convergence=40+bonuses (passes with old/high-vol token), unvetted single=10+bonuses (never passes). Tier 3 single-wallet signals are logged but not published.

## Education Engine (2026-03-17)

- Skill data: `~/otto/education/skills.json` — 10 clusters, 55 nodes, ~100 resources
- API route: `memory/routes/education.py`, prefix `/education` — 6 endpoints
- DB tables: `education_progress` (user_id, cluster_id, node_id, xp_earned, resources_completed, completed), `education_xp_log`
- OMS page: `/education` — cluster list + skill tree, level progression (Initiate→Sovereign), prereq locking
- **DB migration gotcha**: `docker exec -i ... psql ... < /path/to/file` (stdin pipe) silently succeeds but may not actually run. Use heredoc `<<'SQL' ... SQL` format instead to guarantee execution.
- push via: `GH_TOKEN=$(grep -A2 "ottomev" /home/web3relic/.config/gh/hosts.yml | grep "oauth_token:" | awk '{print $2}')` then `git remote set-url ottomev https://ottomev:${GH_TOKEN}@github.com/ottomev/web-next.git`

## Conventions

- Always use both `archived = FALSE AND deleted_at IS NULL` when querying semantic memories
- Deep merge pattern: recurse into nested dicts, replace scalars/lists wholesale
- LLM helper: `llm_chat(messages, system_instruction=..., max_tokens=..., temperature=0.0)` + `extract_json(response)`
