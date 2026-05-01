"""
Restore a pg_dump custom-format (-Fc) archive into a target database.

Typical use: refresh a local mirror from a cloud backup file.

Runs pg_restore with --clean --if-exists --no-owner --no-acl so restores work
across different roles/privileges between Azure and local Postgres.

Usage:
  cd api
  python tools/pg_restore_local_mirror.py --dump ..\\backups\\lexmate.dump \\
      --dbname "postgresql://USER:PASS@localhost:5432/DBNAME"

Optional:
  --jobs N   parallel restore (PostgreSQL supports this for directory-format archives only;
             keep default 1 for a single .dump -Fc file)

Requires: pg_restore on PATH.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dump", "-f", required=True, help="Path to .dump file (pg_dump -Fc)")
    p.add_argument("--dbname", "-d", required=True, help="Target PostgreSQL URI or conninfo string")
    p.add_argument(
        "--jobs",
        "-j",
        type=int,
        default=1,
        help="pg_restore parallel jobs (use 1 for single-file custom format dumps)",
    )
    args = p.parse_args()

    pg_restore_bin = shutil.which("pg_restore")
    if not pg_restore_bin:
        print("pg_restore not found on PATH. Install PostgreSQL client tools.", file=sys.stderr)
        sys.exit(1)

    jobs = max(1, int(args.jobs))
    cmd = [
        pg_restore_bin,
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-acl",
    ]
    if jobs > 1:
        cmd.append(f"--jobs={jobs}")
    cmd.extend([f"--dbname={args.dbname}", args.dump])

    print("Restoring into target DB …")
    subprocess.run(cmd, check=True)
    print("Done.")


if __name__ == "__main__":
    main()
