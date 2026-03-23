-- Migration 070: Tusita Community Locations and Bookings
-- Phase 0: Location registry + booking records. No availability engine yet.

-- 1. Tusita dome/community locations
CREATE TABLE IF NOT EXISTS tusita_locations (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name             TEXT NOT NULL,
    slug             TEXT NOT NULL UNIQUE,
    description      TEXT,
    country          TEXT,
    region           TEXT,
    coordinates      JSONB DEFAULT '{}',           -- {lat, lng}
    dome_type        TEXT DEFAULT 'community',     -- community | meditation | worship | visitor_center
    capacity         INTEGER NOT NULL DEFAULT 0,   -- total bed/guest capacity
    revenue_ytd      NUMERIC NOT NULL DEFAULT 0,   -- year-to-date revenue (USD)
    status           TEXT NOT NULL DEFAULT 'planned',  -- planned | construction | operational | closed
    metadata         JSONB DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    opened_at        TIMESTAMPTZ,
    CONSTRAINT tusita_locations_status_check
        CHECK (status IN ('planned', 'construction', 'operational', 'closed')),
    CONSTRAINT tusita_locations_dome_type_check
        CHECK (dome_type IN ('community', 'meditation', 'worship', 'visitor_center', 'accommodation'))
);

CREATE INDEX IF NOT EXISTS idx_tusita_locations_slug    ON tusita_locations(slug);
CREATE INDEX IF NOT EXISTS idx_tusita_locations_status  ON tusita_locations(status);
CREATE INDEX IF NOT EXISTS idx_tusita_locations_country ON tusita_locations(country) WHERE country IS NOT NULL;

-- 2. Tusita guest bookings
CREATE TABLE IF NOT EXISTS tusita_bookings (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    location_id      UUID NOT NULL REFERENCES tusita_locations(id) ON DELETE RESTRICT,
    guest_name       TEXT NOT NULL,
    guest_email      TEXT,
    guest_handle     TEXT,                         -- ONEON handle if applicable
    check_in         DATE NOT NULL,
    check_out        DATE NOT NULL,
    party_size       INTEGER NOT NULL DEFAULT 1,
    booking_type     TEXT NOT NULL DEFAULT 'visitor',  -- visitor | resident | retreat | volunteer
    status           TEXT NOT NULL DEFAULT 'pending',  -- pending | confirmed | cancelled | completed
    total_amount     NUMERIC,                      -- NULL for voluntary contributions
    currency         TEXT DEFAULT 'USD',
    notes            TEXT,
    metadata         JSONB DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT tusita_bookings_dates_check CHECK (check_out > check_in),
    CONSTRAINT tusita_bookings_status_check
        CHECK (status IN ('pending', 'confirmed', 'cancelled', 'completed')),
    CONSTRAINT tusita_bookings_type_check
        CHECK (booking_type IN ('visitor', 'resident', 'retreat', 'volunteer'))
);

CREATE INDEX IF NOT EXISTS idx_tusita_bookings_location  ON tusita_bookings(location_id);
CREATE INDEX IF NOT EXISTS idx_tusita_bookings_status    ON tusita_bookings(status);
CREATE INDEX IF NOT EXISTS idx_tusita_bookings_check_in  ON tusita_bookings(check_in);
CREATE INDEX IF NOT EXISTS idx_tusita_bookings_handle    ON tusita_bookings(guest_handle) WHERE guest_handle IS NOT NULL;
