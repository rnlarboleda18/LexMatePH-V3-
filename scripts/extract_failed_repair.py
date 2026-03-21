import psycopg2
import re

DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

def extract_failed_repair():
    # Read original target IDs
    with open("target_reformat_facts.txt", "r") as f:
        target_ids = [line.strip() for line in f if line.strip()]

    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    print(f"Checking {len(target_ids)} cases to isolate failures...")
    
    failed_ids = []
    
    for case_id in target_ids:
        cur.execute("SELECT digest_facts FROM sc_decided_cases WHERE id = %s", (case_id,))
        row = cur.fetchone()
        
        if not row or not row[0]:
            continue
            
        facts = row[0]
        # Split by double newlines
        paragraphs = [p for p in re.split(r'\n\s*\n', facts.strip()) if p.strip()]
        
        if len(paragraphs) != 3:
            failed_ids.append(case_id)

    print(f"Found {len(failed_ids)} cases that still failed compliance.")
    
    with open("target_failed_repair.txt", "w") as f:
        f.write('\n'.join(failed_ids))
        
    print("Saved to target_failed_repair.txt")
    conn.close()

if __name__ == "__main__":
    extract_failed_repair()
