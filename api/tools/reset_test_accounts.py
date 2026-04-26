"""
api/tools/reset_test_accounts.py
─────────────────────────────────
Reset specific test email accounts to a clean, unregistered state:
  - Clears clerk_id so the account can be re-registered fresh.
  - Resets all subscription fields to free / inactive.
  - Clears founding-promo state for the account.

NEVER touches the admin email (rnlarboleda18@gmail.com).

Usage (from repo root with venv active):
  python api/tools/reset_test_accounts.py [--dry-run]
"""

import argparse
import os
import sys

# ── Resolve DB connection ──────────────────────────────────────────────────────
# Prefer local.settings.json when running locally; fall back to env var.
def _get_conn_string() -> str:
    local_settings = os.path.join(os.path.dirname(__file__), "..", "local.settings.json")
    try:
        import json
        with open(local_settings) as f:
            data = json.load(f)
        cs = data.get("Values", {}).get("DB_CONNECTION_STRING", "")
        if cs:
            return cs
    except Exception:
        pass
    cs = os.environ.get("DB_CONNECTION_STRING", "")
    if not cs:
        sys.exit("ERROR: DB_CONNECTION_STRING not found in local.settings.json or environment.")
    return cs


# ── Accounts to reset ─────────────────────────────────────────────────────────
TEST_EMAILS = [
    "rnlarboleda6@gmail.com",
    "balong0608.lumindas@gmail.com",
]

# This email is NEVER touched.
ADMIN_EMAIL = "rnlarboleda18@gmail.com"

RESET_SQL = """
UPDATE users SET
    clerk_id                  = NULL,
    subscription_tier         = 'free',
    subscription_status       = 'inactive',
    subscription_source       = NULL,
    subscription_expires_at   = NULL,
    founding_promo_slot       = NULL,
    founding_promo_granted_at = NULL,
    founding_promo_eligible   = TRUE,
    xendit_plan_id            = NULL,
    xendit_pending_plan_key   = NULL
WHERE LOWER(email) = LOWER(%s)
  AND LOWER(email) != LOWER(%s)   -- safety guard: never touch admin
RETURNING email, clerk_id;
"""


def main():
    parser = argparse.ArgumentParser(description="Reset LexMatePH test accounts to unregistered state.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be changed without writing.")
    args = parser.parse_args()

    try:
        import psycopg
    except ImportError:
        sys.exit("ERROR: psycopg not installed. Activate the api venv first.")

    conn_string = _get_conn_string()
    print(f"Connecting to DB…")

    with psycopg.connect(conn_string) as conn:
        with conn.cursor() as cur:
            for email in TEST_EMAILS:
                if email.lower() == ADMIN_EMAIL.lower():
                    print(f"  SKIP (admin):  {email}")
                    continue

                # Preview current state first
                cur.execute(
                    "SELECT email, clerk_id, subscription_tier, subscription_source FROM users WHERE LOWER(email) = LOWER(%s)",
                    (email,),
                )
                row = cur.fetchone()
                if not row:
                    print(f"  NOT FOUND:     {email}")
                    continue

                print(
                    f"  FOUND:         {row[0]}  |  clerk_id={row[1]}  "
                    f"|  tier={row[2]}  |  source={row[3]}"
                )

                if args.dry_run:
                    print(f"  [DRY-RUN] Would reset {email} — skipping write.")
                    continue

                cur.execute(RESET_SQL, (email, ADMIN_EMAIL))
                updated = cur.fetchall()
                if updated:
                    print(f"  RESET OK:      {email}  (clerk_id cleared, tier→free)")
                else:
                    print(f"  NO ROWS UPDATED for {email} (check email spelling?)")

        if not args.dry_run:
            conn.commit()
            print("\nAll changes committed.")
        else:
            conn.rollback()
            print("\nDry-run complete — no changes written.")


if __name__ == "__main__":
    main()
