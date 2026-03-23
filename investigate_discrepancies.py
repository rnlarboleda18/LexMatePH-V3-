import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONNECTION = "dbname=lexmateph-ea-db user=postgres password=b66398241bfe483ba5b20ca5356a87be host=localhost port=5432"

def investigate():
    try:
        conn = psycopg2.connect(DB_CONNECTION)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Investigate specific problematic records
        target_keys = ('XIV-SPO', 'XIV-LAN', 'III-21', 'XIV-18')
        cur.execute("""
            SELECT article_num, article_label, article_title, section_label, content_md 
            FROM const_codal 
            WHERE article_num IN %s;
        """, (target_keys,))
        
        rows = cur.fetchall()
        for row in rows:
            print(f"\n--- {row['article_num']} ---")
            print(f"Label: {row['article_label']}")
            print(f"Title: {row['article_title']}")
            print(f"Section: {row['section_label']}")
            print(f"Content: {row['content_md'][:200]}...")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    investigate()
