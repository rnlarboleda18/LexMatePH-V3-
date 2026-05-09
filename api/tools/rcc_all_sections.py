import json, psycopg2
from pathlib import Path
from psycopg2.extras import RealDictCursor

with open(Path(__file__).parent.parent / "local.settings.json") as f:
    cs = json.load(f)["Values"]["DB_CONNECTION_STRING"]

conn = psycopg2.connect(cs)
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute("""
    SELECT article_num, article_title, LEFT(content_md, 120) AS preview
    FROM rcc_codal
    ORDER BY article_num::int
""")

rows = cur.fetchall()
print(f"Total RCC sections: {len(rows)}\n")
for r in rows:
    title = r["article_title"] or ""
    preview = (r["preview"] or "").replace("\n", " ")[:100]
    print(f"{int(r['article_num']):>4}  {title or preview}")

conn.close()
