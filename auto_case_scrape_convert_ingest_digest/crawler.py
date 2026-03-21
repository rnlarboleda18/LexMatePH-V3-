import os
import requests
import re
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Should point to C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_html
OUTPUT_DIR = Path(BASE_DIR).parent / "data" / "lawphil_html"
TARGET_LIST_FILE = os.path.join(BASE_DIR, "target_list.txt")
MAX_WORKERS = 10
BASE_URL = "https://lawphil.net/judjuris/judjuris.html"

def normalize_gr(gr):
    """Normalize Case No. Uppercase, remove spaces/dots."""
    if not gr: return ""
    # Remove G.R., No., spaces, dots
    clean = re.sub(r'[Gg]\.?[Rr]\.?|No\.?|\s|\.', '', gr).upper()
    return clean

def parse_target_list(filepath):
    """Extracts Case Numbers from the list."""
    targets = {}
    with open(filepath, 'r') as f:
        for line in f:
            if not line.strip(): continue
            # Extract content strictly inside parens matching pattern
            # Jaka Food v. Pacot (G.R. No. 151358, Mar 28, 2005)
            # Regex: ( (G.R. No. ...|A.M. No. ...), Date )
            
            # Simple approach: Find "G.R. No. XXX" or "A.M. No. XXX"
            match = re.search(r'((?:G\.R\.|A\.M\.|A\.C\.|B\.M\.).+?)(?:,|$)', line)
            if match:
                raw_case_no = match.group(1).strip()
                norm = normalize_gr(raw_case_no)
                targets[norm] = raw_case_no
            else:
                print(f"Warning: Could not extract Case No from: {line.strip()}")
    return targets

class TargetedCrawler:
    def __init__(self, targets, output_dir, workers=10):
        self.targets = targets # Dict {Norm: Raw}
        self.found = {}
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.workers = workers
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) LawphilAuto/1.0'})

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

        for a in soup.find_all('a', href=True):
            text = a.get_text().strip()
            href = a['href']
            
            if href.lower().endswith('.pdf'): continue

            norm_text = normalize_gr(text)
            
            for t_norm, t_raw in self.targets.items():
                if t_norm in norm_text:
                    full_url = urljoin(url, href)
                    if t_norm not in self.found:
                        self.found[t_norm] = (full_url, year)
                        print(f"[FOUND] {t_raw} -> {full_url}")
                        self.download_single(full_url, year)

    def download_single(self, url, year):
        try:
            resp = self.session.get(url, timeout=30)
            if resp.status_code == 200:
                y_dir = self.output_dir / year
                y_dir.mkdir(parents=True, exist_ok=True)
                fname = url.split('/')[-1]
                save_path = y_dir / fname
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(resp.text)
                print(f"[SAVED] {save_path}")
        except Exception as e:
            print(f"[ERROR] Failed to save {url}: {e}")

    def crawl(self):
        print(f"Crawling for {len(self.targets)} targets...")
        
        soup = self.get_soup(BASE_URL)
        if not soup: return

        years_to_crawl = []
        for a in soup.find_all('a', href=True):
            text = a.get_text().strip()
            if text.isdigit() and 1901 <= int(text) <= 2025:
                years_to_crawl.append((text, urljoin(BASE_URL, a['href'])))
        
        years_to_crawl.sort(key=lambda x: int(x[0]), reverse=True)

        for year, year_url in years_to_crawl:
            if len(self.found) >= len(self.targets): 
                print("All targets found. Stopping.")
                break
            
            print(f"Scanning {year}...")
            y_soup = self.get_soup(year_url)
            if not y_soup: continue

            month_urls = []
            for a in y_soup.find_all('a', href=True):
                href = a['href']
                if f"juri{year}.html" in href: continue
                if "/" in href and ".html" in href:
                    month_urls.append(urljoin(year_url, href))
            
            month_urls = list(set(month_urls))

            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                futures = [executor.submit(self.find_cases_on_page, m, year) for m in month_urls]
                for f in as_completed(futures): pass

if __name__ == "__main__":
    targets = parse_target_list(TARGET_LIST_FILE)
    crawler = TargetedCrawler(targets, OUTPUT_DIR, workers=MAX_WORKERS)
    crawler.crawl()

