-- PayMongo Subscription Integration Migration
-- Run this against your PostgreSQL database

-- 1. Add subscription and admin columns to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS paymongo_customer_id TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_tier TEXT NOT NULL DEFAULT 'free';
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_status TEXT NOT NULL DEFAULT 'inactive';
ALTER TABLE users ADD COLUMN IF NOT EXISTS paymongo_subscription_id TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_expires_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;

-- 2. Set admin status for specific emails
UPDATE users SET is_admin = TRUE WHERE email IN ('rnlarboleda@gmail.com', 'rnlarboleda18@gmail.com');


-- 2. Create per-day usage tracking table for Free tier enforcement
CREATE TABLE IF NOT EXISTS usage_logs (
    id SERIAL PRIMARY KEY,
    clerk_id TEXT NOT NULL,
    feature TEXT NOT NULL,  -- 'case_digest', 'bar_question', 'flashcard'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usage_logs_clerk_date ON usage_logs(clerk_id, feature, created_at);

-- 3. Verify changes
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'users'
  AND column_name IN ('subscription_tier', 'subscription_status', 'paymongo_customer_id', 'paymongo_subscription_id', 'subscription_expires_at');
