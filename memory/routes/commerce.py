"""
Otto Commerce API — x402-style paid inference endpoints for agent-to-agent commerce.

Implements the x402 HTTP payment protocol pattern:
  1. Client requests a service endpoint
  2. Server returns HTTP 402 with payment requirements (wallet + amount + network)
  3. Client pays USDC on-chain (Base L2)
  4. Client re-requests with X-Payment header containing encoded payment proof
  5. Server verifies payment and serves the response

Configuration (~/memory/.env):
  AGENT_WALLET_ADDRESS   Base (EVM) wallet address to receive USDC payments
  COMMERCE_ENABLED       Set to "true" to enable (default: false for safety)
  COMMERCE_FREE_TIER     Set to "true" to skip payment verification (dev mode)

Pricing:
  /commerce/search       $0.01 USDC per call (semantic memory search)
  /commerce/research     $0.05 USDC per call (research + answer)
  /commerce/context      $0.10 USDC per call (full context briefing)
  /commerce/ask          $0.02 USDC per call (general Q&A via LLM)

x402 Protocol Reference: https://x402.org
"""

import hashlib
import hmac
import json
import logging
import os
import time
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/commerce", tags=["commerce"])

# --- Configuration -----------------------------------------------------------

def _cfg(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


AGENT_WALLET = _cfg("AGENT_WALLET_ADDRESS", "")
COMMERCE_ENABLED = _cfg("COMMERCE_ENABLED", "false").lower() == "true"
FREE_TIER = _cfg("COMMERCE_FREE_TIER", "false").lower() == "true"

# USDC contract on Base L2 (mainnet)
USDC_CONTRACT_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
CHAIN_ID = 8453  # Base mainnet

SERVICE_PRICES = {
    "search": 0.01,    # $0.01 USDC — semantic memory search
    "research": 0.05,  # $0.05 USDC — deep research query
    "context": 0.10,   # $0.10 USDC — full context briefing
    "ask": 0.02,       # $0.02 USDC — general Q&A
}

# --- x402 Payment Models ------------------------------------------------------

class PaymentRequirements(BaseModel):
    """Returned in HTTP 402 response. Tells client how to pay."""
    scheme: str = "exact"
    network: str = "base-mainnet"
    max_amount_required: str  # USDC in 6-decimal integer string (e.g. "10000" = $0.01)
    resource: str             # The endpoint being requested
    description: str
    mime_type: str = "application/json"
    pay_to: str               # EVM wallet address
    max_timeout_seconds: int = 300
    asset: str = USDC_CONTRACT_BASE
    extra: dict = {}


class ServiceCatalogItem(BaseModel):
    service: str
    description: str
    price_usd: float
    endpoint: str
    method: str = "POST"


class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    threshold: float = 0.7


class ResearchRequest(BaseModel):
    question: str
    depth: str = "standard"  # standard | deep


class AskRequest(BaseModel):
    message: str
    context: Optional[str] = None


# --- Payment verification ----------------------------------------------------

def _usdc_amount(price_usd: float) -> str:
    """Convert USD float to USDC 6-decimal integer string."""
    return str(int(price_usd * 1_000_000))


def _payment_requirements(service: str, request_url: str) -> dict:
    """Build x402 payment requirements for a service."""
    price = SERVICE_PRICES.get(service, 0.01)
    return PaymentRequirements(
        max_amount_required=_usdc_amount(price),
        resource=request_url,
        description=f"Otto AI {service} service — {price:.2f} USDC",
        pay_to=AGENT_WALLET or "CONFIGURE_AGENT_WALLET",
        extra={"version": "1.0", "otto": "true"},
    ).model_dump()


def _payment_required_response(service: str, request_url: str) -> JSONResponse:
    """Return HTTP 402 with payment requirements."""
    pmt = _payment_requirements(service, request_url)
    return JSONResponse(
        status_code=402,
        content={
            "error": "Payment Required",
            "x402Version": 1,
            "accepts": [pmt],
        },
        headers={"X-Payment-Required": "true"},
    )


async def _verify_payment(x_payment: str, service: str) -> bool:
    """
    Verify x402 payment proof header.

    In production: verify via Coinbase CDP facilitator or direct Base RPC call.
    In v0 (FREE_TIER=true): skip verification entirely (for testing).
    In v1: decode X-Payment header (base64 JSON), verify TX hash on Base.

    X-Payment header format (x402 spec):
      base64(JSON({
        "x402Version": 1,
        "scheme": "exact",
        "network": "base-mainnet",
        "payload": {
          "signature": "0x...",
          "authorization": { "from": "0x...", "to": "0x...", "value": "10000", ... }
        }
      }))
    """
    if FREE_TIER:
        logger.info("[commerce] Free tier — payment verification skipped")
        return True

    if not x_payment:
        return False

    try:
        import base64
        decoded = base64.b64decode(x_payment + "==").decode("utf-8")
        payment_data = json.loads(decoded)

        # Basic structural validation
        if payment_data.get("x402Version") != 1:
            logger.warning("[commerce] Invalid x402 version")
            return False
        if payment_data.get("network") != "base-mainnet":
            logger.warning("[commerce] Wrong network")
            return False

        payload = payment_data.get("payload", {})
        auth = payload.get("authorization", {})

        # Check payment goes to our wallet
        if AGENT_WALLET and auth.get("to", "").lower() != AGENT_WALLET.lower():
            logger.warning(f"[commerce] Payment to wrong address: {auth.get('to')}")
            return False

        # Check value matches expected price
        expected = _usdc_amount(SERVICE_PRICES.get(service, 0.01))
        if auth.get("value") != expected:
            logger.warning(f"[commerce] Wrong payment amount: {auth.get('value')} vs {expected}")
            return False

        # TODO: verify signature via Coinbase CDP facilitator
        # POST https://api.coinbase.com/api/v1/x402/verify with payment_data
        # For now, trust the structure if wallet + amount check out
        logger.info(f"[commerce] Payment verified (structural check): {service}")
        return True

    except Exception as e:
        logger.warning(f"[commerce] Payment verification error: {e}")
        return False


async def check_payment(
    request: Request,
    service: str,
) -> None:
    """Dependency: check payment before serving a paid endpoint."""
    if not COMMERCE_ENABLED:
        raise HTTPException(status_code=503, detail="Commerce endpoints disabled. Set COMMERCE_ENABLED=true in .env to activate.")

    if not AGENT_WALLET:
        raise HTTPException(status_code=503, detail="Agent wallet not configured. Set AGENT_WALLET_ADDRESS in .env.")

    x_payment = request.headers.get("X-Payment", "")

    if not FREE_TIER and not x_payment:
        # Return 402 payment required
        response = _payment_required_response(service, str(request.url))
        # FastAPI doesn't support returning responses from dependencies
        # We raise an exception instead and handle it in the endpoint
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Payment Required",
                "x402Version": 1,
                "accepts": [_payment_requirements(service, str(request.url))],
            },
        )

    if not FREE_TIER:
        valid = await _verify_payment(x_payment, service)
        if not valid:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "Payment Required — invalid or insufficient payment",
                    "x402Version": 1,
                    "accepts": [_payment_requirements(service, str(request.url))],
                },
            )


