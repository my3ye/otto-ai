#!/usr/bin/env python3
"""
solana_launcher.py — Solana meme token launcher for Project Alpha

Supports two modes:
  1. pump.fun launch (recommended — zero creator cost, auto-graduation)
  2. SPL-only creation (for Raydium CPMM or custom pools — NOT IMPLEMENTED YET)

SAFETY DEFAULTS:
  --dry-run is ON by default. Pass --execute to send real transactions.
  All real-money actions require explicit Mev approval.

Usage:
  # Dry run with Bobby config (default)
  python3 tools/solana_launcher.py --config projects/alpha/launch_configs/bobby.json

  # Estimate costs only
  python3 tools/solana_launcher.py --config projects/alpha/launch_configs/bobby.json --estimate

  # Upload metadata to IPFS (Pinata) — no blockchain tx
  python3 tools/solana_launcher.py --config projects/alpha/launch_configs/bobby.json --upload-metadata

  # REAL LAUNCH (requires explicit flag + env vars set)
  python3 tools/solana_launcher.py --config projects/alpha/launch_configs/bobby.json --execute

Author: Otto (Project Alpha)
Date: 2026-02-21
"""

import argparse
import json
import os
import sys
import time
import hashlib
from pathlib import Path
from typing import Optional

import httpx

# Load .env from alpha project if present
_alpha_env = Path(__file__).parent.parent / "projects" / "alpha" / "bot" / ".env"
if _alpha_env.exists():
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv(_alpha_env)

# ─── Config ──────────────────────────────────────────────────────────────────

HELIUS_API_KEY = os.environ.get("HELIUS_API_KEY", "")
HELIUS_RPC_URL = (
    f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
    if HELIUS_API_KEY
    else "https://api.mainnet-beta.solana.com"
)

PINATA_JWT = os.environ.get("PINATA_JWT", "")
PINATA_API_URL = "https://api.pinata.cloud"

PUMPPORTAL_BASE = "https://pumpportal.fun/api"
JUPITER_QUOTE_URL = "https://quote-api.jup.ag/v6/quote"
RUGCHECK_URL = "https://api.rugcheck.xyz/v1/tokens"

# SOL price estimate for cost display (updated manually or from API)
SOL_USD_ESTIMATE = 170.0

# ─── Cost estimates (SOL) ────────────────────────────────────────────────────

COSTS = {
    "spl_mint_account":         0.00144,   # 82 bytes rent-exempt
    "spl_metadata_account":     0.015,     # Metaplex PDA ~679 bytes
    "pumpfun_creation_fee":     0.02,      # First buyer cost (creator free)
    "jito_bundle_tip":          0.005,     # Anti-bot bundle tip
    "raydium_cpmm_pool":        0.20,      # Pool creation (CPMM, no OpenBook needed)
    "tx_fees_estimate":         0.001,     # 3-5 transactions
}

# ─── Helpers ─────────────────────────────────────────────────────────────────

def sol_to_usd(sol: float) -> str:
    return f"${sol * SOL_USD_ESTIMATE:.2f}"

def print_section(title: str):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print('─' * 60)

def confirm(prompt: str) -> bool:
    resp = input(f"{prompt} [yes/no]: ").strip().lower()
    return resp in ("yes", "y")

# ─── Config loader ────────────────────────────────────────────────────────────

def load_config(path: str) -> dict:
    """Load and validate a launch config JSON."""
    with open(path) as f:
        cfg = json.load(f)

    required = ["name", "symbol", "description", "launch_platform"]
    for field in required:
        if field not in cfg:
            raise ValueError(f"Missing required config field: {field}")

    # Apply defaults
    cfg.setdefault("decimals", 6)
    cfg.setdefault("supply_units", 1_000_000_000)  # 1B tokens
    cfg.setdefault("initial_buy_sol", 0.0)          # Creator buy-in
    cfg.setdefault("use_jito_bundle", False)
    cfg.setdefault("revoke_mint_authority", True)
    cfg.setdefault("revoke_freeze_authority", True)

    return cfg

# ─── Cost Estimator ───────────────────────────────────────────────────────────

