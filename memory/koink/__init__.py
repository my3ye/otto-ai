"""Koink integration module — $KOINK Standard implementation.

Feature-flagged via settings.koink_enabled. Import guard ensures this
module is inert unless the flag is enabled.

Exports:
    KOINK_STANDARD_SPEC — machine-readable spec dict
    validate_koink_params, calculate_dhm_multiplier — standard utilities
    create_koink_token, get_koink_token, list_koink_tokens — launch CRUD
    upsert_dhm_position, get_dhm_positions, snapshot_dhm_positions — DHM
    record_treasury_event, get_treasury_events, get_treasury_balance — treasury
"""

from .standard import (
    KOINK_DEFAULTS,
    KOINK_STANDARD_SPEC,
    SUPPORTED_CHAINS,
    CHAIN_VRF_MAP,
    validate_koink_params,
    calculate_dhm_multiplier,
    calculate_sell_tax_for_holder,
    get_vrf_type_for_chain,
)

from .launch import (
    create_koink_token,
    get_koink_token,
    list_koink_tokens,
    update_koink_status,
)

from .dhm import (
    upsert_dhm_position,
    get_dhm_positions,
    snapshot_dhm_positions,
    get_holder_stats,
)

from .treasury import (
    record_treasury_event,
    get_treasury_events,
    get_treasury_balance,
)

__all__ = [
    # Standard
    "KOINK_DEFAULTS",
    "KOINK_STANDARD_SPEC",
    "SUPPORTED_CHAINS",
    "CHAIN_VRF_MAP",
    "validate_koink_params",
    "calculate_dhm_multiplier",
    "calculate_sell_tax_for_holder",
    "get_vrf_type_for_chain",
    # Launch
    "create_koink_token",
    "get_koink_token",
    "list_koink_tokens",
    "update_koink_status",
    # DHM
    "upsert_dhm_position",
    "get_dhm_positions",
    "snapshot_dhm_positions",
    "get_holder_stats",
    # Treasury
    "record_treasury_event",
    "get_treasury_events",
    "get_treasury_balance",
]
