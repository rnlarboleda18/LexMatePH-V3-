"""Diagnose admin _check_admin DB path: users table + pool connect. Run from repo: api/.venv/Scripts/python tools/diagnose_admin_check.py"""
import json
import os
import sys

API_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if API_ROOT not in sys.path:
    sys.path.insert(0, API_ROOT)
os.chdir(API_ROOT)

from psycopg2.extras import RealDictCursor  # noqa: E402


def main() -> None:
    settings_path = os.path.join(API_ROOT, "local.settings.json")
    with open(settings_path, encoding="utf-8") as f:
        cs = (json.load(f).get("Values") or {}).get("DB_CONNECTION_STRING") or ""
    cs = cs.strip()
    if not cs:
        print("No DB_CONNECTION_STRING in local.settings.json")
        sys.exit(1)

    print("1) Direct psycopg2.connect(local.settings)...")
    import psycopg2

    conn = psycopg2.connect(cs)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'users'
        ORDER BY ordinal_position
        """
    )
    cols = cur.fetchall()
    names = [c["column_name"] for c in cols]
    print(f"   users columns ({len(names)}): {', '.join(names)}")
    need = {"clerk_id", "is_admin"}
    missing = need - set(names)
    if missing:
        print(f"   FATAL: missing columns: {missing}")
        sys.exit(2)

    cur.execute("SELECT COUNT(*) AS n FROM users")
    print(f"   users row count: {cur.fetchone()['n']}")
    cur.execute(
        "SELECT clerk_id, is_admin FROM users WHERE is_admin = true LIMIT 5"
    )
    admins = cur.fetchall()
    print(f"   admin rows (sample): {len(admins)}")
    cur.close()
    conn.close()

    print("2) Same as app: db_pool.get_db_connection + admin query...")
    os.environ["DB_CONNECTION_STRING"] = cs
    import importlib

    import config as _cfg

    importlib.reload(_cfg)
    import db_pool

    importlib.reload(db_pool)
    # Reset pool singleton so reload picks up env - actually reload creates new module with _pool=None
    c2 = db_pool.get_db_connection()
    try:
        with c2.cursor(cursor_factory=RealDictCursor) as cur2:
            cur2.execute(
                "SELECT is_admin FROM users WHERE clerk_id = %s",
                ("user_test_nonexistent",),
            )
            row = cur2.fetchone()
            print(f"   missing clerk_id row: {row} (expect None)")
            cur2.execute(
                "SELECT clerk_id FROM users WHERE is_admin = true LIMIT 1"
            )
            one = cur2.fetchone()
            if one:
                cid = one["clerk_id"]
                cur2.execute(
                    "SELECT is_admin FROM users WHERE clerk_id = %s",
                    (cid,),
                )
                row2 = cur2.fetchone()
                print(f"   admin lookup by real clerk_id: is_admin={row2.get('is_admin') if row2 else None}")
    finally:
        db_pool.put_db_connection(c2)

    print("OK: DB and pool can run the admin check query.")


if __name__ == "__main__":
    main()
