import asyncio
import httpx
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scrape_rules_elib.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/11/"
OUTPUT_DIR = Path(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\html\rules_court_elib")

DOC_IDS = [
    99969, 100842, 99055, 367, 99702, 100762, 100125, 100836, 99241, 98606,
    100128, 368, 98599, 98364, 98802, 98634, 98644, 98776, 371, 99703,
    24, 369, 370, 373, 374, 99262
]

async def fetch_and_save(client, doc_id, semaphore, retries=3):
    file_path = OUTPUT_DIR / f"{doc_id}.html"
    
    if file_path.exists():
        logger.info(f"Skipping {doc_id}, already exists.")
        return "skipped"

    async with semaphore:
        url = f"{BASE_URL}{doc_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        for attempt in range(retries):
            try:
                await asyncio.sleep(1.0) # Be gentle
                response = await client.get(url, timeout=30.0, follow_redirects=True, headers=headers)
                if response.status_code == 200:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(response.text)
                    logger.info(f"Successfully saved: {doc_id}")
                    return "success"
                else:
                    logger.error(f"Error fetching {doc_id}: Status {response.status_code} (attempt {attempt+1})")
            except Exception as e:
                logger.error(f"Exception for {doc_id}: {str(e)} (attempt {attempt+1})")
            
            if attempt < retries - 1:
                await asyncio.sleep(2.0 * (attempt + 1))
        
        return "error"

async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(5)
    
    async with httpx.AsyncClient() as client:
        tasks = [fetch_and_save(client, doc_id, semaphore) for doc_id in DOC_IDS]
        results = await asyncio.gather(*tasks)
        
        stats = {
            "success": results.count("success"),
            "skipped": results.count("skipped"),
            "error": results.count("error")
        }
        logger.info(f"Finished scraping. Stats: {stats}")

if __name__ == "__main__":
    asyncio.run(main())
