
import psycopg2
import json

# Config
DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

def fix_blended():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    # Fetch targets
    cur.execute("SELECT id, digest_issues, digest_ratio FROM sc_decided_cases WHERE digest_issues LIKE '[%' OR digest_ratio LIKE '[%'")
    rows = cur.fetchall()
    
    print(f"Found {len(rows)} cases to fix.")
    
    for rid, issues_raw, ratio_raw in rows:
        print(f"Processing ID {rid}...")
        
        new_issues = issues_raw
        new_ratio = ratio_raw
        
        # 1. Fix Issues
        if issues_raw and issues_raw.strip().startswith('['):
            try:
                data = json.loads(issues_raw)
                # Expecting list of dicts: case 1787 and 1220 have slightly different keys
                lines = []
                for item in data:
                    # Try common keys
                    text = item.get('issue_description') or item.get('issue_text') or item.get('issue') or str(item)
                    lines.append(f"* {text}")
                new_issues = "\n".join(lines)
                print(f"  > Fixed Issues ({len(lines)} bullets)")
            except Exception as e:
                print(f"  ! Failed to parse Issues JSON: {e}")

        # 2. Fix Ratio
        if ratio_raw and ratio_raw.strip().startswith('['):
            try:
                data = json.loads(ratio_raw)
                lines = []
                for item in data:
                     # Try common keys
                    text = item.get('ratio_text') or item.get('ratio') or item.get('holding') or str(item)
                    lines.append(f"* {text}")
                new_ratio = "\n".join(lines)
                print(f"  > Fixed Ratio ({len(lines)} bullets)")
            except Exception as e:
                print(f"  ! Failed to parse Ratio JSON: {e}")
        
        # Update
        cur.execute("""
            UPDATE sc_decided_cases 
            SET digest_issues = %s, digest_ratio = %s 
            WHERE id = %s
        """, (new_issues, new_ratio, rid))
        conn.commit()
        print("  > Saved.")

    conn.close()

if __name__ == "__main__":
    fix_blended()
