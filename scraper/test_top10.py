"""
Test the footnote fix by converting the 10 largest HTML files
"""
import os
import sys
from pathlib import Path

# Add parent directory to path to import the converter
sys.path.insert(0, str(Path(__file__).parent))

from lawphil_converter_html_to_md import CaseConverter

# Get the 10 largest HTML files
html_dir = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_html")
output_dir = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_md2")

# Find all HTML files and sort by size
all_files = list(html_dir.rglob("*.html"))
all_files.sort(key=lambda x: x.stat().st_size, reverse=True)

# Get top 10
top_10 = all_files[:10]

print("=" * 80)
print("TESTING FOOTNOTE FIX WITH 10 LARGEST CASES")
print("=" * 80)
print("\nFiles to convert:")
for i, f in enumerate(top_10, 1):
    size_kb = f.stat().st_size / 1024
    print(f"{i}. {f.name} ({size_kb:.2f} KB)")

print(f"\nOutput directory: {output_dir}")
print("=" * 80)

# Create converter
converter = CaseConverter()

print(f"\nProcessing {len(top_10)} files...")

# Process each file
success_count = 0
errors = []

for i, html_file in enumerate(top_10, 1):
    print(f"\n[{i}/10] Processing: {html_file.name}")
    try:
        # Determine output path
        # Replicate logic: output_dir / relative_path_from_html_dir? 
        # Or just flat in output_dir?
        # The user requested C:\...\lawphil_md2, so let's put them there flat or subdir?
        # Let's put them flat for this test to match previous behavior
        
        name_no_ext = html_file.stem
        # Preserve year folder structure if possible?
        # html_dir is ...\lawphil_html
        # html_file is ...\lawphil_html\1994\file.html
        # rel_path = html_file.relative_to(html_dir)
        # out_path = output_dir / rel_path.with_suffix('.md')
        
        # Simple flat output for now as per previous test script behavior logic (it seemed to put them in subdirs actually? No, my previous script put them in subdirs because the converter did. This one separates logic.)
        
        # Let's flatten for simplicity in test_top10, or keep folders?
        # New converter doesn't auto-create subdirs unless I tell it.
        # Let's use the file name directly in output_dir.
        
        out_path = output_dir / f"{name_no_ext}.md"
        
        converter.process_file(str(html_file), str(out_path))
        print(f"    ✓ Success")
        success_count += 1
    except Exception as e:
        print(f"    ✗ Error: {e}")
        errors.append({"file": str(html_file), "error": str(e)})

# Print summary
print("\n" + "=" * 80)
print("CONVERSION SUMMARY")
print("=" * 80)
print(f"Processed: {len(top_10)}")
print(f"Success: {success_count}")
print(f"Failed: {len(errors)}")

if errors:
    print(f"\nErrors encountered: {len(errors)}")
    for err in errors:
        print(f"  - {err['file']}: {err['error']}")

print("\n✓ Test conversion complete!")
print(f"Output files saved to: {output_dir}")
