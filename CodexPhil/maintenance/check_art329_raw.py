
import psycopg2
import os
import sys

# Windows console encoding fix
import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

def get_db_connection():
    # Use environment variable or fallback for local dev
    conn_str = os.environ.get("DB_CONNECTION_STRING") or "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
    return psycopg2.connect(conn_str)

def check_article_329():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT content
            FROM article_versions
            WHERE code_id = (SELECT code_id FROM legal_codes WHERE short_name = 'RPC')
            AND article_number = '329'
            ORDER BY valid_from DESC
            LIMIT 1
        """
        
        cur.execute(query)
        row = cur.fetchone()
        
        if row:
            print(f"RAW REPR: {repr(row[0])}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_article_329()
