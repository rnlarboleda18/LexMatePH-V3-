
from bs4 import BeautifulSoup
from convert_html_to_markdown import CaseConverter
import hashlib
from pathlib import Path

def compute_content_hash(soup):
    text = soup.get_text(separator=" ", strip=True)
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def debug_process(file_path):
    print(f"Testing: {file_path}")
    try:
        converter = CaseConverter()
        print("Converter initialized.")
        
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        print(f"Read {len(content)} bytes.")
        
        soup = BeautifulSoup(content, "lxml")
        print("Soup parsed.")
        
        case_number = converter.extract_case_number(soup)
        print(f"Case Number: {case_number}")
        
        date = converter.extract_decision_date(soup)
        print(f"Date: {date}")
        
        if not case_number or not date:
            print("Extraction failed.")
            return None
            
        case_key = f"{case_number}_{date}"
        print(f"Key: {case_key}")
        
        file_hash = compute_content_hash(soup)
        print(f"Hash: {file_hash}")
        
        return "Success"
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_file = r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads\2018\may\389.html"
    debug_process(test_file)
