# Heartbeat Orchestrator Memory

## API Quirks
- **RL2F outcome scoring**: Use `PATCH` method, not `PUT` or `POST`. Endpoint: `/reasoning/<id>/outcome`. Both PUT and POST return 405.
- **Proposals endpoint**: `GET /pending/proposals?status=open` works for checking open proposals.
- **Working memory update**: `PUT /working/memory/{slot}` with `{"content": "..."}` body.

## Operational Patterns
- **Idle posture**: When all proposals are blocked on Mev and it's nighttime IST, skip messaging and task creation. Correct behavior.
- **Proposal age threshold**: Nudge Mev if any proposal exceeds 24h without resolution.
- **Rate limit cap**: When rate limit alert is active, cap new task creation at 1 per cycle.

## Current State (cycle 67, 2026-03-07 15:03 IST)
- All products LIVE: webassist.ink, mev.otto.lk, otto.lk
- NEW MEV DIRECTIVE: "Get signals right, so that we can earn through that. Do proper research."
- Signals research task running (f9f5c163, P10, researcher, $8)
- Queue: 0 pending, 1 running, 297 completed, 27 failed
- RL2F: 37.5% (3/8, noise-range)
- 4 crypto proposals open but superseded by signals directive
- WebAssist feature-complete, blocked on GSC (Mev action)
- Tip wallet: web3relic.eth (0x3c54...3be5)
