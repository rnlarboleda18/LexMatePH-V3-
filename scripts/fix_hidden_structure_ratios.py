
import psycopg2
import re

# Config
DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

def fix_hidden_ratios():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()

    print("=== FIX HIDDEN RATIO STRUCTURE ===\n")

    # Fetch candidates: Issues != Ratio (specifically Ratio < Issues)
    cur.execute("""
        SELECT id, digest_issues, digest_ratio 
        FROM sc_decided_cases 
        WHERE digest_issues IS NOT NULL AND digest_ratio IS NOT NULL
          AND digest_issues != '' AND digest_ratio != ''
    """)
    rows = cur.fetchall()

    bullet_pattern = re.compile(r'^\s*([*\-]|\d+\.)\s+', re.MULTILINE)
    edited_count = 0

    for rid, issues, ratio in rows:
        c_issues = len(bullet_pattern.findall(issues))
        c_ratio = len(bullet_pattern.findall(ratio))

        # We only care if Ratio is "under-split" compared to Issues
        if c_ratio < c_issues:
            original_ratio = ratio
            
            # Check for merged bold headers: "Text. **Next Header**"
            # We look for [Space] + [**]
            # We want to replace it with [\n* **]
            # But we must avoid double bulleting if it's already at start of line
            
            # Regex: Find ` **` that is NOT at the start of the string
            # And split there.
            
            # Strategy:
            # 1. Normalize separate lines to single line? No, might lose structure.
            # 2. Simple replace ` **` with `\n* **` if it looks like a header (Capital letter after **?)
            
            # Count bold markers to see if it's worth trying
            bold_count = ratio.count("**") / 2
            
            if bold_count > c_ratio:
                # Attempt Fix: Regex Replace
                # Look for literal "**" preceded by (Start of string OR (Dot + optional whitespace))
                # We want to ensure we don't break existing bullets, but create new ones.
                
                # Pattern: literal "**"
                # If we just force every "**Header" to be a bullet line start:
                
                # 1. Ensure newlines before bold headers
                # Regex: Replace any `**` that is NOT at start of line with `\n* **`
                # But careful of bolding *inside* a sentence. Usually Headers are "On the issue..."
                
                # Check the candidate preview from audit: "* **On...** text... **On...** text"
                # So we want to turn `... text. **On...` -> `... text.\n* **On...`
                
                new_ratio = re.sub(r'(?<=\.)\s*\*\*', r'\n* **', original_ratio)
                
                # Also handle case where it's just spaces: `text   **Header`
                if new_ratio == original_ratio:
                     new_ratio = re.sub(r'\s{2,}\*\*', r'\n* **', original_ratio)

                new_c_ratio = len(bullet_pattern.findall(new_ratio))
                
                if new_c_ratio > c_ratio:
                     print(f"ID {rid}: Split merged structure.")
                     print(f"   Old Ratio ({c_ratio}): {ratio[:40]}...")
                     print(f"   New Ratio ({new_c_ratio}): {new_ratio[:40]}...")
                     
                     cur.execute("UPDATE sc_decided_cases SET digest_ratio = %s WHERE id = %s", (new_ratio, rid))
                     conn.commit()
                     edited_count += 1
            
            # TODO: "On the issue" logic is harder to regex safely without bold.
            # Sticking to bold headers which covers the structural misformatting.

    print(f"\nTotal Cases Fixed: {edited_count}")
    conn.close()

if __name__ == "__main__":
    fix_hidden_ratios()
