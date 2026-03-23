import psycopg2

DB_CONNECTION = "dbname=lexmateph-ea-db user=postgres password=b66398241bfe483ba5b20ca5356a87be host=localhost port=5432"

try:
    conn = psycopg2.connect(DB_CONNECTION)
    cur = conn.cursor()
    # Delete Constitution rows (book_code is CONST or NULL)
    cur.execute("DELETE FROM const_codal WHERE book_code = 'CONST' OR book_code IS NULL;")
    conn.commit()
    print(f"Deleted {cur.rowcount} Constitution-related rows.")
    
    # Final check
    cur.execute("SELECT book_code, COUNT(*) FROM const_codal GROUP BY book_code;")
    rows = cur.fetchall()
    print("Remaining rows by book_code:")
    for row in rows:
        print(f"  {row[0]}: {row[1]}")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
