
import psycopg2
import json
import os

def get_db_connection():
    # Use the same logic as the main apps
    with open('api/local.settings.json') as f:
        settings = json.load(f)
        conn_str = settings['Values']['DB_CONNECTION_STRING']
    return psycopg2.connect(conn_str)

def check_articles():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Check for Article 114
        print("Checking Article 114:")
        cur.execute("SELECT id, article_num, article_title FROM rpc_codal WHERE article_num = '114' OR article_num LIKE '%114%'")
        rows = cur.fetchall()
        for r in rows:
            print(f"  ID: {r[0]}, Num: {r[1]}, Title: {r[2]}")
        if not rows:
            print("  [!] NOT FOUND")

        # Check for Article 122
        print("\nChecking Article 122:")
        cur.execute("SELECT id, article_num, article_title FROM rpc_codal WHERE article_num = '122' OR article_num LIKE '%122%'")
        rows = cur.fetchall()
        for r in rows:
            print(f"  ID: {r[0]}, Num: {r[1]}, Title: {r[2]}")
        if not rows:
            print("  [!] NOT FOUND")
            
    finally:
        conn.close()

if __name__ == "__main__":
    check_articles()
