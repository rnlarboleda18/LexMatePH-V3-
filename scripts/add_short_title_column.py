import psycopg2

CONN_STR = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def add_column():
    try:
        conn = psycopg2.connect(CONN_STR)
        cur = conn.cursor()
        
        print("Checking if 'short_title' column exists...")
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='supreme_decisions' AND column_name='short_title';
        """)
        row = cur.fetchone()
        
        # NOTE: 'short_title' might have existed from original schema but not used correctly or we want to ensure it is TEXT
        # My recall says it WAS in schema. Let's verify.
        if row:
            print("Column 'short_title' already exists.")
        else:
            print("Adding 'short_title' column...")
            cur.execute("ALTER TABLE supreme_decisions ADD COLUMN short_title TEXT;")
            conn.commit()
            print("Column added successfully.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_column()
