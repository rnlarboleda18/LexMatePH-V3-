import re

def merge_fragments(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Regex for list items: (a), a), 1., i., etc.
    list_regex = re.compile(r'^(\s*\(?[a-z0-9]+\)\s+|\s*\d+\.\s+)', re.IGNORECASE)
    
    new_lines = []
    fragments_merged = 0
    list_items = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Skip headers, HTML, markers
        if not stripped or stripped.startswith(('<', '#', 'RULE', 'GENERAL PROVISION', 'Section', '*', '_')):
            new_lines.append(line)
            i += 1
            continue
            
        if stripped[0].islower():
            if list_regex.match(line):
                # This is a list item, keep it but record its line number
                list_items.append((len(new_lines) + 1, stripped))
                new_lines.append(line)
            else:
                # This is a fragment, merge with the PREVIOUS non-empty line in new_lines
                # We need to find the last non-empty line in new_lines and append this text to it
                found_prev = False
                for j in range(len(new_lines)-1, -1, -1):
                    if new_lines[j].strip():
                        # Merge here
                        # Remove existing newline and any trailing space, then add a space and the fragment
                        prev_line = new_lines[j].rstrip()
                        new_lines[j] = prev_line + " " + stripped + "\n"
                        fragments_merged += 1
                        found_prev = True
                        break
                
                if not found_prev:
                    # Fallback if no prev line found (shouldn't happen)
                    new_lines.append(line)
        else:
            new_lines.append(line)
        i += 1
                
    return new_lines, fragments_merged, list_items

if __name__ == "__main__":
    file_path = 'ROC_Combined.md'
    updated_lines, merged_count, list_items = merge_fragments(file_path)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(updated_lines)
    
    print(f"SUCCESS: Merged {merged_count} fragments.")
    print("\n--- Remaining 17 List Items to Check ---")
    for line_num, text in list_items:
        print(f"Line {line_num}: {text[:100]}...")
