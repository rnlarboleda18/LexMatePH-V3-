import re

def to_title_case(text):
    words = text.lower().split()
    new_words = []
    for w in words:
        if w == 'v.':
            new_words.append('v.')
        elif w.startswith('(') and w.endswith(')'):
             new_words.append(w.capitalize())
        else:
            new_words.append(w.capitalize())
    return " ".join(new_words)

def test_regex():
    # TEST DATA
    samples = [
        "G.R. No. 12345 People v. Estrada",
        "G.R. 12345 People v. Estrada", 
        "GR 12345 People vs. Estrada",
        "G.R. No. L-12345 People vs. Estrada",
        "PEOPLE V. ESTRADA",
        "People versus Estrada",
        "Green v. Del Rosario",       # Safety check: Should NOT change
        "Great Southern v. Surigao",  # Safety check: Should NOT change
        "  Start with Spaces v. End  "
    ]

    # REGEX PATTERNS
    
    # 1. G.R. Stripper
    # ^       : Start of string
    # G\.?R\.?: Matches G.R. or GR or G.R or GR.
    # \s*     : Optional whitespace
    # (?:No\.?)? : Optional "No." or "No" non-capturing group
    # \s*     : Optional whitespace
    # [L-]?   : Optional L- prefix (for old cases like L-12345)
    # \d+     : REQUIRED Digits (Prevents matching 'Green')
    # \s*     : Whitespace
    # [.:-]?  : Optional separator
    # \s*     : Trailing whitespace
    gr_pattern = re.compile(r'^G\.?R\.?\s*(?:No\.?)?\s*(?:L-)?\d+\s*[.:-]?\s*', re.IGNORECASE)
    
    # 2. VS Fixer
    vs_pattern = re.compile(r'\b(vs\.?|versus)\b', re.IGNORECASE)

    print(f"{'ORIGINAL':<40} | {'TRANSFORMED':<40}")
    print("-" * 85)

    for original in samples:
        new_title = original.strip()
        
        # Apply G.R. Fix
        if gr_pattern.match(new_title):
            new_title = gr_pattern.sub('', new_title)
            
        # Apply VS Fix
        if vs_pattern.search(new_title):
            new_title = vs_pattern.sub('v.', new_title)
            
        # Fix Double Dots (v.. -> v.)
        new_title = new_title.replace('..', '.')
            
        # Apply Casing Fix (Simple logic for demo)
        letters = [c for c in new_title if c.isalpha()]
        if letters and len(letters) > 5:
            ratio = sum(1 for c in letters if c.isupper()) / len(letters)
            if ratio > 0.8:
                new_title = to_title_case(new_title)
        
        # Cleanup
        new_title = re.sub(r'\s+', ' ', new_title).strip()
        
        # Visualize Result
        changed = " " if new_title == original.strip() else "*"
        print(f"{changed} {original.strip():<38} | {new_title:<40}")

if __name__ == "__main__":
    test_regex()
