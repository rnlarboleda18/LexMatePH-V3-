import psycopg2

CLOUD_DB = "postgresql://bar_admin:RABpass021819!@bar-db-eu-west.postgres.database.azure.com:5432/postgres?sslmode=require"

def inspect_cloud():
    try:
        print("Connecting to CLOUD DB...")
        conn = psycopg2.connect(CLOUD_DB)
        cur = conn.cursor()

        # 1. Get Column names
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'roc_codal'
            ORDER BY ordinal_position
        """)
        cols = cur.fetchall()
        print("\nColumns in cloud roc_codal:")
        for col in cols:
            print(f"  {col[0]} ({col[1]})")

        # 2. Check row count
        cur.execute("SELECT count(*) FROM roc_codal")
        count = cur.fetchone()[0]
        print(f"\nTotal rows in cloud roc_codal: {count}")

        # 3. Inspect a sample row
        if count > 0:
            cur.execute("SELECT * FROM roc_codal LIMIT 1")
            colnames = [desc[0] for desc in cur.description]
            row = cur.fetchone()
            print("\nSample Row Content:")
            row_dict = dict(zip(colnames, row))
            for k, v in row_dict.items():
                val_str = str(v)
                if len(val_str) > 100:
                    val_str = val_str[:100] + "..."
                print(f"  {k}: {val_str}")
        else:
            print("\nTable is empty on cloud.")

        conn.close()
    except Exception as e:
        print(f"Error connecting to cloud DB: {e}")

if __name__ == "__main__":
    inspect_cloud()
