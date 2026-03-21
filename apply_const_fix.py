import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch

def get_conn_str():
    try:
        with open('api/local.settings.json', 'r') as f:
            config = json.load(f)
            return config.get('Values', {}).get('DB_CONNECTION_STRING')
    except Exception: pass
    return None

def apply_fix():
    conn_str = get_conn_str()
    if not conn_str:
        print("Error: Could not find DB connection string.")
        return
    
    conn = None
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # --- PHASE 1: INSERT MISSING ROW FOR 'STATE POLICIES' ---
        print("Step 1: Finding insertion point in Article II...")
        # Find position of SECTION 7 in ARTICLE II
        cur.execute("""
            SELECT list_order 
            FROM const_codal 
            WHERE book_code = 'CONST' 
              AND article_label = 'ARTICLE II' 
              AND section_label = 'SECTION 7.'
        """)
        row = cur.fetchone()
        if not row:
            print("Error: Could not find SECTION 7 of ARTICLE II.")
            cur.close()
            conn.close()
            return
            
        insertion_order = row['list_order']
        print(f"Found SECTION 7 at list_order = {insertion_order}.")
        
        # Check if already inserted to prevent duplicates if Rerun
        cur.execute("""
            SELECT id FROM const_codal 
            WHERE book_code = 'CONST' AND article_num = 'II-STATE-POLICIES'
        """)
        if cur.fetchone():
            print("Row 'II-STATE-POLICIES' already exists. Skipping insertion.")
        else:
            print(f"Expanding list_order for rows >= {insertion_order}...")
            cur.execute("""
                UPDATE const_codal 
                SET list_order = list_order + 1 
                WHERE book_code = 'CONST' AND list_order >= %s
            """, (insertion_order,))
            print(f"Updated {cur.rowcount} rows.")
            
            print("Inserting 'State Policies' subheader row...")
            cur.execute("""
                INSERT INTO const_codal 
                (book_code, list_order, article_num, article_label, section_label, content_md)
                VALUES ('CONST', %s, 'II-STATE-POLICIES', 'ARTICLE II', 'ARTICLE II', '### State Policies')
            """, (insertion_order,))
            print("Inserted 1 row.")

        # --- PHASE 2: POPULATE GROUP_HEADER FOR ALL ROWS ---
        print("\nStep 2: Populating group_header for all rows...")
        cur.execute("""
            SELECT id, list_order, article_num, article_label, section_label, content_md 
            FROM const_codal 
            WHERE book_code = 'CONST'
            ORDER BY list_order ASC 
        """)
        rows = cur.fetchall()
        
        updates = []
        current_group = None
        current_article = None
        
        for r in rows:
            article_num = r['article_num']
            section_label = r['section_label'] or ""
            content = r['content_md'] or ""
            
            # Reset group on new Article
            if r['article_label'] != current_article:
                current_article = r['article_label']
                current_group = None
                
            # Check for subheaders starting with '###'
            if content.startswith('###'):
                 current_group = content.replace('###', '').strip()
                 # Subheader row itself gets None
                 updates.append((None, r['id']))
                 continue
                 
            # Update regular rows
            updates.append((current_group, r['id']))
            
        print(f"Prepared {len(updates)} updates.")
        
        # Execute batch update
        execute_batch(cur, """
            UPDATE const_codal SET group_header = %s WHERE id = %s
        """, updates)
        
        print(f"Batch updated {len(updates)} rows.")
        
        # Commit transaction
        conn.commit()
        print("\nTransaction COMMITTED successfully.")
        
    except Exception as e:
        print(f"Error during execution: {e}")
        if conn:
            print("Rolling back transaction...")
            conn.rollback()
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    apply_fix()
