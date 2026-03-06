"""
Otto Agent Wallet Setup

Creates a Coinbase Developer Platform (CDP) wallet for Otto to:
  - Receive USDC payments via x402 protocol
  - Hold USDC yield (4.1% APR passive)
  - Interact with Virtuals Protocol on Base

Prerequisites:
  1. Coinbase Developer Platform account: https://portal.cdp.coinbase.com
  2. Create an API Key (Project > API Keys > Create)
  3. Download the api_key.json file
  4. pip install cdp-sdk

Usage:
  python setup_agent_wallet.py --create
  python setup_agent_wallet.py --status
  python setup_agent_wallet.py --fund-check

The wallet address goes into ~/memory/.env as:
  AGENT_WALLET_ADDRESS=0x...

For Virtuals Protocol deployment:
  - Also need 100 VIRTUAL tokens on Base (~$73-77)
  - Bridge ETH to Base via https://bridge.base.org
  - Buy VIRTUAL on Uniswap (Base): https://app.uniswap.org
"""

import argparse
import json
import os
import sys
from pathlib import Path

ENV_PATH = Path.home() / "memory" / ".env"
WALLET_STATE = Path(__file__).parent / ".agent_wallet.json"
CDP_KEY_PATH = Path.home() / "memory" / "cdp_api_key.json"


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


def save_wallet_to_env(address: str, network: str = "base-mainnet"):
    """Append wallet address to ~/memory/.env"""
    env_content = ENV_PATH.read_text() if ENV_PATH.exists() else ""

    if "AGENT_WALLET_ADDRESS=" in env_content:
        lines = env_content.splitlines()
        lines = [
            f"AGENT_WALLET_ADDRESS={address}" if l.startswith("AGENT_WALLET_ADDRESS=") else l
            for l in lines
        ]
        ENV_PATH.write_text("\n".join(lines) + "\n")
        print(f"[wallet] Updated AGENT_WALLET_ADDRESS in .env")
    else:
        with open(ENV_PATH, "a") as f:
            f.write(f"\n# Otto Agent Wallet (Base L2, created by setup_agent_wallet.py)\n")
            f.write(f"AGENT_WALLET_ADDRESS={address}\n")
            f.write(f"AGENT_WALLET_NETWORK={network}\n")
        print(f"[wallet] Added AGENT_WALLET_ADDRESS to .env")


def create_wallet():
    """Create a new CDP wallet for Otto."""
    try:
        from cdp import Cdp, Wallet
    except ImportError:
        print("[wallet] ERROR: cdp-sdk not installed.")
        print("  Install: pip install cdp-sdk")
        print("  Or in a venv: pip install cdp-sdk httpx")
        sys.exit(1)

    if not CDP_KEY_PATH.exists():
        print(f"[wallet] ERROR: CDP API key not found at {CDP_KEY_PATH}")
        print("  Steps:")
        print("  1. Go to https://portal.cdp.coinbase.com")
        print("  2. Create an API Key under your project")
        print("  3. Download the JSON key file")
        print(f"  4. Save it to: {CDP_KEY_PATH}")
        sys.exit(1)

    print("[wallet] Loading CDP credentials...")
    key_data = json.loads(CDP_KEY_PATH.read_text())
    Cdp.configure(key_data["name"], key_data["privateKey"])

    print("[wallet] Creating new wallet on Base mainnet...")
    wallet = Wallet.create(network_id="base-mainnet")

    address = wallet.default_address.address_id
    print(f"[wallet] Wallet created!")
    print(f"  Address: {address}")
    print(f"  Network: base-mainnet")

    # Save wallet state for recovery
    wallet_data = wallet.export_data()
    WALLET_STATE.write_text(json.dumps({
        "address": address,
        "network": "base-mainnet",
        "wallet_id": wallet.id,
        "seed": wallet_data.seed,  # encrypted mnemonic
        "created_at": str(__import__("datetime").datetime.now()),
    }, indent=2))
    WALLET_STATE.chmod(0o600)
    print(f"[wallet] Wallet data saved to: {WALLET_STATE}")
    print("[wallet] KEEP THIS FILE SAFE — it contains your wallet seed")

    save_wallet_to_env(address)

    print("\n=== Next Steps ===")
    print(f"1. Fund wallet with ETH (for gas): {address}")
    print(f"   Bridge from Ethereum: https://bridge.base.org")
    print(f"   Min ~0.01 ETH for gas (~$25-30)")
    print(f"")
    print(f"2. Buy 100 VIRTUAL tokens on Uniswap (Base):")
    print(f"   https://app.uniswap.org — cost ~$73-77")
    print(f"   VIRTUAL contract (Base): 0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b")
    print(f"")
    print(f"3. Register Otto on Virtuals Protocol:")
    print(f"   https://app.virtuals.io → Launch Agent")
    print(f"   Set inference URL: https://mev.otto.lk/virtuals/infer")
    print(f"   (or set up a public domain pointing to the memory API on port 8100)")
    print(f"")
    print(f"4. Enable x402 commerce:")
    print(f"   Add to ~/memory/.env:")
    print(f"   COMMERCE_ENABLED=true")

    return address


