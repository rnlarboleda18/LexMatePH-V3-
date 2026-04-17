import psycopg2, json
from pathlib import Path
settings = Path('api/local.settings.json')
cs = json.loads(settings.read_text()).get('Values', {}).get('DB_CONNECTION_STRING')
conn = psycopg2.connect(cs)
cur = conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'article_versions'")
print('article_versions columns:', [c[0] for c in cur.fetchall()])
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'rpc_codal'")
print('rpc_codal columns:', [c[0] for c in cur.fetchall()])
cur.close()
conn.close()
