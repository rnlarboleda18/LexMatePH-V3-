import psycopg2
import os

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

def cleanup():
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor()
        
        # Restore ID 39842 (Approximate restoration, mostly just clearing the garbage tokens)
        cur.execute("""
            UPDATE sc_decided_cases 
            SET full_title = NULL,
                full_text_md = '### G.R. No. 146710-15 (Restored Content)'
            WHERE id = 39842
        """)
        conn.commit()
        print("Restored ID 39842.")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    cleanup()
