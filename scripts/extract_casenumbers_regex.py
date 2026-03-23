import os
import psycopg2
import re

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

def extract_case_numbers():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()

    try:
        print("Fetching cases with case_number = 'REDIGEST'...")
        cur.execute("""
            SELECT id, full_text_md 
            FROM sc_decided_cases 
            WHERE case_number = 'REDIGEST'
            AND full_text_md IS NOT NULL 
            AND full_text_md != ''
        """)
        cases = cur.fetchall()
        print(f"Found {len(cases)} cases to process.")

        updates = []
        
        # Regex for G.R. Number
        # Matches: G.R. No. 12345, G.R. No. 12345-67
        gr_pattern = re.compile(r"G\.?R\.? No\.?\s*(\d+(?:[\d\-\w]+)?)", re.IGNORECASE)

        for case_id, text in cases:
            # Look in the first 2000 chars
            header_text = text[:2000]
            
            match = gr_pattern.search(header_text)
            if match:
                raw_num = match.group(1)
                # Format standard: G.R. No. XXXXX
                new_case_no = f"G.R. No. {raw_num}"
                updates.append((new_case_no, case_id))
                print(f"Case {case_id}: Found {new_case_no}")
            else:
                print(f"Case {case_id}: No G.R. No. found.")

        # Update DB
        if updates:
            print(f"\nUpdating {len(updates)} cases...")
            cur.executemany("""
                UPDATE sc_decided_cases 
                SET case_number = %s, updated_at = NOW() 
                WHERE id = %s
            """, updates)
            conn.commit()
            print("Updates committed.")
        else:
            print("No updates found.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    extract_case_numbers()
