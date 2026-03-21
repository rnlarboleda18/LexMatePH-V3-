import psycopg2
import os

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def cleanup():
    target_case = "G.R. No. 176951"
    keep_id = 50444
    
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    print(f"Cleaning up duplicates for {target_case}...")
    
    # 1. Verify duplicates
    cur.execute("SELECT id, digest_significance FROM supreme_decisions WHERE case_number = %s", (target_case,))
    rows = cur.fetchall()
    print(f"Found {len(rows)} rows.")
    for r in rows:
        print(f"ID: {r[0]} | SigLen: {len(r[1] or '')}")
        
    # 2. Delete garbage
    # We want to delete everything EXCEPT 50444
    ids_to_delete = [r[0] for r in rows if r[0] != keep_id]
    
    if ids_to_delete:
        print(f"Deleting IDs: {ids_to_delete}")
        # Tuple syntax for SQL IN clause handles single item correctly e.g. (1,)
        cur.execute("DELETE FROM supreme_decisions WHERE id IN %s", (tuple(ids_to_delete),))
        print(f"Deleted {cur.rowcount} rows.")
        conn.commit()
    else:
        print("No duplicates to delete.")
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    cleanup()
