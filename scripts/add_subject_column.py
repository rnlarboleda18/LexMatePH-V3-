import psycopg2

CONN_STR = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def add_column():
    try:
        conn = psycopg2.connect(CONN_STR)
        cur = conn.cursor()
        
        print("Checking if 'subject' column exists...")
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='supreme_decisions' AND column_name='subject';
        """)
        if cur.fetchone():
            print("Column 'subject' already exists.")
        else:
            print("Adding 'subject' column...")
            cur.execute("ALTER TABLE supreme_decisions ADD COLUMN subject TEXT;")
            conn.commit()
            print("Column added successfully.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_column()
