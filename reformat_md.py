import os
import re

def reformat_content(content):
    # Rule 1: Question (Year) followed by a blank line
    content = re.sub(r'^(Question\s*\(.*?\))(?!\n\n)', r'\1\n', content, flags=re.MULTILINE)
    
    # Rule 2: Q1: or Q1a: followed by a blank line
    # Matches Q followed by numbers, then optionally letters, then colon
    content = re.sub(r'^(Q\d+[a-z]*:.*?)(?!\n\n)', r'\1\n', content, flags=re.MULTILINE)
    
    # Rule 3: Suggested Answer followed by a blank line
    content = re.sub(r'^(Suggested Answer)(?!\n\n)', r'\1\n', content, flags=re.MULTILINE)
    
    # Rule 4: A1: or A1a: followed by a blank line
    content = re.sub(r'^(A\d+[a-z]*:.*?)(?!\n\n)', r'\1\n', content, flags=re.MULTILINE)
    
    # Ensure there's exactly one blank line (two newlines) by collapsing any triples
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return content

def process_directory(directory):
    for f in os.listdir(directory):
        if f.endswith('.md'):
            file_path = os.path.join(directory, f)
            print(f"Reformatting {f}...")
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            new_content = reformat_content(content)
            
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(new_content)

if __name__ == "__main__":
    target_dir = r"C:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3\pdf quamto\ai_md"
    process_directory(target_dir)
    print("Done!")
