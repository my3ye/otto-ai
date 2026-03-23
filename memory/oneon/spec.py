"""ONEON Identity Network specification constants.

Defines tier structure, DID format conventions, and feature availability by phase.
"""

ONEON_TIERS = {
    "waitlist": {
        "description": "Registered, pending activation",
        "did_available": False,
        "ows_vault": False,
        "governance_weight": 0,
        "phase_available": 0,
    },
    "custodial": {
        "description": "Active identity with custodial OWS vault",
        "did_available": True,
        "ows_vault": True,
        "governance_weight": 1,
        "phase_available": 1,
    },
    "self_sovereign": {
        "description": "Self-sovereign identity with user-controlled OWS vault",
        "did_available": True,
        "ows_vault": True,
        "governance_weight": 2,
        "phase_available": 2,
    },
    "sovereign": {
        "description": "Full sovereignty — DID registry + ONEON subnet node",
        "did_available": True,
        "ows_vault": True,
        "governance_weight": 5,
        "phase_available": 2,
    },
}

# DID method prefix for ONEON identities
# Format: did:oneon:<handle>:<chain>:<address>
DID_METHOD = "oneon"
DID_VERSION = "1.0"

ONEON_SPEC = {
    "version": "1.0",
    "phase": "0",
    "phase_description": (
        "API foundation — identity registry, governance proposals, DID stubs. "
        "No OWS signing or on-chain DID resolution yet."
    ),
    "did_method": DID_METHOD,
    "did_format": "did:oneon:<handle>:<chain>:<address>",
    "identity_tiers": ONEON_TIERS,
    "governance": {
        "voting_model": "weight_by_tier",
        "quorum_default": 10,
        "proposal_types": ["general", "upgrade", "parameter", "emergency"],
    },
    "phase_1_blockers": [
        "OWS custodial vault registration for tier upgrade",
        "On-chain DID resolution (ONEON People Chain)",
    ],
    "phase_2_blockers": [
        "Self-sovereign key derivation",
        "Polkadot People Chain deployment",
    ],
    "ows_integration": {
        "planned_phase": 1,
        "estimated_cost_usd": 8000,
        "wallet_adapter": "OWSWalletAdapter",
        "current_adapter": "NullWalletAdapter (Phase 0 stub)",
    },
}
