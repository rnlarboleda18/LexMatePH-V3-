import psycopg2
import json

def test_remote():
    try:
        with open('api/local.settings.json') as f:
            settings = json.load(f)
            conn_str = settings['Values']['DB_CONNECTION_STRING']
        
        print(f"Connecting to: {conn_str.split('@')[1]}") # Print host without password
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()
        
        cur.execute("SELECT 1")
        print("Connection successful!")
        
        cur.execute("SELECT COUNT(*) FROM legal_codes")
        count = cur.fetchone()[0]
        print(f"Total legal codes: {count}")
        
        cur.execute("SELECT * FROM legal_codes WHERE short_name = 'ROC'")
        row = cur.fetchone()
        if row:
             print("ROC Found in Remote DB!")
        else:
             print("ROC NOT Found in Remote DB (as expected).")

    except Exception as e:
        print(f"Connection failed: {e}")
    finally:
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    test_remote()
