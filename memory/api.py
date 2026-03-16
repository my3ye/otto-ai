import logging
import signal
from contextlib import asynccontextmanager

# Configure application logging — show INFO+ for otto.* modules
logging.basicConfig(level=logging.WARNING, format="%(name)s %(levelname)s: %(message)s")
logging.getLogger("otto").setLevel(logging.INFO)

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from .db import get_pool, close_pool
from .routes import sessions, episodic, semantic, procedural, graph, context, whatsapp, pending, leads, outreach, research, tasks, intake, working, maintenance, consolidation, metrics, reasoning, principles, agents, eval, plans, evaluator, graph_nodes, rl2f, jitrl, workspace, broadcast, files, commerce, virtuals, universe, skills, notify, webassist, articles, contacts, services, live_systems, autoevolve, orders, trading, conclusions  # noqa
from .routes.kernel_routes import router as kernel_router
from .gateway.routes import router as gateway_router
from .routes.maintenance import run_maintenance_job

logger = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler
    # Auto-reap child processes (task_runner.sh) to prevent zombies
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)

    # Startup: initialize connection pool
    pool = await get_pool()

    # Initialize AgentOS kernel
    try:
        from .config import settings as _settings
        from .kernel.provider import load_providers
        await load_providers(pool)
        logger.info("AgentOS kernel providers loaded")

        # Load agent registry
        from .kernel.agents import load_agents
        await load_agents()

        if _settings.kernel_enabled:
            from .kernel.reasoning_kernel import ensure_kernel_running
            ensure_kernel_running()
            logger.info("AgentOS Reasoning Kernel started")

        # Register Phase 5 post-processing hooks (parallel execution)
        from .kernel.ric import setup_post_process_hooks
        setup_post_process_hooks()
    except Exception as e:
        logger.warning(f"AgentOS kernel initialization failed (non-fatal): {e}")

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
    # Scheduled sync pulses for AgentOS kernel
    try:
        from .config import settings as _settings
        if _settings.kernel_enabled:
            async def _scheduled_sync():
                try:
                    from .kernel.sync import run_sync_pulse
                    await run_sync_pulse(trigger="scheduled")
                except Exception as exc:
                    logger.warning(f"Scheduled sync pulse failed: {exc}")

            _scheduler.add_job(
                _scheduled_sync,
                "interval",
                minutes=_settings.sync_interval_minutes,
                id="kernel_sync_pulse",
                name="Cognitive Sync Pulse",
                replace_existing=True,
                misfire_grace_time=300,
            )
            logger.info(f"Kernel sync pulse scheduled every {_settings.sync_interval_minutes}m")
    except Exception as e:
        logger.warning(f"Kernel sync pulse scheduling failed (non-fatal): {e}")

    _scheduler.start()
    logger.info("Nightly memory maintenance scheduler started (02:00 LKT)")

    yield

    # Shutdown
    try:
        from .kernel.reasoning_kernel import stop_kernel_loop
        await stop_kernel_loop()
    except Exception:
        pass
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
app.include_router(gateway_router)
app.include_router(kernel_router)
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
app.include_router(workspace.router)
app.include_router(broadcast.router)
app.include_router(files.router)
app.include_router(commerce.router)
app.include_router(virtuals.router)
app.include_router(universe.router)
app.include_router(skills.router)
app.include_router(notify.router)
app.include_router(webassist.router)
app.include_router(articles.router)
app.include_router(contacts.router)
app.include_router(services.router)
app.include_router(live_systems.router)
app.include_router(autoevolve.router)
app.include_router(orders.router)
app.include_router(trading.router)
app.include_router(conclusions.router)


@app.get("/hello", response_class=HTMLResponse)
async def hello():
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Hello — Otto</title>
  <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Rajdhani:wght@400;600&family=Geist+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --bg: #080c10;
      --surface: #0d1117;
      --border: #1e3a4a;
      --accent: #00d4ff;
      --accent-dim: rgba(0, 212, 255, 0.15);
      --text: #e2e8f0;
      --muted: #64748b;
    }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: 'Rajdhani', sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      overflow: hidden;
    }
    .grid-bg {
      position: fixed;
      inset: 0;
      background-image:
        linear-gradient(rgba(0,212,255,0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,212,255,0.04) 1px, transparent 1px);
      background-size: 40px 40px;
      pointer-events: none;
    }
    .glow {
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -60%);
      width: 600px;
      height: 600px;
      background: radial-gradient(ellipse, rgba(0,212,255,0.08) 0%, transparent 70%);
      pointer-events: none;
    }
    .card {
      position: relative;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 56px 64px;
      text-align: center;
      max-width: 520px;
      width: 90%;
      box-shadow: 0 0 40px rgba(0,212,255,0.06), inset 0 1px 0 rgba(0,212,255,0.08);
    }
    .badge {
      display: inline-block;
      font-family: 'Geist Mono', monospace;
      font-size: 11px;
      letter-spacing: 0.15em;
      color: var(--accent);
      background: var(--accent-dim);
      border: 1px solid rgba(0,212,255,0.3);
      border-radius: 4px;
      padding: 4px 12px;
      margin-bottom: 28px;
    }
    h1 {
      font-family: 'Orbitron', sans-serif;
      font-size: 52px;
      font-weight: 900;
      letter-spacing: -0.02em;
      color: var(--accent);
      text-shadow: 0 0 30px rgba(0,212,255,0.5);
      line-height: 1;
      margin-bottom: 16px;
    }
    p {
      font-size: 17px;
      font-weight: 400;
      color: var(--muted);
      letter-spacing: 0.02em;
      line-height: 1.6;
    }
    .divider {
      width: 60px;
      height: 1px;
      background: linear-gradient(90deg, transparent, var(--accent), transparent);
      margin: 28px auto;
    }
    .meta {
      font-family: 'Geist Mono', monospace;
      font-size: 12px;
      color: var(--muted);
      letter-spacing: 0.08em;
    }
    .dot {
      display: inline-block;
      width: 6px;
      height: 6px;
      background: var(--accent);
      border-radius: 50%;
      margin-right: 8px;
      box-shadow: 0 0 6px var(--accent);
      animation: pulse 2s ease-in-out infinite;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.3; }
    }
  </style>
</head>
<body>
  <div class="grid-bg"></div>
  <div class="glow"></div>
  <div class="card">
    <div class="badge">OTTO · SYSTEM</div>
    <h1>HELLO</h1>
    <div class="divider"></div>
    <p>The management system is online.<br>All systems operational.</p>
    <div class="divider"></div>
    <div class="meta"><span class="dot"></span>mev.otto.lk / hello</div>
  </div>
</body>
</html>"""


@app.get("/health")
async def health():
    pool = await get_pool()
    row = await pool.fetchrow("SELECT 1 as ok")
    return {"status": "healthy", "db": row["ok"] == 1}
