import psycopg2
import re
import json
import argparse

DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

def clean_case_number(cn):
    if not cn:
        return None
    
    original = cn
    # 1. Clear Garbage
    garbage_patterns = [
        r"^NO KNOWN CASE NUMBER$",
        r"^None$",
        r"^Not specified$",
        r"^N/A$",
        r"^filart_1919$",
        r"^Not provided in text$"
    ]
    for pattern in garbage_patterns:
        if re.search(pattern, cn, re.IGNORECASE):
            return None

    # 2. Trim legacy suffixes: (Formerly ...), [Formerly ...], (formerly ...), [FORMERLY ...]
    # Handles nested or sequential parenthesis/brackets as well.
    cn = re.sub(r'\s*[\(\[]\s*Formerly.*[\)\]]', '', cn, flags=re.IGNORECASE)
    
    # 3. Standardize Prefixes
    # Fix internal spacing: G. R. No. -> G.R. No.
    cn = re.sub(r'G\.\s*R\.\s*(No|Nos)\.', r'G.R. \1.', cn, flags=re.IGNORECASE)
    cn = re.sub(r'A\.\s*M\.\s*(No|Nos)\.', r'A.M. \1.', cn, flags=re.IGNORECASE)
    cn = re.sub(r'A\.\s*C\.\s*(No|Nos)\.', r'A.C. \1.', cn, flags=re.IGNORECASE)
    
    # Standardize "No." / "Nos." spacing (Longer pattern first to avoid partial match)
    cn = re.sub(r'Nos\s*\.?\s*', 'Nos. ', cn, flags=re.IGNORECASE)
    cn = re.sub(r'No\s*\.?\s*', 'No. ', cn, flags=re.IGNORECASE)
    
    # Fix plural overlap (e.g., No. s -> Nos.) caused by previous steps if any
    cn = re.sub(r'No\. s\.', 'Nos.', cn, flags=re.IGNORECASE)
    cn = re.sub(r'No\. s', 'Nos.', cn, flags=re.IGNORECASE)
    
    # Fix multiple periods
    cn = re.sub(r'\.\.+', '.', cn)
    
    # Ensure specific prefixes are G.R. No. etc.
    cn = re.sub(r'^G\.?R\.?\s*No', 'G.R. No', cn, flags=re.IGNORECASE)
    cn = re.sub(r'^A\.?M\.?\s*No', 'A.M. No', cn, flags=re.IGNORECASE)
    
    # Clean up double spaces and trim
    cn = re.sub(r'\s+', ' ', cn).strip()
    
    return cn if cn else None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print changes without applying")
    args = parser.parse_args()

    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    cur.execute("SELECT id, case_number FROM sc_decided_cases WHERE case_number IS NOT NULL")
    rows = cur.fetchall()
    
    changes = []
    updates = 0
    
    for rid, cn in rows:
        cleaned = clean_case_number(cn)
        if cleaned != cn:
            changes.append({
                "id": rid,
                "old": cn,
                "new": cleaned
            })
            if not args.dry_run:
                cur.execute("UPDATE sc_decided_cases SET case_number = %s WHERE id = %s", (cleaned, rid))
                updates += 1
    
    if not args.dry_run:
        conn.commit()
        print(f"Applied {updates} updates.")
    else:
        with open("case_number_cleanup_preview.json", "w") as f:
            json.dump(changes, f, indent=2)
        print(f"Dry run complete. Found {len(changes)} potential changes. Preview saved to case_number_cleanup_preview.json")

    conn.close()

if __name__ == "__main__":
    main()
