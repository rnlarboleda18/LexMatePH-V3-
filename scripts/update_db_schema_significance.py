import psycopg2
import os

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def migrate():
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor()
        
        print("Adding 'significance_category' column...")
        cur.execute("""
            ALTER TABLE supreme_decisions 
            ADD COLUMN IF NOT EXISTS significance_category TEXT;
        """)
        
        print("Adding 'secondary_rulings' column...")
        cur.execute("""
            ALTER TABLE supreme_decisions 
            ADD COLUMN IF NOT EXISTS secondary_rulings JSONB;
        """)
        
        conn.commit()
        print("Migration successful columns added.")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
