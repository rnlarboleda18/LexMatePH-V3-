
import psycopg2
import re
import time

# Config
DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

def get_db_connection():
    return psycopg2.connect(DB_CONNECTION_STRING)

def undo_facts_damage():
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("Fetching cases with digest_facts...")
    # Target only broken ones to be efficient? Or just scan all?
    # LIKE '%**The Petition** er%' is a guaranteed hit.
    cur.execute("SELECT id, digest_facts FROM sc_decided_cases WHERE digest_facts LIKE '%**The Petition**%' OR digest_facts LIKE '%**The Appeal**%'")
    rows = cur.fetchall()
    
    print(f"Found {len(rows)} potential cases to revert.")
    
    fixed_count = 0
    
    for rid, text in rows:
        original = text
        modified = text
        
        # FIX 1: "The Petition" er -> "The petitioner"
        # The previous script inserted "\n\n**The Petition** ". 
        # So we look for "\n\n**The Petition** er"
        # We also look for just "**The Petition** er" (case insensitive match on er?)
        
        # Regex for 'The Petition' split
        # Matches: **The Petition** er (with optional spaces/newlines)
        # Note: The original regex removed nothing, it just inserted.
        # So "The petitioner" became "\n\n**The Petition** er".
        # We want to revert to "The petitioner" (Sentence case? or match original?)
        # Likely "The petitioner" is safe.
        
        modified = modified.replace("\n\n**The Petition** er", "The petitioner")
        modified = modified.replace("**The Petition** er", "The petitioner")
        
        # Handle "The Petition" -> "The petition" (Lower case restore if it was mid-sentence?)
        # Wait, if it was "The petition for certiorari", it became "\n\n**The Petition** for certiorari".
        # The user MIGHT want to keep the header if it was a real header?
        # But the USER said "Undo it all".
        # So I should revert "\n\n**The Petition** " back to "The petition " or "The Petition "?
        # It's hard to know casing.
        # But the "Split Word" is the critical error.
        
        # FIX 2: "The Appeal" lant -> "The appellant"
        modified = modified.replace("\n\n**The Appeal** lant", "The appellant")
        modified = modified.replace("**The Appeal** lant", "The appellant")
        
        # FIX 3: "The Petition" ee -> "The petitionee" (Less common but possible)
        modified = modified.replace("\n\n**The Petition** ee", "The petitionee")
        modified = modified.replace("**The Petition** ee", "The petitionee")
        
        # FIX 4: "The Appeal" lee -> "The appellee"
        modified = modified.replace("\n\n**The Appeal** lee", "The appellee")
        modified = modified.replace("**The Appeal** lee", "The appellee")

        # FIX 5: Aggressive Revert of just the inserted formatting for "The Petition"?
        # If the user wants to UNDO IT ALL, I should remove the bolding and newlines I added.
        # My added string was `\n\n**The Petition** `
        # I should output `The Petition ` (or `The petition `?)
        # I'll try to just remove the bolding for now.
        
        # If I strictly remove `\n\n**` and `**` around these words, I return to original state (mostly).
        # But I need to be careful not to remove valid bolding.
        # My script added `\n\n**The Petition** `.
        # I will replace `\n\n**The Petition** ` with `The Petition ` (Keep the space).
        # Same for `\n\n**The Antecedents** ` -> `The Antecedents `.
        # Same for `\n\n**Procedural History** ` -> `Procedural History `.
        
        # Why? Because user said "Undo it all".
        
        patterns_to_strip = [
            "The Antecedents",
            "Procedural History",
            "The Petition",
            "The Appeal"
        ]
        
        for p in patterns_to_strip:
            target = f"\n\n**{p}** "
            replacement = f"{p} "
            modified = modified.replace(target, replacement)
            
            # Also catch the case where I might have missed the space or something
            target_ns = f"\n\n**{p}**"
            replacement_ns = f"{p}"
            modified = modified.replace(target_ns, replacement_ns)

            # Also catch just bold (if newlines were already there) causing double newlines?
            # My regex was `(Header) -> \n\n**Header**`.
            # So `\n\n**Header**` is the artifact.
            
        if modified != original:
            cur.execute("UPDATE sc_decided_cases SET digest_facts = %s WHERE id = %s", (modified, rid))
            fixed_count += 1
            if fixed_count % 100 == 0:
                print(f"Reverted {fixed_count} cases...")
                
    conn.commit()
    conn.close()
    print(f"Finished. Reverted {fixed_count} cases.")

if __name__ == "__main__":
    undo_facts_damage()
