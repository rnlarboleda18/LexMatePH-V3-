-- Founding promo: first N new signups (after this migration) get Barrister tier without charge.
-- Existing users are marked ineligible; only rows inserted after migration default to eligible.

ALTER TABLE users ADD COLUMN IF NOT EXISTS founding_promo_eligible BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS founding_promo_slot INT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS founding_promo_granted_at TIMESTAMPTZ NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_source TEXT NULL;

-- Everyone already in the DB before this promo ships is excluded from the counter.
UPDATE users SET founding_promo_eligible = FALSE WHERE founding_promo_eligible = TRUE;

CREATE TABLE IF NOT EXISTS founding_promo_state (
    id INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    claimed_count INT NOT NULL DEFAULT 0,
    max_slots INT NOT NULL DEFAULT 20
);

INSERT INTO founding_promo_state (id, claimed_count, max_slots) VALUES (1, 0, 20)
ON CONFLICT (id) DO NOTHING;

-- Audit: every verified PayMongo webhook payload stored for compliance/debugging.
CREATE TABLE IF NOT EXISTS billing_webhook_events (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    event_type TEXT,
    clerk_id TEXT,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_billing_webhook_events_created ON billing_webhook_events (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_billing_webhook_events_clerk ON billing_webhook_events (clerk_id) WHERE clerk_id IS NOT NULL;

-- Batch expiry (timer) — optional but helps large user tables
CREATE INDEX IF NOT EXISTS idx_users_founding_promo_expiry
ON users (founding_promo_granted_at)
WHERE subscription_source = 'founding_promo';

-- Env: FOUNDING_PROMO_DURATION_DAYS (default 30), FOUNDING_PROMO_LIMIT (default 20)
