
import os
import re
from pathlib import Path

def identify_direct_rpc_amendments():
    md_dir = Path(r"c:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3\LexCode\Codals\md")
    if not md_dir.exists():
        print(f"Directory not found: {md_dir}")
        return

    # Direct amendment markers (more robust)
    direct_markers = [
        re.compile(r"amended to read as follows", re.IGNORECASE),
        re.compile(r"inserted to read as follows", re.IGNORECASE),
        re.compile(r"hereby inserted to read as follows", re.IGNORECASE),
        re.compile(r"hereby amended to read as follows", re.IGNORECASE),
        re.compile(r"is hereby amended", re.IGNORECASE),
        re.compile(r"following (?:.*?) is (?:hereby )?inserted", re.IGNORECASE),
        re.compile(r"Article [\d\-A-Z]+ (?:.*?) (?:is|are) (?:hereby )?amended", re.IGNORECASE)
    ]

    direct_amendments = []

    for file_path in md_dir.glob("*.md"):
        if file_path.name in ["RPC.md", "CIV_structured.md", "Labor_Code_Articles.md", "1987_Philippine_Constitution.md", "RCC_structured.md", "FC_structured.md"]:
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(10000) # Check even more content
                
                # Must reference RPC
                if not re.search(r"Revised Penal Code|Act No\. 3815|Act 3815", content, re.IGNORECASE):
                    continue
                
                is_direct = any(p.search(content) for p in direct_markers)
                
                if is_direct:
                    # Extract title
                    lines = [l.strip() for l in content.split('\n') if l.strip()]
                    # Title might be inside --- or just the first bold line
                    title = "No title found"
                    for line in lines:
                        if line.startswith("#"):
                            title = line.strip("# ")
                            break
                        if line.startswith("**REPUBLIC ACT") or line.startswith("**ACT") or line.startswith("**COMMONWEALTH"):
                            title = line.strip("* ")
                            break
                        if len(line) > 10 and not line.startswith("---") and not line.startswith("*"):
                            title = line
                            break
                    
                    direct_amendments.append({
                        "filename": file_path.name,
                        "title": title
                    })
        except Exception as e:
            print(f"Error reading {file_path.name}: {e}")

    print("\n--- FINAL LIST OF DIRECT RPC AMENDATORY LAWS ---")
    for item in sorted(direct_amendments, key=lambda x: x['filename']):
        print(f"File: {item['filename']}")
        print(f"  Title: {item['title'][:120]}...")
        print("-" * 80)

if __name__ == "__main__":
    identify_direct_rpc_amendments()
