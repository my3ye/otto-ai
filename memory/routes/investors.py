"""Investor page authentication — server-side token issuance."""
import hashlib
import hmac
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import settings

router = APIRouter(prefix="/investors", tags=["investors"])

# Token lifetime: 24 hours
TOKEN_TTL_SECONDS = 86400
# HMAC secret derived from the investor password (stable across restarts)
_HMAC_SECRET = hashlib.sha256(b"otto-investor-token:" + settings.investor_password.encode()).digest()


def _make_token(ts: int) -> str:
    """Return HMAC-SHA256 of the timestamp (hex)."""
    return hmac.new(_HMAC_SECRET, str(ts).encode(), hashlib.sha256).hexdigest()


def _valid_token(token: str) -> bool:
    """Verify a previously-issued token is still within its TTL."""
    now = int(time.time())
    # Token encodes the issuance timestamp rounded down to TOKEN_TTL_SECONDS windows
    window = now // TOKEN_TTL_SECONDS * TOKEN_TTL_SECONDS
    for ts in (window, window - TOKEN_TTL_SECONDS):
        expected = _make_token(ts)
        if hmac.compare_digest(token, expected):
            return True
    return False


class AuthRequest(BaseModel):
    password: str


class AuthResponse(BaseModel):
    token: str
    expires_in: int


class VerifyRequest(BaseModel):
    token: str


@router.post("/auth", response_model=AuthResponse)
async def auth(req: AuthRequest):
    """Validate investor password and return a short-lived token."""
    if not hmac.compare_digest(req.password.encode(), settings.investor_password.encode()):
        raise HTTPException(status_code=401, detail="Invalid password")
    ts = int(time.time()) // TOKEN_TTL_SECONDS * TOKEN_TTL_SECONDS
    token = _make_token(ts)
    remaining = TOKEN_TTL_SECONDS - (int(time.time()) - ts)
    return AuthResponse(token=token, expires_in=remaining)


@router.post("/verify")
async def verify(req: VerifyRequest):
    """Check whether a token is still valid."""
    if not _valid_token(req.token):
        raise HTTPException(status_code=401, detail="Token expired or invalid")
    return {"valid": True}
