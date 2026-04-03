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

    emails = ['rnlarboleda@gmail.com', 'rnlarboleda18@gmail.com', 'rnlarboleda@icloud.com', 'fgarboleda28@gmail.com']
    
    with psycopg.connect(cs) as conn:
        with conn.cursor() as cur:
            for email in emails:
                cur.execute("""
                    SELECT clerk_id, email, is_admin, subscription_tier, subscription_status, subscription_source
                    FROM users WHERE LOWER(email) = LOWER(%s)
                """, (email,))
                u = cur.fetchone()
                if u:
                    print(f"User: {u[1]}")
                    print(f"  clerk_id: {u[0]}")
                    print(f"  is_admin: {u[2]}")
                    print(f"  tier: {u[3]}")
                    print(f"  status: {u[4]}")
                    print(f"  source: {u[5]}")
                else:
                    print(f"User: {email} NOT FOUND")

if __name__ == "__main__":
    main()
