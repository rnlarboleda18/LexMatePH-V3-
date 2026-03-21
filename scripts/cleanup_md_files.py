import os
import re

MD_DIR = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\sc_elib_md"

def cleanup():
    count_deleted = 0
    total_files = 0
    
    print(f"Scanning {MD_DIR}...")
    
    files = [f for f in os.listdir(MD_DIR) if f.endswith('.md')]
    total_files = len(files)
    
    for filename in files:
        filepath = os.path.join(MD_DIR, filename)
        try:
            # Check 1: Size
            if os.path.getsize(filepath) < 600:
                print(f"[DELETE] {filename} (Size < 600 bytes)")
                os.remove(filepath)
                count_deleted += 1
                continue
                
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check 2: Error Message
            if "Document not available on the database!" in content:
                 print(f"[DELETE] {filename} (Contains error message)")
                 os.remove(filepath)
                 count_deleted += 1
                 continue

            # Check 3: Missing Header
            # A valid decision usually has "G.R. No." or "Republic".
            # Some old cases might just start with "EN BANC".
            # We need to be careful. Let's look for known "good" markers.
            # If NONE of the good markers are present, it's suspicious.
            
            good_markers = [
                r"G\.R\. No\.",
                r"REPUBLIC OF THE PHILIPPINES",
                r"EN BANC",
                r"SECOND DIVISION",
                r"FIRST DIVISION",
                r"THIRD DIVISION",
                r"Resolution",
                r"Decision",
                r"DECISION", # sometimes capitalized
                r"RESOLUTION"
            ]
            
            has_marker = False
            for marker in good_markers:
                if re.search(marker, content, re.IGNORECASE):
                    has_marker = True
                    break
            
            if not has_marker:
                # Double check size - if it's large but no header, maybe it's a weird format but valid text?
                # If it's small-ish (< 2KB) and no header, likely trash.
                if len(content) < 2000:
                    print(f"[DELETE] {filename} (No header & small content)")
                    os.remove(filepath)
                    count_deleted += 1
                else:
                    print(f"[WARN] {filename} has no header but large content ({len(content)} bytes). Keeping.")
                    
        except Exception as e:
            print(f"Error processing {filename}: {e}")

    print(f"Cleanup complete. Deleted {count_deleted} of {total_files} files.")

if __name__ == "__main__":
    cleanup()
