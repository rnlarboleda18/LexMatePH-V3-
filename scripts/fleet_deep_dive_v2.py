import psycopg2
conn=psycopg2.connect('postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local')
cur=conn.cursor()

print("--- RECENT UPDATES (Last 5 mins handled by Terminals) ---")
cur.execute("SELECT id, short_title, updated_at FROM sc_decided_cases WHERE updated_at > NOW() - INTERVAL '5 minutes' ORDER BY updated_at DESC LIMIT 20")
rows = cur.fetchall()
for r in rows:
    print(f"  {r[0]}: {r[1]} @ {r[2]}")

cur.execute("SELECT count(*) FROM sc_decided_cases WHERE updated_at > NOW() - INTERVAL '6 hours'")
total_standardized = cur.fetchone()[0]

print(f"\nTotal cases standardized in this batch (last 6h): {total_standardized:,}")
conn.close()
