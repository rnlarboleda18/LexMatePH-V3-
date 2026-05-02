#!/usr/bin/env python3
"""
Remove RPC codex rows that incorrectly store Republic Act No. 6425 (Dangerous Drugs Act)
sections as if they were Revised Penal Code articles.

RA 7659 amended both the RPC (penalty upgrades) and RA 6425. The amendatory text uses
``Sec. 14-A``, ``Sec. 15-a``, ``Sec. 20-A`` under the Drugs Act — these must not appear
as ``article_versions`` / ``rpc_codal`` keys ``14-A``, ``15-a``, ``20-A``.

This script deletes those stubs only. It does **not** remove genuine RPC Art. **211-A**
(Qualified Bribery), which RA 7659 incorporates as a new RPC article after Art. 211.

Inputs:
  --dry-run   Print DELETE counts only; rollback.

Environment:
  DB_CONNECTION_STRING (cloud) or process_amendment.get_db_connection fallbacks.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_SCRIPTS))
sys.path.insert(0, str(_REPO / "api"))

from process_amendment import get_db_connection  # noqa: E402

# Exact keys as stored in the DB (case-sensitive match to current bad rows).
MISFILED_ARTICLE_NUMS = ("14-A", "15-a", "20-A")


def main() -> int:
    parser = argparse.ArgumentParser(description="Drop misfiled RA 6425 sections from RPC tables")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT code_id FROM legal_codes WHERE short_name = 'RPC'")
    row = cur.fetchone()
    if not row:
        print("No RPC legal_codes row")
        return 2
    code_id = row[0]
    tup = tuple(MISFILED_ARTICLE_NUMS)

    cur.execute(
        """
        SELECT article_number, amendment_id, LEFT(content, 60)
        FROM article_versions
        WHERE code_id = %s AND article_number IN %s
        """,
        (code_id, tup),
    )
    av_rows = cur.fetchall()
    print(f"article_versions rows to delete: {len(av_rows)}")
    for r in av_rows:
        print(f"  {r}")

    cur.execute(
        "SELECT article_num, LEFT(content_md, 60) FROM rpc_codal WHERE article_num IN %s",
        (tup,),
    )
    rpc_rows = cur.fetchall()
    print(f"rpc_codal rows to delete: {len(rpc_rows)}")
    for r in rpc_rows:
        print(f"  {r}")

    if args.dry_run:
        conn.rollback()
        print("Dry run — rolled back.")
        cur.close()
        conn.close()
        return 0

    cur.execute(
        "DELETE FROM article_versions WHERE code_id = %s AND article_number IN %s",
        (code_id, tup),
    )
    cur.execute("DELETE FROM rpc_codal WHERE article_num IN %s", (tup,))
    conn.commit()
    print("Done (committed).")
    cur.close()
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
