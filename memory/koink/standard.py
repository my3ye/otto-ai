"""$KOINK Standard — constants, validation, and DHM calculations.

Single source of truth for the $KOINK Standard spec (chain-agnostic
tokenomics: anti-whale cap, graduated sell tax, Diamond Hands Multiplier,
VRF fair launch, treasury allocation).
"""

import math
from typing import Optional

# ─── Constants ────────────────────────────────────────────────────────────────

KOINK_DEFAULTS = {
    "anti_whale_cap_pct": 2.0,       # max % of supply per wallet at launch
    "sell_tax_initial_bps": 500,     # initial sell tax (500 = 5%)
    "sell_tax_floor_bps": 100,       # floor sell tax for diamond hands (100 = 1%)
    "treasury_pct": 20.0,            # % of each tx routed to treasury
    "dhm_max_multiplier": 3.0,       # max governance weight multiplier
    "dhm_months": 12,                # months to reach max multiplier
    "vrf_type": "chainlink",         # default VRF provider
    "creator_fee_pct": 2.0,          # creator fee % of raise
    "liquidity_pct": 60.0,           # % of raise allocated to initial LP
    "total_supply": 1_000_000_000,   # 1B default supply
}

SUPPORTED_CHAINS = ["base", "eth", "arbitrum", "optimism", "solana"]

# Maps each chain to its native VRF provider
CHAIN_VRF_MAP = {
    "base": "chainlink",
    "eth": "chainlink",
    "arbitrum": "chainlink",
    "optimism": "chainlink",
    "solana": "switchboard",
}

# Validation bounds
PARAM_BOUNDS = {
    "anti_whale_cap_pct": (0.1, 10.0),       # 0.1% – 10%
    "sell_tax_initial_bps": (0, 2000),        # 0 – 20%
    "sell_tax_floor_bps": (0, 1000),          # 0 – 10%
    "treasury_pct": (0.0, 50.0),             # 0% – 50%
    "dhm_max_multiplier": (1.0, 10.0),        # 1x – 10x
    "dhm_months": (1, 60),                    # 1 – 60 months
    "creator_fee_pct": (0.0, 10.0),           # 0% – 10%
    "liquidity_pct": (10.0, 95.0),            # 10% – 95%
    "total_supply": (1_000, 1_000_000_000_000),  # 1K – 1T
}

# Machine-readable $KOINK Standard spec
KOINK_STANDARD_SPEC = {
    "version": "0.1.0",
    "name": "$KOINK Standard",
    "description": "Chain-agnostic meme tokenomics specification with fair launch mechanics",
    "chains": SUPPORTED_CHAINS,
    "defaults": KOINK_DEFAULTS,
    "mechanics": {
        "anti_whale": {
            "description": "Max % of total supply any single wallet can hold at launch",
            "default_pct": KOINK_DEFAULTS["anti_whale_cap_pct"],
        },
        "sell_tax": {
            "description": "Graduated sell tax that decreases as holders diamond-hand",
            "initial_bps": KOINK_DEFAULTS["sell_tax_initial_bps"],
            "floor_bps": KOINK_DEFAULTS["sell_tax_floor_bps"],
        },
        "treasury": {
            "description": "Portion of each transaction routed to community treasury",
            "default_pct": KOINK_DEFAULTS["treasury_pct"],
            "governance": "Gnosis Safe multi-sig (Phase 1+)",
        },
        "dhm": {
            "description": "Diamond Hands Multiplier — governance weight accrued by holding",
            "max_multiplier": KOINK_DEFAULTS["dhm_max_multiplier"],
            "ramp_months": KOINK_DEFAULTS["dhm_months"],
        },
        "vrf_fair_launch": {
            "description": "Verifiable random seed for launch sequencing (no insider front-run)",
            "evm_provider": "Chainlink VRF v2.5",
            "solana_provider": "Switchboard VRF",
        },
    },
    "phase": "0",
    "phase_note": "Phase 0: DB/API only. Phase 1: EVM contracts. Phase 2: Solana.",
}


# ─── Validation ───────────────────────────────────────────────────────────────

