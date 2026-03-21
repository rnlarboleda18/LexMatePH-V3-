import os
import glob
import psycopg2
from multiprocessing import Pool, cpu_count
import time

# Configuration
DB_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"
SOURCE_DIR = r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\data\lawphil_md"
WORKERS = 15
BATCH_SIZE = 10

def get_db_connection():
    return psycopg2.connect(DB_CONNECTION_STRING)

def process_batch(file_paths):
    """
    Reads a batch of files and inserts them into DB.
    Returns count of successful inserts.
    """
    if not file_paths:
        return 0

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        args_list = []
        for fp in file_paths:
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    content = f.read()
                filename = os.path.basename(fp)
                args_list.append((content, filename))
            except Exception as read_err:
                print(f"Error reading {fp}: {read_err}")

        if args_list:
            # Bulk insert
            # We use distinct placeholders for each row
            # args_str = ','.join(cur.mogrify("(%s,%s)", x).decode('utf-8') for x in args_list)
            # cur.execute("INSERT INTO sc_decided_cases (full_text_md, scrape_source) VALUES " + args_str)
            
            # Using executemany is cleaner often, but mogrify bulk is faster. 
            # Let's use executemany for simplicity and sufficient speed for text.
            cur.executemany("INSERT INTO sc_decided_cases (full_text_md, scrape_source) VALUES (%s, %s)", args_list)
            
            conn.commit()
            return len(args_list)
        return 0

    except Exception as e:
        print(f"Batch Error: {e}")
        if conn:
            conn.rollback()
        return 0
    finally:
        if conn:
            conn.close()

def chunked_iterable(iterable, size):
    """Yield successive chunks from iterable."""
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]

def main():
    print(f"Scanning files in {SOURCE_DIR}...")
    files = glob.glob(os.path.join(SOURCE_DIR, "**", "*.md"), recursive=True)
    total_files = len(files)
    print(f"Found {total_files} Markdown files.")
    
    if total_files == 0:
        return

    # Create batches
    batches = list(chunked_iterable(files, BATCH_SIZE))
    print(f"Processing in {len(batches)} batches with {WORKERS} workers...")

    start_time = time.time()
    
    total_processed = 0
    with Pool(processes=WORKERS) as pool:
        results = pool.imap_unordered(process_batch, batches)
        
        for i, count in enumerate(results):
            total_processed += count
            if i % 10 == 0:
                print(f"Progress: {total_processed}/{total_files} files ingested...", end='\r')

    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\nDone! Ingested {total_processed} files in {duration:.2f} seconds.")

if __name__ == "__main__":
    main()
