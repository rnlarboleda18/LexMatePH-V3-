import psycopg2
import psycopg2.extras
import json
import re

def natural_keys(text):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]

def clean_structural_label(label):
    if not label: return ""
    return re.sub(r'^#\s+', '', label).strip()

try:
    with open('api/local.settings.json') as f:
        settings = json.load(f)
        conn_str = settings['Values']['DB_CONNECTION_STRING']
except Exception:
    conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

conn = psycopg2.connect(conn_str)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Simulate the endpoint logic
cur.execute("SELECT * FROM roc_codal")
rows = cur.fetchall()

print(f"Total Rows from DB: {len(rows)}")

rows.sort(key=lambda x: natural_keys(str(x['article_num']) if x['article_num'] else ""))

mapped_rows = []
for r in rows:
    mapped_rows.append({
        'article_num': r.get('article_num'),
        'book_label': r.get('book_label')
    })

print(f"Mapped Rows Count: {len(mapped_rows)}")

# Print the last 10 rows to see what rules they are
print("\n--- Last 10 rows ---")
for r in mapped_rows[-10:]:
    print(r)

cur.close()
conn.close()
print("\nDone testing API response count.")
