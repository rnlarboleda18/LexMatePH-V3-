import os
import time
import requests
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURATION ---
GR_LIST_PATH = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\scripts\gr_rescape_list.txt"
OUTPUT_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_html_scraped")
MAX_WORKERS = 5
BASE_URL = "https://lawphil.net/judjuris/judjuris.html"

def normalize_gr(gr):
    """Normalize G.R. No. for comparison: uppercase, remove spaces, dots, and select first if range."""
    if not gr: return ""
    gr = gr.upper().replace("G.R.", "").replace("NO.", "").replace(".", "").replace(" ", "").strip()
    # Handle ranges like 105402-04 -> 105402
    if "-" in gr:
        # Check if it's L-12345 or just 12345-46
        if gr.startswith("L-"):
             pass # Keep L- prefix
        else:
             gr = gr.split("-")[0]
    return gr

class TargetedLawphilCrawler:
    def __init__(self, targets, output_dir=OUTPUT_DIR, workers=5):
        self.targets = {normalize_gr(t): t for t in targets}
        self.found = {} # normalized -> full_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.workers = workers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) LawphilRescraper/1.0'
        })

    def get_soup(self, url):
        try:
            resp = self.session.get(url, timeout=20)
            if resp.status_code == 200:
                return BeautifulSoup(resp.content, 'html.parser')
        except: pass
        return None

    def find_cases_on_page(self, url, year):
        soup = self.get_soup(url)
        if not soup: return
        
        links = soup.find_all('a', href=True)
        for a in links:
            text = a.get_text().strip()
            href = a['href']
            
            # Check if text contains any of our targets
            norm_text = normalize_gr(text)
            if norm_text in self.targets:
                full_url = urljoin(url, href)
                self.found[norm_text] = (full_url, year)
                print(f"[FOUND] {self.targets[norm_text]} at {full_url}")

    def crawl_all_years(self, start_year=1975, end_year=2025):
        print(f"Crawling Lawphil indices from {start_year} to {end_year}...")
        
        # Step 1: Get Years
        soup = self.get_soup(BASE_URL)
        if not soup:
            print("Failed to fetch main index.")
            return

        years_to_crawl = []
        for a in soup.find_all('a', href=True):
            text = a.get_text().strip()
            if text.isdigit() and start_year <= int(text) <= end_year:
                years_to_crawl.append((text, urljoin(BASE_URL, a['href'])))
        
        # Step 2: For each year, get months
        for year, year_url in sorted(years_to_crawl, reverse=True):
            if not self.targets: break
            
            print(f"Checking Year {year}...")
            y_soup = self.get_soup(year_url)
            if not y_soup: continue
            
            month_urls = []
            for a in y_soup.find_all('a', href=True):
                href = a['href']
                # Month pages usually look like jan2015/jan2015.html
                if f"juri{year}.html" in href and len(href) < 20: continue # Skip main year index in itself
                if "/" in href and ".html" in href:
                    month_urls.append(urljoin(year_url, href))
            
            month_urls = list(set(month_urls))
            
            # Step 3: Scan each month page
            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                futures = [executor.submit(self.find_cases_on_page, m_url, year) for m_url in month_urls]
                for f in as_completed(futures):
                    pass # Result is stored in self.found

    def download_found_cases(self):
        print(f"\nDownloading {len(self.found)} found cases...")
        
        def download_one(norm_gr, info):
            url, year = info
            try:
                resp = self.session.get(url, timeout=30)
                if resp.status_code == 200:
                    year_dir = self.output_dir / year
                    year_dir.mkdir(parents=True, exist_ok=True)
                    filename = url.split('/')[-1]
                    save_path = year_dir / filename
                    with open(save_path, 'w', encoding='utf-8', errors='replace') as f:
                        f.write(resp.text)
                    return True
            except: pass
            return False

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = [executor.submit(download_one, k, v) for k, v in self.found.items()]
            success = 0
            for f in as_completed(futures):
                if f.result(): success += 1
        
        print(f"Download Complete: {success}/{len(self.found)}")

if __name__ == "__main__":
    with open(GR_LIST_PATH, 'r') as f:
        grs = [line.strip() for line in f if line.strip()]
    
    crawler = TargetedLawphilCrawler(grs, workers=MAX_WORKERS)
    crawler.crawl_all_years()
    crawler.download_found_cases()
    
    # Report missing
    found_norm = set(crawler.found.keys())
    missing = [g for g in grs if normalize_gr(g) not in found_norm]
    
    with open("targeted_crawler_missing.txt", "w") as f:
        for m in missing:
            f.write(f"{m}\n")
    
    print(f"\nFinal Report: Found {len(crawler.found)}, Missing {len(missing)}")
    if missing:
        print(f"Missing list saved to targeted_crawler_missing.txt")
