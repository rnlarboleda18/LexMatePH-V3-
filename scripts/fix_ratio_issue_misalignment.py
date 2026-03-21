import psycopg2
import re
import argparse
import logging

DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

logging.basicConfig(level=logging.INFO, format='%(message)s')

def fix_misalignment(ratio_text):
    if not ratio_text:
        return ratio_text
    
    # Pattern to find "* **On Issue X (Continued ...):**"
    # We want to merge these into the previous bullet point if they refer to the same issue ID.
    
    lines = ratio_text.split('\n')
    new_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if it's a "Continued" bullet
        match = re.search(r'^\* \*\*On Issue (\d+) \(Continued - ([^)]+)\):\*\*(.*)', line)
        if match:
            issue_num = match.group(1)
            sub_topic = match.group(2)
            content = match.group(3)
            
            # Find the last line that matches "On Issue X"
            merged = False
            for i in range(len(new_lines) - 1, -1, -1):
                if f"**On Issue {issue_num}:**" in new_lines[i] or f"**On Issue {issue_num}**" in new_lines[i]:
                    # Append this content to the previous issue instead of a new bullet
                    new_lines[i] = new_lines[i] + f"\n\n**{sub_topic}:**{content}"
                    merged = True
                    break
            
            if not merged:
                # If no parent found, keep it as is but maybe clean it
                new_lines.append(line)
        else:
            new_lines.append(line)
            
    return "\n".join(new_lines)

def run_fix(dry_run=True):
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    cur.execute("SELECT id, short_title, digest_ratio FROM sc_decided_cases WHERE digest_ratio ILIKE '%Continued%'")
    rows = cur.fetchall()
    
    logging.info(f"Checking {len(rows)} cases...")
    
    for row in rows:
        cid, title, ratio = row
        fixed_ratio = fix_misalignment(ratio)
        
        if fixed_ratio != ratio:
            if dry_run:
                logging.info(f"--- [DRY RUN] Case {cid}: {title} ---")
                logging.info(f"ORIGINAL:\n{ratio[:300]}...")
                logging.info(f"FIXED:\n{fixed_ratio[:300]}...")
            else:
                cur.execute("UPDATE sc_decided_cases SET digest_ratio = %s, updated_at = NOW() WHERE id = %s", (fixed_ratio, cid))
                logging.info(f"Updated Case {cid}: {title}")
        
    if not dry_run:
        conn.commit()
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    run_fix(dry_run=not args.apply)
