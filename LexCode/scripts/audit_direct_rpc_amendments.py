
import os
import re
from pathlib import Path

def identify_direct_rpc_amendments():
    md_dir = Path(r"c:\Users\rnlar\.gemini\antigravity\scratch\LexMatePH v3\LexCode\Codals\md")
    if not md_dir.exists():
        print(f"Directory not found: {md_dir}")
        return

    # Direct amendment markers
    direct_markers = [
        re.compile(r"amended to read as follows", re.IGNORECASE),
        re.compile(r"inserted (?:as|after) Article [\d\-A-Z]+", re.IGNORECASE),
        re.compile(r"Article [\d\-A-Z]+ of (?:.*?) is (?:hereby )?amended", re.IGNORECASE)
    ]

    direct_amendments = []

    for file_path in md_dir.glob("*.md"):
        if file_path.name in ["RPC.md", "CIV_structured.md", "Labor_Code_Articles.md", "1987_Philippine_Constitution.md", "RCC_structured.md", "FC_structured.md"]:
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(5000) # Check more content
                
                # Must reference RPC
                if not re.search(r"Revised Penal Code|Act No\. 3815|Act 3815", content, re.IGNORECASE):
                    continue
                
                is_direct = any(p.search(content) for p in direct_markers)
                
                if is_direct:
                    # Extract title
                    lines = [l.strip() for l in content.split('\n') if l.strip()]
                    title = lines[0] if lines else "No title found"
                    
                    # Estimate article count
                    articles = re.findall(r"Article [\d\-A-Z]+", content, re.IGNORECASE)
                    article_count = len(set(articles))
                    
                    direct_amendments.append({
                        "filename": file_path.name,
                        "title": title,
                        "articles_mentioned": article_count
                    })
        except Exception as e:
            print(f"Error reading {file_path.name}: {e}")

    print("\n--- DIRECT RPC AMENDATORY LAWS (Textual Amendments) ---")
    for item in sorted(direct_amendments, key=lambda x: x['filename']):
        print(f"File: {item['filename']}")
        print(f"  Title: {item['title'][:100]}...")
        # print(f"  Estimated Articles: {item['articles_mentioned']}")
        print("-" * 60)

if __name__ == "__main__":
    identify_direct_rpc_amendments()
