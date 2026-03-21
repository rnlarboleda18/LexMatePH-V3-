import psycopg2
import os

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def add_column():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    try:
        print("Checking for full_text_html column...")
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='supreme_decisions' AND column_name='full_text_html';
        """)
        if not cur.fetchone():
            print("Adding full_text_html column...")
            cur.execute("ALTER TABLE supreme_decisions ADD COLUMN full_text_html TEXT;")
            conn.commit()
            print("Column added.")
        else:
            print("Column already exists.")
            
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    add_column()
