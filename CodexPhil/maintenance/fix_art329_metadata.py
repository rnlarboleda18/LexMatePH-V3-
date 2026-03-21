
import psycopg2
import os

def get_db_connection():
    # Use environment variable or fallback for local dev
    conn_str = os.environ.get("DB_CONNECTION_STRING") or "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
    return psycopg2.connect(conn_str)

def fix_article_329():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check current state
        print("Checking current state...")
        cur.execute("""
            SELECT version_id, amendment_id, valid_from 
            FROM article_versions 
            WHERE code_id = (SELECT code_id FROM legal_codes WHERE short_name = 'RPC')
            AND article_number = '329'
            AND valid_to IS NULL
        """)
        row = cur.fetchone()
        if row:
            print(f"Current: {row}")
            
            # Update to correct amendment metadata
            print("Updating to Act No. 3999...")
            cur.execute("""
                UPDATE article_versions
                SET amendment_id = 'Act No. 3999',
                    valid_from = '1932-12-05'
                WHERE version_id = %s
            """, (row[0],))
            
            conn.commit()
            print("Update committed.")
        else:
            print("Article 329 not found.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_article_329()
