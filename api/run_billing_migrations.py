"""
Apply sql/paymongo_migration.sql then sql/founding_promo_migration.sql to DB_CONNECTION_STRING.
Loads api/local.settings.json Values into os.environ (same pattern as run_migration.py).
Run from repo root: python api/run_billing_migrations.py
Or from api:       python run_billing_migrations.py
"""
import json
import os
import sys
from pathlib import Path

import psycopg

def _load_local_settings():
    here = Path(__file__).resolve().parent
    root = here.parent
    for candidate in (here / "local.settings.json", root / "local.settings.json"):
        try:
            with open(candidate, encoding="utf-8") as f:
                data = json.load(f)
            for k, v in (data.get("Values") or {}).items():
                if k not in os.environ:
                    os.environ[k] = str(v) if v is not None else ""
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

    here = Path(__file__).resolve().parent
    root = here.parent
    files = [
        root / "sql" / "paymongo_migration.sql",
        root / "sql" / "founding_promo_migration.sql",
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
