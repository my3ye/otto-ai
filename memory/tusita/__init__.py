"""Tusita community locations and bookings integration module.

Feature-flagged via settings.tusita_enabled.
Phase 0: Location registry + booking management. No availability engine.
"""

from .locations import (
    create_location,
    get_location,
    get_location_by_slug,
    list_locations,
    update_location_status,
    record_revenue,
    get_location_stats,
)

from .bookings import (
    create_booking,
    get_booking,
    list_bookings,
    update_booking_status,
)

__all__ = [
    # Locations
    "create_location",
    "get_location",
    "get_location_by_slug",
    "list_locations",
    "update_location_status",
    "record_revenue",
    "get_location_stats",
    # Bookings
    "create_booking",
    "get_booking",
    "list_bookings",
    "update_booking_status",
]
