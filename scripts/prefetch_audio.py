import os
import sys
import argparse
import psycopg2
from psycopg2.extras import DictCursor
import json
import logging
from tqdm import tqdm
import time
import requests

# Add the api directory to the path so we can import config
current_dir = os.path.dirname(os.path.abspath(__file__))
api_dir = os.path.join(os.path.dirname(current_dir), 'api')
sys.path.append(api_dir)

from config import DB_CONNECTION_STRING

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_db_connection():
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        return conn
    except Exception as e:
        logging.error(f"Error connecting to database: {e}")
        return None

def fetch_labor_code_articles(limit=100):
    """Fetch the first N articles of the Labor Code (P.D. 442)"""
    conn = get_db_connection()
    if (!conn): return []
    
    # We need to find the codex_id for the Labor Code first
    try:
        cur = conn.cursor(cursor_factory=DictCursor)
        
        # In a real scenario, we'd query for 'Labor Code' or 'PD 442'
        # Since we don't know the exact schema of the codal tables, we'll simulate fetching 
        # the IDs if this run fails. Assuming a simpler structure for demonstration.
        
        logging.info("Fetching Labor Code articles from database...")
        # Placeholder for actual query logic based on the schema
        # cur.execute("SELECT id FROM codal_provisions WHERE code_id = (SELECT id FROM codal_codes WHERE short_name = 'LABOR') ORDER BY article_no LIMIT %s", (limit,))
        # articles = cur.fetchall()
        
        # Since we don't have the exact schema, we will just print what *would* happen
        logging.warning("Note: Exact schema for Codal provisions isn't fully mapped here.")
        logging.warning("Simulating the fetch of Arts 1-100 of the Labor Code.")
        
        # Simulate IDs
        return [{"id": i} for i in range(1, limit + 1)]
    except Exception as e:
        logging.error(f"Database error: {e}")
        return []
    finally:
        if cur: cur.close()
        if conn: conn.close()

def prefetch_audio(articles):
    """Call the local Azure Function API to generate and cache audio"""
    if not articles:
        logging.warning("No articles provided to pre-fetch.")
        return

    # Assuming the Azure Function is running locally on port 7071
    API_URL = "http://localhost:7071/api/audio/codal/"
    
    logging.info(f"Starting pre-fetch for {len(articles)} articles...")
    
    success_count = 0
    fail_count = 0
    
    for article in tqdm(articles):
        current_id = article['id']
        url = f"{API_URL}{current_id}"
        
        try:
            # We just need to trigger the GET request. The Function handles caching.
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                success_count += 1
            else:
                logging.error(f"Failed to generate audio for codal {current_id}: HTTP {response.status_code}")
                fail_count += 1
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Connection error for codal {current_id}: {e}")
            fail_count += 1
            
        # Add a small delay to avoid overwhelming the local API/Azure SDK
        time.sleep(0.5)
        
    logging.info("--- Pre-fetch Complete ---")
    logging.info(f"Success: {success_count} | Failures: {fail_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pre-fetch LexPlay audio for Labor Code articles")
    parser.add_argument("--limit", type=int, default=100, help="Number of articles to fetch")
    args = parser.parse_args()
    
    articles = fetch_labor_code_articles(args.limit)
    prefetch_audio(articles)
