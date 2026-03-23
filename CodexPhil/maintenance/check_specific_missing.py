
import psycopg2
import os
import sys
import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

def get_db_connection():
    conn_str = os.environ.get("DB_CONNECTION_STRING") or "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
    return psycopg2.connect(conn_str)

def check_missing_amendments():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        articles = ['48', '9', '190']
        print("\n=== CHECKING SPECIFIC ARTICLES ===")
        
        for art in articles:
            print(f"\nChecking Article {art}:")
            cur.execute("""
                SELECT version_id, amendment_id, valid_from, valid_to 
                FROM article_versions 
                WHERE code_id = (SELECT code_id FROM legal_codes WHERE short_name = 'RPC')
                AND article_number = %s
                ORDER BY valid_from DESC
            """, (art,))
            rows = cur.fetchall()
            
            if not rows:
                print("  [X] Article not found")
            else:
                for row in rows:
                    print(f"  Version: {row[0]}")
                    print(f"    Amendment: {row[1]}")
                    print(f"    Valid: {row[2]} to {row[3]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_missing_amendments()
