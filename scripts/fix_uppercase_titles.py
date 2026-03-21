
import psycopg2
import re

DB_CONNECTION_STRING = "postgresql://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"

# Words to keep lowercase (unless first word)
LOWER_PARTICLES = {
    'of', 'the', 'v.', 'vs.', 'and', 'in', 'on', 'at', 'to', 'for', 'by', 'with', 'a', 'an'
}

# Acronyms to keep UPPERCASE
ACRONYM_WHITELIST = {
    'GSIS', 'NLRC', 'COMELEC', 'BIR', 'PNP', 'AFP', 'USA', 'PEZA', 'COA', 'DPWH', 
    'MMDA', 'SSS', 'PHILCOMSAT', 'PHILJA', 'NAPOCOR', 'PAGCOR', 'PCGG', 'SANDIGANBAYAN'
}
# Note: Sandroganbayan is usually Title Cased "Sandiganbayan". Removed. Keep PCGG.

def smart_title_case(title):
    words = title.split()
    new_words = []
    
    for i, word in enumerate(words):
        clean_word = re.sub(r'[^a-zA-Z0-9\.]', '', word) # Strip punctuation for check
        upper_word = clean_word.upper()
        
        # Check if it's a whitelisted acronym
        if upper_word in ACRONYM_WHITELIST:
            new_words.append(upper_word + word[len(clean_word):]) # Append original punctuation
            continue
            
        # Standard Title Casing
        lower_word = word.lower()
        if lower_word in LOWER_PARTICLES and i > 0:
            new_words.append(lower_word)
        else:
            # Handle tricky cases like "McArthur" or "O'Connor" ? 
            # For now, simple capitalize is safer than complex logic
            new_words.append(word.capitalize())
            
    return " ".join(new_words)

def fix_titles():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    print("Fetching candidates...")
    cur.execute("""
        SELECT id, short_title 
        FROM sc_decided_cases 
        WHERE short_title ~ '[A-Z]{3,}' -- Optimization
        AND LENGTH(short_title) > 3
    """)
    rows = cur.fetchall()
    
    fixed_count = 0
    for cid, title in rows:
        if not title: continue
        
        # Density Check
        caps_count = sum(1 for c in title if c.isupper())
        total_len = len(title)
        ratio = caps_count / total_len
        
        if ratio > 0.5:
            new_title = smart_title_case(title)
            
            # Commit update
            if new_title != title:
                cur.execute("UPDATE sc_decided_cases SET short_title = %s WHERE id = %s", (new_title, cid))
                print(f"Fixed {cid}: {title[:30]}... -> {new_title}")
                fixed_count += 1
                
    conn.commit()
    print(f"\nTotal Titles Fixed: {fixed_count}")
    conn.close()

if __name__ == "__main__":
    fix_titles()
