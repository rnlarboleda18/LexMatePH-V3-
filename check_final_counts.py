import psycopg2

DB_CONNECTION = "dbname=lexmateph-ea-db user=postgres password=b66398241bfe483ba5b20ca5356a87be host=localhost port=5432"

try:
    conn = psycopg2.connect(DB_CONNECTION)
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM consti_codal;")
    consti_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM fc_codal;")
    fc_count = cur.fetchone()[0]
    
    print(f"Constitution records (consti_codal): {consti_count}")
    print(f"Family Code records (fc_codal): {fc_count}")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
