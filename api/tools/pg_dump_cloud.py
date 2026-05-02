"""
Dump cloud PostgreSQL using pg_dump custom format (-Fc).

Reads DB_CONNECTION_STRING from the environment or api/local.settings.json.

Purpose: Hosts such as Azure Functions often lack pg_dump on PATH; run this on a
developer machine with PostgreSQL client tools installed.

Usage:
  cd api
  python tools/pg_dump_cloud.py --output ..\\backups\\lexmate.dump

Requires: pg_dump on PATH.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _conn_string() -> str:
    env = (os.getenv("DB_CONNECTION_STRING") or os.getenv("DATABASE_URL") or "").strip()
    if env:
        return env
    root = Path(__file__).resolve().parents[1]
    cfg = root / "local.settings.json"
    if not cfg.is_file():
        print("Set DB_CONNECTION_STRING or create api/local.settings.json", file=sys.stderr)
        sys.exit(1)
    val = json.loads(cfg.read_text(encoding="utf-8")).get("Values", {}).get("DB_CONNECTION_STRING")
    if not val or not str(val).strip():
        print("DB_CONNECTION_STRING missing in local.settings.json", file=sys.stderr)
        sys.exit(1)
    return str(val).strip()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--output", "-o", required=True, help="Path to write .dump file (custom format)")
    args = p.parse_args()

    pg_dump_bin = shutil.which("pg_dump")
    if not pg_dump_bin:
        print("pg_dump not found on PATH. Install PostgreSQL client tools.", file=sys.stderr)
        sys.exit(1)

    out = Path(args.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    uri = _conn_string()
    cmd = [
        pg_dump_bin,
        "--format=custom",
        "--no-owner",
        "--no-acl",
        f"--file={str(out)}",
        f"--dbname={uri}",
    ]
    print(f"Writing {out} …")
    subprocess.run(cmd, check=True)
    print("Done.")


if __name__ == "__main__":
    main()
