import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONNECTION = "dbname=lexmateph-ea-db user=postgres password=b66398241bfe483ba5b20ca5356a87be host=localhost port=5432"

def inspect_postgres():
    try:
        conn = psycopg2.connect(DB_CONNECTION)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check table structure
        print("Schema of const_codal:")
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'const_codal'
            ORDER BY ordinal_position;
        """)
        for row in cur.fetchall():
            print(f"  - {row['column_name']} ({row['data_type']})")
            
        # Check content
        print("\nFirst 10 rows of const_codal:")
        cur.execute("SELECT article_num, article_label, article_title, section_label, LEFT(content_md, 50) as snippet FROM const_codal ORDER BY list_order LIMIT 10;")
        for row in cur.fetchall():
            print(row)
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_postgres()
