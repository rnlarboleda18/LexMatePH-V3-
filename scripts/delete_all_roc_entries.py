import sys
import os
import psycopg2

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api.db_pool import DB_CONNECTION_STRING

def main():
    print(f"Connecting to DB with: {DB_CONNECTION_STRING}")
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor()
        
        print("Truncating/Deleting all rows from `roc_codal` fully...")
        cur.execute("TRUNCATE TABLE roc_codal")
        # cur.execute("DELETE FROM roc_codal")
        
        conn.commit()
        print("🎉 Successfully cleared `roc_codal` table absolute!")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error executing cleanup: {e}")

if __name__ == "__main__":
    main()
