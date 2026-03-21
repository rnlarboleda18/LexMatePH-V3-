import psycopg2
import json

def get_db_connection():
    with open('local.settings.json') as f:
        settings = json.load(f)
        conn_str = settings['Values']['DB_CONNECTION_STRING']
    return psycopg2.connect(conn_str)

def delete_junk_case():
    conn = get_db_connection()
    cur = conn.cursor()
    
    case_id = 34338
    print(f"Deleting junk case {case_id}...")
    
    cur.execute("DELETE FROM sc_decided_cases WHERE id = %s", (case_id,))
    conn.commit()
    
    print("Deletion complete.")
    conn.close()

if __name__ == "__main__":
    delete_junk_case()
