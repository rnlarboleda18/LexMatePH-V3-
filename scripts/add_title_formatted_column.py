import psycopg2
import os

CONN_STR = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def add_column():
    print("Adding title_formatted column...")
    try:
        conn = psycopg2.connect(CONN_STR)
        cur = conn.cursor()
        
        cur.execute("""
            ALTER TABLE supreme_decisions 
            ADD COLUMN IF NOT EXISTS title_formatted BOOLEAN DEFAULT FALSE;
        """)
        
        # Create index for faster searching
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_supreme_decisions_title_formatted 
            ON supreme_decisions(title_formatted) 
            WHERE title_formatted = FALSE;
        """)
        
        conn.commit()
        print("Column added successfully.")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_column()
