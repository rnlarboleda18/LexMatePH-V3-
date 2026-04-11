"""
Report rpc_codal rows where structural_map paragraph count != \\n\\n split of content_md.

Note: The LexCodeStream UI uses finer line-based segmentation for RPC/ROC; this check
validates the DB invariant used by structural_mapper (article_versions diffs). Mismatches
here suggest regenerating maps via LexCode/scripts/structural_mapper.py after content edits.
"""

import json
import os
import re
import sys

import psycopg2
from psycopg2.extras import RealDictCursor


def split_paragraphs(text):
    if not text:
        return []
    return [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]


def main():
    conn_str = os.environ.get("DB_CONNECTION_STRING")
    if not conn_str:
        settings_path = os.path.join(os.path.dirname(__file__), "..", "api", "local.settings.json")
        try:
            with open(settings_path) as f:
                import json as _j

                conn_str = _j.load(f)["Values"]["DB_CONNECTION_STRING"]
        except Exception:
            print("Set DB_CONNECTION_STRING or provide api/local.settings.json", file=sys.stderr)
            sys.exit(1)

    conn = psycopg2.connect(conn_str)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """
        SELECT article_num, content_md, structural_map, amendments
        FROM rpc_codal
        ORDER BY article_num
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    issues = []
    for r in rows:
        sm = r.get("structural_map")
        if sm is None:
            continue
        if isinstance(sm, str):
            try:
                sm = json.loads(sm)
            except json.JSONDecodeError:
                issues.append((r["article_num"], "invalid JSON structural_map", None, None))
                continue
        if not isinstance(sm, list):
            continue
        paras = split_paragraphs((r.get("content_md") or "").strip())
        if len(sm) != len(paras):
            am = r.get("amendments")
            has_am = bool(am and str(am) not in ("[]", "null"))
            issues.append((r["article_num"], "len mismatch", len(sm), len(paras), has_am))

    print(f"Checked {len(rows)} rows; {len(issues)} issue(s).")
    for item in issues[:200]:
        print(item)
    if len(issues) > 200:
        print(f"... and {len(issues) - 200} more")


if __name__ == "__main__":
    main()