def estimate_costs(cfg: dict) -> dict:
    """Estimate launch costs based on config."""
    platform = cfg.get("launch_platform", "pumpfun")
    initial_buy = cfg.get("initial_buy_sol", 0.0)
    use_jito = cfg.get("use_jito_bundle", False)

    costs = {}

    if platform == "pumpfun":
        # pump.fun: creator pays 0 SOL, but first buyer pays ~0.02 SOL
        # If creator IS the first buyer, that's their initial_buy
        costs["pump_fun_creation"] = 0.0  # creator free
        costs["first_buyer_fee"] = COSTS["pumpfun_creation_fee"]  # ~0.02 SOL (if anyone buys)
        costs["creator_initial_buy"] = initial_buy  # optional
        if use_jito:
            costs["jito_bundle_tip"] = COSTS["jito_bundle_tip"]
    elif platform == "raydium_cpmm":
        costs["spl_mint"] = COSTS["spl_mint_account"]
        costs["metadata"] = COSTS["spl_metadata_account"]
        costs["cpmm_pool"] = COSTS["raydium_cpmm_pool"]
        costs["initial_liquidity"] = initial_buy  # doubles as LP seed
        if use_jito:
            costs["jito_bundle_tip"] = COSTS["jito_bundle_tip"]
    else:
        costs["unknown_platform"] = 0.0

    costs["tx_fees"] = COSTS["tx_fees_estimate"]
    costs["total"] = sum(costs.values())

    return costs

def print_cost_estimate(cfg: dict):
    print_section("COST ESTIMATE")
    costs = estimate_costs(cfg)
    print(f"  Platform:       {cfg.get('launch_platform', 'pumpfun')}")
    print(f"  Token:          {cfg['name']} (${cfg['symbol']})")
    print()
    for k, v in costs.items():
        if k == "total":
            continue
        print(f"  {k:<30} {v:.5f} SOL  ({sol_to_usd(v)})")
    print()
    total_sol = costs["total"]
    print(f"  {'TOTAL':<30} {total_sol:.5f} SOL  ({sol_to_usd(total_sol)})")
    print()
    print(f"  Note: KOL spend not included (external, USD-only, manual)")
    print(f"  Note: SOL price estimate: ${SOL_USD_ESTIMATE:.0f}/SOL (update as needed)")

# ─── Metadata Builder ─────────────────────────────────────────────────────────

def build_metadata(cfg: dict) -> dict:
    """Construct Metaplex-compatible metadata JSON from config."""
    meta = {
        "name": cfg["name"],
        "symbol": cfg["symbol"],
        "description": cfg["description"],
        "image": cfg.get("image_uri", ""),
        "external_url": cfg.get("website", ""),
    }

    extensions = {}
    for field in ["twitter", "telegram", "discord", "website"]:
        if cfg.get(field):
            extensions[field] = cfg[field]
    if extensions:
        meta["extensions"] = extensions

    if cfg.get("attributes"):
        meta["attributes"] = cfg["attributes"]

    return meta

def print_metadata(cfg: dict):
    print_section("TOKEN METADATA")
    meta = build_metadata(cfg)
    print(json.dumps(meta, indent=2))

# ─── IPFS Upload (Pinata) ─────────────────────────────────────────────────────

