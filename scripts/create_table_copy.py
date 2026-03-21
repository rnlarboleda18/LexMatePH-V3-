import psycopg2
import sys

DB_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def duplicate_table():
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Check if source exists
        cur.execute("SELECT to_regclass('public.sc_decisions')")
        if not cur.fetchone()[0]:
            print("Error: Source table 'sc_decisions' does not exist.")
            # Fallback check or just exit? User asked for sc_decisions.
            return

        # Check if target exists
        cur.execute("SELECT to_regclass('public.sc_decided_cases')")
        if cur.fetchone()[0]:
            print("Target table 'sc_decided_cases' already exists. Dropping it to recreate...")
            cur.execute("DROP TABLE sc_decided_cases")

        print("Creating table copy...")
        # INCLUDING ALL copies defaults, constraints, indexes, comments, storage parameters
        cur.execute("""
            CREATE TABLE sc_decided_cases (
                LIKE sc_decisions INCLUDING ALL
            )
        """)
        
        print("Success! Table 'sc_decided_cases' created.")
        
        # Verify
        cur.execute("""
            SELECT count(*) FROM sc_decided_cases
        """)
        count = cur.fetchone()[0]
        print(f"Row count in new table: {count} (Should be 0)")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    duplicate_table()
