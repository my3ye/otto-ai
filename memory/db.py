import json
import logging

import asyncpg
from .config import settings

logger = logging.getLogger(__name__)
_pool: asyncpg.Pool | None = None
_traced_pool = None  # TracedPool wrapper (set when OTel active)


async def _init_connection(conn: asyncpg.Connection):
    """Set up JSON codec so JSONB columns return Python objects."""
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )
    await conn.set_type_codec(
        "json",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


class TracedPool:
    """Thin wrapper adding OTel spans around asyncpg pool operations.

    Delegates all unknown attributes to the underlying pool, so existing code
    using pool.acquire(), pool.release(), etc. continues to work.
    """

    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
        try:
            from opentelemetry import trace
            self._tracer = trace.get_tracer("otto.db")
        except ImportError:
            self._tracer = None

    async def fetch(self, query, *args, **kwargs):
        if self._tracer:
            with self._tracer.start_as_current_span(
                "db.fetch", attributes={"db.statement": query[:200]}
            ):
                return await self._pool.fetch(query, *args, **kwargs)
        return await self._pool.fetch(query, *args, **kwargs)

    async def fetchrow(self, query, *args, **kwargs):
        if self._tracer:
            with self._tracer.start_as_current_span(
                "db.fetchrow", attributes={"db.statement": query[:200]}
            ):
                return await self._pool.fetchrow(query, *args, **kwargs)
        return await self._pool.fetchrow(query, *args, **kwargs)

    async def fetchval(self, query, *args, **kwargs):
        if self._tracer:
            with self._tracer.start_as_current_span(
                "db.fetchval", attributes={"db.statement": query[:200]}
            ):
                return await self._pool.fetchval(query, *args, **kwargs)
        return await self._pool.fetchval(query, *args, **kwargs)

    async def execute(self, query, *args, **kwargs):
        if self._tracer:
            with self._tracer.start_as_current_span(
                "db.execute", attributes={"db.statement": query[:200]}
            ):
                return await self._pool.execute(query, *args, **kwargs)
        return await self._pool.execute(query, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._pool, name)


async def get_pool() -> asyncpg.Pool:
    global _pool, _traced_pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            user=settings.postgres_user,
            password=settings.postgres_password,
            database=settings.postgres_db,
            host=settings.postgres_host,
            port=settings.postgres_port,
            min_size=2,
            max_size=10,
            init=_init_connection,
        )
        # Wrap with tracing if OTel is enabled
        if settings.otel_enabled:
            _traced_pool = TracedPool(_pool)
            logger.info("DB pool wrapped with OTel TracedPool")
    if _traced_pool is not None:
        return _traced_pool
    return _pool


async def close_pool():
    global _pool, _traced_pool
    _traced_pool = None
    if _pool is not None:
        await _pool.close()
        _pool = None
