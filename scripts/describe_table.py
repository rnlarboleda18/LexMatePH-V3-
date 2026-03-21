import psycopg2

DB_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def describe_table():
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default 
            FROM information_schema.columns 
            WHERE table_name = 'sc_decided_cases' 
            ORDER BY ordinal_position
        """)
        rows = cur.fetchall()
        
        print(f"Structure of 'sc_decided_cases' ({len(rows)} columns):")
        print(f"{'Column':<25} {'Type':<20} {'Nullable':<10} {'Default'}")
        print("-" * 70)
        
        for r in rows:
            default_val = r[3] if r[3] else "NULL"
            if len(default_val) > 20: default_val = default_val[:17] + "..."
            print(f"{r[0]:<25} {r[1]:<20} {r[2]:<10} {default_val}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    describe_table()
