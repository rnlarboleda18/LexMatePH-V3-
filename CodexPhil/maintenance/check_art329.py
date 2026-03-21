
import psycopg2
import json
import os

def get_db_connection():
    # Use environment variable or fallback for local dev
    conn_str = os.environ.get("DB_CONNECTION_STRING") or "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
    return psycopg2.connect(conn_str)

def check_article_329():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT version_id, content, valid_from, valid_to, amendment_id
            FROM article_versions
            WHERE code_id = (SELECT code_id FROM legal_codes WHERE short_name = 'RPC')
            AND article_number = '329'
            ORDER BY valid_from DESC
        """
        
        cur.execute(query)
        rows = cur.fetchall()
        
        print("\n=== ARTICLE 329 HISTORY ===")
        for row in rows:
            print(f"\n[Version ID: {row[0]}]")
            print(f"Valid From: {row[2]}")
            print(f"Valid To: {row[3]}")
            print(f"Amendment ID: {row[4]}")
            print("-" * 40)
            print(row[1])
            print("-" * 40)
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_article_329()
