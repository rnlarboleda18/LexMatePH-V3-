import psycopg2
import re
import csv

DB_CONN = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

def get_db():
    return psycopg2.connect(DB_CONN)

def to_title_case(text):
    words = text.split() # Use original case first to detect acronyms? No, input is often ALL CAPS
    # If input is ALL CAPS, we can't detect 'Abc' vs 'ABC'.
    # Heuristic: Keep 2-4 letter words uppercase? 
    # Risk: "THE" -> "THE". "FOR" -> "FOR". 
    # Better: Keep commonly known acronyms or just accept Title Case for now?
    # User said: "Acronymn for companies are actually allowed example ABC Builders"
    # If the user provides ALL CAPS `ABC BUILDERS`, we can't distinguish `ABC` from `THE`.
    # COMPROMISE: We will title case everything, BUT checks against a whitelist of common acronyms?
    # No, simple heuristic: If we change `NPC` to `Npc`, it's acceptable vs `PEOPLE`.
    # Wait, user explicitly checked for this. 
    # Let's try to be smarter: 
    # If word length <= 4, keep uppercase? No "WITH" -> "WITH".
    # Let's just standard Title Case (Capitalize first letter). 
    # User example "ABC Builders" implies Mixed Case input. 
    # If input is "ABC BUILDERS", it becomes "Abc Builders". 
    # The user might have to manually fix acronyms if they provided ALL CAPS source.
    
    # Actually, allow me to define a small list of known legal acronyms to force UPPER
    ACRONYMS = {'GSIS', 'SSS', 'NLRC', 'NPC', 'BIR', 'COMELEC', 'DPWH', 'PLDT', 'MERALCO', 'PNB', 'DBP', 'LBP', 'DOJ', 'DOH'}
    
    words = text.lower().split()
    new_words = []
    for w in words:
        clean_w = w.strip('.,()')
        if clean_w.upper() in ACRONYMS:
            new_words.append(w.upper())
        elif w == 'v.':
            new_words.append('v.')
        elif w.startswith('(') and w.endswith(')'):
             new_words.append(w.capitalize())
        else:
            new_words.append(w.capitalize())
    return " ".join(new_words)

def fix_titles(dry_run=True):
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT id, short_title FROM sc_decided_cases WHERE short_title IS NOT NULL")
    rows = cur.fetchall()
    
    updates = []
    
    gr_pattern = re.compile(r'^G\.?R\.?\s*(?:No\.?)?\s*(?:L-)?\d+\s*[.:-]?\s*', re.IGNORECASE)
    vs_pattern = re.compile(r'\b(vs\.?|versus)\b', re.IGNORECASE)
    
    for case_id, title in rows:
        original = title.strip()
        new_title = original
        
        # 1. Remove G.R. prefix
        # SAFETY: Only remove if there is text AFTER the G.R. number
        match = gr_pattern.match(new_title)
        if match:
            potential_strip = gr_pattern.sub('', new_title).strip()
            if len(potential_strip) > 2: # Ensure meaningful title remains
                new_title = potential_strip
            else:
                # Logic: If result is empty/tiny, DO NOT STRIP. 
                # Ideally, we should fetch "People v. Name" from full citation if possible, 
                # but regarding this specific task, we just skip the fix to avoid creating empty titles.
                pass
            
        # 2. Fix "vs." -> "v."
        if vs_pattern.search(new_title):
            new_title = vs_pattern.sub('v.', new_title)
            
        # Fix Double Dots
        new_title = new_title.replace('..', '.')
            
        # 3. Fix ALL CAPS
        letters = [c for c in new_title if c.isalpha()]
        if letters and len(letters) > 5:
            ratio = sum(1 for c in letters if c.isupper()) / len(letters)
            if ratio > 0.8:
                new_title = to_title_case(new_title)
                
        new_title = re.sub(r'\s+', ' ', new_title).strip()
        
        if new_title != original:
            updates.append((case_id, original, new_title))
            
    print(f"Total Records: {len(rows)}")
    print(f"Proposed Fixes: {len(updates)}")
    
    if updates:
        print("\n=== SAMPLE FIXES ===")
        for i in range(min(10, len(updates))):
            uid, old, new = updates[i]
            print(f"[{uid}]")
            print(f"  OLD: {old}")
            print(f"  NEW: {new}")
            print("-" * 20)
            
    if not dry_run:
        print(f"\nApplying {len(updates)} updates to DB...")
        # Batch update
        # execute_batch from psycopg2.extras is better but simple loop fine for 10k
        for uid, old, new in updates:
            cur.execute("UPDATE sc_decided_cases SET short_title = %s WHERE id = %s", (new, uid))
        conn.commit()
        print("Updates Committed.")
    else:
        print("\n[DRY RUN] No changes made.")
        
    conn.close()

if __name__ == "__main__":
    import sys
    # Check arg for apply
    apply = len(sys.argv) > 1 and sys.argv[1] == '--apply'
    fix_titles(dry_run=not apply)
