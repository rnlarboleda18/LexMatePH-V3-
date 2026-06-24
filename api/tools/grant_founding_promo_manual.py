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

from utils.founding_promo import try_grant_founding_promo, get_promo_slot_limit

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

    emails = ["fluxiontechinc@gmail.com", "jharboleda1208@gmail.com"]
    print(f"Target emails to grant: {emails}")

    with psycopg.connect(cs) as conn:
        with conn.cursor() as cur:
            # Check current promo state
            cur.execute("SELECT claimed_count, max_slots FROM founding_promo_state WHERE id = 1 FOR UPDATE")
            row = cur.fetchone()
            if not row:
                print("founding_promo_state row missing. Creating...")
                cur.execute(
                    "INSERT INTO founding_promo_state (id, claimed_count, max_slots) VALUES (1, 0, 30) RETURNING claimed_count, max_slots"
                )
                row = cur.fetchone()
            
            claimed_before = row[0]
            max_slots = row[1]
            limit = get_promo_slot_limit()
            print(f"Promo state BEFORE: claimed_count={claimed_before}, max_slots={max_slots}, current limit={limit}")

            for email in emails:
                print(f"\nProcessing {email}...")
                cur.execute("SELECT clerk_id, founding_promo_slot, subscription_tier FROM users WHERE LOWER(email) = LOWER(%s)", (email,))
                u = cur.fetchone()
                if not u:
                    print(f"  User {email} NOT FOUND in users table. Skipping.")
                    continue
                clerk_id, slot, tier = u
                print(f"  clerk_id: {clerk_id}")
                print(f"  existing slot: {slot}")
                print(f"  existing tier: {tier}")
                
                if slot is not None:
                    print(f"  User already has promo slot {slot}. Skipping.")
                    continue
                
                # Run the actual grant logic
                print(f"  Attempting to grant promo to {clerk_id}...")
                try_grant_founding_promo(cur, clerk_id, is_admin=False)
                
                # Check if it was successfully granted
                cur.execute(
                    """
                    SELECT founding_promo_slot, subscription_tier, subscription_status, subscription_source, subscription_expires_at
                    FROM users WHERE clerk_id = %s
                    """,
                    (clerk_id,),
                )
                res = cur.fetchone()
                if res and res[0] is not None:
                    print(f"  SUCCESS! Granted slot {res[0]} to {email}.")
                    print(f"  New Tier: {res[1]}, Status: {res[2]}, Source: {res[3]}, Expires: {res[4]}")
                else:
                    print(f"  FAILED to grant promo slot. Check if limit is reached or other condition met.")

            # Check final promo state
            cur.execute("SELECT claimed_count, max_slots FROM founding_promo_state WHERE id = 1")
            state = cur.fetchone()
            print(f"\nPromo state AFTER: claimed_count={state[0]}, max_slots={state[1]}")
            
            # Commit changes to database
            print("Committing transaction...")
            conn.commit()
            print("Transaction committed successfully.")

if __name__ == "__main__":
    main()
