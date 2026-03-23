import psycopg2

DB_CONNECTION = "dbname=lexmateph-ea-db user=postgres password=b66398241bfe483ba5b20ca5356a87be host=localhost port=5432"

try:
    conn = psycopg2.connect(DB_CONNECTION)
    cur = conn.cursor()
    cur.execute("SELECT book_code, COUNT(*) FROM const_codal GROUP BY book_code;")
    rows = cur.fetchall()
    print("Table const_codal contents:")
    for row in rows:
        print(f"  {row[0]}: {row[1]}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