# --- Service Catalog --------------------------------------------------------

@router.get("/catalog")
async def get_catalog():
    """
    List all available commerce endpoints with pricing.
    Free to call — no payment required.
    """
    wallet = AGENT_WALLET or "NOT_CONFIGURED"
    return {
        "name": "Otto AI Commerce API",
        "description": "Pay-per-use AI agent services. Semantic search, research, and reasoning powered by Otto.",
        "wallet": wallet,
        "network": "base-mainnet",
        "payment_asset": USDC_CONTRACT_BASE,
        "enabled": COMMERCE_ENABLED,
        "services": [
            ServiceCatalogItem(
                service="search",
                description="Semantic search through Otto's knowledge base. Returns most relevant facts.",
                price_usd=0.01,
                endpoint="/commerce/search",
            ).model_dump(),
            ServiceCatalogItem(
                service="ask",
                description="Ask Otto a question. Returns LLM-generated answer with memory context.",
                price_usd=0.02,
                endpoint="/commerce/ask",
            ).model_dump(),
            ServiceCatalogItem(
                service="research",
                description="Deep research query. Otto searches memory, synthesizes an answer.",
                price_usd=0.05,
                endpoint="/commerce/research",
            ).model_dump(),
            ServiceCatalogItem(
                service="context",
                description="Full context briefing — all current priorities, recent events, active tasks.",
                price_usd=0.10,
                endpoint="/commerce/context",
            ).model_dump(),
        ],
        "x402_version": 1,
        "how_to_pay": (
            "1. Call any /commerce/* endpoint. "
            "2. If payment required, you'll get HTTP 402 with X-Payment-Required header. "
            "3. Pay the listed USDC amount to the wallet address on Base mainnet. "
            "4. Encode payment proof as base64 JSON per x402 spec. "
            "5. Re-call the endpoint with X-Payment: <encoded_proof> header."
        ),
    }


# --- Paid Endpoints ----------------------------------------------------------

@router.post("/search")
async def paid_search(body: SearchRequest, request: Request):
    """
    Paid semantic search — $0.01 USDC per call.
    Searches Otto's semantic memory for facts relevant to the query.
    """
    await check_payment(request, "search")

    from ..embeddings import get_embedding
    from ..db import get_pool

    pool = await get_pool()
    embed = await get_embedding(body.query)
    rows = await pool.fetch(
        """
        SELECT content, category, relevance_score,
               1 - (embedding <=> $1::vector) AS similarity
        FROM semantic_memories
        WHERE deleted_at IS NULL AND archived = FALSE
          AND 1 - (embedding <=> $1::vector) >= $3
        ORDER BY embedding <=> $1::vector
        LIMIT $2
        """,
        embed,
        body.limit,
        body.threshold,
    )
    results = [
        {"content": r["content"], "category": r["category"], "similarity": float(r["similarity"])}
        for r in rows
    ]
    return {
        "service": "search",
        "query": body.query,
        "results": results,
        "cost_usd": SERVICE_PRICES["search"],
    }


