import psycopg2
import re

# Config
DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

def fix_formatting():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()

    print("Fetching cases with Antecedents/Procedural History...")
    cur.execute("SELECT id, digest_facts FROM sc_decided_cases WHERE digest_facts IS NOT NULL AND digest_facts LIKE '%Antecedents%'")
    rows = cur.fetchall()
    
    print(f"Found {len(rows)} potential cases.")
    
    updated_count = 0
    
    # Regex Patterns
    # Matches: **The Antecedents** :** | The Antecedents:** | **Antecedents:** etc.
    # We want to capture the specific phrase and reformat it.
    
    # Pattern 1: Antecedents
    p_antecedents = re.compile(r"(?i)(?:\*\*|)\s*(The Antecedents|Antecedents)\s*(?:\*\*|)\s*[:\.]*\s*(?:\*\*|)\s*")
    
    # Pattern 2: Procedural History
    p_history = re.compile(r"(?i)(?:\*\*|)\s*(Procedural History)\s*(?:\*\*|)\s*[:\.]*\s*(?:\*\*|)\s*")
    
    # Pattern 3: The Petition / The Appeal
    p_petition = re.compile(r"(?i)(?:\*\*|)\s*(The Petition|The Appeal)\s*(?:\*\*|)\s*[:\.]*\s*(?:\*\*|)\s*")

    for rid, facts in rows:
        original = facts
        
        # Apply Replacements
        # We use a lambda or direct sub to ensure format "\n\n**Header:** "
        
        # 1. Antecedents (Sometimes it's at the very start, so we strip leading newlines later)
        facts = p_antecedents.sub(r"\n\n**The Antecedents:** ", facts)
        
        # 2. Procedural History
        facts = p_history.sub(r"\n\n**Procedural History:** ", facts)
        
        # 3. Petition/Appeal
        facts = p_petition.sub(r"\n\n**\1:** ", facts) # \1 preserves "The Petition" or "The Appeal"
        
        # Cleanup: Remove leading newlines at the very start of the string
        facts = facts.lstrip()
        
        # Cleanup: Fix triple newlines if any
        facts = facts.replace("\n\n\n", "\n\n")

        if facts != original:
            cur.execute("UPDATE sc_decided_cases SET digest_facts = %s WHERE id = %s", (facts, rid))
            updated_count += 1
            if updated_count % 1000 == 0:
                print(f"Updated {updated_count} cases...")

    conn.commit()
    print(f"Done! Updated {updated_count} cases.")
    conn.close()

if __name__ == "__main__":
    fix_formatting()
