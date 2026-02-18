from contextlib import asynccontextmanager
from fastapi import FastAPI
from .db import get_pool, close_pool
from .routes import sessions, episodic, semantic, procedural, graph, context, whatsapp, pending, leads


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize connection pool
    await get_pool()
    yield
    # Shutdown: close pool
    await close_pool()


app = FastAPI(
    title="Otto Memory API",
    version="0.1.0",
    lifespan=lifespan,
)

# Register routes
app.include_router(sessions.router)
app.include_router(episodic.router)
app.include_router(semantic.router)
app.include_router(procedural.router)
app.include_router(graph.router)
app.include_router(context.router)
app.include_router(whatsapp.router)
app.include_router(pending.router)
app.include_router(leads.router)


@app.get("/health")
async def health():
    pool = await get_pool()
    row = await pool.fetchrow("SELECT 1 as ok")
    return {"status": "healthy", "db": row["ok"] == 1}
