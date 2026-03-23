import psycopg2

DB_CONNECTION = "dbname=lexmateph-ea-db user=postgres password=b66398241bfe483ba5b20ca5356a87be host=localhost port=5432"

try:
    conn = psycopg2.connect(DB_CONNECTION)
    cur = conn.cursor()
    
    print("Checking group_headers:")
    cur.execute("SELECT article_num, section_label, group_header FROM const_codal WHERE group_header IS NOT NULL LIMIT 5;")
    for row in cur.fetchall():
        print(row)
        
    print("\nChecking Constitution COUNT:")
    cur.execute("SELECT COUNT(*) FROM const_codal WHERE book_code = 'CONST';")
    print(cur.fetchone()[0])
    
    cur.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")
