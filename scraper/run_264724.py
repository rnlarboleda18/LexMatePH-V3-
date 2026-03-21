
import os
import sys
from pathlib import Path
from lawphil_convert_html_to_markdown import CaseConverter, OUTPUT_DIR

# Set encoding to UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# Correct path to the specific file
target_file = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_html\2025\gr_264724_2025.html"

print(f"Processing single file: {target_file}")

# Initialize converter with correct output dir matching user's workflow
custom_output = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\MD\lawphil_v2")
converter = CaseConverter(output_dir=custom_output)

# Run process
result = converter.process_file(target_file, overwrite=True)

if result:
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        print(f"Output MD: {result.get('entry', {}).get('output_md')}")
    else:
        print(f"Status: failed")
        import traceback
        traceback.print_exc()
        print(f"Error: {result.get('error')}")