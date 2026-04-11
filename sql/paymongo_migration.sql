-- PayMongo Subscription Migration
-- Run once against your PostgreSQL database.
-- Safe to re-run (all statements use IF NOT EXISTS / IF EXISTS guards).
-- Apply via: python api/run_billing_migrations.py

-- ── User profile columns (needed for PayMongo customer creation) ─────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name  TEXT;

-- ── Subscription columns on users ────────────────────────────────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS paymongo_customer_id      TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS paymongo_subscription_id  TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_tier         TEXT NOT NULL DEFAULT 'free';
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_status       TEXT NOT NULL DEFAULT 'inactive';
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_expires_at   TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_source       TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin                  BOOLEAN NOT NULL DEFAULT FALSE;

-- ── Seed admin accounts ───────────────────────────────────────────────────────
UPDATE users
SET is_admin = TRUE
WHERE email IN ('rnlarboleda@gmail.com', 'rnlarboleda18@gmail.com');

-- ── Free-tier daily usage tracking ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS usage_logs (
    id         SERIAL      PRIMARY KEY,
    clerk_id   TEXT        NOT NULL,
    feature    TEXT        NOT NULL,   -- 'case_digest' | 'bar_question' | 'flashcard'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usage_logs_clerk_date
    ON usage_logs (clerk_id, feature, created_at);
