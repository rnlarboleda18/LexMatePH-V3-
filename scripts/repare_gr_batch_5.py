import json
import psycopg
import glob
import math

settings = json.load(open('api/local.settings.json'))
conn_str = settings['Values']['DB_CONNECTION_STRING']

def main():
    print("Repartitioning G.R. Batch for 5 Workers...")
    
    # 1. Load all original G.R. IDs
    gr_ids = []
    files = glob.glob("data/batches/ids_gr_*.txt")
    for f in files:
        with open(f, 'r') as fp:
            content = fp.read().replace('\n', ',')
            gr_ids.extend([x.strip() for x in content.split(',') if x.strip()])
            
    if not gr_ids:
        print("No G.R. IDs found.")
        return

    print(f"Total G.R. IDs: {len(gr_ids)}")

    # 2. Check for incomplete cases
    pending_ids = []
    stuck_ids = []
    
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            # Fetch incomplete IDs (NULL or PROCESSING)
            cur.execute("""
                SELECT id, digest_significance 
                FROM sc_decided_cases 
                WHERE id = ANY(%s) 
                AND (digest_significance IS NULL OR digest_significance LIKE '%%PROCESSING%%')
            """, (gr_ids,))
            
            rows = cur.fetchall()
            for r in rows:
                case_id = str(r[0])
                status = r[1]
                pending_ids.append(case_id)
                if status and 'PROCESSING' in status:
                    stuck_ids.append(case_id)

            print(f"Pending Cases: {len(pending_ids)}")
            print(f"Stuck Cases:   {len(stuck_ids)}")
            
            # 3. Reset Locks for Stuck Cases
            if stuck_ids:
                cur.execute("""
                    UPDATE sc_decided_cases 
                    SET digest_significance = NULL 
                    WHERE id = ANY(%s)
                """, (stuck_ids,))
                conn.commit()
                print(f"Reset {len(stuck_ids)} stuck cases.")

    # 4. Partition into 5 Files
    if not pending_ids:
        print("No pending cases to process.")
        return
        
    chunk_size = math.ceil(len(pending_ids) / 5)
    print(f"Splitting into 5 batches of approx {chunk_size} cases.")
    
    for i in range(5):
        chunk = pending_ids[i * chunk_size : (i + 1) * chunk_size]
        filename = f"data/batches/gr_retry_0{i+1}.txt"
        if chunk:
            with open(filename, 'w') as f:
                f.write(",".join(chunk))
            print(f"Created {filename} with {len(chunk)} IDs.")
        else:
             print(f"Skipping {filename} (empty).")

if __name__ == "__main__":
    main()
