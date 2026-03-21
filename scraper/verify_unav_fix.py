from convert_html_to_markdown import CaseConverter
from bs4 import BeautifulSoup
import os

files_to_test = [
    r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\1961\january\6.html",
    r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\1979\september\298.html",
    r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\1961\november\563.html",
    r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\1963\february\69.html" 
]

converter = CaseConverter()

print("--- Verifying Fix on Real Code ---")
for fpath in files_to_test:
    if os.path.exists(fpath):
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            soup = BeautifulSoup(content, 'html.parser')
            case_number = converter.extract_case_number(content, soup)
            print(f"File: {os.path.basename(fpath)}")
            print(f"  Extracted: {case_number}")
    else:
        print(f"File not found: {fpath}")
