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

    print("FOUNDING_PROMO_LIMIT env:", os.environ.get("FOUNDING_PROMO_LIMIT"))
    print("get_promo_slot_limit() returns:", get_promo_slot_limit())
    print("get_promo_duration_days() returns:", get_promo_duration_days())

    with psycopg.connect(cs) as conn:
        with conn.cursor() as cur:
            # 1. Check founding_promo_state
            cur.execute("SELECT id, claimed_count, max_slots FROM founding_promo_state")
            state = cur.fetchone()
            print("\nfounding_promo_state Row:")
            if state:
                print(f"  id: {state[0]}")
                print(f"  claimed_count: {state[1]}")
                print(f"  max_slots: {state[2]}")
            else:
                print("  (No rows found!)")

            # 2. Check the specific users who signed up recently but didn't get promo
            emails = ["fluxiontechinc@gmail.com", "jharboleda1208@gmail.com", "atbakidan@gmail.com"]
            print("\nSpecific User Records:")
            for email in emails:
                cur.execute("""
                    SELECT clerk_id, email, is_admin, founding_promo_eligible, founding_promo_slot, 
                           subscription_tier, subscription_status, subscription_source, founding_promo_granted_at
                    FROM users WHERE LOWER(email) = LOWER(%s)
                """, (email,))
                u = cur.fetchone()
                if u:
                    print(f"User: {u[1]}")
                    print(f"  clerk_id: {u[0]}")
                    print(f"  is_admin: {u[2]}")
                    print(f"  founding_promo_eligible: {u[3]}")
                    print(f"  founding_promo_slot: {u[4]}")
                    print(f"  subscription_tier: {u[5]}")
                    print(f"  subscription_status: {u[6]}")
                    print(f"  subscription_source: {u[7]}")
                    print(f"  founding_promo_granted_at: {u[8]}")
                else:
                    print(f"User: {email} NOT FOUND")

if __name__ == "__main__":
    main()
