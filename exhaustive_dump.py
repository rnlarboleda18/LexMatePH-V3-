import psycopg2
from psycopg2.extras import RealDictCursor
import json

DB_CONNECTION = "dbname=lexmateph-ea-db user=postgres password=b66398241bfe483ba5b20ca5356a87be host=localhost port=5432"

def exhaustive_dump():
    conn = psycopg2.connect(DB_CONNECTION)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Query all records that are NOT part of the Family Code
    cur.execute("""
        SELECT article_num, section_label, group_header, article_title, article_label, list_order, LEFT(content_md, 30) as content_start 
        FROM const_codal 
        WHERE book_code IS NULL OR book_code = 'CONST'
        ORDER BY list_order ASC;
    """)
    rows = cur.fetchall()
    
    with open('exhaustive_dump.json', 'w') as f:
        json.dump(rows, f, indent=2, default=str)
    
    print(f"Dumped {len(rows)} records to exhaustive_dump.json")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    exhaustive_dump()
