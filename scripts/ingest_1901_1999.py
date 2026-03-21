import os
import json
import psycopg2
from concurrent.futures import ProcessPoolExecutor, as_completed
import time
import re
import logging

# Reuse logic from ingest_supreme_to_postgres
from ingest_supreme_to_postgres import process_year, init_db

# Configuration (re-declare if needed or import)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    print("Ensuring Database is Ready...")
    init_db()
    
    # Historical Batch
    years = list(range(1901, 2000)) 
    
    print(f"Starting HISTORICAL ingestion for {len(years)} years (1901-1999) with 10 workers...")
    
    start_time = time.time()
    
    with ProcessPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_year, year): year for year in years}
        
        for future in as_completed(futures):
            year = futures[future]
            try:
                result = future.result()
                print(result)
            except Exception as e:
                print(f"Year {year}: Unhandled Exception - {e}")
                
    print(f"Total time: {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    main()
