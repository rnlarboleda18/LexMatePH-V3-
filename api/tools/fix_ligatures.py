import os
import re

def fix_ligatures_in_content(content):
    # 1. Safely fix 'fi' and 'fl' splits (these are not valid standalone words)
    content = re.sub(r'fi\s+([a-z])', r'fi\1', content)
    content = re.sub(r'fl\s+([a-z])', r'fl\1', content)
    
    # 2. Fix common 'ff' splits (using safe prefixes or exact words)
    # 'offi' -> 'offic' (office, official, etc)
    content = re.sub(r'offi\s+([a-z])', r'offi\1', content)
    # 'eff' -> 'effect' etc
    content = re.sub(r'eff\s+([a-z])', r'eff\1', content)
    # 'suff' -> 'suffer', 'sufficient'
    content = re.sub(r'suff\s+([a-z])', r'suff\1', content)
    # 'diff' -> 'difficult'
    content = re.sub(r'diff\s+([a-z])', r'diff\1', content)
    
    # 3. Explicit fixes for other 'off' splits to avoid 'off the' collisions
    content = re.sub(r'off\s+eror', 'offeror', content, flags=re.IGNORECASE)
    content = re.sub(r'off\s+ered', 'offered', content, flags=re.IGNORECASE)
    content = re.sub(r'off\s+ering', 'offering', content, flags=re.IGNORECASE)
    content = re.sub(r'off\s+ers', 'offers', content, flags=re.IGNORECASE)
    content = re.sub(r'off\s+er\s', 'offer ', content, flags=re.IGNORECASE) # space to ensure it's the word
    
    return content

def main():
    directory = r'c:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\LexCode\Codals\md\ROC'
    files_to_process = [
        '1. ROC Civil Procedure as amended 2019.md',
        '2. ROC Special Proceeding.md',
        '3. ROC Criminal Procedure_cleaned.md',
        '4. ROC Evidence as amended 2019.md'
    ]
    
    for filename in files_to_process:
        filepath = os.path.join(directory, filename)
        if not os.path.exists(filepath):
            print(f"Skipping (Not found): {filename}")
            continue
            
        print(f"Processing: {filename}...")
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        fixed = fix_ligatures_in_content(content)
        
        if fixed != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(fixed)
            print(f"-> Fixed typos in {filename}")
        else:
            print(f"-> No changes needed for {filename}")

if __name__ == "__main__":
    main()
