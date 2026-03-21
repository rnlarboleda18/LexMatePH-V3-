from convert_html_to_markdown import CaseConverter
from bs4 import BeautifulSoup
import os
import re

files_to_test = [
    r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\2022\february\31.html",
    r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\2021\september\872.html",
    r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\2021\may\577.html",
    r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\2021\january\300.html",
    r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\2021\january\272.html"
]

converter = CaseConverter()

print("--- DEBUGGING 2020s FAILURES ---")
for fpath in files_to_test:
    if os.path.exists(fpath):
        print(f"\nProcessing: {os.path.basename(fpath)}")
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            soup = BeautifulSoup(content, 'html.parser')
            
            # 1. Try standard extraction
            case_number = converter.extract_case_number(content, soup)
            print(f"  Result: {case_number}")
            
            if not case_number:
                # 2. Dump Title and H1/H2 for analysis if it fails
                print("  [ANALYSIS]")
                title = soup.find('title')
                if title:
                    print(f"  Title: {title.get_text().strip()}")
                
                for h1 in soup.find_all('h1'):
                    print(f"  H1: {h1.get_text().strip()}")
                
                # Check for J.I.B. or other patterns
                text = soup.get_text()
                match = re.search(r'(J\.?\s*I\.?\s*B\.?\s*No\.?\s*[^,:\-]+)', text, re.IGNORECASE)
                if match:
                     print(f"  Found J.I.B. pattern: {match.group(1)}")

    else:
        print(f"File not found: {fpath}")
