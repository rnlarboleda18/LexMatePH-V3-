
import os
import psycopg

# Config
DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def delete_null_ids():
    print("Connecting to DB...")
    with psycopg.connect(DB_CONNECTION_STRING, autocommit=True) as conn:
        with conn.cursor() as cur:
            print("Checking for records with NULL id...")
            cur.execute("SELECT COUNT(*) FROM sc_decisionsv2 WHERE id IS NULL")
            count = cur.fetchone()[0]
            
            if count > 0:
                print(f"Found {count} records with NULL ID. Deleting...")
                cur.execute("DELETE FROM sc_decisionsv2 WHERE id IS NULL")
                print("Deletion complete.")
            else:
                print("No records with NULL ID found.")

if __name__ == "__main__":
    delete_null_ids()
