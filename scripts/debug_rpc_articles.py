import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = "postgresql://bar_admin:RABpass021819!@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"

def debug_rpc():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT article_num, article_title, content_md 
        FROM rpc_codal 
        WHERE article_num IN ('266A', '266B', '266C', '266D') 
        ORDER BY article_num
    """)
    rows = cur.fetchall()
    
    for r in rows:
        print(f"==========================================================")
        print(f"ARTICLE: {r['article_num']}")
        print(f"TITLE:   {r['article_title']}")
        print(f"CONTENT BREAKDOWN (First 150 chars):")
        print(f"--- START ---\n{r['content_md'][:150]}\n--- END ---")
        print(f"==========================================================\n")

    cur.close()
    conn.close()

if __name__ == "__main__":
    debug_rpc()
