import os
import json
import psycopg
from pathlib import Path
import sys

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

    with psycopg.connect(cs) as conn:
        with conn.cursor() as cur:
            # Check users with founding_promo_slot
            cur.execute("""
                SELECT clerk_id, email, founding_promo_slot, founding_promo_granted_at, subscription_tier, subscription_status
                FROM users
                WHERE founding_promo_slot IS NOT NULL
                ORDER BY founding_promo_slot ASC
            """)
            rows = cur.fetchall()
            print(f"--- Users with founding_promo_slot in DB (Total: {len(rows)}) ---")
            slots_in_use = []
            for r in rows:
                print(f"Slot {r[2]} | Email: {r[1]} | Granted: {r[3]} | Tier: {r[4]} | Status: {r[5]}")
                slots_in_use.append(r[2])
                
            print("\nSlots in use:", slots_in_use)
            
            # Check founding_promo_state claimed_count
            cur.execute("SELECT claimed_count, max_slots FROM founding_promo_state WHERE id = 1")
            state = cur.fetchone()
            print(f"\nfounding_promo_state: claimed_count={state[0]}, max_slots={state[1]}")

if __name__ == "__main__":
    main()
