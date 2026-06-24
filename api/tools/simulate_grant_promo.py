import os
import json
import psycopg
from pathlib import Path
import sys

# Add api to python path
here = Path(__file__).resolve().parent
api_dir = here.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from utils.founding_promo import get_promo_slot_limit, get_promo_duration_days

def _load_local_settings():
    for candidate in (Path(".") / "api" / "local.settings.json", Path(".") / "local.settings.json"):
        if candidate.exists():
            try:
                with open(candidate, encoding="utf-8") as f:
                    data = json.load(f)
                for k, v in (data.get("Values") or {}).items():
                    if k not in os.environ:
                        os.environ[k] = str(v) if v is not None else ""
                return
            except OSError:
                continue

def main():
    _load_local_settings()
    cs = os.environ.get("DB_CONNECTION_STRING")
    if not cs:
        print("Missing DB_CONNECTION_STRING")
        return

    clerk_id = "user_3FYmwKleaepQdYI5NndiMlnVtc0" # fluxiontechinc@gmail.com
    print(f"Simulating try_grant_founding_promo for clerk_id={clerk_id}...")

    with psycopg.connect(cs) as conn:
        with conn.cursor() as cur:
            # Let's execute the logic step by step and print findings
            cur.execute(
                """
                INSERT INTO founding_promo_state (id, claimed_count, max_slots)
                VALUES (1, 0, 30)
                ON CONFLICT (id) DO NOTHING
                """
            )
            print("INSERT INTO founding_promo_state run. Rowcount:", cur.rowcount)

            cur.execute("SELECT claimed_count FROM founding_promo_state WHERE id = 1 FOR UPDATE")
            row = cur.fetchone()
            print("SELECT claimed_count row:", row)

            limit = get_promo_slot_limit()
            print("Limit is:", limit)
            claimed = row[0]
            print("Claimed is:", claimed)
            if claimed >= limit:
                print("ABORT: claimed >= limit")
                return

            cur.execute(
                """
                SELECT founding_promo_eligible, founding_promo_slot, is_admin
                FROM users WHERE clerk_id = %s FOR UPDATE
                """,
                (clerk_id,),
            )
            u = cur.fetchone()
            print("SELECT user row:", u)
            if not u:
                print("ABORT: User not found in DB")
                return

            eligible, existing_slot, db_admin = u
            print(f"eligible={eligible}, existing_slot={existing_slot}, db_admin={db_admin}")
            if db_admin:
                print("ABORT: User is db_admin")
                return
            if not eligible:
                print("ABORT: User is not founding_promo_eligible")
                return
            if existing_slot is not None:
                print("ABORT: User already has existing_slot")
                return

            # Let's try the UPDATE on state
            cur.execute(
                """
                UPDATE founding_promo_state
                SET claimed_count = claimed_count + 1
                WHERE id = 1 AND claimed_count < %s
                RETURNING claimed_count
                """,
                (limit,),
            )
            slot_row = cur.fetchone()
            print("UPDATE founding_promo_state RETURNING claimed_count:", slot_row)
            if not slot_row:
                print("ABORT: UPDATE founding_promo_state returned no rows")
                return
            slot = slot_row[0]
            print("Granted Slot:", slot)

            days = get_promo_duration_days()
            print("Days:", days)
            
            cur.execute(
                """
                UPDATE users SET
                    subscription_tier       = 'barrister',
                    subscription_status     = 'active',
                    founding_promo_slot     = %s,
                    founding_promo_granted_at = NOW(),
                    subscription_source     = 'founding_promo',
                    subscription_expires_at = NOW() + make_interval(days => %s)
                WHERE clerk_id = %s AND founding_promo_slot IS NULL
                """,
                (slot, days, clerk_id),
            )
            print("UPDATE users rowcount:", cur.rowcount)
            
            # Since this is a simulation, let's roll back
            print("Rolling back transaction to keep DB unchanged for now.")
            conn.rollback()

if __name__ == "__main__":
    main()
