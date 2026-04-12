import psycopg2
from psycopg2.extras import RealDictCursor
import sys

# Add path to db_pool
sys.path.append(r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api')
from db_pool import get_db_connection

try:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # List rows for Articles 1 to 20
    cur.execute("""
        SELECT article_num, content_md, article_title 
        FROM rpc_codal 
        WHERE book = '1'
          AND CAST(REGEXP_REPLACE(article_num, '\D', '', 'g') AS INTEGER) BETWEEN 1 AND 20
        ORDER BY 
            CAST(REGEXP_REPLACE(article_num, '\D', '', 'g') AS INTEGER) ASC
    """)
    rows = cur.fetchall()

    print(f"Total rows: {len(rows)}")
    for i, r in enumerate(rows):
        print(f"[{i+1}] ArticleNum: {repr(r['article_num'])} | Title: {repr(r['article_title'])}")
        print(f"    ContentMD (first 120): {repr(r['content_md'][:120] if r['content_md'] else '')}")
        print("-" * 50)

except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals():
        conn.close()
