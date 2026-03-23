import psycopg2
import logging
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format='%(message)s')

HOST = "localhost"
USER = "postgres"
PASS = "b66398241bfe483ba5b20ca5356a87be"
DB = "lexmateph-ea-db"

def fix_and_link():
    conn = None
    try:
        conn = psycopg2.connect(host=HOST, user=USER, password=PASS, dbname=DB)
        conn.autocommit = True
        cur = conn.cursor()

        # 1. Add Primary Key
        logging.info("1. Adding Primary Key constraint to 'id'...")
        try:
            cur.execute("ALTER TABLE sc_decided_cases ADD PRIMARY KEY (id);")
            logging.info("   Constraint added.")
        except psycopg2.errors.InvalidTableDefinition:
            logging.info("   Constraint already exists (or similar error).")
        except Exception as e:
            logging.warning(f"   Warning adding PK: {e}")

        # 2. Add parent_id Column
        logging.info("2. Adding 'parent_id' column...")
        try:
             cur.execute("""
                ALTER TABLE sc_decided_cases 
                ADD COLUMN IF NOT EXISTS parent_id INTEGER REFERENCES sc_decided_cases(id);
            """)
             logging.info("   Column added.")
        except Exception as e:
            logging.error(f"   Error adding column: {e}")
            return # Blocked

        # 3. Create Index
        try:
             cur.execute("CREATE INDEX IF NOT EXISTS idx_parent_id ON sc_decided_cases(parent_id);")
        except:
            pass

        # 4. Link Opinions
        logging.info("3. Linking Separate Opinions...")
        # Identify groups
        cur.execute("""
            SELECT case_number, date, array_agg(id) 
            FROM sc_decided_cases 
            WHERE case_number IS NOT NULL AND date IS NOT NULL
            GROUP BY case_number, date 
            HAVING COUNT(*) > 1
        """)
        groups = cur.fetchall()
        logging.info(f"   Found {len(groups)} groups.")

        updated_count = 0
        
        for case_num, date, ids in tqdm(groups):
            # Fetch details
            cur.execute("""
                SELECT id, document_type, short_title, LENGTH(COALESCE(full_text_md, '')) as len
                FROM sc_decided_cases 
                WHERE id = ANY(%s)
                ORDER BY len DESC
            """, (ids,))
            candidates = cur.fetchall()
            
            parent = None
            # Heuristics
            # 1. Type
            for c in candidates:
                dtype = (c[1] or "").lower()
                if dtype in ['decision', 'resolution']:
                    parent = c
                    break
            # 2. Title
            if not parent:
                for c in candidates:
                    title = (c[2] or "").lower()
                    if "opinion" not in title and "dissent" not in title and "concur" not in title:
                        parent = c
                        break
            # 3. Length
            if not parent:
                parent = candidates[0]
            
            # Apply Link
            if parent:
                parent_id = parent[0]
                children_ids = [c[0] for c in candidates if c[0] != parent_id]
                
                if children_ids:
                    cur.execute("""
                        UPDATE sc_decided_cases 
                        SET parent_id = %s 
                        WHERE id = ANY(%s)
                    """, (parent_id, children_ids))
                    updated_count += len(children_ids)

        logging.info(f"Done! Linked {updated_count} records.")

    except Exception as e:
        logging.error(f"Critical Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    fix_and_link()
