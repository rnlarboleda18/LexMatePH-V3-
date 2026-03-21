import re
from pathlib import Path

# Directory containing converted markdown files
md_dir = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_md2")

print(f"Verifying markdown files in: {md_dir}")
print("=" * 80)

files = list(md_dir.rglob("*.md"))
files.sort(key=lambda x: x.stat().st_size, reverse=True)

if not files:
    print("No markdown files found!")
    exit(1)

for f in files:
    try:
        content = f.read_text(encoding="utf-8")
        
        # Regex for markers in text: [^1], [^2], etc. (negative lookahead for colon to avoid matching definitions)
        # Note: This is a simple check; it might overcount if markers are discussed in text, but good enough for verification.
        markers = re.findall(r'\[\^(\d+)\](?!:)', content)
        
        # Regex for definitions: [^1]: ... at start of line
        definitions = re.findall(r'^\s*\[\^(\d+)\]:', content, re.MULTILINE)
        
        has_footer = "### Footnotes" in content
        
        marker_count = len(markers)
        def_count = len(definitions)
        
        # Check for duplicate definitions (IDs should be unique)
        unique_defs = len(set(definitions))
        duplicate_defs = def_count - unique_defs
        
        status = "✓"
        if marker_count == 0 and def_count == 0:
            status = "-" # No footnotes
        elif def_count == 0 and marker_count > 0:
            status = "✗ MISSING DEFS"
        elif duplicate_defs > 0:
            status = "✗ DUPLICATES"
        elif abs(marker_count - def_count) > 5: # Allow some drift if markers are repeated
             # Ideally definitions should match unique markers, but let's just inspect counts
            status = "?" 

        print(f"\nFile: {f.name}")
        print(f"  Size: {f.stat().st_size / 1024:.2f} KB")
        print(f"  Status: {status}")
        print(f"  Markers found: {marker_count}")
        print(f"  Definitions found: {def_count}")
        print(f"  Duplicate definitions: {duplicate_defs}")
        print(f"  Has '### Footnotes' header: {has_footer}")
        
        if def_count > 0:
            # Check for blockquote artifacts in definitions
            blockquote_artifacts = re.findall(r'^\s*\[\^(\d+)\]:\s*>', content, re.MULTILINE)
            if blockquote_artifacts:
                print(f"  ✗ WARNING: Found {len(blockquote_artifacts)} definitions with leading '>' artifacts!")
                for bad_id in blockquote_artifacts[:3]:
                    print(f"    - [^{bad_id}]")

    except Exception as e:
        print(f"Error reading {f.name}: {e}")

print("\n" + "=" * 80)
print("Verification Complete")
