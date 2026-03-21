import psycopg2
from psycopg2.extras import RealDictCursor
import json

try:
    with open('api/local.settings.json') as f:
        settings = json.load(f)
        conn_str = settings['Values']['DB_CONNECTION_STRING']
except Exception:
    conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

conn = psycopg2.connect(conn_str)
cur = conn.cursor(cursor_factory=RealDictCursor)

targets = [
    "%REVISED RULES OF CRIMINAL PROCEDURE%",
    "%2019 AMENDMENTS TO THE 1989 REVISED RULES ON EVIDENCE%"
]

with open('scripts/inspect_garbage_out.txt', 'w', encoding='utf-8') as log:
    log.write("Searching for garbage nodes...\n")
    for t in targets:
        cur.execute("SELECT id, article_num, section_label, title_label, content_md FROM roc_codal WHERE content_md LIKE %s OR section_label LIKE %s OR title_label LIKE %s", (t, t, t))
        rows = cur.fetchall()
        log.write(f"\nMatch for: {t}\n")
        for r in rows:
            log.write(f"ID: {r['id']} | Num: {r['article_num']}\n")
            log.write(f"  Sec Label: {r['section_label']}\n")
            log.write(f"  Title: {r['title_label']}\n")
            log.write(f"  Content (Truncated): {str(r['content_md'])[:100]}\n")

cur.close()
conn.close()
