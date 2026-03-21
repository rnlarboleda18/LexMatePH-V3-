import re
import sys
import io
from bs4 import BeautifulSoup

# Force UTF-8 stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def debug_ponente(html_path):
    print(f"Debugging {html_path}...")
    with open(html_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    
    # Simulate cleaning
    if soup.head: soup.head.decompose()
    lawphil_table = soup.find('table', id='lwphl')
    if lawphil_table:
        content_block = lawphil_table.find('blockquote')
        if content_block:
             soup = BeautifulSoup(str(content_block), 'html.parser')
    
    paragraphs = soup.find_all('p', limit=50)
    print(f"Scanning {len(paragraphs)} paragraphs (Cleaned)...")
    
    for i, p in enumerate(paragraphs):
        p_text = p.get_text().strip()
        print(f"[{i}] '{p_text}'")
        
        # Test Regex
        regex = r"^([A-Z\s\.]+),\s*(?:C\.?J\.?|J\.?|JJ\.?|P\.?)\.?:?$"
        match = re.search(regex, p_text)
        if match:
             print(f"  MATCH: {match.group(1)}")
             name = p_text.split(",")[0].strip()
             print(f"  EXTRACTED: {name}")

debug_ponente(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_html\2024\ac_11433_2024.html")
