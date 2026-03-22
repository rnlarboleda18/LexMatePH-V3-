import os
import psycopg
import logging

def drop_mock_tables():
    conn_string = os.environ.get("DB_CONNECTION_STRING")
    if not conn_string:
        # Check local.settings.json
        import json
        try:
            with open('local.settings.json', 'r') as f:
                settings = json.load(f)
                conn_string = settings.get('Values', {}).get('DB_CONNECTION_STRING')
        except Exception as e:
            print(f"Could not read local.settings.json: {e}")
            
    if not conn_string:
        print("Error: DB_CONNECTION_STRING not found.")
        return

    try:
        print("Connecting to database...")
        with psycopg.connect(conn_string) as conn:
            with conn.cursor() as cur:
                print("Dropping table user_mock_scores...")
                cur.execute("DROP TABLE IF EXISTS user_mock_scores CASCADE;")
                conn.commit()
                print("Successfully dropped user_mock_scores.")
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    drop_mock_tables()
