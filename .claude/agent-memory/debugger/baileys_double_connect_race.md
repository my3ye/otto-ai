---
name: baileys_double_connect_race
description: Baileys WhatsApp service double-connect race condition — when liveness monitor forces reconnect, calling _sock.end() AND start() creates two concurrent connections
type: feedback
---

## The Bug Pattern

In Baileys-based WhatsApp service.mjs, the liveness monitor had this pattern:

```js
// BROKEN — causes double connect:
_connected = false
try { _sock?.end(undefined) } catch {}
_sock = null
start()  // ← direct call
```

When `_sock.end()` is called, it fires `connection.update({ connection: 'close' })`, and the close handler schedules `setTimeout(start, 5000)`. Because `start()` was also called directly (and completes in ~2s before `_startingUp` flag clears), both `start()` calls execute — creating two concurrent WA connections.

Symptoms in logs: `Starting [service] WhatsApp service` appears **twice in 5 seconds** per reconnect cycle.

**Why:** The `_startingUp` guard (`if (_startingUp) return`) doesn't protect against this race because the first `start()` call from the liveness monitor completes before the second one fires via `setTimeout`.

## The Fix

Remove the direct `start()` call from the liveness monitor. Just call `_sock.end()` — the close handler's `setTimeout(start, 5000)` handles reconnect:

```js
// FIXED — single reconnect path:
_connected = false
// NOTE: do NOT call start() here — _sock.end() triggers connection.update('close')
// which already schedules setTimeout(start, 5000). Calling start() here as well
// creates a second concurrent connection (the double-connect bug).
try { _sock?.end(undefined) } catch {}
_sock = null
```

## Additional Fixes Applied

- **`LIVENESS_TIMEOUT_MS`**: 5 minutes is too aggressive for customer-facing lines (Athena/WebAssist) that may go hours without messages. Set to 30 minutes.
- **`syncFullHistory: false`**: Add to `makeWASocket()` options to suppress `AwaitingInitialSync` timeout warnings and speed up reconnect.

## Where to Apply

Any new Baileys WhatsApp service derived from Otto's `interfaces/whatsapp/service.mjs` template (e.g., `interfaces/athena-whatsapp/service.mjs`) needs all three fixes if it's a customer-facing line.

**Why:** Otto's primary WhatsApp (Otto↔Mev line) also has the same double-connect bug but Mev messages frequently so the 5-min stale timer rarely triggers in practice. Customer lines are idle most of the time.