def validate_koink_params(params: dict) -> tuple[bool, list[str]]:
    """Validate KOINK Standard parameters against bounds.

    Args:
        params: Dict of parameter names → values

    Returns:
        (is_valid, errors) — errors is empty list if valid
    """
    errors: list[str] = []

    # Chain validation
    chain = params.get("chain")
    if chain and chain not in SUPPORTED_CHAINS:
        errors.append(f"Unsupported chain '{chain}'. Supported: {', '.join(SUPPORTED_CHAINS)}")

    # VRF type validation
    vrf_type = params.get("vrf_type")
    if vrf_type and vrf_type not in ("chainlink", "switchboard", "none"):
        errors.append(f"Invalid vrf_type '{vrf_type}'. Must be: chainlink | switchboard | none")

    # Solana chain must use switchboard VRF
    if chain == "solana" and vrf_type and vrf_type not in ("switchboard", "none"):
        errors.append("Solana chain requires vrf_type='switchboard' (Chainlink VRF not supported on Solana)")

    # Numeric bounds
    for field, (lo, hi) in PARAM_BOUNDS.items():
        val = params.get(field)
        if val is not None:
            if not (lo <= val <= hi):
                errors.append(f"{field} must be between {lo} and {hi}, got {val}")

    # sell_tax_floor must not exceed sell_tax_initial
    initial = params.get("sell_tax_initial_bps")
    floor = params.get("sell_tax_floor_bps")
    if initial is not None and floor is not None and floor > initial:
        errors.append(f"sell_tax_floor_bps ({floor}) cannot exceed sell_tax_initial_bps ({initial})")

    # Required fields for a full launch record (strip to catch whitespace-only strings)
    required = ["name", "symbol", "chain"]
    for field in required:
        val = params.get(field)
        if not val or (isinstance(val, str) and not val.strip()):
            errors.append(f"Required field missing or blank: {field}")

    return (len(errors) == 0, errors)


# ─── DHM Calculation ──────────────────────────────────────────────────────────

def calculate_dhm_multiplier(
    hold_days: int,
    dhm_months: int = 12,
    max_multiplier: float = 3.0,
) -> float:
    """Calculate governance weight multiplier based on hold duration.

    Linear ramp from 1.0x at day 0 to max_multiplier at dhm_months.
    Caps at max_multiplier after the ramp period.

    Args:
        hold_days: Number of days the holder has held continuously
        dhm_months: Months to reach max_multiplier (default 12)
        max_multiplier: Maximum governance weight (default 3.0x)

    Returns:
        float: Multiplier in range [1.0, max_multiplier]
    """
    if hold_days <= 0:
        return 1.0

    dhm_days = dhm_months * 30.44  # avg days per month
    progress = min(hold_days / dhm_days, 1.0)

    # Linear ramp: 1.0 + progress * (max - 1.0)
    multiplier = 1.0 + progress * (max_multiplier - 1.0)
    return round(multiplier, 4)


def calculate_sell_tax_for_holder(
    hold_days: int,
    sell_tax_initial_bps: int = 500,
    sell_tax_floor_bps: int = 100,
    dhm_months: int = 12,
) -> int:
    """Calculate current sell tax in bps for a holder based on hold duration.

    Tax decreases linearly from initial to floor over dhm_months.

    Args:
        hold_days: Number of days held
        sell_tax_initial_bps: Starting sell tax (e.g. 500 = 5%)
        sell_tax_floor_bps: Minimum sell tax (e.g. 100 = 1%)
        dhm_months: Months to reach floor tax

    Returns:
        int: Current sell tax in basis points
    """
    if hold_days <= 0:
        return sell_tax_initial_bps

    dhm_days = dhm_months * 30.44
    progress = min(hold_days / dhm_days, 1.0)

    tax_range = sell_tax_initial_bps - sell_tax_floor_bps
    current_tax = sell_tax_initial_bps - round(progress * tax_range)
    return max(current_tax, sell_tax_floor_bps)


def get_vrf_type_for_chain(chain: str) -> str:
    """Return the recommended VRF provider for a given chain."""
    return CHAIN_VRF_MAP.get(chain, "chainlink")
