import psycopg2
import json

settings_path = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api\local.settings.json'
with open(settings_path) as f:
    settings = json.load(f)

conn_str = settings['Values']['DB_CONNECTION_STRING']
conn = psycopg2.connect(conn_str)
cur = conn.cursor()

def dump_row(cid):
    cur.execute("SELECT article_num, content_md FROM const_codal WHERE article_num = %s", (cid,))
    r = cur.fetchone()
    if r:
        print(f"\n=== ARTICLE: {r[0]} ===")
        print(r[1])
    else:
        print(f"\nRow {cid} not found")

dump_row('I-0')
dump_row('II-0')
dump_row('III-1')

cur.close()
conn.close()
