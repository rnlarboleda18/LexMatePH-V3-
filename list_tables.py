import psycopg2

DB_CONNECTION = "dbname=bar_reviewer_local user=postgres password=b66398241bfe483ba5b20ca5356a87be host=localhost port=5432"

try:
    conn = psycopg2.connect(DB_CONNECTION)
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
    rows = cur.fetchall()
    print("Database Tables:")
    for row in rows:
        print(f"  - {row[0]}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
