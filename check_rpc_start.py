import psycopg
import json
import os

def check_rpc():
    try:
        with open('api/local.settings.json', 'r') as f:
            settings = json.load(f)
        conn_str = settings['Values']['DB_CONNECTION_STRING']
    except Exception as e:
        print(f"Error loading settings: {e}")
        return

    try:
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                # Check for rpc_codal starting rows
                cur.execute("SELECT id, article_num, article_title FROM rpc_codal ORDER BY id ASC LIMIT 5")
                rows = cur.fetchall()
                print("First 5 RPC rows (by ID):")
                for r in rows:
                    print(r)
                
                # Check if '0' or 'PREAMBLE' exists as article_num
                cur.execute("SELECT article_num FROM rpc_codal WHERE article_num IN ('0', 'PREAMBLE', 'Article 0')")
                exists = cur.fetchall()
                print(f"Direct Article 0/Preamble matches: {exists}")
                
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == '__main__':
    check_rpc()
