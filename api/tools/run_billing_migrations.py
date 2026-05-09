"""
Apply billing-related SQL migrations to DB_CONNECTION_STRING.

Migrations applied (in order):
  1. sql/users_clerk_identity_migration.sql — clerk_id + unique (required for Clerk + admin API)
  2. sql/paymongo_migration.sql           — subscription columns + usage_logs table
  3. sql/founding_promo_migration.sql     — founding promo columns
  4. sql/webhook_events_idempotency.sql   — webhook deduplication table
  5. sql/xendit_migration.sql             — Xendit customer/plan/pending columns
  6. sql/trial_reminder_migration.sql      — trial_reminder_sent_at for one-time reminder email

Loads api/local.settings.json Values into os.environ. **DB_CONNECTION_STRING from the file
always overrides** any value already in the process environment so this script hits the same DB
as Azure Functions local.settings.json (avoids silent migrations to the wrong server).

Run from repo root: python api/tools/run_billing_migrations.py
Or from api/tools: python run_billing_migrations.py
"""
import json
import os
import sys
from pathlib import Path

import psycopg

def _load_local_settings():
    here = Path(__file__).resolve().parent          # api/tools/
    api_dir = here.parent                           # api/
    repo_root = here.parent.parent                  # repo root
    for candidate in (here / "local.settings.json", api_dir / "local.settings.json", repo_root / "api" / "local.settings.json"):
        try:
            with open(candidate, encoding="utf-8") as f:
                data = json.load(f)
            vals = data.get("Values") or {}
            db_from_file = (vals.get("DB_CONNECTION_STRING") or "").strip()
            for k, v in vals.items():
                if k not in os.environ:
                    os.environ[k] = str(v) if v is not None else ""
            if db_from_file:
                os.environ["DB_CONNECTION_STRING"] = db_from_file
            return
        except OSError:
            continue


def _conn_str():
    cs = (os.environ.get("DB_CONNECTION_STRING") or "").strip()
    if ":5432/" in cs:
        cs = cs.replace(":5432/", ":5432/")
    return cs


def _run_file(conn, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    # psycopg3 accepts multiple statements in one execute on the connection
    with conn.cursor() as cur:
        cur.execute(sql)


def main() -> int:
    _load_local_settings()
    cs = _conn_str()
    if not cs:
        print("DB_CONNECTION_STRING not set. Add Values.DB_CONNECTION_STRING to api/local.settings.json or export it.")
        return 1

    here = Path(__file__).resolve().parent       # api/tools/
    root = here.parent.parent                    # repo root (sql/ lives here)
    files = [
        root / "sql" / "users_clerk_identity_migration.sql",
        root / "sql" / "paymongo_migration.sql",
        root / "sql" / "founding_promo_migration.sql",
        root / "sql" / "webhook_events_idempotency.sql",
        root / "sql" / "xendit_migration.sql",
        root / "sql" / "trial_reminder_migration.sql",
    ]
    for p in files:
        if not p.is_file():
            print(f"Missing {p}")
            return 1

    print("Connecting...")
    with psycopg.connect(cs, autocommit=True) as conn:
        for p in files:
            print(f"Applying {p.name}...")
            _run_file(conn, p)
            print(f"  OK: {p.name}")

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
