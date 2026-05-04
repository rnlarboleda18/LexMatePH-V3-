-- One-time "trial ending soon" email: claim row with trial_reminder_sent_at (see utils/trial.py).
ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_reminder_sent_at TIMESTAMPTZ;
