import os
import psycopg2
import re
from datetime import datetime

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

def aggressive_date_extract():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()

    try:
        # Fetch cases with NULL date but DO have a case number (skip empty ghosts)
        print("Fetching target cases...")
        cur.execute("""
            SELECT id, full_text_md 
            FROM sc_decided_cases 
            WHERE date IS NULL 
            AND case_number IS NOT NULL 
            AND case_number != ''
            AND full_text_md IS NOT NULL 
            ORDER BY id
        """)
        cases = cur.fetchall()
        print(f"Found {len(cases)} candidates.")

        updates = []
        
        # Regex for standard date: Month DD, YYYY
        # (January|February|...) \d{1,2}, \d{4}
        date_pattern = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}", re.IGNORECASE)
        
        # Keywords to boost confidence
        keywords = ["Promulgated", "Decided", "Manila", "Dated", "City"]

        for case_id, text in cases:
            if not text: continue
            
            # Focus on header and footer
            header = text[:1500]
            footer = text[-2000:]
            
            # 1. Look for explicit "Promulgated" pattern first (High Confidence)
            # This handles cases identifying the promulgate date explicitly
            promulgated_match = re.search(r"(?i)(Promulgated|Decided|Dated)[:\s]+.*?((January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})", text)
            
            best_date = None
            
            if promulgated_match:
                best_date = promulgated_match.group(2)
            else:
                # 2. Aggressive Scan in Footer (Highest priority for loose dates)
                # Dates at the end are usually the promulgation/signature date.
                footer_matches = date_pattern.findall(footer)
                if footer_matches:
                    # Search findall returns tuples if groups used, or strings?
                    # With the group (Month), it returns tuples or the full match? 
                    # Let's use finditer for full match objects to be safe.
                    matches = list(date_pattern.finditer(footer))
                    if matches:
                        # Take the LAST date found in the footer
                        best_date = matches[-1].group(0)
                
                # 3. If no footer date, try Header
                if not best_date:
                    matches = list(date_pattern.finditer(header))
                    if matches:
                        # Take the FIRST date found in the header (often "Manila, January 1...")
                        best_date = matches[0].group(0)

            if best_date:
                # Clean up match
                clean_date = best_date.replace('.', '').replace(',', '').strip()
                try:
                    # Normalize to YYYY-MM-DD
                    dt = datetime.strptime(clean_date, "%B %d %Y")
                    iso_date = dt.strftime("%Y-%m-%d")
                    
                    # Basic sanity check: Year between 1900 and 2026
                    if 1900 <= dt.year <= 2026:
                        updates.append((iso_date, case_id))
                        print(f"Case {case_id}: Found '{best_date}' -> {iso_date}")
                    else:
                        print(f"Case {case_id}: Ignored out-of-range date '{clean_date}'")
                except ValueError:
                     # Try %b for abbreviated months if needed, but regex enforced full names mostly
                     pass
            else:
                pass 
                # print(f"Case {case_id}: No date found in header/footer.")

        # Update DB
        if updates:
            print(f"\nUpdating {len(updates)} cases...")
            cur.executemany("""
                UPDATE sc_decided_cases 
                SET date = %s, updated_at = NOW() 
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
    aggressive_date_extract()
