import psycopg2
from psycopg2.extras import RealDictCursor
import sys

# Add path to db_pool
sys.path.append(r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api')
from db_pool import get_db_connection

try:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Query rows around Article 11 or containing CHAPTER II
    cur.execute("""
        SELECT article_num, content_md, structural_map 
        FROM rpc_codal 
        WHERE article_num IN ('11', '12', '10') 
           OR content_md ILIKE '%CHAPTER II%'
    """)
    rows = cur.fetchall()

    for r in rows:
        print(f"--- Article {r['article_num']} ---")
        print(f"Content MD: {repr(r['content_md'])}")
        print(f"Structural Map: {repr(r['structural_map'])}")
        print("\n")

except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals():
        conn.close()
