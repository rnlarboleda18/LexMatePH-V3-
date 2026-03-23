import os
import psycopg2
import re

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

def populate_titles():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()

    try:
        # Fetch target cases
        print("Fetching cases with NULL title...")
        cur.execute("""
            SELECT id, full_text_md 
            FROM sc_decided_cases 
            WHERE full_title IS NULL 
            AND full_text_md IS NOT NULL 
            ORDER BY id
        """)
        cases = cur.fetchall()
        print(f"Found {len(cases)} cases.")
        
        updates = []
        
        # Regex to capture title block
        # Look for [Date] ... text ... [Decision/Judge]
        # Or look for "Petitioner" / "Respondent" lines
        
        # Pattern:
        # 1. Start line: Usually follows G.R. No. or Date
        # 2. End line: Often "D E C I S I O N", "R E S O L U T I O N", or Judge Name (**NAME, J.:**)
        
        # We'll use a scanning approach per case
        
        for case_id, text in cases:
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            
            title_lines = []
            capturing = False
            has_parties = False
            
            # Simple Heuristic:
            # - Skip initial headers (EN BANC, G.R. No...)
            # - Capture lines until we hit a "Decision" marker or Judge Name
            # - Must contain "Petitioner" or "Respondent" or "Plaintiff" or "Accused" to be valid
            
            headers_seen = False
            
            for line in lines[:50]: # Look only in first 50 lines
                
                # Check for start (after G.R. No)
                if "G.R. No." in line or "A.M. No." in line:
                    headers_seen = True
                    continue
                
                if not headers_seen:
                    # heuristic: first few lines might be court division ("EN BANC") text
                    # if we see petitioner here, assume header was missing or implicit
                     if "vs." in line.lower() or "petitioner" in line.lower():
                         headers_seen = True # Start capturing immediately
                     else:
                         continue

                # Stop markers
                if re.match(r"(?i)^(D\s?E\s?C\s?I\s?S\s?I\s?O\s?N|R\s?E\s?S\s?O\s?L\s?U\s?T\s?I\s?O\s?N|SYLLABUS|.*, J\.:|.*, J\*\*:)", line):
                    break
                
                # Valid title content check
                # Exclude purely metadata lines?
                if "petitioner" in line.lower() or "respondent" in line.lower() or \
                   "plaintiff" in line.lower() or "accused" in line.lower() or \
                   "complainant" in line.lower() or "vs." in line.lower():
                    has_parties = True
                    
                # Clean specific markdown chars
                clean_line = line.replace('**', '').replace('###', '').strip()
                title_lines.append(clean_line)

            if title_lines and has_parties:
                # remove "vs." standalone line if present to merge? 
                # actually just joining by space is usually okay, or space-dash-space
                full_title = " ".join(title_lines)
                # Cleanup excess whitespace
                full_title = re.sub(r'\s+', ' ', full_title).strip()
                
                # Limit length
                if len(full_title) > 2000:
                    full_title = full_title[:2000]
                
                updates.append((full_title, case_id))

        if updates:
            print(f"Prepared {len(updates)} updates. Writing to DB...")
            # Use execute_values or executemany
            # Batch in 1000s
            batch_size = 1000
            for i in range(0, len(updates), batch_size):
                batch = updates[i:i+batch_size]
                cur.executemany("UPDATE sc_decided_cases SET full_title = %s WHERE id = %s", batch)
                conn.commit()
                print(f"Committed batch {i//batch_size + 1}")
                
            print("Completed.")
        else:
            print("No updates found.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    populate_titles()
