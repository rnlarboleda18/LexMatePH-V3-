import re
from bs4 import BeautifulSoup

def extract_case_number_v2(html_content, file_path):
    soup = BeautifulSoup(html_content, 'html.parser')
    text = soup.get_text(" ", strip=True)
    
    # Current pattern (simplified)
    current_prefix_pattern = r'(?:G\.\s*R\.|A\.\s*C\.|A\.\s*M\.|B\.\s*M\.)'
    
    # Proposed new pattern
    # Adds: UNAV, Adm. Case, Adm. Matter, U.D.K (just in case)
    new_prefix_pattern = r'(?:G\.\s*R\.|A\.\s*C\.|A\.\s*M\.|B\.\s*M\.|Adj\.\s*Res\.|Adm\.\s*Case|Adm\.\s*Matter|UNAV)'
    
    # Test 1: Title Tag
    title_tag = soup.find('title')
    if title_tag:
        title_text = title_tag.get_text().strip()
        print(f"Title: {title_text}")
        
        match_current = re.search(f'({current_prefix_pattern}\s*No\.?\s*[^,]+)', title_text, re.IGNORECASE)
        print(f"  Current Regex Match: {match_current.group(1) if match_current else 'None'}")
        
        # For UNAV, it might not have "No."
        match_new = re.search(f'({new_prefix_pattern}\s*(?:No\.?)?\s*[^,:\-]+)', title_text, re.IGNORECASE)
        print(f"  New Regex Match:     {match_new.group(1) if match_new else 'None'}")

    # Test 2: Fallback to UNAV specific check if standard fails
    if "UNAV" in text:
         match_unav = re.search(r'(UNAV\s*[^,:\-]+)', text)
         print(f"  UNAV Text Match:     {match_unav.group(1) if match_unav else 'None'}")

files_to_test = [
    r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\1961\january\6.html",
    r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\1979\september\298.html",
    r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\1961\november\563.html"
]

print("--- Starting Debug ---")
for fpath in files_to_test:
    print(f"\nProcessing: {fpath}")
    try:
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            extract_case_number_v2(content, fpath)
    except FileNotFoundError:
        print("  File not found.")
