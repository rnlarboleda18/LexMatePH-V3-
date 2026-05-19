import psycopg2
import os

conn = psycopg2.connect(os.environ.get('DB_CONNECTION_STRING', 'postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db'))
cur = conn.cursor()
cur.execute("SELECT created_at FROM codal_case_links WHERE statute_id = 'CPRA' ORDER BY created_at DESC LIMIT 1")
res = cur.fetchone()
if res:
    print('Last link created at:', res[0])
else:
    print('No links found')
