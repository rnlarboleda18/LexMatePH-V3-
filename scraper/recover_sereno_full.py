
import sys
import os
import re
from bs4 import BeautifulSoup
from pathlib import Path

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from convert_html_to_markdown import CaseConverter
except ImportError:
    # Fallback if running from scratch dir but convert is in sc_scraper
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sc_scraper"))
    from convert_html_to_markdown import CaseConverter

files = [
    r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\2018\may\399.html",
    r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\2018\may\394.html",
    r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\2018\may\400.html",
    r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\2018\may\395.html",
    r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\2018\may\393.html",
    r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\2018\may\389.html",
    r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\2018\may\392.html",
    r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\2018\may\391.html",
    r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\2018\may\397.html",
    r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\2018\may\398.html"
]

def main():
    print("Initializing converter...")
    converter = CaseConverter()
    converted_docs = [] # list of dicts

    print(f"Processing {len(files)} files...")
    for path in files:
        if not os.path.exists(path):
            print(f"Skipping missing file: {path}")
            continue
            
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        
        soup = BeautifulSoup(html, "lxml")
        
        # Classification
        text = soup.get_text(" ", strip=True)[:5000].upper()
        op_type = "Main"
        
        if "DISSENTING OPINION" in text: op_type = "Dissent"
        elif "SEPARATE OPINION" in text: op_type = "Separate"
        elif "CONCURRING OPINION" in text: op_type = "Concurring"
        elif "SEPARATE CONCURRING" in text: op_type = "Concurring"
        
        author = "Unknown"
        match = re.search(r'(?:JUSTICE|J\.)\s+([A-Z]+)', text)
        if match: author = match.group(1)
        
        if "389.html" in path:
            op_type = "Main"
            
        md_content = converter.clean_and_convert(html)
        
        converted_docs.append({
            "type": op_type,
            "author": author,
            "content": md_content,
            "path": path
        })

    # Sort
    main_docs = [d for d in converted_docs if d['type'] == 'Main']
    others = [d for d in converted_docs if d['type'] != 'Main']
    others.sort(key=lambda x: x['type'])
    final_docs = main_docs + others
    
    separator = "\n\n<br/><br/><hr style='border: 2px solid black;'/><br/><br/>\n\n"
    
    final_cleaned_content = []
    
    print("Reverting: Skipping regex cleaning...")
    for doc in final_docs:
        content = doc['content']
        
        # SKIP CLEANING STEPS
        # Just use raw content
        
        # Add Header
        header = f"# {doc['type']} Opinion"
        if doc['type'] == "Main": header = "# Main Decision"
        elif doc['author'] != "Unknown": header += f" ({doc['author']})"
        
        final_cleaned_content.append(f"{header}\n\n{content}")
        
    full_output = separator.join(final_cleaned_content)
    
    out_path = r"C:\Users\rnlar\.gemini\antigravity\scratch\MD converted final\G.R._No._237428_2018-05-11.md"
    
    # Force delete if exists
    if os.path.exists(out_path):
        os.remove(out_path)
    
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(full_output)
        
    print(f"Successfully Reverted (No Cleanup) to: {out_path}")

if __name__ == "__main__":
    main()
