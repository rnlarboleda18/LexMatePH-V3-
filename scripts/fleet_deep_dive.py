import psycopg2
conn=psycopg2.connect('postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db')
cur=conn.cursor()

# Check specific patterns
cur.execute("SELECT count(*) FROM sc_decided_cases WHERE short_title LIKE 'People of the Philippines%'")
people = cur.fetchone()[0]

cur.execute("SELECT count(*) FROM sc_decided_cases WHERE short_title NOT LIKE '% v. %'")
no_v = cur.fetchone()[0]

cur.execute("SELECT count(*) FROM sc_decided_cases WHERE updated_at > NOW() - INTERVAL '5 minutes'")
recent = cur.fetchone()[0]

cur.execute("SELECT id, short_title, updated_at FROM sc_decided_cases WHERE updated_at > NOW() - INTERVAL '1 minute' ORDER BY updated_at DESC LIMIT 5")
recent_cases = cur.fetchall()

print(f"People of the Philippines: {people}")
print(f"Missing ' v. ': {no_v}")
print(f"Updates in last 5m: {recent}")
print("Most recent updates:")
for r in recent_cases:
    print(f"  {r[0]}: {r[1]} @ {r[2]}")

conn.close()
