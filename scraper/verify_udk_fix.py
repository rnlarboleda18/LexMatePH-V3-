
import os
import re
from bs4 import BeautifulSoup
from convert_html_to_markdown import CaseConverter

def verify_udk(file_path):
    print(f"Verifying {file_path}...")
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    converter = CaseConverter()
    soup = BeautifulSoup(content, 'lxml')
    
    case_number = converter.extract_case_number(content, soup)
    print(f"Extracted Case Number: {case_number}")
    
    if case_number and "UDK" in case_number:
        print("SUCCESS: UDK case number extracted.")
    else:
        print("FAILURE: Could not extract UDK case number.")

if __name__ == "__main__":
    # Test with 577.html (UDK 16838)
    verify_udk(r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\2021\may\577.html")
    # Test with 31.html (UDK 16915)
    verify_udk(r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\2022\february\31.html")
