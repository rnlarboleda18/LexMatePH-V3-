
import json
import re
import os
from pathlib import Path
from bs4 import BeautifulSoup
from convert_html_to_markdown import CaseConverter

# Configuration
SC_SCRAPER_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper")
REPORT_FILE = SC_SCRAPER_DIR / "collision_report.json"
OUTPUT_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\MD converted final")

class OpinionRecoverer:
    def __init__(self):
        self.converter = CaseConverter()
        
    def classify_opinion(self, soup):
        """
        Attempts to identify opinion type and author.
        Returns (type_slug, author_slug)
        e.g. ("Dissent", "Carpio"), ("Separate", "Leonen"), ("Main", None)
        """
        text = soup.get_text(" ", strip=True)[:3000].upper()
        
        op_type = "Main"
        if "DISSENTING OPINION" in text:
            op_type = "Dissent"
        elif "SEPARATE OPINION" in text:
            op_type = "Separate"
        elif "CONCURRING OPINION" in text:
            op_type = "Concurring"
        elif "SEPARATE CONCURRING OPINION" in text:
            op_type = "Concurring"
            
        # Author Extraction Heuristic
        # Extract patterns like "JUSTICE [NAME]:"
        author = "Unknown"
        match = re.search(r'(?:JUSTICE|J\.)\s+([A-Z]+)', text)
        if match:
            author = match.group(1)
            
        return op_type, author

    def run(self):
        if not REPORT_FILE.exists():
            print(f"Report not found: {REPORT_FILE}")
            return
            
        with open(REPORT_FILE, "r", encoding="utf-8") as f:
            report = json.load(f)
            
        collisions = report.get("distinct_collisions", {})
        print(f"Found {len(collisions)} collision groups to process.")
        
        processed_count = 0
        
        for key, files in collisions.items():
            print(f"Processing Group: {key} ({len(files)} files)")
            
            used_filenames = set()
            
            for file_info in files:
                path = file_info['path']
                
                # Extract year/month from path for better date accuracy
                path_parts = Path(path).parts
                year = None
                month = None
                if len(path_parts) >= 3:
                    for part in path_parts:
                        if part.isdigit() and len(part) == 4:
                            year = part
                            try:
                                 idx = path_parts.index(part)
                                 if idx + 1 < len(path_parts):
                                     month = path_parts[idx+1]
                            except:
                                pass
                            break

                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        html_content = f.read()
                        
                    soup = BeautifulSoup(html_content, "lxml")
                    op_type, author = self.classify_opinion(soup)
                    
                    suffix = ""
                    if op_type != "Main":
                        suffix = f"_{op_type}"
                        if author and author != "Unknown":
                            suffix += f"_{author}"
                    else:
                        suffix = "_Ponencia" 
                        if author and author != "Unknown":
                            suffix += f"_{author}"
                            
                    case_number = self.converter.extract_case_number(html_content, soup)
                    date = self.converter.extract_date(soup, year, month)
                    
                    if not case_number or not date:
                         print(f"  Skipping {path}: Could not extract metadata.")
                         continue

                    # Sanitize
                    clean_case_num = self.converter.sanitize_filename(self.converter.clean_case_number(case_number))
                    base_filename = f"{clean_case_num}_{date}"
                    
                    # Ensure Uniqueness
                    final_filename = f"{base_filename}{suffix}.md"
                    
                    counter = 1
                    while final_filename in used_filenames:
                        counter += 1
                        # Insert counter before .md
                        final_filename = f"{base_filename}{suffix}_{counter}.md"
                    
                    used_filenames.add(final_filename)
                    output_path = OUTPUT_DIR / final_filename
                    
                    markdown = self.converter.clean_and_convert(html_content)
                    
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(markdown)
                        
                    print(f"  Saved: {final_filename}")
                    processed_count += 1
                    
                except Exception as e:
                    print(f"  Error processing {path}: {e}")
                    
        print(f"Recovery Complete. Processed {processed_count} files.")

if __name__ == "__main__":
    recoverer = OpinionRecoverer()
    recoverer.run()
