"""Lightweight hook registry for kernel event processing.

Inspired by OpenViking's extensibility pattern. Hooks allow Phase 5
post-processing steps to run concurrently via asyncio.gather instead
of sequentially. Two-phase design:
  - "message.post":      Independent hooks (episodic, persistence, graph, matching)
  - "message.post.late": Hooks that may depend on earlier hooks completing
                         (lesson extraction, reactive dispatch, drift)

Usage:
    from . import hooks
    hooks.register("message.post", my_hook_fn)
    await hooks.fire("message.post", pool=pool, content=content, ...)
"""

import asyncio
import logging
from typing import Any, Callable, Coroutine

log = logging.getLogger("otto.kernel.hooks")

_hooks: dict[str, list[Callable[..., Coroutine]]] = {}


def register(event: str, fn: Callable[..., Coroutine]) -> None:
    """Register an async function as a hook for the given event."""
    _hooks.setdefault(event, []).append(fn)
    log.debug(f"Hook registered: {event} -> {fn.__name__}")


def clear(event: str | None = None) -> None:
    """Clear hooks for a specific event, or all hooks if event is None."""
    if event:
        _hooks.pop(event, None)
    else:
        _hooks.clear()


def list_hooks(event: str | None = None) -> dict[str, list[str]]:
    """List registered hooks (by name) for debugging."""
    if event:
        return {event: [fn.__name__ for fn in _hooks.get(event, [])]}
    return {e: [fn.__name__ for fn in fns] for e, fns in _hooks.items()}


async def fire(event: str, **kwargs) -> list[Any]:
    """Fire all hooks registered for the event concurrently.

    Each hook receives **kwargs. Exceptions are caught per-hook and logged,
    never propagated — one failing hook cannot break other hooks.
    Returns list of results (or Exception objects for failed hooks).
    """
    handlers = _hooks.get(event, [])
    if not handlers:
        return []

    t0 = asyncio.get_event_loop().time()
    results = await asyncio.gather(
        *(fn(**kwargs) for fn in handlers),
        return_exceptions=True,
    )

    elapsed_ms = (asyncio.get_event_loop().time() - t0) * 1000
    successes = sum(1 for r in results if not isinstance(r, Exception))
    failures = len(results) - successes

    if failures:
        for fn, result in zip(handlers, results):
            if isinstance(result, Exception):
                log.warning(f"Hook {fn.__name__} failed for {event}: {result}")
        log.info(f"Hooks {event}: {successes}/{len(results)} ok, {failures} failed ({elapsed_ms:.0f}ms)")
    else:
        log.info(f"Hooks {event}: {len(results)} ok ({elapsed_ms:.0f}ms)")

    return results
