
import psycopg2
import os
import sys
import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

def get_db_connection():
    conn_str = os.environ.get("DB_CONNECTION_STRING") or "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
    return psycopg2.connect(conn_str)

def list_amended_articles():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            WITH Amplitudes AS (
                SELECT article_number FROM article_versions GROUP BY article_number HAVING COUNT(*) > 1
            )
            SELECT av.article_number, av.amendment_id 
            FROM article_versions av 
            JOIN Amplitudes a ON av.article_number = a.article_number 
            WHERE av.valid_to IS NULL 
            ORDER BY av.article_number::int
        """
        
        cur.execute(query)
        rows = cur.fetchall()
        
        print("\n=== CURRENTLY AMENDED ARTICLES ===")
        for r in rows:
            print(f"Article {r[0]}: '{r[1]}'")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_amended_articles()
