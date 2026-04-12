"""Print column-by-column differences for two sc_decided_cases rows (by id).

Usage (repo root):
  python scripts/diff_sc_decided_rows.py 54679 71926
  python scripts/diff_sc_decided_rows.py 50551 71391

Connection: DB_CONNECTION_STRING or api/local.settings.json.
Large text values are shown as len + md5 when they differ.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("pip install psycopg2-binary", file=sys.stderr)
    sys.exit(1)

LARGE = 400  # chars: show summary instead of full value when different


def conn_str() -> str:
    if os.environ.get("DB_CONNECTION_STRING"):
        return os.environ["DB_CONNECTION_STRING"]
    for p in ("api/local.settings.json", "local.settings.json"):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)["Values"]["DB_CONNECTION_STRING"]
        except OSError:
            continue
    sys.exit("No DB connection configured.")


def norm(v):
    if v is None:
        return None
    if isinstance(v, memoryview):
        v = v.tobytes()
    if isinstance(v, bytes):
        return v.hex()[:64] + ("..." if len(v) > 32 else "")
    return v


def summarize_text(s: str) -> str:
    raw = s.encode("utf-8", errors="replace")
    h = hashlib.md5(raw).hexdigest()
    return f"len={len(s)} md5={h}"


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__.strip())
        sys.exit(1)
    a_id, b_id = int(sys.argv[1]), int(sys.argv[2])

    conn = psycopg2.connect(conn_str())
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM sc_decided_cases WHERE id = %s", (a_id,))
    row_a = cur.fetchone()
    cur.execute("SELECT * FROM sc_decided_cases WHERE id = %s", (b_id,))
    row_b = cur.fetchone()
    conn.close()

    if not row_a or not row_b:
        print("One or both ids not found.", row_a and "a ok" or "a missing", row_b and "b ok" or "b missing")
        sys.exit(1)

    keys = sorted(set(row_a.keys()) | set(row_b.keys()))
    same = []
    diff = []
    for k in keys:
        va, vb = row_a.get(k), row_b.get(k)
        na, nb = norm(va), norm(vb)
        if na == nb:
            same.append(k)
            continue
        # display
        def fmt(v):
            if v is None:
                return "NULL"
            if isinstance(v, str) and len(v) > LARGE:
                return summarize_text(v)
            return repr(v)[:500] + ("..." if isinstance(v, str) and len(v) > 500 else "")

        diff.append((k, fmt(va), fmt(vb)))

    print(f"Compare id {a_id} (A) vs id {b_id} (B)\n")
    print(f"Columns identical ({len(same)}): {', '.join(same)}\n")
    print(f"Columns different ({len(diff)}):\n")
    for k, fa, fb in diff:
        print(f"  [{k}]")
        print(f"    A: {fa}")
        print(f"    B: {fb}")
        print()


if __name__ == "__main__":
    main()
