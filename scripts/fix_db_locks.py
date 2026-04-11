import psycopg2
import json
import os

with open('api/local.settings.json', 'r') as f:
    conn_string = json.load(f)['Values']['DB_CONNECTION_STRING']

try:
    with psycopg2.connect(conn_string) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            # Terminate all other connections to clear locks on rpc_codal updates
            cur.execute('''
                SELECT pg_terminate_backend(pid) 
                FROM pg_stat_activity 
                WHERE datname = current_database() AND pid <> pg_backend_pid();
            ''')
            print("Successfully cleared all database locks!")
except Exception as e:
    print(f"Error clearing locks: {e}")
