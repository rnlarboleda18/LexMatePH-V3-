
import os
import re
from pathlib import Path
from collections import defaultdict

# Configuration
OUTPUT_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\MD converted final")

def get_sort_key(filename):
    """
    Sort logic:
    1. Ponencia (Main) first
    2. Concurring
    3. Separate
    4. Dissent
    5. Others alpha
    """
    fname = filename.lower()
    if "_ponencia" in fname:
        # Check if it has a counter like _ponencia_2, put it after _ponencia
        if re.search(r'_ponencia_\d+', fname):
             return 1 # secondary main? (rare)
        return 0 # Primary
    if "_concurring" in fname:
        return 2
    if "_separate" in fname:
        return 3
    if "_dissent" in fname:
        return 4
    return 5

def main():
    print(f"Scanning {OUTPUT_DIR} for split case files...")
    
    # regex to capture base case name:
    # Matches "G.R._No._XXXX_YYYY-MM-DD" 
    # Stops before _Ponencia, _Dissent, _Separate, etc.
    # Pattern: ^(.*_\d{4}-\d{2}-\d{2})(_[A-Za-z]+.*)\.md$
    
    pattern = re.compile(r'^(.*_\d{4}-\d{2}-\d{2})(_[A-Za-z]+.*)?\.md$')
    
    groups = defaultdict(list)
    all_files = list(OUTPUT_DIR.glob("*.md"))
    
    file_count = 0
    
    for f in all_files:
        match = pattern.match(f.name)
        if match:
            base_name = match.group(1)
            suffix = match.group(2)
            
            # We ONLY care about groups that have at least one suffixed file (recovered collision)
            # If suffix is None, it's a standard file. We include it in the group to potentially merge/overwrite.
            
            groups[base_name].append(f)
            file_count += 1
            
    print(f"Grouped {file_count} files into {len(groups)} cases.")
    
    merged_count = 0
    
    for base_name, files in groups.items():
        # Filter for groups that actually HAVE suffixes (collisions)
        has_suffix = any("_Ponencia" in f.name or "_Dissent" in f.name or "_Separate" in f.name or "_Concurring" in f.name for f in files)
        
        if not has_suffix:
            continue
            
        print(f"Merging Group: {base_name} ({len(files)} files)")
        
        # Sort files
        # We need to be careful with the "Standard" file (no suffix).
        # If we have [Standard, Ponencia, Dissent], the Standard is likely a duplicate of Ponencia or Dissent.
        # We should probably prioritize the explicitly named Ponencia content.
        # Strategy: If Ponencia exists, ignore Standard? Or just append everything?
        # User said "Merge all cases". 
        # But if Standard == Ponencia, we duplicate text.
        # Let's assume recovered content (Ponencia/Dissent) is the source of truth.
        # We will Exclude the "Standard" file from content if explicit parts exist.
        
        has_ponencia = any("_Ponencia" in f.name for f in files)
        
        files_to_merge = []
        standard_file = None
        
        for f in files:
            if f.name == f"{base_name}.md":
                standard_file = f
            else:
                files_to_merge.append(f)
        
        # Sort the specific parts
        files_to_merge.sort(key=lambda x: get_sort_key(x.name))
        
        # Check integrity
        # If we have parts, we generally don't need the standard file (it was the 'colliding' output)
        # UNLESS we didn't recover a Ponencia for some reason?
        # But recovery script generated _Ponencia.
        # So safe to ignore standard file content, BUT we will overwrite it as the target.
        
        target_file = OUTPUT_DIR / f"{base_name}.md"
        
        merged_content = ""
        
        for i, part_file in enumerate(files_to_merge):
            try:
                with open(part_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                # Add Header if not first?
                # Or based on filename
                
                header = generate_header(part_file.name, base_name)
                
                if i > 0:
                     merged_content += f"\n\n\n{'-'*40}\n\n"
                     
                merged_content += f"{header}\n\n"
                merged_content += content
                
            except Exception as e:
                print(f"  Error reading {part_file}: {e}")
                
        # Write merged content
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(merged_content)
            
        print(f"  Merged to: {target_file.name}")
        
        # Delete constituent files (EXCEPT the target file if it was in the list, though files_to_merge excluded it)
        for part_file in files_to_merge:
            try:
                os.remove(part_file)
                # print(f"    Deleted: {part_file.name}")
            except Exception as e:
                print(f"    Error deleting {part_file.name}: {e}")
                
        merged_count += 1
        
    print(f"Merge Complete. Consolidated {merged_count} cases.")

def generate_header(filename, base_name):
    """
    Generates a markdown header based on the suffix.
    filename: G.R._No._123_Ponencia_Carpio.md
    base: G.R._No._123
    """
    name = filename.replace(base_name, "").replace(".md", "").strip("_")
    # Result: Ponencia_Carpio
    
    parts = name.split('_')
    type_map = {
        "Ponencia": "Main Decision",
        "Dissent": "Dissenting Opinion",
        "Separate": "Separate Opinion",
        "Concurring": "Concurring Opinion"
    }
    
    op_type = parts[0]
    readable_type = type_map.get(op_type, op_type)
    
    author = ""
    if len(parts) > 1:
        # Join rest as author?
        # remove counters if numeric
        rest = [p for p in parts[1:] if not p.isdigit()]
        if rest:
            author = " ".join(rest)
            
    header = f"# {readable_type}"
    if author:
        header += f" ({author})"
        
    return header

if __name__ == "__main__":
    main()
