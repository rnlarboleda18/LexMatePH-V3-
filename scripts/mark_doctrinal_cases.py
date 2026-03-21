import re
import psycopg2
import os

INPUT_FILE = r'C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\doctrinal_cases_full_list.txt'
DB_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def normalize_gr(gr):
    """
    Normalize G.R. No. for comparison.
    Example: "G.R. No. 12345" -> "12345"
            "G.R. No. L-12345" -> "L-12345"
            "A.C. No. 123" -> "AC123" (Let's stick to simple stripped version)
    """
    if not gr: return ""
    # Remove common prefixes and whitespace
    clean = gr.upper().replace(".", "").replace(" ", "")
    clean = clean.replace("GRNO", "").replace("GR", "")
    clean = clean.replace("ACNO", "").replace("AC", "")
    clean = clean.replace("AMNO", "").replace("AM", "")
    clean = clean.replace("BMNO", "").replace("BM", "")
    return clean.strip()

def extract_case_numbers(text):
    """
    Extracts case numbers from text content.
    Looks for patterns like G.R. No. 12345, G.R. 12345, A.C. No. 123, etc.
    """
    # Pattern to catch G.R., A.C., A.M., B.M. followed by optional No. and digits/letters
    # Handles ranges like 123-125
    pattern = r'(?:G\.R\.|A\.C\.|A\.M\.|B\.M\.|UDK)[.\s]*No\.?\s*([L\d\-]+)'
    matches = re.findall(pattern, text, re.IGNORECASE)
    
    # Also catch "G.R. 12345" without "No."
    pattern2 = r'(?:G\.R\.|A\.C\.|A\.M\.|B\.M\.|UDK)\s+([L\d\-]+)'
    matches2 = re.findall(pattern2, text, re.IGNORECASE)
    
    return list(set(matches + matches2))

def mark_doctrinal():
    if not os.path.exists(INPUT_FILE):
        print(f"File not found: {INPUT_FILE}")
        return

    print(f"Reading {INPUT_FILE}...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract all case numbers found in the file
    case_numbers = extract_case_numbers(content)
    print(f"Found {len(case_numbers)} potential case IDs in the text file.")
    
    # Normalize them for matching
    normalized_targets = set(normalize_gr(c) for c in case_numbers)
    
    print("Connecting to database...")
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor()
        
        # Reset current flags (optional, if we want a fresh start)
        # cur.execute("UPDATE sc_decided_cases SET is_doctrinal = FALSE") 
        
        # We need to fetch all case numbers from DB to match against
        print("Fetching existing cases from DB...")
        cur.execute("SELECT id, case_number, title FROM sc_decided_cases WHERE case_number IS NOT NULL")
        db_cases = cur.fetchall()
        
        matched_ids = []
        
        for db_id, db_case_no, db_title in db_cases:
            # Normalize DB case number
            # db_case_no often looks like "G.R. No. 12345"
            # matched against our normalized list "12345"
            
            # We iterate parts because db_case_no might be "G.R. No. 12345, G.R. No. 12346"
            # split by comma or semi-colon
            parts = re.split(r'[;,]', db_case_no)
            for p in parts:
                norm = normalize_gr(p)
                if norm in normalized_targets:
                    matched_ids.append(db_id)
                    break
        
        print(f"Matched {len(matched_ids)} cases in the PostgreSQL database.")
        
        if matched_ids:
            # Batch update
            print("Updating database...")
            # Convert list to tuple for SQL IN clause
            # Process in chunks to avoid query size limits if list is huge
            chunk_size = 1000
            for i in range(0, len(matched_ids), chunk_size):
                chunk = tuple(matched_ids[i:i+chunk_size])
                cur.execute(f"UPDATE sc_decided_cases SET is_doctrinal = TRUE WHERE id IN %s", (chunk,))
            
            conn.commit()
            print("Update complete.")
            
            # Verification
            cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE is_doctrinal = TRUE")
            count = cur.fetchone()[0]
            print(f"Total Doctrinal Cases in DB now: {count}")
            
        else:
            print("No matches found to update.")

        conn.close()
        
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    mark_doctrinal()
