import psycopg2, json, sys
from pathlib import Path
settings = Path(__file__).resolve().parents[2] / 'api' / 'local.settings.json'
cs = json.loads(settings.read_text()).get('Values', {}).get('DB_CONNECTION_STRING')
conn = psycopg2.connect(cs)
cur = conn.cursor()
cur.execute("SELECT article_num, section_label FROM rpc_codal WHERE section_label IS NOT NULL AND section_label != '' LIMIT 5")
rows = cur.fetchall()
print('Articles WITH section labels:')
for row in rows:
    print(row)
    
cur.execute("SELECT COUNT(*) FROM rpc_codal WHERE section_label IS NOT NULL AND section_label != ''")
count = cur.fetchone()[0]
print(f"Total RPC articles with section labels: {count}")
cur.close()
conn.close()
