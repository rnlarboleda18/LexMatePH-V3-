import psycopg2
import os

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def main():
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor()
        
        # Check if column exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'sc_decided_cases' AND column_name = 'ai_model';
        """)
        
        if cur.fetchone():
            print("Column 'ai_model' already exists.")
        else:
            print("Adding 'ai_model' column...")
            cur.execute("ALTER TABLE sc_decided_cases ADD COLUMN ai_model VARCHAR(50);")
            conn.commit()
            print("Success.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
