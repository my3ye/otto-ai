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

## Conventions

- Always use both `archived = FALSE AND deleted_at IS NULL` when querying semantic memories
- Deep merge pattern: recurse into nested dicts, replace scalars/lists wholesale
- LLM helper: `llm_chat(messages, system_instruction=..., max_tokens=..., temperature=0.0)` + `extract_json(response)`
