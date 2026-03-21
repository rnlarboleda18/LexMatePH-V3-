import psycopg2
import os

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:6432/postgres?sslmode=require"

def main():
    print("Deleting Garbage & Incomplete Records...")
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    try:
        # 1. Count targets
        query_garbage = "SELECT COUNT(*) FROM sc_decided_cases WHERE digest_significance = 'GARBAGE'"
        cur.execute(query_garbage)
        count_garbage = cur.fetchone()[0]

        query_incomplete = "SELECT COUNT(*) FROM sc_decided_cases WHERE (case_number IS NULL OR date IS NULL) AND (digest_significance != 'GARBAGE' OR digest_significance IS NULL)"
        cur.execute(query_incomplete)
        count_incomplete = cur.fetchone()[0]
        
        total_to_delete = count_garbage + count_incomplete
        
        print(f"Targeting for Deletion:")
        print(f"- Marked Garbage: {count_garbage}")
        print(f"- Remaining Incomplete (NULL Metadata): {count_incomplete}")
        print(f"- Total: {total_to_delete}")
        
        # 2. Execute Deletion
        # Note: We delete anything marked 'GARBAGE' OR anything with missing metadata.
        delete_sql = """
            DELETE FROM sc_decided_cases 
            WHERE digest_significance = 'GARBAGE' 
               OR (case_number IS NULL OR date IS NULL)
        """
        
        cur.execute(delete_sql)
        deleted_count = cur.rowcount
        conn.commit()
        
        print(f"\nSuccessfully Deleted: {deleted_count} rows.")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
