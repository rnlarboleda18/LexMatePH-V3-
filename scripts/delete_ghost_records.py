import os
import psycopg2

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

def delete_ghosts():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()

    try:
        # 1. Identify Ghosts
        # Criteria: Date is NULL AND (Case Number is NULL OR Title is NULL)
        # These are the ones that failed all recovery attempts.
        cur.execute("""
            SELECT id, case_number, short_title 
            FROM sc_decided_cases 
            WHERE date IS NULL 
            AND (case_number IS NULL OR short_title IS NULL)
        """)
        rows = cur.fetchall()
        
        count = len(rows)
        if count == 0:
            print("No ghost records found to delete.")
            return

        print(f"Found {count} ghost records to delete.")
        ids_to_delete = [r[0] for r in rows]
        id_list_str = ", ".join(str(x) for x in ids_to_delete)
        
        # Log IDs just in case
        print(f"Deleting IDs: {id_list_str}")
        
        # 2. Delete
        cur.execute(f"DELETE FROM sc_decided_cases WHERE id IN ({id_list_str})")
        conn.commit()
        
        print(f"Successfully deleted {count} records.")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    delete_ghosts()
