import json
import os
import re
from pathlib import Path

# CONFIGURATION
# Default to the path in the user snippet, but comments indicate validation issues if strictly used without context.
# However, I will use exactly what was requested.
MANIFEST_PATH = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\Converted MD\conversion_manifest.json")
OUTPUT_DIR = MANIFEST_PATH.parent

def load_manifest():
    if not MANIFEST_PATH.exists():
        print(f"Manifest file not found: {MANIFEST_PATH}")
        print("Run the conversion script first.")
        return []
    with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def sanitize_filename(text):
    """Sanitize text for use in Windows filenames (Same logic as CaseConverter)"""
    text = re.sub(r'[<>:"/\\|?*]', '_', text)
    text = re.sub(r'[_\s]+', '_', text).strip('_')
    return text[:100]

def is_opinion(text):
    """Check if file is likely a separate opinion"""
    header = text[:1000].upper()
    # distinct Justice Name in header (e.g. "JARDELEZA, J. -" or "CARPIO, J.:")
    justice_header = re.search(r"[A-ZÑ]+,?\s+(?:C\.?J|J)\.?\s*[-:]", header)
    if justice_header:
        return True

    keywords = [
        "DISSENTING OPINION", "CONCURRING OPINION", "SEPARATE OPINION", 
        "CONCURRING AND DISSENTING", "SEPARATE CONCURRING",
        "CERTIFICATION", "VOTE", "DISSENT", "CONCUR"
    ]
    return any(k in header for k in keywords)

