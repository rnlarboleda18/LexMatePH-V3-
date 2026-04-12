import psycopg2
from psycopg2.extras import RealDictCursor
import sys

sys.path.append(r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\api')
from db_pool import get_db_connection

try:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 1. Query Article 11 Row
    cur.execute("SELECT * FROM rpc_codal WHERE article_num = '11'")
    r11 = cur.fetchone()
    if r11:
        print("=== ARTICLE 11 ROW ===")
        for k, v in r11.items():
            if k == 'content_md':
                 print(f"{k}: {repr(v[:200])} ...") # Print snippet
            else:
                 print(f"{k}: {repr(v)}")
        print("\n")

    # 2. Query rows with Non-Numeric Article Numbers (Structural Rows maybe?)
    cur.execute("""
        SELECT article_num, article_title, content_md 
        FROM rpc_codal 
        WHERE article_num ~ '^[A-Za-z]'
        LIMIT 20
    """)
    struct_rows = cur.fetchall()
    
    print(f"=== STRUCTURAL ROWS (Non-Numeric) found: {len(struct_rows)} ===")
    for i, r in enumerate(struct_rows):
         print(f"[{i+1}] Num: {repr(r['article_num'])} | Title: {repr(r['article_title'])}")
         print(f"    ContentMD: {repr(r['content_md'][:120] if r['content_md'] else '')}")
         print("-" * 50)

except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals():
        conn.close()
