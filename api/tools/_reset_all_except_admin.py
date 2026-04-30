"""
api/tools/_reset_all_except_admin.py
One-off script: reset ALL user accounts to unregistered state,
except rnlarboleda18@gmail.com (the admin).
"""
import json, os, sys

settings = os.path.join(os.path.dirname(__file__), "..", "local.settings.json")
with open(settings) as f:
    cs = json.load(f)["Values"]["DB_CONNECTION_STRING"]

ADMIN_EMAIL = "rnlarboleda18@gmail.com"

try:
    import psycopg
except ImportError:
    sys.exit("ERROR: activate the api venv first.")

DRY_RUN = "--dry-run" in sys.argv

with psycopg.connect(cs) as conn:
    with conn.cursor() as cur:
        # Preview how many rows will be touched
        cur.execute(
            "SELECT COUNT(*) FROM users WHERE LOWER(email) != LOWER(%s)",
            (ADMIN_EMAIL,),
        )
        total = cur.fetchone()[0]
        print(f"Rows to reset: {total}  (admin is excluded)")

        if DRY_RUN:
            cur.execute(
                "SELECT email, clerk_id, subscription_tier, subscription_source FROM users WHERE LOWER(email) != LOWER(%s) ORDER BY email",
                (ADMIN_EMAIL,),
            )
            for r in cur.fetchall():
                print(f"  would reset: {r[0]:<45} clerk={r[1]} tier={r[2]} src={r[3]}")
            print("\nDry-run — no changes written.")
        else:
            cur.execute(
                """
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
                WHERE LOWER(email) != LOWER(%s)
                RETURNING email
                """,
                (ADMIN_EMAIL,),
            )
            updated = cur.fetchall()
            conn.commit()
            print(f"Reset {len(updated)} accounts:")
            for r in updated:
                print(f"  - {r[0]}")
            print("\nDone.")