def merge_case_groups(manifest):
    # 1. Group files by UNIQUE KEY (Case Number + Date)
    groups = {}
    for entry in manifest:
        # Normalize keys to ensure strict matching
        c_num = entry['case_number'].strip()
        c_date = entry['date'].strip()
        key = f"{c_num}|{c_date}"
        
        if key not in groups:
            groups[key] = []
        groups[key].append(entry)

    print(f"Found {len(groups)} unique cases (Database Rows).")
    
    new_manifest = []
    merged_count = 0
    renamed_count = 0

    # 2. Process groups
    for key, entries in groups.items():
        case_num, case_date = key.split('|')
        
        # Define the Perfect Canonical Filename
        safe_num = sanitize_filename(case_num)
        final_filename = f"{safe_num}_{case_date}.md"
        final_path = OUTPUT_DIR / final_filename

        # --- SCENARIO A: Single File (No Merging Needed) ---
        if len(entries) < 2:
            entry = entries[0]
            current_path = Path(entry['output_md'])
            
            # Rename it to the canonical name if it isn't already
            # (e.g., renames "GR_123_2024_v2.md" -> "GR_123_2024.md")
            if current_path.name != final_filename:
                try:
                    if final_path.exists():
                        # If we are effectively renaming onto itself or overwriting, handle carefully
                        try:
                           if current_path.resolve() != final_path.resolve():
                               os.remove(final_path) # Overwrite existing clean file
                        except FileNotFoundError:
                             pass

                    if current_path.exists():
                        os.rename(current_path, final_path)
                        entry['output_md'] = str(final_path)
                        entry['filename'] = final_filename
                        renamed_count += 1
                except Exception as e:
                    print(f"  Warning: Could not rename {current_path.name}: {e}")
            
            new_manifest.append(entry)
            continue

        # --- SCENARIO B: Multiple Files (Merging Logic with Collision Detection) ---
        print(f"Merging {len(entries)} files for: {key}")
        
        valid_entries = []
        for entry in entries:
            file_path = Path(entry['output_md'])
            if not file_path.exists():
                print(f"  Skipping missing file: {file_path}")
                continue
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            valid_entries.append((entry, content))

        if not valid_entries:
            continue

        # 1. Identify "Main Decisions" vs "Opinions"
        # We classify something as an Opinion if it usually contains specific headers.
        # If it DOESN'T, we treat it as a potential Main Decision candidate.
        main_candidates = []
        opinions = []
        
        for entry, content in valid_entries:
            if is_opinion(content):
                opinions.append((entry, content))
            else:
                main_candidates.append((entry, content))

        # 2. Check for COLLISIONS (Multiple Main Decisions)
        if len(main_candidates) > 1:
            print(f"  WARNING: Collision Detected for {key}!")
            print(f"  Found {len(main_candidates)} potential main decisions. Treating as separate cases.")
            
            # Strategy: Suffix them (_A, _B, etc.) and Attach opinions to the first one (or duplicates?)
            # Valid approach: Keep them separate. Don't merge opinions blindly if we don't know which they belong to.
            # Ideally, specific opinions link to specific main decisions, but we lack that link.
            # Fallback: Save identifying Main Decisions as separate files.
            
            for idx, (entry, content) in enumerate(main_candidates):
                suffix = chr(65 + idx) # A, B, C...
                collision_filename = f"{safe_num}_{case_date}_{suffix}.md"
                collision_path = OUTPUT_DIR / collision_filename
                
                with open(collision_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                current_path = Path(entry['output_md'])
                # If we created a new file, we can optionally remove the old one or just update manifest
                # Here we update manifest to point to the new suffixed file
                new_entry = entry.copy()
                new_entry['output_md'] = str(collision_path)
                new_entry['filename'] = collision_filename
                new_manifest.append(new_entry)
                
                print(f"  -> Resolved Collision: {collision_filename}")
                renamed_count += 1
                
                # Cleanup old file if different
                try:
                    if current_path.resolve() != collision_path.resolve():
                        if current_path.exists():
                             os.remove(current_path)
                except Exception:
                    pass

            # What to do with Separated Opinions in a collision? 
            # We will append them to the FIRST main decision (Candidate A) for now, 
            # or save them separately. Let's save them strictly separately to differ manual review.
            for op_entry, op_content in opinions:
                 # Just keep opinions as they are (or rename to canonical format _Opinion_X)
                 # For now, let's just add them to manifest as-is to avoid data loss.
                 new_manifest.append(op_entry) 
            
            continue

        # 3. Standard Merge (0 or 1 Main Decision + N Opinions)
        # If 0 Main Decisions, we pick the longest Opinion as the "Anchor" (rare case)
        main_doc_entry = None
        main_doc_content = ""
        
        if main_candidates:
             # Sort candidates by length (longest is likely the true main decision if logic holds)
             main_candidates.sort(key=lambda x: len(x[1]), reverse=True)
             main_doc_entry, main_doc_content = main_candidates[0]
        else:
             # No "Main Decision" label found? Use longest file.
             valid_entries.sort(key=lambda x: len(x[1]), reverse=True)
             main_doc_entry, main_doc_content = valid_entries[0]
             # Remove it from the opinions list for merging
             opinions = [x for x in valid_entries if x != (main_doc_entry, main_doc_content)]

        # Construct Merged Content
        final_content = main_doc_content
        
        # Determine strict order for opinions (e.g. Dissenting last?)
        # For now, original order (or file sort?)
        for op_entry, op_content in opinions:
            separator = f"\n\n{'='*40}\nSEPARATE OPINION\n{'='*40}\n\n"
            final_content += separator + op_content

        # Write to the CANONICAL Path (Overwrite if exists)
        with open(final_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
            
        print(f"  -> Created: {final_filename}")
        merged_count += 1

        # Delete ALL original partial files
        # (Be careful not to delete the file we just wrote if inputs were different)
        # We collected all inputs from 'entries'
        for entry in entries:
             old_path = Path(entry['output_md'])
             try:
                if old_path.resolve() != final_path.resolve():
                    if old_path.exists():
                        os.remove(old_path)
             except Exception as e:
                print(f"  -> Error deleting partial file {old_path.name}: {e}")

        # Update Manifest
        merged_entry = main_doc_entry.copy()
        merged_entry['output_md'] = str(final_path)
        merged_entry['filename'] = final_filename
        new_manifest.append(merged_entry)

    # 8. Update the Manifest File
    with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
        json.dump(new_manifest, f, indent=2, ensure_ascii=False)

    print(f"\nProcessing Complete.")
    print(f"  - Cases Merged: {merged_count}")
    print(f"  - Files Renamed (Cleaned up): {renamed_count}")
    print(f"  - Manifest Updated: {MANIFEST_PATH}")

if __name__ == "__main__":
    data = load_manifest()
    if data:
        merge_case_groups(data)
