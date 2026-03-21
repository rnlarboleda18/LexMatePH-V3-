
import os
import psycopg
from collections import defaultdict
import re

# Config
DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING")
if not DB_CONNECTION_STRING:
     DB_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def fix_duplicates():
    print("Connecting to DB...")
    with psycopg.connect(DB_CONNECTION_STRING, autocommit=True) as conn:
        with conn.cursor() as cur:
            print("Fetching all case records...")
            # Fetch essential fields to decide which to keep
            cur.execute("""
                SELECT id, case_number, LENGTH(full_text_md), keywords 
                FROM sc_decisionsv2
            """)
            rows = cur.fetchall()
            
            print(f"Total rows: {len(rows)}")
            
            # Group by normalized case number
            def normalize(s):
                if not s: return ""
                return re.sub(r'[\W_]+', '', s).lower()
            
            groups = defaultdict(list)
            for r in rows:
                rid, cnum, length, keywords = r
                if not cnum: continue
                if rid is None: continue # Should not happen for PK, but safe guard
                
                # Score criteria:
                # 1. Has keywords? (1 = yes, 0 = no)
                # 2. Content Length
                # 3. ID (Inverse, prefer smaller/older)
                has_keywords = 1 if keywords else 0
                content_len = length if length else 0
                
                groups[normalize(cnum)].append({
                    "id": rid,
                    "cnum": cnum,
                    "score": (has_keywords, content_len, -rid) # Higher is better. -rid means lower ID is better.
                })
                
            duplicates = {k: v for k, v in groups.items() if len(v) > 1}
            print(f"Found {len(duplicates)} duplicate groups.")
            
            ids_to_delete = []
            
            for k, items in duplicates.items():
                # Sort descending by score
                items.sort(key=lambda x: x["score"], reverse=True)
                
                start_cnt = len(items)
                survivor = items[0]
                candidates = items[1:]
                
                for c in candidates:
                    ids_to_delete.append(c["id"])
            
            print(f"Identified {len(ids_to_delete)} records to delete.")
            
            if not ids_to_delete:
                print("Nothing to delete.")
                return

            print("Deleting duplicates in batches...")
            batch_size = 1000
            total_deleted = 0
            
            for i in range(0, len(ids_to_delete), batch_size):
                batch = ids_to_delete[i:i+batch_size]
                cur.execute(f"DELETE FROM sc_decisionsv2 WHERE id = ANY(%s)", (batch,))
                total_deleted += len(batch)
                print(f"Deleted {total_deleted}/{len(ids_to_delete)}...")
                
            print("Cleanup complete.")

if __name__ == "__main__":
    fix_duplicates()
