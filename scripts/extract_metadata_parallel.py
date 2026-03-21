
import os
import re
import psycopg
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import time

# Config
DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"
MAX_WORKERS = 20
BATCH_SIZE = 50

def get_connection():
    return psycopg.connect(DB_CONNECTION_STRING, autocommit=True)

def extract_metadata_from_text(text):
    if not text:
        return None
        
    meta = {}
    
    # Extract G.R. Number
    # Patterns: "G.R. No. 12345", "G.R. Nos. 12345 & 12346", "Administrative Matter No. ..."
    # We look for the first clear case number pattern near the top
    
    # Try generic G.R. pattern first
    gr_match = re.search(r'(G\.R\.\s+N[oO]s?\.?\s+[\w\d\-\&\,\s]+?)(?=\s|$)', text[:5000])
    if gr_match:
        meta['case_number'] = gr_match.group(1).strip()
    
    # Extract Date
    # Look for standard date formats: "March 15, 2023", "15 March 2023"
    date_match = re.search(r'([A-Z][a-z]+\s+\d{1,2},\s+\d{4})', text[:5000])
    if date_match:
        meta['date'] = date_match.group(1).strip()
    
    # Title (First significant line often)
    # This is hard to perfect with regex, maybe skip for now or take top line?
    # Let's try to find "Petitioner" vs "Respondent" block
    
    return meta

def process_batch(batch):
    updates = []
    
    for record in batch:
        rid, text = record
        meta = extract_metadata_from_text(text)
        
        if meta:
            # Prepare update
            updates.append({
                "id": rid,
                "case_number": meta.get("case_number"),
                "date": meta.get("date")
            })
            
    if not updates:
        return 0
        
    # Bulk Update
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # We update case_number and date ONLY if they are currently NULL to avoid overwriting good data?
                # User said "populate", implying we might be filling gaps.
                # Actually, user said "extract... not from file name". This implies overwriting or setting verification.
                # I will overwrite for now as requested.
                
                # We execute updates individually or broadly? 
                # executemany with UPDATE FROM VALUES is best for Postgres.
                
                # Construct complex query for batch update? 
                # Simpler to just loop updates for safety in this script or use executemany
                cur.executemany("""
                    UPDATE sc_decisionsv2 
                    SET 
                        case_number = COALESCE(%s, case_number),
                        date = CASE WHEN %s::text IS NOT NULL THEN %s::date ELSE date END
                    WHERE id = %s
                """, [(u['case_number'], u['date'], u['date'], u['id']) for u in updates])
                
        return len(updates)
    except Exception as e:
        print(f"Batch Error: {e}")
        return 0

def run_extraction():
    print("Fetching records needing metadata (or all?)...")
    # For now, let's target records with NULL case_number OR NULL date to save time?
    # Or forcing update on all? User said "populate... not from filename".
    # I'll target ALL records but prioritize those with missing info if possible.
    # Actually, fetching 65k records text is HEAVY.
    # We should fetch ID and Text only.
    
    ids_to_process = []
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, full_text_md FROM sc_decisionsv2 -- WHERE case_number IS NULL OR date IS NULL") 
            # I will process ALL to ensure accuracy as requested
            rows = cur.fetchall()
            ids_to_process = rows
            
    print(f"Loaded {len(ids_to_process)} records. Starting extraction with {MAX_WORKERS} workers...")
    
    # Batches
    batches = [ids_to_process[i:i + BATCH_SIZE] for i in range(0, len(ids_to_process), BATCH_SIZE)]
    
    total_updated = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_batch, b): b for b in batches}
        
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(batches)):
            try:
                cnt = future.result()
                total_updated += cnt
            except Exception as e:
                print(f"Future Error: {e}")
                
    print(f"Done. Updated metadata for {total_updated} records.")

if __name__ == "__main__":
    run_extraction()
