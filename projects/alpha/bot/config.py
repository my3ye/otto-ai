"""
Configuration loader for Project Alpha Solana trading bot.
Reads secrets from environment / .env file.
"""

import os
from dotenv import load_dotenv

load_dotenv()

HELIUS_API_KEY: str = os.environ.get("HELIUS_API_KEY", "")
WALLET_PRIVATE_KEY: str = os.environ.get("WALLET_PRIVATE_KEY", "")

# Helius RPC endpoint (staked if key provided, else public devnet-safe)
HELIUS_RPC_URL: str = (
    f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
    if HELIUS_API_KEY
    else "https://api.mainnet-beta.solana.com"
)

# Helius DAS / Enhanced API base URL
HELIUS_API_BASE: str = "https://api.helius.xyz/v0"

# How far back to look when filtering recent transactions (seconds)
SCAN_WINDOW_SECONDS: int = 30 * 60  # 30 minutes

# Path to the wallets seed file (relative to project alpha root)
WALLETS_JSON_PATH: str = "/home/web3relic/otto/projects/alpha/wallets.json"
