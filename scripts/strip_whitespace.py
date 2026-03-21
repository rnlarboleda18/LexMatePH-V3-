import os

MD_DIR = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\sc_elib_md"

def strip_whitespace():
    count_modified = 0
    total_files = 0
    
    print(f"Scanning {MD_DIR}...")
    
    files = [f for f in os.listdir(MD_DIR) if f.endswith('.md')]
    total_files = len(files)
    
    for filename in files:
        filepath = os.path.join(MD_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            stripped_content = content.lstrip()
            
            if len(content) != len(stripped_content):
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(stripped_content)
                count_modified += 1
                if count_modified % 1000 == 0:
                    print(f"Modified {count_modified} files...")
                    
        except Exception as e:
            print(f"Error processing {filename}: {e}")

    print(f"Cleanup complete. Modified {count_modified} of {total_files} files.")

if __name__ == "__main__":
    strip_whitespace()
