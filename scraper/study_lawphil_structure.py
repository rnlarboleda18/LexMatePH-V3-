import os
import random
import re
from pathlib import Path
from bs4 import BeautifulSoup

# Config
DATA_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_html")
OUTPUT_REPORT = Path("c:/Users/rnlar/.gemini/antigravity/scratch/sc_scraper/structure_study.txt")

def analyze_file(html_path, year):
    try:
        with open(html_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # 1. Header Analysis (Division/En Banc)
        text = soup.get_text()
        headers = []
        for kw in ["EN BANC", "FIRST DIVISION", "SECOND DIVISION", "THIRD DIVISION"]:
            if re.search(fr"\b{kw}\b", text, re.IGNORECASE):
                headers.append(kw)
        
        # 2. Ponente Analysis
        ponente_candidates = []
        
        # Priority 1: Explicit "Ponente: NAME"
        match = re.search(r"Ponente:?\s*([A-Z\.\s]+)", text, re.IGNORECASE)
        if match:
            ponente_candidates.append(f"Explicit: {match.group(1).strip()[:50]}")
            
        # Priority 2: "NAME, J.:" (Classic format start of opinion)
        # Matches "LEONEN, J.:" or "PER CURIAM:"
        # Look in the first 2000 chars to avoid signatures at bottom
        start_text = text[:8000]
        
        # Catch "Per Curiam"
        if re.search(r"\bPer\s+Curiam:?", start_text, re.IGNORECASE):
             ponente_candidates.append("Per Curiam")
             
        # Catch "NAME, J.:"
        j_match = re.search(r"([A-Z\s\.]+),\s*J\.?:", start_text)
        if j_match:
             ponente_candidates.append(f"J_Format: {j_match.group(1).strip()}")

        # Priority 3: "By: NAME"
        by_match = re.search(r"By:?\s+([A-Z\s\.]+)", start_text)
        if by_match:
             ponente_candidates.append(f"By_Format: {by_match.group(1).strip()[:30]}")

        # 3. Citation Analysis (Quick check for 'Id.', 'Rollo', 'Art.', 'Sec.')
        citations = []
        if "Id." in text: citations.append("Id.")
        if "Rollo" in text: citations.append("Rollo")
        if "CONST." in text or "Constitution" in text: citations.append("Constitution")
        
        print(f"[{year}] {html_path.name}")
        print(f"  Headers: {headers}")
        print(f"  Ponente: {ponente_candidates}")
        print("-" * 40)
        
        return {
            "year": year,
            "file": html_path.name,
            "headers": headers,
            "ponente": ponente_candidates,
            "structure_len": len(text)
        }

    except Exception as e:
        print(f"Error reading {html_path}: {e}")
        return None

def main():
    years = sorted([int(d) for d in os.listdir(DATA_DIR) if d.isdigit() and 1980 <= int(d) <= 2024])
    print(f"Found years: {min(years)} to {max(years)}")
    
    results = []
    
    for year in years:
        year_path = DATA_DIR / str(year)
        files = [f for f in os.listdir(year_path) if f.endswith(".html") and not f.endswith(".pdf.html") and not f.endswith("#top.html")]
        
        if not files:
            continue
            
        # seed random for reproducibility
        random.seed(42)  
        # Take 1 random file (or fixed if needed)
        sample = random.choice(files)
        
        res = analyze_file(year_path / sample, year)
        if res: results.append(res)
        
    print("\nComplete.")

if __name__ == "__main__":
    main()
