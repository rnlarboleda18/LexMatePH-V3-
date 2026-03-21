import psycopg2
import os

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def apply_constraint():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    print("Step 1: finding duplicates based on (case_number, date)...")
    # Identify groups of duplicates
    cur.execute("""
        SELECT case_number, date, COUNT(*) 
        FROM supreme_decisions 
        GROUP BY case_number, date
        HAVING COUNT(*) > 1;
    """)
    dupe_groups = cur.fetchall()
    print(f"Found {len(dupe_groups)} groups of duplicates.")
    
    for case_num, date_val, count in dupe_groups:
        print(f"Resolving {case_num} ({date_val}) - {count} copies...")
        
        # Fetch IDs for this group, prioritized by content length (keep the 'best' one)
        cur.execute("""
            SELECT id, length(coalesce(raw_content, '')) as len
            FROM supreme_decisions
            WHERE case_number = %s AND date = %s
            ORDER BY len DESC, id DESC
        """, (case_num, date_val))
        
        rows = cur.fetchall()
        
        # Keep the first one (longest content, or latest ID if tied)
        keep_id = rows[0][0]
        delete_ids = [r[0] for r in rows[1:]]
        
        if delete_ids:
            cur.execute("DELETE FROM supreme_decisions WHERE id IN %s", (tuple(delete_ids),))
            print(f"  > Kept ID {keep_id}, Deleted IDs {delete_ids}")
            
    conn.commit()
    print("Step 2: Cleaned up duplicates. Applying UNIQUE CONSTRAINT...")
    
    try:
        cur.execute("""
            ALTER TABLE supreme_decisions 
            ADD CONSTRAINT unique_case_date UNIQUE (case_number, date);
        """)
        conn.commit()
        print("SUCCESS: Constraint 'unique_case_date' added.")
    except Exception as e:
        print(f"FAILED to add constraint: {e}")
        conn.rollback()

    cur.close()
    conn.close()

if __name__ == "__main__":
    apply_constraint()
