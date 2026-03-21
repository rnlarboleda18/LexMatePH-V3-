import psycopg2
import re

DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

def audit():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    # Target anything that isn't a proper case number
    cur.execute("""
        SELECT id, length(full_text_md), full_text_md, case_number 
        FROM sc_decided_cases 
        WHERE case_number IS NULL 
           OR case_number IN ('LEGIT_RESCUE_FAILED', 'UNKNOWN_INVALID_DATE', 'UNKNOWN_AI_FAILED')
    """)
    rows = cur.fetchall()
    
    legit_cases = []
    junk_cases = []
    
    for rid, length, text, current_status in rows:
        if not text or length < 200:
            junk_cases.append((rid, length, "Too Short/Empty"))
            continue
            
        # Markers for a real Philippine SC case
        markers = {
            "G.R. No": r"G\.?R\.?\s*No\.?\s*\d+",
            "Resolution/Decision": r"D\s*E\s*C\s*I\s*S\s*I\s*O\s*N|R\s*E\s*S\s*O\s*L\s*U\s*T\s*I\s*O\s*N",
            "Justice Name": r"J\s*U\s*S\s*T\s*I\s*C\s*E",
            "Petitioner/Respondent": r"vs\.?|v\.?|Petitioner|Respondent",
            "Date": r"January|February|March|April|May|June|July|August|September|October|November|December.*\d{4}"
        }
        
        found = []
        for name, pattern in markers.items():
            if re.search(pattern, text, re.IGNORECASE):
                found.append(name)
        
        if len(found) >= 2 or length > 5000:
            legit_cases.append((rid, length, ", ".join(found)))
        else:
            junk_cases.append((rid, length, "No Case Markers Found"))

    with open("final_legitimacy_report.txt", "w", encoding="utf-8") as f:
        f.write("=== LEGITIMATE CASES (VALID TEXT BUT AI FAILED METADATA) ===\n")
        for rid, length, reason in legit_cases:
            f.write(f"ID: {rid} | Len: {length} | Evidence: {reason}\n")
            
        f.write("\n=== JUNK / FRAGMENT CASES (NO REAL CONTENT) ===\n")
        for rid, length, reason in junk_cases:
            f.write(f"ID: {rid} | Len: {length} | Reason: {reason}\n")

    print(f"Audit Complete: {len(legit_cases)} Legit, {len(junk_cases)} Junk.")
    conn.close()

if __name__ == "__main__":
    audit()
