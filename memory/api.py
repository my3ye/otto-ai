import logging
import signal
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI

from .db import get_pool, close_pool
from .routes import sessions, episodic, semantic, procedural, graph, context, whatsapp, pending, leads, outreach, research, tasks, intake, working, maintenance, consolidation, metrics, reasoning, principles, agents, eval, plans, evaluator, graph_nodes, rl2f, jitrl
from .routes.maintenance import run_maintenance_job

logger = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler
    # Auto-reap child processes (task_runner.sh) to prevent zombies
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)

    # Startup: initialize connection pool
    await get_pool()

    # Start nightly maintenance scheduler (02:00 LKT = 20:30 UTC)
    _scheduler = AsyncIOScheduler(timezone="Asia/Colombo")
    _scheduler.add_job(
        run_maintenance_job,
        CronTrigger(hour=2, minute=0, timezone="Asia/Colombo"),
        id="nightly_maintenance",
        name="Nightly memory decay + consolidation",
        replace_existing=True,
        misfire_grace_time=3600,  # allow up to 1hr late if service was down
    )
    _scheduler.start()
    logger.info("Nightly memory maintenance scheduler started (02:00 LKT)")

    yield

    # Shutdown
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
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
app.include_router(graph_nodes.router)  # Must be before graph (catch-all proxy)
app.include_router(graph.router)
app.include_router(context.router)
app.include_router(whatsapp.router)
app.include_router(pending.router)
app.include_router(leads.router)
app.include_router(outreach.router)
app.include_router(research.router)
app.include_router(tasks.router)
app.include_router(intake.router)
app.include_router(working.router)
app.include_router(maintenance.router)
app.include_router(consolidation.router)
app.include_router(metrics.router)
app.include_router(reasoning.router)
app.include_router(principles.router)
app.include_router(agents.router)
app.include_router(eval.router)
app.include_router(plans.router)
app.include_router(evaluator.router)
app.include_router(rl2f.router)
app.include_router(jitrl.router)


@app.get("/health")
async def health():
    pool = await get_pool()
    row = await pool.fetchrow("SELECT 1 as ok")
    return {"status": "healthy", "db": row["ok"] == 1}
