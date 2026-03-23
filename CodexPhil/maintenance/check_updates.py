
import os
import json
import psycopg2

def get_db_connection():
    try:
        settings_path = 'local.settings.json'
        if not os.path.exists(settings_path):
             settings_path = '../local.settings.json'
        if not os.path.exists(settings_path):
             settings_path = 'c:/Users/rnlar/.gemini/antigravity/scratch/bar_project_v2/local.settings.json'
             
        if os.path.exists(settings_path):
            with open(settings_path) as f:
                settings = json.load(f)
                conn_str = settings['Values']['DB_CONNECTION_STRING']
                return conn_str
    except Exception:
        pass
    
    return "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@127.0.0.1:5432/lexmateph-ea-db"

def check_updates():
    db_conn_string = get_db_connection()
    conn_string = db_conn_string.replace("localhost", "127.0.0.1")

    try:
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()

        print("Checking Progress of Applied Amendments...")
        cursor.execute("""
            SELECT amendment_id, COUNT(*) as articles, MIN(valid_from) as applied_date
            FROM article_versions
            WHERE amendment_id IS NOT NULL
            GROUP BY amendment_id
            ORDER BY applied_date DESC
        """)
        
        rows = cursor.fetchall()
        print(f"Total Amendments Applied: {len(rows)}")
        for row in rows:
            print(f"- {row[0]} ({row[1]} articles) - {row[2]}")
            
        print("\nChecking Article 266-A and 266-B:")
        cursor.execute("SELECT article_number FROM article_versions WHERE article_number IN ('266-A', '266-B')")
        found = [row[0] for row in cursor.fetchall()]
        print(f"Found Articles: {found}")
            
        print("\nChecking RA 10951:")
        cursor.execute("SELECT COUNT(*) FROM article_versions WHERE amendment_id LIKE '%10951%'")
        res = cursor.fetchone()
        print(f"RA 10951 Articles: {res[0]}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
             conn.close()

if __name__ == "__main__":
    check_updates()
