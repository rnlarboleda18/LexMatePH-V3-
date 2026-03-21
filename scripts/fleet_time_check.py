import psycopg2
conn=psycopg2.connect('postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local')
cur=conn.cursor()

cur.execute("SELECT NOW(), MAX(updated_at) FROM sc_decided_cases")
row = cur.fetchone()
print(f"DB NOW: {row[0]}")
print(f"MAX UPDATED_AT: {row[1]}")

cur.execute("SELECT id, short_title, updated_at FROM sc_decided_cases WHERE updated_at > (SELECT MAX(updated_at) FROM sc_decided_cases) - INTERVAL '1 minute' ORDER BY updated_at DESC LIMIT 5")
rows = cur.fetchall()
print("\nMost Recent Updates relative to MAX(updated_at):")
for r in rows:
    print(f"  {r[0]}: {r[1]} @ {r[2]}")

conn.close()
