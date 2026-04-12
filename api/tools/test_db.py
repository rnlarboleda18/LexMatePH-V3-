import os
import psycopg
conn_string = os.environ.get('DB_CONNECTION_STRING', 'postgresql://postgres:postgres@localhost:5432/postgres')
try:
    with psycopg.connect(conn_string) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'playlist_items';")
            rows = cur.fetchall()
            if not rows:
                print("Table 'playlist_items' DOES NOT EXIST")
            else:
                for r in rows:
                    print(f"{r[0]}: {r[1]}")
except Exception as e:
    print(f"Error: {e}")
