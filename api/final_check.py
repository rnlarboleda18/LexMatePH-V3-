import os
import json
import psycopg
from pathlib import Path

def _load_local_settings():
    here = Path(__file__).resolve().parent
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

    emails = ["rnlarboleda@icloud.com", "fgarboleda28@gmail.com"]
    
    with psycopg.connect(cs) as conn:
        with conn.cursor() as cur:
            print("--- Users Check (Case-Insensitive) ---")
            for email in emails:
                cur.execute("""
                    SELECT clerk_id, email, is_admin, founding_promo_eligible, founding_promo_slot, subscription_tier, subscription_status 
                    FROM users WHERE LOWER(email) = LOWER(%s)
                """, (email,))
                rows = cur.fetchall()
                if rows:
                    for u in rows:
                        print(f"User: {u[1]}")
                        print(f"  clerk_id: {u[0]}")
                        print(f"  eligible: {u[3]}")
                        print(f"  tier: {u[5]}")
                        print(f"  status: {u[6]}")
                else:
                    print(f"User: {email} NOT FOUND")
            
            print("\n--- Promo Claimed ---")
            cur.execute("SELECT claimed_count FROM founding_promo_state")
            state = cur.fetchone()
            if state:
                print(f"Count: {state[0]}")

if __name__ == "__main__":
    main()