@router.post("/ask")
async def paid_ask(body: AskRequest, request: Request):
    """
    Paid Q&A — $0.02 USDC per call.
    Routes question through Otto's LLM with relevant memory context.
    """
    await check_payment(request, "ask")

    from ..llm import llm_chat
    from ..embeddings import get_embedding
    from ..db import get_pool

    # Get relevant memories
    pool = await get_pool()
    try:
        embed = await get_embedding(body.message)
        rows = await pool.fetch(
            """
            SELECT content, category, relevance_score
            FROM semantic_memories
            WHERE deleted_at IS NULL AND archived = FALSE
            ORDER BY embedding <=> $1::vector
            LIMIT 5
            """,
            embed,
        )
        memory_context = "\n".join(
            f"[{r['category']}] {r['content']}" for r in rows
        )
    except Exception as e:
        logger.warning(f"[commerce/ask] Memory fetch failed: {e}")
        memory_context = ""

    system = (
        "You are Otto, an AI agent with persistent memory. "
        "Answer the user's question concisely using your memory context where relevant. "
        "If memory context doesn't cover the question, use your general knowledge."
    )
    if memory_context:
        system += f"\n\nMemory context:\n{memory_context}"
    if body.context:
        system += f"\n\nAdditional context: {body.context}"

    answer = await llm_chat(
        messages=[{"role": "user", "content": body.message}],
        system_instruction=system,
        max_tokens=500,
    )

    return {
        "service": "ask",
        "answer": answer,
        "cost_usd": SERVICE_PRICES["ask"],
    }


@router.post("/research")
async def paid_research(body: ResearchRequest, request: Request):
    """
    Paid deep research — $0.05 USDC per call.
    Otto searches memory and synthesizes a research-grade answer.
    """
    await check_payment(request, "research")

    from ..llm import llm_chat
    from ..embeddings import get_embedding
    from ..db import get_pool

    pool = await get_pool()
    try:
        embed = await get_embedding(body.question)
        rows = await pool.fetch(
            """
            SELECT content, category, relevance_score, created_at
            FROM semantic_memories
            WHERE deleted_at IS NULL AND archived = FALSE
            ORDER BY embedding <=> $1::vector
            LIMIT 10
            """,
            embed,
        )
        facts = "\n".join(
            f"[{r['category']}] {r['content']}" for r in rows
        )
    except Exception as e:
        logger.warning(f"[commerce/research] Memory fetch failed: {e}")
        facts = ""

    depth_instruction = (
        "Provide a thorough, structured answer with sources cited where known."
        if body.depth == "deep"
        else "Provide a clear, direct answer synthesizing the available information."
    )

    system = (
        f"You are Otto, an AI research agent. {depth_instruction} "
        "Draw on both memory context and your general knowledge."
    )
    if facts:
        system += f"\n\nMemory context:\n{facts}"

    answer = await llm_chat(
        messages=[{"role": "user", "content": body.question}],
        system_instruction=system,
        max_tokens=800,
    )

    return {
        "service": "research",
        "question": body.question,
        "answer": answer,
        "depth": body.depth,
        "cost_usd": SERVICE_PRICES["research"],
    }


@router.post("/context")
async def paid_context(request: Request):
    """
    Paid full context briefing — $0.10 USDC per call.
    Returns Otto's complete current state: priorities, tasks, recent events.
    """
    await check_payment(request, "context")

    from ..db import get_pool

    pool = await get_pool()

    # Recent episodic events
    events = await pool.fetch(
        """
        SELECT event_type, content, created_at
        FROM episodic_events
        ORDER BY created_at DESC
        LIMIT 10
        """,
    )

    # Active tasks
    tasks = await pool.fetch(
        """
        SELECT id, prompt, status, priority, created_at
        FROM tasks
        WHERE status IN ('pending', 'running')
        ORDER BY priority DESC, created_at DESC
        LIMIT 10
        """,
    )

    return {
        "service": "context",
        "recent_events": [
            {"type": r["event_type"], "content": r["content"][:200], "at": str(r["created_at"])}
            for r in events
        ],
        "active_tasks": [
            {"id": str(r["id"]), "status": r["status"], "priority": r["priority"]}
            for r in tasks
        ],
        "cost_usd": SERVICE_PRICES["context"],
    }


# --- x402 Error Handler (for proper 402 responses) --------------------------

def register_commerce_exception_handler(app):
    """
    Register a custom exception handler to return proper x402 402 responses.
    Call this from api.py after app creation:
        from .routes.commerce import register_commerce_exception_handler
        register_commerce_exception_handler(app)
    """
    from fastapi.responses import JSONResponse
    from fastapi.exceptions import RequestValidationError

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        if exc.status_code == 402 and isinstance(exc.detail, dict):
            return JSONResponse(
                status_code=402,
                content=exc.detail,
                headers={
                    "X-Payment-Required": "true",
                    "Access-Control-Expose-Headers": "X-Payment-Required",
                },
            )
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
