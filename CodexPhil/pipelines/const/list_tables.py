import psycopg2
conn_str = "dbname=bar_reviewer_local user=postgres password=b66398241bfe483ba5b20ca5356a87be host=localhost port=5432"
conn = psycopg2.connect(conn_str)
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;")
print("Tables:")
for row in cur.fetchall():
    print(f"- {row[0]}")

# Also check columns of rpc_codal if it exists
print("\nColumns of rpc_codal (if exists):")
try:
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'rpc_codal';")
    for row in cur.fetchall():
        print(f"  {row[0]} ({row[1]})")
except:
    pass

conn.close()
