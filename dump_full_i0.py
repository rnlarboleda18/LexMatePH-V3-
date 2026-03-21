import psycopg2
import json

settings_path = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api\local.settings.json'
with open(settings_path) as f:
    settings = json.load(f)

conn_str = settings['Values']['DB_CONNECTION_STRING']
conn = psycopg2.connect(conn_str)
cur = conn.cursor()

cur.execute("SELECT content_md FROM const_codal WHERE article_num = 'I-0'")
r = cur.fetchone()

with open('content_i0.txt', 'w', encoding='utf-8') as f:
    f.write(r[0])

cur.close()
conn.close()
print("Done writing content_i0.txt")