def check_status():
    """Check wallet status and balances."""
    address = os.environ.get("AGENT_WALLET_ADDRESS", "")
    if not address:
        print("[wallet] No wallet configured. Run: python setup_agent_wallet.py --create")
        return

    print(f"[wallet] Agent wallet: {address}")
    print(f"[wallet] Network: base-mainnet")
    print(f"[wallet] Explorer: https://basescan.org/address/{address}")

    # Try to check balance via public RPC
    import urllib.request
    import urllib.error

    # Check ETH balance via Base public RPC
    try:
        payload = json.dumps({
            "jsonrpc": "2.0",
            "method": "eth_getBalance",
            "params": [address, "latest"],
            "id": 1,
        }).encode()
        req = urllib.request.Request(
            "https://mainnet.base.org",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            balance_hex = data.get("result", "0x0")
            eth_balance = int(balance_hex, 16) / 1e18
            print(f"[wallet] ETH balance: {eth_balance:.6f} ETH")
    except Exception as e:
        print(f"[wallet] Could not fetch ETH balance: {e}")

    # Check USDC balance
    USDC_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    try:
        # ERC20 balanceOf call
        selector = "0x70a08231"  # balanceOf(address)
        padded = address.lower().replace("0x", "").zfill(64)
        data_hex = selector + padded
        payload = json.dumps({
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [{"to": USDC_CONTRACT, "data": data_hex}, "latest"],
            "id": 2,
        }).encode()
        req = urllib.request.Request(
            "https://mainnet.base.org",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            result = data.get("result", "0x0")
            usdc_balance = int(result, 16) / 1e6  # USDC is 6 decimals
            print(f"[wallet] USDC balance: ${usdc_balance:.2f}")
    except Exception as e:
        print(f"[wallet] Could not fetch USDC balance: {e}")

    # Check VIRTUAL balance
    VIRTUAL_CONTRACT = "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b"
    try:
        padded = address.lower().replace("0x", "").zfill(64)
        data_hex = "0x70a08231" + padded
        payload = json.dumps({
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [{"to": VIRTUAL_CONTRACT, "data": data_hex}, "latest"],
            "id": 3,
        }).encode()
        req = urllib.request.Request(
            "https://mainnet.base.org",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            result = data.get("result", "0x0")
            virtual_balance = int(result, 16) / 1e18  # VIRTUAL is 18 decimals
            print(f"[wallet] VIRTUAL balance: {virtual_balance:.2f} VIRTUAL")
            if virtual_balance < 100:
                remaining = 100 - virtual_balance
                print(f"[wallet] Need {remaining:.0f} more VIRTUAL to launch on Virtuals Protocol")
    except Exception as e:
        print(f"[wallet] Could not fetch VIRTUAL balance: {e}")


def main():
    parser = argparse.ArgumentParser(description="Otto Agent Wallet Manager")
    parser.add_argument("--create", action="store_true", help="Create new CDP wallet")
    parser.add_argument("--status", action="store_true", help="Check wallet status and balances")
    args = parser.parse_args()

    if args.create:
        create_wallet()
    elif args.status:
        check_status()
    else:
        parser.print_help()
        print()
        print("Quick start:")
        print("  1. python setup_agent_wallet.py --create")
        print("  2. Fund wallet with ETH + VIRTUAL tokens")
        print("  3. python setup_agent_wallet.py --status")


if __name__ == "__main__":
    main()
