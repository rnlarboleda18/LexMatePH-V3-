import psycopg2
from psycopg2.extras import RealDictCursor
import json

DB_CONNECTION = "dbname=bar_reviewer_local user=postgres password=b66398241bfe483ba5b20ca5356a87be host=localhost port=5432"

def verify_art1_2():
    conn = psycopg2.connect(DB_CONNECTION)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check Article I and II
    print("--- ARTICLE I & II VERIFICATION ---")
    cur.execute("SELECT article_num, article_label, article_title, section_label, LEFT(content_md, 200) as body FROM consti_codal WHERE article_num IN ('I', 'II') ORDER BY list_order ASC LIMIT 10;")
    for row in cur.fetchall():
        print(json.dumps(row, indent=2, default=str))

    cur.close()
    conn.close()

if __name__ == "__main__":
    verify_art1_2()
