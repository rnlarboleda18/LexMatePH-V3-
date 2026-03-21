import os
import time
import requests
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Import Converter
try:
    from lawphil_convert_html_to_markdown import CaseConverter as LawphilConverter
except ImportError:
    sys.path.append(str(Path(__file__).parent))
    from lawphil_convert_html_to_markdown import CaseConverter as LawphilConverter

# Setup Base Path
BASE_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_html")
# User requested output in lawphil_md (implied by "d files in this dir")
MD_OUTPUT_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_md")

class LawphilScraper:
    BASE_URL = "https://lawphil.net/judjuris/judjuris.html"
    
    def __init__(self, output_dir=BASE_DIR, delay=1.0, workers=10, test_limit=None, download_only=False, overwrite=False):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.md_output_dir = Path(MD_OUTPUT_DIR)
        self.md_output_dir.mkdir(parents=True, exist_ok=True)
        
        self.delay = delay
        self.workers = workers
        self.test_limit = test_limit 
        self.download_only = download_only
        self.overwrite = overwrite
        
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) LawphilBot/1.0'})
        
        # Robust Retry Logic
        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        self.visited_log = self.output_dir / "visited_urls.json"
        self.visited = self.load_visited()
        
        self.converter = LawphilConverter(output_dir=self.md_output_dir)

    def load_visited(self):
        if self.visited_log.exists():
            try:
                with open(self.visited_log, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            except: return set()
        return set()
    
    def save_visited(self):
        with open(self.visited_log, 'w', encoding='utf-8') as f:
            json.dump(list(self.visited), f)
            
    def get_soup(self, url):
        try:
            resp = self.session.get(url, timeout=20)
            if resp.status_code == 404: return None
            # Handle encoding robustly
            if resp.encoding == 'ISO-8859-1':
                resp.encoding = 'cp1252' 
            return BeautifulSoup(resp.content, 'html.parser')
        except Exception as e:
            # print(f"Error fetching {url}: {e}")
            return None

    def crawl_all(self, start_year=None):
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
        
        all_case_urls = []
        
        # Phase 1: Collect Case URLs
        print(f"Phase 1: Collecting URLs with {self.workers} workers...")
        
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            future_to_year = {executor.submit(self.get_cases_for_year, y[0], y[1]): y[0] for y in years}
            
            for future in as_completed(future_to_year):
                year = future_to_year[future]
                try:
                    cases = future.result()
                    all_case_urls.extend([(year, c) for c in cases])
                    print(f"  Year {year}: Found {len(cases)} cases.")
                except Exception as e:
                    print(f"  Year {year}: Error {e}")
                    
        print(f"Phase 1 Complete. Total Cases Found: {len(all_case_urls)}")
        
        # Phase 2: Download & Convert
        print(f"Phase 2: Processing Cases with {self.workers} workers...")
        
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            future_to_case = {executor.submit(self.process_single_case, year, url): url for year, url in all_case_urls}
            
            completed = 0
            for future in as_completed(future_to_case):
                completed += 1
                if completed % 50 == 0:
                     print(f"Progress: {completed}/{len(all_case_urls)}...")
        
        self.save_visited()

    def get_cases_for_year(self, year, year_url):
        soup = self.get_soup(year_url)
        if not soup: return []
        
        months = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if f"juri{year}.html" in href and len(href) < 20: continue
            if "/" in href and ".html" in href:
                 months.append(urljoin(year_url, href))
        months = list(set(months))
        
        case_urls = []
        for month_url in months:
             if self.test_limit and len(case_urls) >= self.test_limit: break
             
             m_soup = self.get_soup(month_url)
             if not m_soup: continue
             
             for a in m_soup.find_all('a', href=True):
                  href = a['href']
                  text = a.get_text().strip()
                  if href.lower().startswith(('javascript:', 'mailto:', '#')): continue
                  if href.lower().endswith('.pdf'): continue 

                  # --- FILTERING LOGIC START ---
                  
                  # 1. Filter Top/Index Pages
                  # Matches juri2021.html, oct2021.html, etc.
                  if re.search(r'(juri\d{4}|[a-z]+\d{4})\.html$', href, re.IGNORECASE):
                      continue
                  if text.upper() in ['BACK', 'TOP']:
                      continue

                  # 2. Filter Separate Opinions
                  # URL Check
                  if '_so_' in href.lower(): 
                      continue
                  
                  # Basename Check (heuristic: usually ends in digits or _year)
                  # If it ends in letters (e.g. _sereno.html), it's likely an opinion
                  basename_no_ext = href.split('/')[-1].replace('.html', '')
                  if not re.search(r'(_\d{4}|\d+)$', basename_no_ext):
                       # Suspicious, likely a named opinion file like 'gr_..._leonen.html'
                       # But be careful of edge cases.
                       # User example: gr_227670_a-reyes.html -> should skip
                       continue

                  # Text Check
                  if text.upper().startswith(('J.', 'JUSTICE')):
                      continue
                  if 'OPINION' in text.upper():
                      continue
                  
                  # --- FILTERING LOGIC END ---

                  if month_url.split('/')[-1] in href: continue 
                  full_url = urljoin(month_url, href)
                  
                  # VALIDATION LOGIC:
                  # Don't trust self.visited blindly. Check if file exists and is good.
                  basename = full_url.split('/')[-1]
                  if not basename.lower().endswith('.pdf') and not basename.endswith('.html'): 
                      basename += '.html'
                  
                  file_path = self.output_dir / str(year) / basename
                  
                  # If file exists and > 2KB, assume valid and skip (UNLESS OVERWRITE)
                  if not self.overwrite and file_path.exists() and file_path.stat().st_size > 2000:
                      continue
                      
                  # If file is missing or small (or overwrite), add to list (re-download)
                  case_urls.append(full_url)
                  
                  if self.test_limit and len(case_urls) >= self.test_limit: break
        
        return case_urls

    def process_single_case(self, year, case_url):
        try:
            # 1. Download
            resp = self.session.get(case_url, timeout=30) # Increased timeout
            if resp.status_code == 404: 
                # print(f"404: {case_url}")
                return

            # Content-Type Validation
            content_type = resp.headers.get('Content-Type', '').lower()
            if 'application/pdf' in content_type:
                print(f"Skipping PDF content: {case_url}")
                return
                
            resp.encoding = resp.apparent_encoding
            content = resp.text
            
            if len(content) < 500: # Suspiciously small
                print(f"Warning: Small content for {case_url} ({len(content)} bytes)")
                # Don't return, save it anyway but maybe don't mark visited? 
                # Actually, if it's the real page, we should save it.
            
            # Save HTML
            year_dir = self.output_dir / str(year)
            year_dir.mkdir(parents=True, exist_ok=True)
            
            basename = case_url.split('/')[-1]
            if not basename.lower().endswith('.pdf') and not basename.endswith('.html'): 
                basename += '.html'
            
            html_path = year_dir / basename
            with open(html_path, 'w', encoding='utf-8', errors='replace') as f:
                f.write(content)
            
            # Only add to visited if successful write
            if html_path.exists() and html_path.stat().st_size > 0:
                self.visited.add(case_url)

            if self.download_only: return

            # 2. Convert using Legacy Converter (as requested)
            # Legacy process_file signature: process_file(self, html_path, metadata=None, use_llm=False, overwrite=False)
            result = self.converter.process_file(html_path, overwrite=True)
            if result.get('status') == 'failed':
                 print(f"Conversion Failed {basename}: {result.get('error')}")
            
        except Exception as e:
            print(f"Error processing {case_url}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=10, help="Number of workers")
    parser.add_argument("--limit", type=int, default=None, help="Process only N cases per year")
    parser.add_argument("--start", type=int, default=None, help="Start year")
    parser.add_argument("--download-only", action="store_true", help="Download HTML only, do not convert")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files (Full Rescrape)")
    args = parser.parse_args()
    
    scraper = LawphilScraper(workers=args.workers, test_limit=args.limit, download_only=args.download_only, overwrite=args.overwrite)
    scraper.crawl_all(start_year=args.start)
