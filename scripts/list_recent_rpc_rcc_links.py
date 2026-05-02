"""List recent codal_case_links for RPC/RCC with case titles (for gavel / LexCode checks)."""
import json
import os
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

root = Path(__file__).resolve().parent.parent
vals = json.loads((root / "api" / "local.settings.json").read_text(encoding="utf-8")).get(
    "Values"
) or {}
db = (os.environ.get("DB_CONNECTION_STRING") or vals.get("DB_CONNECTION_STRING") or "").strip()
if not db:
    sys.exit("No DB")

conn = psycopg2.connect(db)
cur = conn.cursor(cursor_factory=RealDictCursor)
cur.execute(
    """
    SELECT l.statute_id::text AS statute_id,
           l.provision_id::text AS provision_id,
           l.target_paragraph_index,
           l.created_at,
           s.short_title,
           s.id AS case_id
    FROM codal_case_links l
    JOIN sc_decided_cases s ON s.id = l.case_id
    WHERE UPPER(TRIM(l.statute_id::text)) IN ('RPC', 'RCC')
    ORDER BY l.created_at DESC NULLS LAST, l.id DESC
    LIMIT 50
    """
)
rows = cur.fetchall()
print(f"Recent RPC/RCC links (up to 50): {len(rows)} rows\n")
for r in rows:
    print(
        f"{r['statute_id']:4} | prov {str(r['provision_id']):8} | ¶{r['target_paragraph_index']} | "
        f"{(r['short_title'] or '')[:55]} | case_id={r['case_id']}"
    )
cur.close()
conn.close()
