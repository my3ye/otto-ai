"""Otto AI — Memory API

A persistent memory and task coordination API for autonomous agents.
Provides semantic memory (vector search), episodic events, procedural learning,
and a task queue for detached agent execution.

Run with:
    uvicorn memory.api:app --host 0.0.0.0 --port 8100 --reload
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import close_pool
from .routes import health, sessions, semantic, episodic, procedural, tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown: close DB pool
    await close_pool()


app = FastAPI(
    title="Otto AI Memory API",
    description="Persistent memory and task coordination for autonomous agents",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    # allow_credentials=True is intentionally omitted: browsers reject credentialed
    # requests when allow_origins is a wildcard ("*"). If you need cookies/auth headers
    # from a web app, replace allow_origins with an explicit list of your origins.
)

# Register routes
app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(semantic.router)
app.include_router(episodic.router)
app.include_router(procedural.router)
app.include_router(tasks.router)
