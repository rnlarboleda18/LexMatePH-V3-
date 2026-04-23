"""
Runs universal_rpc_linker across all years that have RPC-tagged cases.
Reads DB_CONNECTION_STRING + GOOGLE_API_KEY from environment (or api/local.settings.json).
Usage:
    python scripts/run_rpc_linker_all_years.py [--dry-run] [--workers N] [--year-from YYYY] [--year-to YYYY]
"""
import os
import sys
import argparse
import json
import subprocess

# ---- load local.settings.json if env vars not yet set ----
_settings_path = os.path.join(os.path.dirname(__file__), '..', 'api', 'local.settings.json')
if os.path.exists(_settings_path):
    with open(_settings_path) as f:
        _vals = json.load(f).get('Values', {})
    for _k, _v in _vals.items():
        if _k not in os.environ:
            os.environ[_k] = str(_v)

import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING", "")
if not DB_CONNECTION_STRING:
    print("ERROR: DB_CONNECTION_STRING not set")
    sys.exit(1)

def get_rpc_years():
    """Return years that have at least one RPC-tagged case, newest first."""
    conn = psycopg2.connect(DB_CONNECTION_STRING, connect_timeout=15)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT EXTRACT(YEAR FROM date)::int AS yr, COUNT(*) c
        FROM sc_decided_cases
        WHERE (statutes_involved::text ILIKE '%RPC%'
            OR statutes_involved::text ILIKE '%Revised Penal Code%')
          AND date IS NOT NULL
        GROUP BY yr
        ORDER BY yr DESC
    """)
    years = [(r['yr'], r['c']) for r in cur.fetchall()]
    conn.close()
    return years

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--year-from', type=int, default=None)
    parser.add_argument('--year-to', type=int, default=None)
    args = parser.parse_args()

    mode = 'dry-run' if args.dry_run else 'commit'
    linker = os.path.join(os.path.dirname(__file__), 'universal_rpc_linker.py')

    years = get_rpc_years()
    if args.year_from:
        years = [(y, c) for y, c in years if y >= args.year_from]
    if args.year_to:
        years = [(y, c) for y, c in years if y <= args.year_to]

    print(f"RPC cases by year: {years}")
    print(f"Mode: {mode.upper()} | Workers: {args.workers}\n")

    total_years = len(years)
    for i, (yr, case_count) in enumerate(years, 1):
        print(f"\n[{i}/{total_years}] Year {yr} ({case_count} tagged cases)...")
        cmd = [
            sys.executable, linker,
            '--year', str(yr),
            '--workers', str(args.workers),
            mode
        ]
        env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
        result = subprocess.run(cmd, env=env)
        if result.returncode != 0:
            print(f"  !! Linker exited with code {result.returncode} for year {yr}")

    print("\nDone.")

if __name__ == '__main__':
    main()
