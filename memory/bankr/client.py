"""
BANKR Bot API client.

Wraps api.bankr.bot Agent API with:
  - Async job execution with inline polling (up to bankr_job_poll_timeout seconds)
  - NL prompt composers — convert structured inputs to safe BANKR NL
  - Portfolio/balance fetching
  - Feature-flagged: all methods raise BankrDisabledError if BANKR_ENABLED=false

API pattern (BANKR async):
  POST /agent/prompt → {"jobId": "...", "status": "pending", ...}
  GET  /agent/job/{jobId} → {"status": "completed|failed", "result": {...}}
"""

import asyncio
import logging
import time
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class BankrError(Exception):
    """BANKR API error."""
    def __init__(self, message: str, status_code: int = 0, raw: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.raw = raw


class BankrDisabledError(BankrError):
    """Raised when BANKR_ENABLED=false or BANKR_API_KEY is not set."""
    pass


# ── NL Prompt Composers ────────────────────────────────────────────────────────

def compose_trade_prompt(
    action: str,           # "buy" | "sell" | "swap"
    amount: str,           # e.g. "200", "0.1"
    amount_unit: str,      # e.g. "USD", "ETH"
    token: str,            # e.g. "ETH", "$BNKR", "USDC"
    chain: Optional[str] = None,
    to_token: Optional[str] = None,    # for swaps
) -> str:
    """Generate a safe, unambiguous BANKR NL trade prompt."""
    if action == "swap" and to_token:
        base = f"Swap {amount} {amount_unit} to {to_token}"
    elif action == "buy":
        base = f"Buy {amount} {amount_unit} of {token}"
    elif action == "sell":
        base = f"Sell {amount} {amount_unit} of {token}"
    else:
        base = f"{action.capitalize()} {amount} {amount_unit} of {token}"

    if chain:
        base += f" on {chain}"
    return base


def compose_limit_prompt(
    action: str,           # "buy" | "sell"
    token: str,
    amount: str,
    amount_unit: str,
    trigger_type: str,     # "price" | "pct_change"
    trigger_value: str,    # e.g. "3200" or "5%"
    chain: Optional[str] = None,
) -> str:
    """Generate a BANKR NL limit order prompt."""
    if trigger_type == "pct_change":
        trigger = f"if {token} changes by {trigger_value}"
    else:
        trigger = f"when {token} reaches {trigger_value}"

    prompt = f"Set a limit order to {action} {amount} {amount_unit} of {token} {trigger}"
    if chain:
        prompt += f" on {chain}"
    return prompt


def compose_dca_prompt(
    token: str,
    amount: str,
    amount_unit: str,
    frequency: str,        # "daily" | "weekly" | "monthly"
    duration: Optional[str] = None,  # e.g. "for 3 months"
    chain: Optional[str] = None,
) -> str:
    """Generate a BANKR NL DCA strategy prompt."""
    prompt = f"DCA {amount} {amount_unit} into {token} {frequency}"
    if duration:
        prompt += f" {duration}"
    if chain:
        prompt += f" on {chain}"
    return prompt


def compose_stop_loss_prompt(
    token: str,
    trigger_pct: str,      # e.g. "-20%" or "-15%"
    chain: Optional[str] = None,
    all_holdings: bool = False,
) -> str:
    """Generate a BANKR NL stop-loss prompt."""
    if all_holdings:
        prompt = f"Set stop loss for all holdings at {trigger_pct}"
    else:
        prompt = f"Set stop loss for {token} at {trigger_pct}"
    if chain:
        prompt += f" on {chain}"
    return prompt


def compose_launch_prompt(
    token_name: str,
    token_symbol: str,
    supply: str,
    platform: str = "doppler",     # "doppler" | "raydium"
    description: Optional[str] = None,
    chain: Optional[str] = None,
) -> str:
    """Generate a BANKR NL token launch prompt."""
    prompt = f"Launch a token called {token_name} with symbol {token_symbol} and supply {supply}"
    if platform == "doppler":
        prompt += " using Doppler fair launch"
    elif platform == "raydium":
        prompt += " using Raydium LaunchLab"
    if description:
        prompt += f". Description: {description}"
    if chain:
        prompt += f" on {chain}"
    return prompt


# ── BankrClient ────────────────────────────────────────────────────────────────

class BankrClient:
    """
    Async BANKR Agent API client.

    Usage:
        client = BankrClient.from_settings()
        result = await client.execute(prompt="Buy $100 of ETH on Base")
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.bankr.bot",
        poll_timeout: int = 30,
        poll_interval: float = 2.0,
        enabled: bool = True,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.poll_timeout = poll_timeout
        self.poll_interval = poll_interval
        self.enabled = enabled

    @classmethod
    def from_settings(cls) -> "BankrClient":
        """Create client from Otto settings."""
        from ..config import settings
        return cls(
            api_key=settings.bankr_api_key,
            base_url=settings.bankr_api_url,
            poll_timeout=settings.bankr_job_poll_timeout,
            poll_interval=settings.bankr_job_poll_interval,
            enabled=settings.bankr_enabled,
        )

    def _check_enabled(self):
        if not self.enabled:
            raise BankrDisabledError(
                "BANKR integration is disabled. Set BANKR_ENABLED=true and provide BANKR_API_KEY."
            )
        if not self.api_key:
            raise BankrDisabledError(
                "BANKR_API_KEY is not configured. Obtain a bk_... key from bankr.bot."
            )

    def _headers(self) -> dict:
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _post(self, path: str, payload: dict) -> Any:
        """POST to BANKR API."""
        self._check_enabled()
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.post(url, json=payload, headers=self._headers())
                if resp.status_code >= 400:
                    raise BankrError(
                        f"BANKR API error {resp.status_code}: {resp.text[:200]}",
                        status_code=resp.status_code,
                        raw=resp.text,
                    )
                return resp.json()
            except httpx.RequestError as e:
                raise BankrError(f"BANKR API unreachable: {e}")

    async def _get(self, path: str) -> Any:
        """GET from BANKR API."""
        self._check_enabled()
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(url, headers=self._headers())
                if resp.status_code >= 400:
                    raise BankrError(
                        f"BANKR API error {resp.status_code}: {resp.text[:200]}",
                        status_code=resp.status_code,
                    )
                return resp.json()
            except httpx.RequestError as e:
                raise BankrError(f"BANKR API unreachable: {e}")

    async def submit_prompt(
        self,
        prompt: str,
        thread_id: Optional[str] = None,
    ) -> dict:
        """
        Submit a NL prompt to BANKR Agent API.
        Returns immediately with jobId (does not wait for completion).
        """
        payload: dict[str, Any] = {"prompt": prompt}
        if thread_id:
            payload["threadId"] = thread_id
        return await self._post("/agent/prompt", payload)

    async def get_job(self, job_id: str) -> dict:
        """Poll a single job status."""
        return await self._get(f"/agent/job/{job_id}")

    async def execute(
        self,
        prompt: str,
        thread_id: Optional[str] = None,
    ) -> dict:
        """
        Submit prompt and poll until completed/failed or timeout.

        Returns dict with:
          {
            "job_id": str,
            "status": "completed" | "failed" | "pending",
            "result": {...} | None,    # BANKR result on success
            "error": str | None,
            "timed_out": bool,
            "elapsed": float,
          }
        """
        submission = await self.submit_prompt(prompt, thread_id)
        job_id = submission.get("jobId") or submission.get("id")
        if not job_id:
            raise BankrError(f"No jobId in BANKR response: {submission}")

        logger.info("BANKR job submitted: %s (prompt: %.60s...)", job_id, prompt)

        start = time.monotonic()
        elapsed = 0.0
        while elapsed < self.poll_timeout:
            await asyncio.sleep(self.poll_interval)
            elapsed = time.monotonic() - start

            job = await self.get_job(job_id)
            status = job.get("status", "").lower()

            if status in ("completed", "success"):
                logger.info("BANKR job %s completed in %.1fs", job_id, elapsed)
                return {
                    "job_id": job_id,
                    "status": "completed",
                    "result": job.get("result") or job,
                    "error": None,
                    "timed_out": False,
                    "elapsed": elapsed,
                }
            elif status in ("failed", "error", "cancelled"):
                error_msg = job.get("error") or job.get("message") or "Job failed"
                logger.warning("BANKR job %s failed: %s", job_id, error_msg)
                return {
                    "job_id": job_id,
                    "status": "failed",
                    "result": None,
                    "error": error_msg,
                    "timed_out": False,
                    "elapsed": elapsed,
                }
            # still pending — continue polling

        logger.warning("BANKR job %s timed out after %.1fs", job_id, elapsed)
        return {
            "job_id": job_id,
            "status": "pending",
            "result": None,
            "error": None,
            "timed_out": True,
            "elapsed": elapsed,
        }

    async def get_portfolio(self) -> dict:
        """
        Fetch cross-chain balances.
        Uses /agent/balances endpoint.
        """
        return await self._get("/agent/balances")

    async def get_status(self) -> dict:
        """
        Check API key health and account status.
        Returns sanitized status (no key exposure).
        """
        data = await self._get("/agent/status")
        # Scrub any key leakage
        data.pop("apiKey", None)
        data.pop("api_key", None)
        return data
