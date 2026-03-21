import asyncio
import json
import os
import argparse
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Configuration
METADATA_DIR = "."  # Current directory where split metadata files are
BASE_DOWNLOAD_DIR = "downloads_enhanced"
SEPARATE_OPINION_DIR = "downloads_enhanced/Separate Opinions"
DEFAULT_CONCURRENCY = 20  # User requested 20 workers
TIMEOUT_MS = 30000  # 30 seconds
HEADLESS = True

SEPARATE_OPINION_KEYWORDS = [
    "DISSENTING OPINION",
    "CONCURRING OPINION",
    "SEPARATE OPINION",
    "CONCURRING AND DISSENTING",
    "CONCURRING SEPARATE",
    "DISSENTING SEPARATE"
]

async def scrape_case(context, case_data, semaphore):
    """
    Scrapes a single case using a browser context.
    """
    async with semaphore:
        year = str(case_data.get('year', 'unknown'))
        month = case_data.get('month', 'unknown')
        case_id = case_data.get('id')
        url = case_data.get('url')
        title = case_data.get('title', '').upper()

        # Determine Save Directory based on Title
        is_separate_opinion = any(kw in title for kw in SEPARATE_OPINION_KEYWORDS)
        
        if is_separate_opinion:
            # Save to Separate Opinions folder (User req: C:\Users\rnlar\.gemini\antigravity\scratch\sc_scraper\downloads_enhanced\Separate Opinions)
            # We preserve year/month structure inside for organization, or just flat if strict adherence is needed?
            # User path implies a root. I will append year/month to avoid 40k files in one folder.
            save_dir = Path(SEPARATE_OPINION_DIR) / year / month
        else:
            save_dir = Path(BASE_DOWNLOAD_DIR) / year / month

        save_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{case_id}.html"
        output_path = save_dir / filename

        # Skip if already exists and large enough (unless overwrite is True)
        if not case_data.get('overwrite', False) and output_path.exists() and output_path.stat().st_size > 1000:
            return "skipped"

        page = await context.new_page()
        try:
            # Block media/images to save bandwidth
            await page.route("**/*.{png,jpg,jpeg,gif,svg,mp4,woff,woff2}", lambda route: route.abort())
            
            # Navigate
            try:
                await page.goto(url, timeout=TIMEOUT_MS, wait_until="domcontentloaded")
            except Exception as e:
                # print(f"Error navigating {case_id}: {e}")
                await page.close()
                return "failed_nav"

            # ------------------------------------------------------------------
            # ROBUST WAIT LOGIC FOR FOOTNOTES
            # ------------------------------------------------------------------
            # 1. Scroll to bottom to trigger lazy loading
            try:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000) # Wait 2s after scroll
            except:
                pass

            # 2. Wait for common footnote selectors
            try:
                # ChanRobles footnotes often have ids like fn1, fn_1, etc.
                # Or they might be in a div with class "footnote"
                # We wait specifically for an element with ID starting with "fn" if possible
                # But to be safe, just a slightly longer wait + network idle is usually best for generic scrapping
                await page.wait_for_load_state("networkidle", timeout=10000)
            except:
                pass 
            
            # 3. Explicit check (optional optimization)
            # await page.wait_for_selector('[id^="fn"]', timeout=2000)

            content = await page.content()
            output_path.write_text(content, encoding="utf-8")
            
            await page.close()
            return "success"

        except Exception as e:
            # print(f"Failed {case_id}: {e}")
            await page.close()
            return "error"

def load_all_metadata(start_year, end_year):
    """Loads metadata from split JSON files (metadata_YYYY.json)."""
    all_cases = []
    print(f"Loading metadata for years {start_year}-{end_year}...")
    
    for year in range(start_year, end_year + 1):
        filename = f"metadata_{year}.json"
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    cases = json.load(f)
                    all_cases.extend(cases)
            except Exception as e:
                print(f"Error loading {filename}: {e}")
        else:
            # print(f"Warning: Metadata file {filename} not found.")
            pass
            
    print(f"Total cases loaded: {len(all_cases)}")
    return all_cases

async def main():
    parser = argparse.ArgumentParser(description="Mass Browser Scraper")
    parser.add_argument("--workers", type=int, default=DEFAULT_CONCURRENCY, help="Number of concurrent workers")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of cases to process")
    parser.add_argument("--start-year", type=int, default=1975)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    # Load metadata from split files
    target_cases = load_all_metadata(args.start_year, args.end_year)
    
    # Optional Re-filter by year logic if metadata contains mixed years (unlikely but safe)
    target_cases = [
        c for c in target_cases 
        if args.start_year <= int(c.get('year', 0)) <= args.end_year
    ]

    if args.limit > 0:
        target_cases = target_cases[:args.limit]

    print(f"Targeting {len(target_cases)} cases with {args.workers} workers.")
    
    semaphore = asyncio.Semaphore(args.workers)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        context = await browser.new_context()
        
        tasks = []
        for case in target_cases:
            if args.overwrite:
                case['overwrite'] = True
            tasks.append(scrape_case(context, case, semaphore))
        
        # Run with progress tracking
        results = []
        total = len(tasks)
        completed = 0
        
        print(f"Starting scraping job (PID: {os.getpid()}). Check sc_scraper.log for details.")

        for f in asyncio.as_completed(tasks):
            res = await f
            results.append(res)
            completed += 1
            if completed % 100 == 0:
                print(f"Progress: {completed}/{total} ({results.count('success')} success, {results.count('skipped')} skipped, {results.count('error')} errors)")

        await browser.close()
    
    print("Scraping completed.")

if __name__ == "__main__":
    asyncio.run(main())
