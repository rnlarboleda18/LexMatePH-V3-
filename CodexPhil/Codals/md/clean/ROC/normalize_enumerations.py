import re
import os

def normalize_enumeration(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split merged lines first if they contain clear enumeration patterns
    content = re.sub(r'([:;.\)])\s*(\([a-z]{1,2}\))[\s\xa0]+', r'\1\n\2 ', content)
    content = re.sub(r'([:;.\)])\s*(\(\d+\))[\s\xa0]+', r'\1\n\2 ', content)
    
    lines = content.splitlines(keepends=True)

    # Regex definitions for markers
    # Level 1: (a), (b)... (aa), (bb)... (Ensuring it's not "Section" or similar)
    re_lvl1 = re.compile(r'^\s*(\([a-z]{1,2}\)|[a-z]{1,2}[\)\.])[\s\xa0]+(.*)', re.IGNORECASE)
    # Level 2: (1), (2)... (Ensuring it's not just a part of "Section 1")
    re_lvl2 = re.compile(r'^\s*(\(\d+\)|\d+[\)\.])[\s\xa0]+(.*)', re.IGNORECASE)
    # Level 3: (i), (ii)... (Roman)
    re_lvl3 = re.compile(r'^\s*(\([ivx]+\)|[ivx]+[\)\.])[\s\xa0]+(.*)', re.IGNORECASE)

    new_lines = []
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            new_lines.append(line)
            continue
            
        # EXCLUDE lines that are clearly Section headers or Rule headers
        # More robust check: starts with "Section " or "(n) Section " or similar
        if re.match(r'^(?:\(\w+\)\s+)?Section\s+\d+', stripped, re.IGNORECASE) or stripped.startswith('<p'):
            new_lines.append(line)
            continue
            
        # Match from most specific to least, but handle the Alpha/Roman overlap
        m3 = re_lvl3.match(line)
        m2 = re_lvl2.match(line)
        m1 = re_lvl1.match(line)
        
        target_indent = None
        marker = None
        content_part = None
        
        # Heuristic for Alpha vs Roman:
        # If it matches L3 (Roman) and it's NOT a single 'i', 'v', 'x' (which are also Alpha),
        # it's definitely Roman (ii, iii, iv, vi...).
        # If it matches L1 (Alpha) and NOT L3, it's definitely Alpha.
        # If it matches BOTH (i, v, x):
        #   Check the context? No, let's look at the current line's indentation.
        #   If it was already indented with 12 spaces in the original, it's likely L3.
        #   If it was 0 or 4, it's likely L1.
        
        if m2: # Numeric (Level 2)
            target_indent = " " * 8
            marker = m2.group(1)
            content_part = m2.group(2)
        elif m3 and len(m3.group(1).strip('().')) > 1: # Clearly Roman like ii, iii (Level 3)
            target_indent = " " * 12
            marker = m3.group(1)
            content_part = m3.group(2)
        elif m1: # Alpha (Level 1) or Single-letter Roman
            # If it's i, v, x and matched L3 too
            if m3 and line.startswith("            "): # 12 spaces
                target_indent = " " * 12
                marker = m3.group(1)
                content_part = m3.group(2)
            else:
                target_indent = " " * 4
                marker = m1.group(1)
                content_part = m1.group(2)
            
        if target_indent:
            # Reconstruct with single space and no trailing blank lines before
            content_text = content_part.strip() if content_part else ""
            new_line = f"{target_indent}{marker} {content_text}\n"
            
            # Remove all blank lines before this item to ensure continuous list
            # ALSO remove space between Section header and its first item
            while new_lines and not new_lines[-1].strip():
                new_lines.pop()
            
            new_lines.append(new_line)
        else:
            new_lines.append(line)
                
    return new_lines

def process_roc_combined():
    file_path = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\clean\ROC\ROC_Combined.md'
    
    if os.path.exists(file_path):
        print(f"Normalizing {file_path}...")
        updated = normalize_enumeration(file_path)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(updated)
    else:
        print(f"File not found: {file_path}")

if __name__ == "__main__":
    process_roc_combined()
    print("Enumeration normalization complete for ROC_Combined.md.")
