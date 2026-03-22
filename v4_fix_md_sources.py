import os
import re

def fix_content(content):
    # 1. Remove duplicate question markers (e.g., Q440 on its own line before Q440:)
    content = re.sub(r'^(Q\d+[a-z]?)\s*\n+\1:', r'\1:', content, flags=re.MULTILINE)
    
    # 2. Normalize Q#: and A#: spacing (Blank line before and after)
    content = re.sub(r'\n+(Q\d+[a-z]?:)\s*', r'\n\n\1\n\n', content)
    content = re.sub(r'\n+(A\d+[a-z]?:)\s*', r'\n\n\1\n\n', content)
    
    # 3. Handle Suggested Answer spacing
    content = re.sub(r'\n\s*Suggested\s+Answer\s*\n', r'\n\nSuggested Answer\n\n', content, flags=re.IGNORECASE)
    
    # 4. Handle ALTERNATIVE ANSWER: (ensure two newlines before)
    content = re.sub(r'\s+ALTERNATIVE\s+ANSWER:', r'\n\nALTERNATIVE ANSWER:', content, flags=re.IGNORECASE)
    
    # 5. Promote Year to Question Header
    # Pattern: find a Question block, check for (Year BAR) at the end of the first paragraph of text
    # This is complex to do with a single regex on the whole file. 
    # Let's split into logic units and reassemble.
    
    # First, split by things that look like question starts or "Question ("
    parts = re.split(r'\n(?=Question\s*\(|Q\d+[a-z]?:)', content)
    new_parts = []
    current_year = "0000"
    
    for part in parts:
        part = part.strip()
        if not part: continue
        
        # 1. Detect existing header
        header_match = re.search(r'Question\s*\((\d{4}).*?BAR\)', part, re.IGNORECASE)
        if header_match:
            current_year = header_match.group(1)
            # If it's JUST a header block, skip it (we re-add it to the actual Qs)
            if re.fullmatch(r'Question\s*\(.*?\)', part, re.IGNORECASE):
                continue
        
        # 2. Check for question marker at start
        if re.match(r'Q\d+[a-z]?:', part, re.IGNORECASE):
            # Split into Question and Answer if possible
            qa_split = re.split(r'(\n\s*Suggested\s+Answer\s*\n)', part, maxsplit=1, flags=re.IGNORECASE)
            
            q_part = qa_split[0]
            ans_part = ""
            if len(qa_split) > 1:
                ans_part = "".join(qa_split[1:])
            
            # Extract year from Q part
            year_match = re.search(r'\((\d{4}).*?BAR\)', q_part)
            year_to_use = year_match.group(1) if year_match else current_year
            
            # Clean Q marker from start
            marker_match = re.match(r'^(Q\d+[a-z]?:)\s*', q_part, re.IGNORECASE)
            marker = marker_match.group(1) if marker_match else ""
            q_text = q_part[len(marker):].strip()
            
            # Reconstruct
            unit = f"Question ({year_to_use} BAR)\n\n{marker}\n\n{q_text}"
            if ans_part:
                unit += f"\n\n{ans_part.strip()}"
            new_parts.append(unit)
        else:
            # Preserve anything else (headers, intro text, etc.)
            new_parts.append(part)
            
    content = "\n\n".join(new_parts)
    
    # Final cleanup: no multiple blank lines
    content = re.sub(r'\n{3,}', r'\n\n', content)
    return content.strip()

dir_path = r"C:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3\pdf quamto\ai_md"
for filename in os.listdir(dir_path):
    if filename.endswith(".md"):
        file_path = os.path.join(dir_path, filename)
        print(f"Fixing {filename}...")
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        new_content = fix_content(content)
        
        # Write back
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

print("Done fixing MD sources.")
