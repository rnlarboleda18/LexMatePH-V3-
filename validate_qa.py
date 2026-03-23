import os
import re

def extract_entities(text):
    # Match single uppercase letters (like A, B, X, Y)
    single_letters = set(re.findall(r'\b[A-Z]\b', text))
    
    # Match capitalized names (simplistic approach: words starting with capital letter)
    # Exclude common first words of sentences or common capitalized words if possible, but for this heuristic,
    # just getting all capitalized words and filtering short ones is enough.
    capitalized_words = set(re.findall(r'\b[A-Z][a-z]+\b', text))
    
    # Filter out common starts of sentences or legal terms that might not be names
    stop_words = {"The", "A", "An", "In", "On", "At", "If", "When", "What", "Why", "Is", "Are", "Yes", "No", "Under", "According", "Article", "Section", "Republic", "Act", "Court", "Supreme"}
    
    names = {w for w in capitalized_words if w not in stop_words and len(w) > 2}
    
    return single_letters.union(names)

def validate_md_file(filepath):
    print(f"\n--- Validating: {os.path.basename(filepath)} ---")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by the separator "---"
    blocks = content.split('---')
    
    flagged = []
    
    for block in blocks:
        block = block.strip()
        if not block or block.startswith('# Extracted'):
            continue
            
        # Extract Qs and As from this block (which represents a single main Question pair)
        # There might be multiple Qs and As due to subquestions
        q_lines = re.findall(r'^(Q\d+[a-z]?):\s*(.*)$', block, re.MULTILINE)
        a_lines = re.findall(r'^(A\d+[a-z]?):\s*(.*)$', block, re.MULTILINE)
        
        q_dict = {tag: text for tag, text in q_lines}
        a_dict = {tag.replace('A', 'Q', 1): text for tag, text in a_lines}
        
        for q_tag, q_text in q_dict.items():
            a_text = a_dict.get(q_tag, "")
            
            # 1. Empty Answer Check
            if not a_text.strip():
                flagged.append(f"[{q_tag}] Empty Answer")
                continue
                
            # 2. Short Answer Check
            if len(a_text) < 15:
                flagged.append(f"[{q_tag}] Suspiciously short answer: {a_text}")
                continue
                
            # 3. Entity Matching Heuristic
            # If the Q asks about specific people (Pedro, X, Y), 
            # ideally the A should mention at least one of them.
            entities = extract_entities(q_text)
            
            # If we found entities, check if ANY exist in the answer
            if entities:
                found_match = False
                for e in entities:
                    # check for exact word match
                    if re.search(r'\b' + re.escape(e) + r'\b', a_text):
                        found_match = True
                        break
                
                if not found_match:
                    # It's possible the answer is general like "Yes, the crime is murder."
                    # We'll flag it as a "Soft Warning"
                    flagged.append(f"[{q_tag}] POSSIBLE MISMATCH: Answer doesn't mention any names from Question. Found entities: {entities}")
                    
    if flagged:
        print(f"Found {len(flagged)} potential issues:")
        for issue in flagged[:15]: # Print first 15 issues per file to avoid spam
            print(f"  - {issue}")
        if len(flagged) > 15:
            print(f"  ... and {len(flagged) - 15} more.")
    else:
        print("Looks pristine!")
        
    return len(flagged)

if __name__ == "__main__":
    md_dir = r"C:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3\pdf quamto\md"
    total_issues = 0
    
    for f in os.listdir(md_dir):
        if f.endswith('.md'):
            total_issues += validate_md_file(os.path.join(md_dir, f))
            
    print(f"\nTotal potential issues flagged across all files: {total_issues}")
