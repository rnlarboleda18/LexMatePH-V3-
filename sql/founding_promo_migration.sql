-- Founding Promo Migration
-- Extends the users table with founding-promo tracking and creates the
-- global counter table used by api/utils/founding_promo.py.
-- Safe to re-run (all statements use IF NOT EXISTS guards).
-- Apply via: python api/run_billing_migrations.py

-- ── Founding-promo columns on users ──────────────────────────────────────────
-- founding_promo_eligible: set FALSE to opt a user out of the promo
-- founding_promo_slot:     slot number assigned when the promo was granted (1-based)
-- founding_promo_granted_at: timestamp when the Barrister promo was granted
ALTER TABLE users ADD COLUMN IF NOT EXISTS founding_promo_eligible   BOOLEAN     NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS founding_promo_slot       INTEGER;
ALTER TABLE users ADD COLUMN IF NOT EXISTS founding_promo_granted_at TIMESTAMPTZ;

-- ── Global promo state (single-row counter) ───────────────────────────────────
-- claimed_count: how many slots have been granted so far
-- max_slots:     mirrors FOUNDING_PROMO_LIMIT env var; code overrides this at runtime
CREATE TABLE IF NOT EXISTS founding_promo_state (
    id            INTEGER PRIMARY KEY,
    claimed_count INTEGER NOT NULL DEFAULT 0,
    max_slots     INTEGER NOT NULL DEFAULT 20
);

-- Seed the single control row (id = 1); no-op if already present
INSERT INTO founding_promo_state (id, claimed_count, max_slots)
VALUES (1, 0, 20)
ON CONFLICT (id) DO NOTHING;
