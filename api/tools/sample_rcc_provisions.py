import json, psycopg2
from pathlib import Path
from psycopg2.extras import RealDictCursor

with open(Path(__file__).parent.parent / "local.settings.json") as f:
    cs = json.load(f)["Values"]["DB_CONNECTION_STRING"]

conn = psycopg2.connect(cs)
cur = conn.cursor(cursor_factory=RealDictCursor)

target = ["2","23","36","45","65","15","17","38","40","93"]
cur.execute("""
    SELECT article_num, article_title, LEFT(content_md, 400) AS preview
    FROM rcc_codal
    WHERE article_num = ANY(%s)
    ORDER BY article_num::int
""", (target,))

for r in cur.fetchall():
    num = r["article_num"]
    title = r["article_title"] or ""
    text = (r["preview"] or "").replace("\n", " ")
    print(f"Sec {num} - {title}")
    print(f"  {text[:350]}")
    print()

conn.close()
