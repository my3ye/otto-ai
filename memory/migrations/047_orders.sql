-- WebAssist Orders table — manual payment flow
CREATE TABLE IF NOT EXISTS webassist_orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_name     TEXT NOT NULL,
    client_email    TEXT NOT NULL,
    business_name   TEXT NOT NULL,
    requirements    TEXT,
    amount_usd      NUMERIC(10, 2) NOT NULL DEFAULT 499.00,
    currency        TEXT NOT NULL DEFAULT 'USD',
    payment_method  TEXT CHECK (payment_method IN ('bank', 'wise', 'crypto', 'pending')) DEFAULT 'pending',
    payment_status  TEXT NOT NULL CHECK (payment_status IN ('pending', 'confirmed', 'cancelled')) DEFAULT 'pending',
    admin_notes     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    confirmed_at    TIMESTAMPTZ,
    confirmed_by    TEXT
);

CREATE INDEX IF NOT EXISTS idx_webassist_orders_status ON webassist_orders(payment_status);
CREATE INDEX IF NOT EXISTS idx_webassist_orders_created ON webassist_orders(created_at DESC);
