"""SOS Systems integration module — education ladder + refuge network.

Feature-flagged via settings.sos_enabled.
Phase 0: Learner registry, contribution tracking, case management.
"""

from .learners import (
    register_learner,
    get_learner,
    get_learner_by_handle,
    list_learners,
    award_contribution,
    get_learner_stats,
    TIER_XP_THRESHOLDS,
    get_tier_for_xp,
)

from .cases import (
    create_case,
    get_case,
    list_cases,
    update_case_status,
    get_case_stats,
)

__all__ = [
    # Learners
    "register_learner",
    "get_learner",
    "get_learner_by_handle",
    "list_learners",
    "award_contribution",
    "get_learner_stats",
    "TIER_XP_THRESHOLDS",
    "get_tier_for_xp",
    # Cases
    "create_case",
    "get_case",
    "list_cases",
    "update_case_status",
    "get_case_stats",
]
