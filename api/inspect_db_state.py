import psycopg2
import json
from psycopg2.extras import RealDictCursor

def get_db_connection():
    try:
        with open('local.settings.json') as f:
            settings = json.load(f)
            conn_str = settings['Values']['DB_CONNECTION_STRING']
    except Exception:
        conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
    return psycopg2.connect(conn_str)

def inspect_db():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        print("--- legal_codes ---")
        cur.execute("SELECT * FROM legal_codes")
        rows = cur.fetchall()
        for r in rows:
            print(f"ID: {r['code_id']}, Short: {r['short_name']}, Full: {r['full_name']}")

        print("\n--- Count of articles ---")
        cur.execute("SELECT COUNT(*) FROM roc_codal")
        count = cur.fetchone()['count']
        print(f"roc_codal count: {count}")

        cur.execute("SELECT COUNT(*) FROM article_versions")
        count_av = cur.fetchone()['count']
        print(f"article_versions count (All): {count_av}")

        # Check if any article version mapped to ROC
        cur.execute("SELECT COUNT(*) FROM article_versions av JOIN legal_codes lc ON av.code_id = lc.code_id WHERE lc.short_name = 'ROC'")
        count_roc_av = cur.fetchone()['count']
        print(f"article_versions for ROC: {count_roc_av}")

    except Exception as e:
         print(f"Error: {e}")
    finally:
         conn.close()

if __name__ == "__main__":
    inspect_db()
