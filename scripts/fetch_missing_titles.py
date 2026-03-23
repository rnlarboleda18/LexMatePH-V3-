import psycopg2
conn = psycopg2.connect("postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db")
cur = conn.cursor()
cur.execute("SELECT id FROM sc_decided_cases WHERE short_title IS NULL OR short_title = ''")
ids = [str(r[0]) for r in cur.fetchall()]
print(f"MISSING_TITLES={','.join(ids)}")
conn.close()
