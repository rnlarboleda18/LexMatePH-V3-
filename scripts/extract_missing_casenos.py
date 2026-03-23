import os
import psycopg2
import re

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

def extract_casenos():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()

    try:
        # Get target cases
        cur.execute("""
            SELECT id, full_text_md 
            FROM sc_decided_cases 
            WHERE case_number IS NULL OR case_number = ''
        """)
        rows = cur.fetchall()
        print(f"Scanning {len(rows)} cases...")
        
        updates = []
        
        # Regex for various case number formats
        # G.R. No. | A.M. No. | B.M. No. | A.C. No. | UDK | I.P.I. No.
        # Capture: Type + Number
        # ex: "A.M. No. R-218-MTJ", "G.R. No. L-45213"
        pattern = re.compile(r"(G\.R\.|A\.M\.|B\.M\.|A\.C\.|U\.D\.K\.|OCA\s+I\.P\.I\.)\s*(No\.)?\s*([A-Za-z0-9\-]+)", re.IGNORECASE)
        
        for r in rows:
            case_id, text = r
            if not text: continue
            
            # Scan header (first 2000 chars)
            header = text[:2000]
            
            match = pattern.search(header)
            if match:
                # Construct clean case number
                # Group 1: Type (G.R., A.M.)
                # Group 2: "No." (optional)
                # Group 3: The Number
                
                raw_type = match.group(1).replace(" ", "").upper()
                raw_num = match.group(3)
                
                # Format: "Type No. Number"
                # Standardize known types
                if "G.R." in raw_type: prefix = "G.R. No."
                elif "A.M." in raw_type: prefix = "A.M. No."
                elif "B.M." in raw_type: prefix = "B.M. No."
                elif "A.C." in raw_type: prefix = "A.C. No."
                elif "U.D.K." in raw_type: prefix = "UDK No."
                else: prefix = raw_type + " No. " 

                case_no = f"{prefix} {raw_num}"
                
                print(f"ID {case_id}: Found '{case_no}'")
                updates.append((case_no, case_id))

        if updates:
            print(f"Updating {len(updates)} cases...")
            cur.executemany("UPDATE sc_decided_cases SET case_number = %s WHERE id = %s", updates)
            conn.commit()
            print("Done.")
        else:
            print("No case numbers found.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    extract_casenos()
