
import os
import re
from pathlib import Path

def identify_rpc_amendments():
    md_dir = Path(r"c:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3\LexCode\Codals\md")
    if not md_dir.exists():
        print(f"Directory not found: {md_dir}")
        return

    rpc_patterns = [
        re.compile(r"Revised Penal Code", re.IGNORECASE),
        re.compile(r"Act (?:No\.\s*)?3815", re.IGNORECASE),
        re.compile(r"amending (?:.*?) (?:Revised Penal Code|Act 3815)", re.IGNORECASE),
        re.compile(r"An Act (?:.*?) Revised Penal Code", re.IGNORECASE)
    ]

    amendatory_files = []

    for file_path in md_dir.glob("*.md"):
        # Skip known base codes or unrelated files if obvious
        if file_path.name in ["RPC.md", "CIV_structured.md", "Labor_Code_Articles.md", "1987_Philippine_Constitution.md", "RCC_structured.md", "FC_structured.md"]:
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Read only first 2000 chars for identification
                content = f.read(2000)
                
                is_rpc = any(p.search(content) for p in rpc_patterns)
                
                if is_rpc:
                    # Try to extract a title (usually first non-empty line)
                    lines = [l.strip() for l in content.split('\n') if l.strip()]
                    title = lines[0] if lines else "No title found"
                    amendatory_files.append({
                        "filename": file_path.name,
                        "title": title
                    })
        except Exception as e:
            print(f"Error reading {file_path.name}: {e}")

    print("\n--- Identified RPC Amendatory Laws ---")
    for item in sorted(amendatory_files, key=lambda x: x['filename']):
        print(f"File: {item['filename']}")
        print(f"  Title: {item['title'][:100]}...")
        print("-" * 40)

if __name__ == "__main__":
    identify_rpc_amendments()
