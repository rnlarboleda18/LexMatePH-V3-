import os
import json
import psycopg
from pathlib import Path

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
            # Let's list the 20 most recently created/updated users
            # Wait, let's see what columns are in the users table by querying information_schema
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users'
            """)
            cols = [r[0] for r in cur.fetchall()]
            print("Users table columns:", cols)
            
            # Let's see all users ordered by something or just all users if there are few
            cur.execute("""
                SELECT clerk_id, email, is_admin, subscription_tier, subscription_status, subscription_source, founding_promo_slot, founding_promo_eligible
                FROM users
                LIMIT 50
            """)
            rows = cur.fetchall()
            print(f"\n--- Total users found: {len(rows)} (showing up to 50) ---")
            for u in rows:
                print(f"Email: {u[1]} | clerk_id: {u[0]} | admin: {u[2]} | tier: {u[3]} | status: {u[4]} | source: {u[5]} | promo_slot: {u[6]} | promo_eligible: {u[7]}")

if __name__ == "__main__":
    main()
