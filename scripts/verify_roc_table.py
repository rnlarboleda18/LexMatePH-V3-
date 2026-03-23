import psycopg2
import json

try:
    with open('api/local.settings.json') as f:
        settings = json.load(f)
        conn_str = settings['Values']['DB_CONNECTION_STRING']
except Exception:
    conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

conn = psycopg2.connect(conn_str)
cur = conn.cursor()

cur.execute("""
    SELECT book_label, COUNT(*), MIN(article_num), MAX(article_num)
    FROM roc_codal
    GROUP BY book_label
""")
rows = cur.fetchall()

with open('scripts/verify_roc_table_output.txt', 'w', encoding='utf-8') as log:
    log.write("\n--- ROC Codal Contents ---\n")
    for r in rows:
        log.write(f"Book: {r[0]} | Count: {r[1]} | Min: {r[2]} | Max: {r[3]}\n")

cur.close()
conn.close()
print("Counts written to scripts/verify_roc_table_output.txt")
