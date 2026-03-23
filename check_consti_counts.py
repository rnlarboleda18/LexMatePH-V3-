import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONNECTION = "dbname=lexmateph-ea-db user=postgres password=b66398241bfe483ba5b20ca5356a87be host=localhost port=5432"

try:
    conn = psycopg2.connect(DB_CONNECTION)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check if there are any records with book_code = 'CONST' or NULL
    cur.execute("SELECT book_code, COUNT(*) FROM consti_codal GROUP BY book_code;")
    print("Table consti_codal records by book_code:")
    for row in cur.fetchall():
        print(f"  {row['book_code']}: {row['count']}")
        
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
