import psycopg2
import logging
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format='%(message)s')

HOST = "localhost"
USER = "postgres"
PASS = "b66398241bfe483ba5b20ca5356a87be"
DB = "lexmateph-ea-db"

def link_opinions():
    conn = None
    try:
        conn = psycopg2.connect(host=HOST, user=USER, password=PASS, dbname=DB)
        conn.autocommit = True
        cur = conn.cursor()

        # 1. Identify groups
        logging.info("Identifying duplicate groups (Case Number + Date)...")
        cur.execute("""
            SELECT case_number, date, COUNT(*), array_agg(id) 
            FROM sc_decided_cases 
            WHERE case_number IS NOT NULL AND date IS NOT NULL
            GROUP BY case_number, date 
            HAVING COUNT(*) > 1
        """)
        groups = cur.fetchall()
        logging.info(f"Found {len(groups)} groups with potential parent-child relationships.")

        updated_count = 0
        
        for case_num, date, count, ids in tqdm(groups):
            # Fetch details for this group to apply heuristics
            # We fetch: id, document_type, short_title, length of text
            cur.execute("""
                SELECT id, document_type, short_title, LENGTH(COALESCE(full_text_md, '')) as len
                FROM sc_decided_cases 
                WHERE id = ANY(%s)
                ORDER BY len DESC
            """, (ids,))
            
            candidates = cur.fetchall()
            
            # --- Heuristic Logic ---
            parent = None
            
            # Rule 1: Priority by Document Type
            # Try to find explicit "Decision" or "Resolution"
            for c in candidates:
                dtype = (c[1] or "").lower()
                if dtype in ['decision', 'resolution']:
                    parent = c
                    break
            
            # Rule 2: If no explicit type, check Title (exclude opinions)
            if not parent:
                for c in candidates:
                    title = (c[2] or "").lower()
                    if "opinion" not in title and "dissent" not in title and "concur" not in title:
                        parent = c
                        break
            
            # Rule 3: Fallback to Longest Text (already sorted by len DESC)
            if not parent:
                parent = candidates[0]
            
            # --- Apply Updates ---
            if parent:
                parent_id = parent[0]
                children_ids = [c[0] for c in candidates if c[0] != parent_id]
                
                if children_ids:
                    # Update these children to point to parent_id
                    cur.execute("""
                        UPDATE sc_decided_cases 
                        SET parent_id = %s 
                        WHERE id = ANY(%s)
                    """, (parent_id, children_ids))
                    updated_count += len(children_ids)

        logging.info(f"Done! Linked {updated_count} separate opinions/records to their main decisions.")

        # Verification Step
        cur.execute("SELECT COUNT(*) FROM sc_decided_cases WHERE parent_id IS NOT NULL")
        final_count = cur.fetchone()[0]
        logging.info(f"Total records links in DB: {final_count}")

    except Exception as e:
        logging.error(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    link_opinions()