def upload_metadata_to_pinata(cfg: dict, dry_run: bool = True) -> Optional[str]:
    """Upload metadata JSON to Pinata IPFS. Returns IPFS URI or None."""
    meta = build_metadata(cfg)
    name = f"{cfg['symbol'].lower()}_metadata.json"

    if dry_run:
        print_section("METADATA UPLOAD (DRY RUN)")
        print(f"  Would upload to Pinata IPFS: {name}")
        print(f"  Payload: {json.dumps(meta, indent=4)}")
        print()
        print(f"  Required: PINATA_JWT env var")
        print(f"  PINATA_JWT set: {'YES' if PINATA_JWT else 'NO'}")
        print(f"  Cost: Free (Pinata free tier = 1GB storage)")
        return None

    if not PINATA_JWT:
        print("ERROR: PINATA_JWT not set. Cannot upload metadata.")
        sys.exit(1)

    print_section("UPLOADING METADATA TO PINATA")
    print(f"  Uploading {name}...")

    headers = {
        "Authorization": f"Bearer {PINATA_JWT}",
        "Content-Type": "application/json",
    }
    payload = {
        "pinataContent": meta,
        "pinataMetadata": {"name": name},
    }

    try:
        resp = httpx.post(
            f"{PINATA_API_URL}/pinning/pinJSONToIPFS",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        ipfs_hash = result["IpfsHash"]
        uri = f"https://ipfs.io/ipfs/{ipfs_hash}"
        print(f"  SUCCESS: {uri}")
        print(f"  IPFS Hash: {ipfs_hash}")
        return uri
    except Exception as e:
        print(f"  ERROR uploading to Pinata: {e}")
        sys.exit(1)

# ─── Helius Asset Check ───────────────────────────────────────────────────────

def check_token_safety(mint_address: str) -> dict:
    """Run safety checks on a deployed token via Helius getAsset + RugCheck."""
    results = {"mint": mint_address, "checks": {}, "passed": True}

    # Helius getAsset
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getAsset",
            "params": {"id": mint_address},
        }
        resp = httpx.post(HELIUS_RPC_URL, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("result", {})

        supply = data.get("token_info", {})
        authorities = data.get("authorities", [])
        mint_auth = next((a for a in authorities if a.get("scopes") == ["mint"]), None)
        freeze_auth = next((a for a in authorities if a.get("scopes") == ["freeze"]), None)

        results["checks"]["mint_authority_revoked"] = mint_auth is None
        results["checks"]["freeze_authority_revoked"] = freeze_auth is None
        results["checks"]["supply"] = supply.get("supply", "unknown")

        if mint_auth:
            results["passed"] = False
            results["checks"]["mint_authority_warning"] = f"Active: {mint_auth.get('address')}"
        if freeze_auth:
            results["passed"] = False
            results["checks"]["freeze_authority_warning"] = f"Active: {freeze_auth.get('address')}"

    except Exception as e:
        results["checks"]["helius_error"] = str(e)

    # RugCheck.xyz
    try:
        resp = httpx.get(
            f"{RUGCHECK_URL}/{mint_address}/report/summary",
            timeout=15,
        )
        if resp.status_code == 200:
            rug = resp.json()
            score = rug.get("score", -1)
            risks = rug.get("risks", [])
            results["checks"]["rugcheck_score"] = score
            results["checks"]["rugcheck_risks"] = [r.get("name") for r in risks]
            if score > 5000:  # RugCheck scores higher = riskier
                results["passed"] = False
                results["checks"]["rugcheck_warning"] = f"HIGH RISK score: {score}"
        else:
            results["checks"]["rugcheck_status"] = resp.status_code
    except Exception as e:
        results["checks"]["rugcheck_error"] = str(e)

    return results

# ─── pump.fun Launch ──────────────────────────────────────────────────────────

def launch_pumpfun(cfg: dict, metadata_uri: str, dry_run: bool = True) -> Optional[str]:
    """
    Launch token on pump.fun via PumpPortal API.

    PumpPortal provides two options:
    A) Local wallet: POST /trade-local — returns unsigned tx for self-signing
    B) IPFS + create: POST /create — accepts form data with image + metadata

    We use option A (local wallet) for programmatic control.
    The wallet private key must be set as SOLANA_PRIVATE_KEY env var (base58 or array).

    Returns: transaction signature or None (dry run)
    """
    private_key = os.environ.get("SOLANA_PRIVATE_KEY", "")
    initial_buy = cfg.get("initial_buy_sol", 0.0)

    if dry_run:
        print_section("PUMP.FUN LAUNCH (DRY RUN)")
        print(f"  Token:          {cfg['name']} (${cfg['symbol']})")
        print(f"  Metadata URI:   {metadata_uri}")
        print(f"  Initial buy:    {initial_buy} SOL ({sol_to_usd(initial_buy)})")
        print(f"  Jito bundle:    {'YES' if cfg.get('use_jito_bundle') else 'NO'}")
        print()
        print(f"  Required env vars:")
        print(f"    SOLANA_PRIVATE_KEY: {'SET' if private_key else 'NOT SET ⚠️'}")
        print(f"    HELIUS_API_KEY:     {'SET' if HELIUS_API_KEY else 'NOT SET ⚠️'}")
        print()
        print(f"  Dry run complete. No transactions sent.")
        print(f"  Pass --execute to send real transactions.")
        return None

    if not private_key:
        print("ERROR: SOLANA_PRIVATE_KEY not set. Cannot launch.")
        sys.exit(1)

    print_section("PUMP.FUN LAUNCH — LIVE")
    print(f"  WARNING: This will create a real token on Solana mainnet.")
    print(f"  Token: {cfg['name']} (${cfg['symbol']})")
    print(f"  Initial buy: {initial_buy} SOL")

    if not confirm("CONFIRM: Proceed with live pump.fun launch?"):
        print("  Aborted by user.")
        return None

    # PumpPortal create API
    # Ref: https://pumpportal.fun/api-docs (create + trade endpoints)
    # Step 1: Generate token mint keypair via PumpPortal
    try:
        resp = httpx.get(f"{PUMPPORTAL_BASE}/random-keypair", timeout=15)
        resp.raise_for_status()
        mint_keypair = resp.json()
        mint_pubkey = mint_keypair.get("publicKey")
        mint_privkey = mint_keypair.get("privateKey")
        print(f"  Mint address: {mint_pubkey}")
    except Exception as e:
        print(f"  ERROR generating mint keypair: {e}")
        sys.exit(1)

    # Step 2: Build create+buy payload
    payload = {
        "publicKey": _get_public_key(private_key),
        "action": "create",
        "tokenMetadata": {
            "name": cfg["name"],
            "symbol": cfg["symbol"],
            "uri": metadata_uri,
        },
        "mint": mint_privkey,
        "denominatedInSol": "true",
        "amount": initial_buy,
        "slippage": cfg.get("slippage_bps", 1000) // 100,  # convert bps to %
        "priorityFee": cfg.get("priority_fee_sol", 0.0005),
        "pool": "pump",
    }

    if cfg.get("use_jito_bundle"):
        payload["jito"] = "true"
        payload["jitoTipLamports"] = int(COSTS["jito_bundle_tip"] * 1e9)

    # Step 3: Get unsigned transaction
    try:
        resp = httpx.post(
            f"{PUMPPORTAL_BASE}/trade-local",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        tx_data = resp.json()
    except Exception as e:
        print(f"  ERROR getting transaction from PumpPortal: {e}")
        sys.exit(1)

    # Step 4: Sign and send
    try:
        from solders.keypair import Keypair
        from solders.transaction import VersionedTransaction
        from solana.rpc.api import Client
        import base58

        # Decode private key
        if isinstance(private_key, str) and private_key.startswith("["):
            key_bytes = bytes(json.loads(private_key))
        else:
            key_bytes = base58.b58decode(private_key)

        keypair = Keypair.from_bytes(key_bytes)
        client = Client(HELIUS_RPC_URL)

        # PumpPortal returns base64-encoded tx
        tx_bytes = bytes.fromhex(tx_data.get("transaction", ""))
        tx = VersionedTransaction.from_bytes(tx_bytes)

        # Sign
        signed_tx = tx.sign([keypair])

        # Submit
        result = client.send_raw_transaction(
            bytes(signed_tx),
            opts={"skipPreflight": True, "maxRetries": 5},
        )
        sig = result.value
        print(f"\n  SUCCESS!")
        print(f"  Tx signature: {sig}")
        print(f"  Mint address: {mint_pubkey}")
        print(f"  View on pump.fun: https://pump.fun/{mint_pubkey}")
        print(f"  View on Solscan: https://solscan.io/tx/{sig}")
        return str(sig)

    except ImportError as e:
        print(f"  ERROR: Missing library — {e}")
        print(f"  Install: pip install solders solana base58")
        sys.exit(1)
    except Exception as e:
        print(f"  ERROR signing/sending transaction: {e}")
        sys.exit(1)

def _get_public_key(private_key_b58: str) -> str:
    """Derive public key from base58 private key."""
    try:
        from solders.keypair import Keypair
        import base58
        key_bytes = base58.b58decode(private_key_b58)
        kp = Keypair.from_bytes(key_bytes)
        return str(kp.pubkey())
    except Exception:
        return "UNKNOWN_PUBKEY"

# ─── Post-launch Monitor ──────────────────────────────────────────────────────

def monitor_bonding_curve(mint_address: str, poll_interval: int = 60):
    """Poll pump.fun for bonding curve progress (non-blocking, prints status)."""
    print_section(f"BONDING CURVE MONITOR: {mint_address}")
    print(f"  Polling every {poll_interval}s. Ctrl+C to stop.")
    print()

    while True:
        try:
            resp = httpx.get(
                f"https://frontend-api.pump.fun/coins/{mint_address}",
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                market_cap = data.get("usd_market_cap", 0)
                virtual_sol = data.get("virtual_sol_reserves", 0) / 1e9
                bonding_pct = min(100, (virtual_sol / 85) * 100)
                graduated = data.get("complete", False)

                print(f"  [{time.strftime('%H:%M:%S')}] "
                      f"MC: ${market_cap:,.0f} | "
                      f"Curve: {bonding_pct:.1f}% | "
                      f"{'🎓 GRADUATED' if graduated else 'bonding'}")

                if graduated:
                    print(f"\n  Token graduated to PumpSwap!")
                    print(f"  View: https://pump.fun/{mint_address}")
                    break
            else:
                print(f"  [{time.strftime('%H:%M:%S')}] API status {resp.status_code}")
        except Exception as e:
            print(f"  [{time.strftime('%H:%M:%S')}] Error: {e}")

        time.sleep(poll_interval)

# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Solana meme token launcher — Project Alpha / Otto"
    )
    parser.add_argument(
        "--config", required=True,
        help="Path to launch config JSON (e.g. projects/alpha/launch_configs/bobby.json)"
    )
    parser.add_argument(
        "--estimate", action="store_true",
        help="Show cost estimate only, then exit"
    )
    parser.add_argument(
        "--upload-metadata", action="store_true",
        help="Upload metadata to Pinata IPFS only (no blockchain tx)"
    )
    parser.add_argument(
        "--check-safety", metavar="MINT_ADDRESS",
        help="Run safety checks on an existing mint address"
    )
    parser.add_argument(
        "--monitor", metavar="MINT_ADDRESS",
        help="Monitor bonding curve progress for a launched token"
    )
    parser.add_argument(
        "--execute", action="store_true",
        help="SEND REAL TRANSACTIONS. Without this flag, everything is a dry run."
    )
    parser.add_argument(
        "--metadata-uri", default="",
        help="Pre-uploaded metadata URI (skip Pinata upload)"
    )

    args = parser.parse_args()

    dry_run = not args.execute

    if dry_run:
        print("\n" + "=" * 60)
        print("  DRY RUN MODE (default)")
        print("  No real transactions will be sent.")
        print("  Pass --execute to go live.")
        print("=" * 60)

    # Safety check mode
    if args.check_safety:
        results = check_token_safety(args.check_safety)
        print_section(f"SAFETY CHECK: {args.check_safety}")
        print(json.dumps(results, indent=2))
        sys.exit(0 if results["passed"] else 1)

    # Monitor mode
    if args.monitor:
        monitor_bonding_curve(args.monitor)
        sys.exit(0)

    # Load config
    try:
        cfg = load_config(args.config)
    except FileNotFoundError:
        print(f"ERROR: Config not found: {args.config}")
        sys.exit(1)
    except ValueError as e:
        print(f"ERROR: Invalid config: {e}")
        sys.exit(1)

    print_section(f"LAUNCH CONFIG: {cfg['name']} (${cfg['symbol']})")
    print(f"  Platform:     {cfg.get('launch_platform', 'pumpfun')}")
    print(f"  Description:  {cfg.get('description', '')[:80]}")
    print(f"  Supply:       {cfg.get('supply_units', 1_000_000_000):,} tokens")
    print(f"  Decimals:     {cfg.get('decimals', 6)}")
    print(f"  Initial buy:  {cfg.get('initial_buy_sol', 0.0)} SOL")
    print(f"  Jito bundle:  {cfg.get('use_jito_bundle', False)}")

    # Estimate only
    if args.estimate:
        print_cost_estimate(cfg)
        sys.exit(0)

    # Show metadata
    print_metadata(cfg)

    # Cost estimate always shown
    print_cost_estimate(cfg)

    # Metadata upload
    if args.metadata_uri:
        metadata_uri = args.metadata_uri
        print(f"\n  Using pre-uploaded metadata URI: {metadata_uri}")
    elif args.upload_metadata or not dry_run:
        metadata_uri = upload_metadata_to_pinata(cfg, dry_run=dry_run)
        if dry_run:
            metadata_uri = "https://ipfs.io/ipfs/DRY_RUN_HASH/metadata.json"
    else:
        print_section("METADATA UPLOAD")
        print("  Skipped (dry run). Pass --upload-metadata to test upload.")
        metadata_uri = "https://ipfs.io/ipfs/DRY_RUN_HASH/metadata.json"

    # Launch
    platform = cfg.get("launch_platform", "pumpfun")
    if platform == "pumpfun":
        sig = launch_pumpfun(cfg, metadata_uri, dry_run=dry_run)
    else:
        print(f"  Platform '{platform}' not implemented yet.")
        print(f"  Supported: pumpfun")
        sys.exit(1)

    if sig:
        print_section("LAUNCH COMPLETE")
        print(f"  Signature: {sig}")
        print(f"  Next steps:")
        print(f"    1. Monitor: python3 tools/solana_launcher.py --monitor <MINT>")
        print(f"    2. Post CA on Twitter/Telegram")
        print(f"    3. Tag KOLs, activate community")

    print()

if __name__ == "__main__":
    main()
