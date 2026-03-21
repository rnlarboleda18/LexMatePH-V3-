import asyncio
import httpx
import os
import argparse
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("elib_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/"
DEFAULT_OUTPUT_DIR = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\sc_elib_html (missing from lawphil)"

async def fetch_and_save(client, doc_id, output_dir, semaphore, retries=3):
    file_path = output_dir / f"{doc_id}.html"
    
    if file_path.exists():
        return "skipped"

    async with semaphore:
        url = f"{BASE_URL}{doc_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        for attempt in range(retries):
            try:
                # Add a delay between requests to be very gentle
                await asyncio.sleep(0.5)
                response = await client.get(url, timeout=30.0, follow_redirects=True, headers=headers)
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
                    logger.error(f"Error fetching {doc_id}: Status {response.status_code} (attempt {attempt+1})")
            except Exception as e:
                logger.error(f"Exception for {doc_id}: {str(e)} (attempt {attempt+1})")
            
            if attempt < retries - 1:
                await asyncio.sleep(5.0 * (attempt + 1))  # More aggressive backoff
        
        return "error"

async def main(start_id, end_id, concurrency, output_dir_str):
    output_dir = Path(output_dir_str)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    semaphore = asyncio.Semaphore(concurrency)
    
    async with httpx.AsyncClient(limits=httpx.Limits(max_keepalive_connections=concurrency)) as client:
        tasks = []
        for doc_id in range(start_id, end_id + 1):
            tasks.append(fetch_and_save(client, doc_id, output_dir, semaphore))
        
        results = await asyncio.gather(*tasks)
        
        # Summarize results
        stats = {
            "success": results.count("success"),
            "skipped": results.count("skipped"),
            "not_found": results.count("not_found"),
            "error": results.count("error"),
            "exception": results.count("exception"),
            "invalid_content": results.count("invalid_content")
        }
        logger.info(f"Finished scraping range {start_id}-{end_id}. Stats: {stats}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape SC eLib HTML files.")
    parser.add_argument("--start", type=int, default=40392, help="Start ID")
    parser.add_argument("--end", type=int, default=70041, help="End ID")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of concurrent requests")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT_DIR, help="Output directory")
    
    args = parser.parse_args()
    
    asyncio.run(main(args.start, args.end, args.concurrency, args.output))
