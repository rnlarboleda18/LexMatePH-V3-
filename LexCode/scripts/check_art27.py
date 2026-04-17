import psycopg2, json, sys
from pathlib import Path
settings = Path(__file__).resolve().parents[2] / 'api' / 'local.settings.json'
cs = json.loads(settings.read_text()).get('Values', {}).get('DB_CONNECTION_STRING')
conn = psycopg2.connect(cs)
cur = conn.cursor()
cur.execute("SELECT content_md FROM rpc_codal WHERE article_num='27'")
row = cur.fetchone()
if row:
    print('RAW DB CONTENT for Art 27:')
    print(row[0])
else:
    print("Art 27 not found")
cur.close()
conn.close()
