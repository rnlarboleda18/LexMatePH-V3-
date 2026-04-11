"""
Optional one-time maintenance: remove leading SECTION blocks from rpc_codal.content_md
when they duplicate section_label (same rules as LexPlay tts_strip_leading_embedded_section).

Use when you want the database copy cleaned for the web reader, not only TTS.

  python scripts/strip_rpc_embedded_sections_db.py

Reads DB_CONNECTION_STRING from api/local.settings.json Values (same pattern as other scripts).
"""

from __future__ import annotations

import json
import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_SCRIPT_DIR, ".."))
_API_DIR = os.path.join(_REPO_ROOT, "api")
if _API_DIR not in sys.path:
    sys.path.insert(0, _API_DIR)

import psycopg2
from psycopg2.extras import RealDictCursor

from codal_text import tts_strip_leading_embedded_section


def _conn_str() -> str:
    try:
        path = os.path.join(_REPO_ROOT, "api", "local.settings.json")
        with open(path, encoding="utf-8") as f:
            return json.load(f)["Values"]["DB_CONNECTION_STRING"]
    except Exception:
        return os.environ.get("DB_CONNECTION_STRING", "")


def main() -> None:
    cs = _conn_str()
    if not cs:
        print("No DB_CONNECTION_STRING / local.settings.json")
        sys.exit(1)
    conn = psycopg2.connect(cs)
    updated = 0
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, article_num, section_label, content_md FROM rpc_codal "
                "WHERE content_md IS NOT NULL AND TRIM(content_md) <> '' "
                "AND (TRIM(COALESCE(section_label, '')) <> '' OR article_num ~* %s)",
                (r"^266\s*[-]?\s*[ABCD]$",),
            )
            rows = cur.fetchall()
        with conn.cursor() as cur:
            for r in rows:
                old = r["content_md"] or ""
                new = tts_strip_leading_embedded_section(
                    old, r.get("section_label"), r.get("article_num")
                )
                if new != old:
                    cur.execute(
                        "UPDATE rpc_codal SET content_md = %s WHERE id = %s",
                        (new, r["id"]),
                    )
                    updated += cur.rowcount
        conn.commit()
    finally:
        conn.close()
    print(f"Updated {updated} row(s).")


if __name__ == "__main__":
    main()
