"""
Otto CDP AgentKit Integration

Wraps the Coinbase Developer Platform SDK v1.x (CdpClient) to give Otto:
  - EVM server account (non-custodial, CDP-managed key)
  - USDC/ETH balance checks on Base
  - Transfer and payment primitives for x402 / commerce endpoints

Env vars (from ~/memory/.env):
  CDP_API_KEY_NAME  — full key name (organizations/.../apiKeys/...)
  CDP_API_KEY_ID    — short UUID (fallback)
  CDP_API_KEY_SECRET — EC private key PEM

Usage:
  from projects.alpha.cdp_agentkit import OttoWallet
  wallet = OttoWallet()
  await wallet.ensure_account()
  print(wallet.address)
"""

import asyncio
import json
import os
from pathlib import Path

ENV_PATH = Path.home() / "memory" / ".env"
WALLET_STATE = Path(__file__).parent / ".agent_wallet.json"


def load_env():
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k not in os.environ:
            os.environ[k] = v


load_env()


def get_cdp_client():
    """Initialize CdpClient from env vars."""
    try:
        from cdp import CdpClient
    except ImportError:
        raise RuntimeError("cdp-sdk not installed. Run: pip install cdp-sdk --break-system-packages")

    key_id = os.environ.get("CDP_API_KEY_NAME") or os.environ.get("CDP_API_KEY_ID")
    key_secret = os.environ.get("CDP_API_KEY_SECRET", "")

    # Unescape \n in PEM key when loaded from .env
    if "\\n" in key_secret:
        key_secret = key_secret.replace("\\n", "\n")

    if not key_id or not key_secret:
        raise RuntimeError("CDP_API_KEY_NAME and CDP_API_KEY_SECRET must be set in ~/memory/.env")

    wallet_secret = os.environ.get("CDP_WALLET_SECRET")
    return CdpClient(api_key_id=key_id, api_key_secret=key_secret, wallet_secret=wallet_secret)


class OttoWallet:
    """High-level wrapper around CDP for Otto's onchain operations."""

    def __init__(self):
        self.client = get_cdp_client()
        self.account = None
        self.address = None

        # Load persisted address if exists
        if WALLET_STATE.exists():
            data = json.loads(WALLET_STATE.read_text())
            self.address = data.get("address")

    async def ensure_account(self, network: str = "base-mainnet"):
        """Get or create Otto's EVM server account."""
        result = await self.client.evm.list_accounts()
        account_list = result.accounts if hasattr(result, "accounts") else list(result)
        if account_list:
            self.account = account_list[0]
            self.address = self.account.address
            print(f"[cdp] Loaded existing account: {self.address}")
        else:
            print("[cdp] Creating new EVM server account on Base...")
            self.account = await self.client.evm.create_account()
            self.address = self.account.address
            print(f"[cdp] Account created: {self.address}")
            self._save_wallet_state(network)
        return self.account

    def _save_wallet_state(self, network: str):
        """Persist wallet address for recovery."""
        import datetime
        data = {
            "address": self.address,
            "network": network,
            "created_at": str(datetime.datetime.now()),
            "account_id": getattr(self.account, "id", None),
        }
        WALLET_STATE.write_text(json.dumps(data, indent=2))
        WALLET_STATE.chmod(0o600)
        print(f"[cdp] Wallet state saved to {WALLET_STATE}")

    async def get_eth_balance(self) -> float:
        """Check ETH balance via Base public RPC."""
        import urllib.request
        if not self.address:
            return 0.0
        payload = json.dumps({
            "jsonrpc": "2.0", "method": "eth_getBalance",
            "params": [self.address, "latest"], "id": 1,
        }).encode()
        req = urllib.request.Request(
            "https://mainnet.base.org", data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return int(data.get("result", "0x0"), 16) / 1e18

    async def get_usdc_balance(self) -> float:
        """Check USDC balance on Base."""
        import urllib.request
        USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
        if not self.address:
            return 0.0
        padded = self.address.lower().replace("0x", "").zfill(64)
        data_hex = "0x70a08231" + padded
        payload = json.dumps({
            "jsonrpc": "2.0", "method": "eth_call",
            "params": [{"to": USDC, "data": data_hex}, "latest"], "id": 2,
        }).encode()
        req = urllib.request.Request(
            "https://mainnet.base.org", data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return int(data.get("result", "0x"), 16) / 1e6

    async def close(self):
        await self.client.__aexit__(None, None, None)


async def verify_connectivity():
    """Test CDP connectivity and print account info."""
    print("[cdp] Verifying CDP connectivity...")
    wallet = OttoWallet()
    try:
        await wallet.ensure_account()
        print(f"[cdp] Address: {wallet.address}")
        eth = await wallet.get_eth_balance()
        usdc = await wallet.get_usdc_balance()
        print(f"[cdp] ETH balance: {eth:.6f} ETH")
        print(f"[cdp] USDC balance: ${usdc:.2f}")
        print("[cdp] Connectivity verified.")
        return wallet.address
    finally:
        await wallet.close()


if __name__ == "__main__":
    asyncio.run(verify_connectivity())
