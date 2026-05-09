"""
Sync clerk_id from Clerk API into the users table.
Queries Clerk for each user by email and updates clerk_id + is_admin.
Run from repo root: api/.venv/Scripts/python api/tools/sync_clerk_ids.py
"""
import json
import os
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parent.parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

import psycopg2
import requests


def load_settings():
    path = API_ROOT / "local.settings.json"
    with open(path, encoding="utf-8") as f:
        values = json.load(f).get("Values") or {}
    for k, v in values.items():
        if k not in os.environ:
            os.environ[k] = str(v) if v is not None else ""


def clerk_get_users(secret_key):
    """Fetch all users from Clerk (up to 500)."""
    resp = requests.get(
        "https://api.clerk.com/v1/users",
        headers={"Authorization": f"Bearer {secret_key}"},
        params={"limit": 500},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    load_settings()

    cs = os.environ.get("DB_CONNECTION_STRING", "").strip()
    if not cs:
        print("ERROR: DB_CONNECTION_STRING not set")
        sys.exit(1)

    secret_key = os.environ.get("CLERK_SECRET_KEY", "").strip().strip("'\"")
    if not secret_key:
        print("ERROR: CLERK_SECRET_KEY not set in local.settings.json")
        sys.exit(1)

    print("Fetching users from Clerk...")
    clerk_users = clerk_get_users(secret_key)
    print(f"  Found {len(clerk_users)} Clerk users")

    # Build email → clerk_id map (primary + all email addresses)
    email_to_clerk = {}
    for u in clerk_users:
        cid = u.get("id")
        for ea in u.get("email_addresses") or []:
            addr = (ea.get("email_address") or "").lower().strip()
            if addr:
                email_to_clerk[addr] = cid

    print(f"  Email map: {list(email_to_clerk.keys())}")

    conn = psycopg2.connect(cs)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, email, clerk_id, is_admin FROM users")
            rows = cur.fetchall()

        print(f"\nDB has {len(rows)} users:")
        updated = 0
        for row_id, email, existing_clerk_id, is_admin in rows:
            email_lc = (email or "").lower().strip()
            clerk_id = email_to_clerk.get(email_lc)
            marker = ""
            if clerk_id:
                if existing_clerk_id != clerk_id:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE users SET clerk_id = %s WHERE id = %s",
                            (clerk_id, row_id),
                        )
                    conn.commit()
                    marker = "  ← UPDATED clerk_id"
                    updated += 1
                else:
                    marker = "  (already synced)"
            else:
                marker = "  !! NOT found in Clerk"

            admin_tag = " [ADMIN]" if is_admin else ""
            print(f"  {email}{admin_tag}: {clerk_id or 'N/A'}{marker}")

        print(f"\nDone. {updated} clerk_id(s) updated.")

        # Also ensure the admin emails have is_admin = true
        admin_emails = ["rnlarboleda@gmail.com", "rnlarboleda18@gmail.com"]
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_admin = TRUE WHERE LOWER(email) = ANY(%s) AND is_admin IS DISTINCT FROM TRUE",
                (admin_emails,),
            )
            if cur.rowcount:
                print(f"  Also set is_admin=TRUE for {cur.rowcount} row(s).")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
