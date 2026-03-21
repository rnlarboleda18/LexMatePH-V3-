from lawphil_convert_html_to_markdown import CaseConverter
import os
from pathlib import Path

# Setup
source_file = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_html\1901\gr_l-299_1901.html"
output_dir = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\MD\debug"
os.makedirs(output_dir, exist_ok=True)

converter = CaseConverter()

print(f"Processing {source_file}...")
try:
    with open(source_file, 'r', encoding='cp1252', errors='replace') as f:
        html_content = f.read()
            
    # Convert
    full_content = converter.clean_and_convert(html_content)
    
    # Save
    output_path = Path(output_dir) / "G.R. No. L-299_Debug.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_content)
        
    print(f"Saved to {output_path}")
    print("Content Preview (First 500 chars):")
    print(full_content[:500])

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Error: {e}")
