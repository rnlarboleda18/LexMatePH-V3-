import json
import psycopg
import math
import os

# --- CONFIGURATION ---
BATCH_PREFIX = "gr_retry10_"
NUM_BATCHES = 10

settings = json.load(open('api/local.settings.json'))
conn_str = settings['Values']['DB_CONNECTION_STRING']

def partition_ids(ids, n):
    """Yield n chunks from ids."""
    if not ids: return [[] for _ in range(n)]
    k, m = divmod(len(ids), n)
    return (ids[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))

def main():
    print("Connecting to database and identifying G.R. cases...")
    
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            # 1. Fetch all currently undigested G.R. cases
            # Criteria: full_text_md exists, but digest is missing or empty
            # We filter by G.R. prefix in case_number
            cur.execute("""
                SELECT id, case_number
                FROM sc_decided_cases 
                WHERE full_text_md IS NOT NULL 
                AND (digest_facts IS NULL OR digest_facts = '')
            """)
            rows = cur.fetchall()
            
            gr_ids = [str(r[0]) for r in rows if (r[1] or "").strip().upper().startswith("G.R.")]
            
            print(f"Total current undigested G.R. cases identified: {len(gr_ids)}")

            if not gr_ids:
                print("No G.R. cases left to digest!")
                return

            # 2. Reset any 'PROCESSING' locks for these IDs
            # This ensures new workers can claim them immediately
            cur.execute("""
                UPDATE sc_decided_cases 
                SET digest_significance = NULL 
                WHERE id = ANY(%s) 
                AND digest_significance LIKE '%%PROCESSING%%'
            """, (gr_ids,))
            
            print(f"Reset {cur.rowcount} stalled locks.")
            conn.commit()

    # 3. Partition into 10 files
    print(f"Partitioning {len(gr_ids)} cases into {NUM_BATCHES} batches...")
    
    # Ensure directory exists (optional, root for now)
    gr_chunks = list(partition_ids(gr_ids, NUM_BATCHES))
    
    for i, chunk in enumerate(gr_chunks):
        filename = f"{BATCH_PREFIX}{i+1:02d}.txt"
        with open(filename, "w") as f:
            f.write("\n".join(chunk))
        print(f"  Created {filename} with {len(chunk)} cases.")

    print("\nNext: Run scripts/launch_gr_retry_10.ps1")

if __name__ == "__main__":
    main()
