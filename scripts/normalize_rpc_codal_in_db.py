"""
Apply api.codal_text.normalize_storage_markdown to all rpc_codal.content_md rows.

Run after backup. If articles have amendments, re-run LexCode/scripts/structural_mapper.py
per article (or your amendment pipeline) so structural_map stays aligned with paragraphs.
"""

import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_API_DIR = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", "api"))
if _API_DIR not in sys.path:
    sys.path.insert(0, _API_DIR)

import json
import psycopg2
from psycopg2.extras import RealDictCursor

from codal_text import normalize_storage_markdown


def main():
    settings_path = os.path.join(_API_DIR, "local.settings.json")
    conn_str = os.environ.get("DB_CONNECTION_STRING")
    if not conn_str:
        with open(settings_path) as f:
            conn_str = json.load(f)["Values"]["DB_CONNECTION_STRING"]

    conn = psycopg2.connect(conn_str)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id, article_num, content_md FROM rpc_codal")
    rows = cur.fetchall()
    updated = 0
    upd = conn.cursor()
    for r in rows:
        raw = (r.get("content_md") or "").strip()
        norm = normalize_storage_markdown(raw)
        if norm != raw:
            try:
                upd.execute(
                    "UPDATE rpc_codal SET content_md = %s, updated_at = NOW() WHERE id = %s",
                    (norm, r["id"]),
                )
            except Exception:
                upd.execute("UPDATE rpc_codal SET content_md = %s WHERE id = %s", (norm, r["id"]))
            updated += 1
            print(f"Updated article_num={r['article_num']} id={r['id']}")
    conn.commit()
    upd.close()
    conn.close()
    print(f"Done. {updated} row(s) changed.")


if __name__ == "__main__":
    main()
