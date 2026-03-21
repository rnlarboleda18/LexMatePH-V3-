import requests
import os
import argparse
import logging
import time
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("elib_scraper_sync.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/"
DEFAULT_OUTPUT_DIR = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\sc_elib_html (missing from lawphil)"

def get_session():
    session = requests.Session()
    retry = Retry(
        total=5,
        read=5,
        connect=5,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://elibrary.judiciary.gov.ph/"
    })
    return session

def fetch_and_save(session, doc_id, output_dir):
    file_path = output_dir / f"{doc_id}.html"
    
    if file_path.exists():
        # logger.info(f"Skipping existing: {doc_id}")
        return "skipped"

    url = f"{BASE_URL}{doc_id}"
    try:
        # Respectful delay
        time.sleep(1.0)
        
        response = session.get(url, timeout=30.0)
        
        if response.status_code == 200:
            if "Supreme Court E-Library" in response.text or "D E C I S I O N" in response.text:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(response.text)
                logger.info(f"Successfully saved: {doc_id}")
                return "success"
            else:
                logger.warning(f"Response received for {doc_id} but content seems invalid/empty.")
                return "invalid_content"
        elif response.status_code == 404:
            return "not_found"
        else:
            logger.error(f"Error fetching {doc_id}: Status {response.status_code}")
            return "error"
    except Exception as e:
        logger.error(f"Exception for {doc_id}: {str(e)}")
        # If we get a connection error, sleep a bit longer
        time.sleep(5)
        return "exception"

import concurrent.futures

def main(start_id, end_id, output_dir_str, max_workers=5):
    output_dir = Path(output_dir_str)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a session globally or per thread? Global is fine if thread-safe.
    # requests.Session is thread-safe.
    session = get_session()
    # Increase pool size to match workers
    adapter = HTTPAdapter(pool_connections=max_workers, pool_maxsize=max_workers, max_retries=Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504]))
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    stats = {
        "success": 0,
        "skipped": 0,
        "not_found": 0,
        "error": 0,
        "exception": 0,
        "invalid_content": 0        
    }
    
    logger.info(f"Starting crawl from {start_id} to {end_id} with {max_workers} workers")
    
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Create a list of all IDs
            all_ids = list(range(start_id, end_id + 1))
            
            # Submit all tasks
            future_to_id = {executor.submit(fetch_and_save, session, doc_id, output_dir): doc_id for doc_id in all_ids}
            
            for i, future in enumerate(concurrent.futures.as_completed(future_to_id)):
                doc_id = future_to_id[future]
                try:
                    result = future.result()
                    stats[result] += 1
                except Exception as exc:
                    logger.error(f'{doc_id} generated an exception: {exc}')
                    stats['exception'] += 1
                
                if (i + 1) % 50 == 0:
                    logger.info(f"Progress: {i + 1}/{len(all_ids)} - Stats: {stats}")

    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user.")
    finally:
        logger.info(f"Finished scraping range {start_id}-{end_id}. Final Stats: {stats}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape SC eLib HTML files (Synchronous Threaded).")
    parser.add_argument("--start", type=int, default=40392, help="Start ID")
    parser.add_argument("--end", type=int, default=70041, help="End ID")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--workers", type=int, default=5, help="Number of worker threads")
    
    args = parser.parse_args()
    
    main(args.start, args.end, args.output, args.workers)
