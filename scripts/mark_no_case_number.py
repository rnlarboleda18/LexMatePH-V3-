import os
import psycopg2

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

IDS_TO_UPDATE = [
    3114, 3115, 4418, 4619, 4620, 4621, 4622, 4623, 4743, 4964, 4965, 4966, 4967, 4968, 5125, 5127,
    6047, 6261, 6464, 6613, 6614, 6615, 6616, 6765, 6768, 7003, 7005, 7006, 7007, 7008, 7009, 7254, 7255,
    9482, 9486, 10105, 11604, 13791, 21248, 21660, 22277, 22525, 26069,
    23056, 24855, 28632
]

def update_historical_cases():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    try:
        # Check counts before
        cur.execute("SELECT count(*) FROM sc_decided_cases WHERE id = ANY(%s) AND case_number IS NULL", (IDS_TO_UPDATE,))
        print(f"Cases targeted that are currently NULL: {cur.fetchone()[0]}")

        cur.execute("UPDATE sc_decided_cases SET case_number = 'NO KNOWN CASE NUMBER' WHERE id = ANY(%s)", (IDS_TO_UPDATE,))
        updated_count = cur.rowcount
        conn.commit()
        print(f"Successfully updated {updated_count} cases to 'NO KNOWN CASE NUMBER'.")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    update_historical_cases()
