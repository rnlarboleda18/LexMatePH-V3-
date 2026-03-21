
import sys
import shutil
from pathlib import Path

# Ensure we can import from the same directory
sys.path.append(str(Path(__file__).parent))

from lawphil_scraper import LawphilScraper
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

class LawphilCounter(LawphilScraper):
    def __init__(self, workers=20):
        # Use a dummy directory so we don't assume files exist (triggers "download" logic which is really "count" logic)
        temp_dir = Path("./temp_count_dir")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir()
        
        super().__init__(output_dir=temp_dir, workers=workers)
        
    def count_all(self, start_year=None):
        print("Fetching Year Index...")
        soup = self.get_soup(self.BASE_URL)
        if not soup: 
            print("Failed to fetch year index.")
            return

        years = []
        for a in soup.find_all('a', href=True):
            text = a.get_text().strip()
            if text.isdigit() and len(text) == 4:
                if start_year and int(text) < int(start_year): continue
                link = urljoin(self.BASE_URL, a['href'])
                years.append((text, link))
        
        years.sort(key=lambda x: x[0], reverse=True)
        print(f"Found {len(years)} years.")
        
        total_cases = 0
        year_counts = {}

        print(f"Counting cases with {self.workers} workers...")
        
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            future_to_year = {executor.submit(self.get_cases_for_year, y[0], y[1]): y[0] for y in years}
            
            for future in as_completed(future_to_year):
                year = future_to_year[future]
                try:
                    cases = future.result() # This returns list of URLs after exclusions
                    count = len(cases)
                    total_cases += count
                    year_counts[year] = count
                    print(f"  Year {year}: {count} valid cases found.")
                except Exception as e:
                    print(f"  Year {year}: Error {e}")
                    
        print(f"\n========================================")
        print(f"TOTAL CASES (After Exclusions): {total_cases}")
        print(f"========================================")
        
        # Breakdown
        print("\nBreakdown by Year:")
        for year in sorted(year_counts.keys(), reverse=True):
            print(f"{year}: {year_counts[year]}")
            
        # Cleanup
        try:
            shutil.rmtree(self.output_dir)
        except:
            pass

if __name__ == "__main__":
    counter = LawphilCounter()
    counter.count_all()
