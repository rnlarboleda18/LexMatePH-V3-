import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor, Json

def load_env():
    # Attempt to load settings from api/local.settings.json
    try:
        settings_path = 'api/local.settings.json'
        if not os.path.exists(settings_path):
            settings_path = '../local.settings.json' # fallback if run from within api/tools/
            
        with open(settings_path, encoding="utf-8") as f:
            vals = json.load(f).get("Values") or {}
            for k, v in vals.items():
                if k not in os.environ:
                    os.environ[str(k)] = str(v)
    except Exception as e:
        print("Error loading env:", e)

def main():
    load_env()
    db_str = os.environ.get("DB_CONNECTION_STRING")
    if not db_str:
        print("Error: DB_CONNECTION_STRING not found in environment.")
        return

    print("Connecting to cloud database...")
    conn = psycopg2.connect(db_str)
    
    try:
        # Use RealDictCursor to work with column dictionaries
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Inspect both rows before proceeding
        print("Retrieving information for duplicate case G.R. No. 231639...")
        cur.execute("SELECT * FROM sc_decided_cases WHERE id = 61166")
        row61166 = cur.fetchone()
        
        cur.execute("SELECT * FROM sc_decided_cases WHERE id = 73287")
        row73287 = cur.fetchone()
        
        if not row61166:
            print("Error: Source duplicate row ID 61166 not found. Already merged?")
            return
        if not row73287:
            print("Error: Target row ID 73287 not found.")
            return
            
        print(f"Source row (61166) has short_title='{row61166.get('short_title')}' and full_text_md length={len(row61166.get('full_text_md') or '')}")
        print(f"Target row (73287) has short_title='{row73287.get('short_title')}' and full_text_md length={len(row73287.get('full_text_md') or '')}")
        
        # 2. Identify fields to update (exclude keys that must stay unique/intact on target)
        exclude_keys = {'id', 'full_text_md', 'sc_url', 'scrape_source', 'created_at', 'updated_at'}
        update_fields = {}
        
        for col, val in row61166.items():
            if col not in exclude_keys:
                update_fields[col] = val
                
        # Also ensure crucial metadata is explicitly set/overridden to correct clean values
        update_fields['case_number'] = "G.R. No. 231639"
        update_fields['date'] = "2020-01-22"
        update_fields['short_title'] = "Heirs of Lupena v. Pagsisihan"
        update_fields['full_title'] = "THE HEIRS OF MARSELLA T. LUPENA (IN SUBSTITUTION OF MARSELLA T. LUPENA), PETITIONERS, VS. PASTORA MEDINA, JOVITO PAGSISIHAN, CENON PATRICIO, AND BERNARDO DIONISIO, RESPONDENTS."
        
        print(f"Merging {len(update_fields)} fields from ID 61166 to ID 73287...")
        
        # Build dynamic UPDATE statement
        set_clauses = []
        set_values = []
        for col, val in update_fields.items():
            set_clauses.append(f"{col} = %s")
            if isinstance(val, (dict, list)):
                set_values.append(Json(val))
            else:
                set_values.append(val)
            
        set_values.append(73287) # for WHERE clause
        update_query = f"UPDATE sc_decided_cases SET {', '.join(set_clauses)} WHERE id = %s"
        
        cur.execute(update_query, tuple(set_values))
        print("Target row 73287 updated successfully.")
        
        # 2.5. Find and update referencing foreign keys dynamically
        print("Finding all tables with foreign keys referencing sc_decided_cases...")
        fk_query = """
            SELECT
                tc.table_name AS referencing_table, 
                kcu.column_name AS referencing_column
            FROM 
                information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                  AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' AND ccu.table_name='sc_decided_cases'
        """
        cur.execute(fk_query)
        fkeys = cur.fetchall()
        print(f"Found {len(fkeys)} referencing foreign key columns:")
        for fk in fkeys:
            ref_table = fk['referencing_table']
            ref_col = fk['referencing_column']
            print(f"  - Table '{ref_table}', Column '{ref_col}'")
            
            # Update the references
            update_fk_query = f"UPDATE {ref_table} SET {ref_col} = %s WHERE {ref_col} = %s"
            cur.execute(update_fk_query, (73287, 61166))
            print(f"    Updated references from 61166 to 73287 in {ref_table}.")

        # 3. Safely delete the corrupt row 61166
        print("Deleting corrupt duplicate row ID 61166...")
        cur.execute("DELETE FROM sc_decided_cases WHERE id = 61166")
        print("Row ID 61166 deleted successfully.")
        
        # 4. Verify everything was correctly updated on 73287
        print("Verifying merged database record...")
        cur.execute("SELECT id, case_number, short_title, date, left(full_text_md, 200) FROM sc_decided_cases WHERE id = 73287")
        verify_row = cur.fetchone()
        
        if verify_row:
            print("="*60)
            print("VERIFICATION SUCCESSFUL:")
            print(f"  ID: {verify_row['id']}")
            print(f"  Case Number: {verify_row['case_number']}")
            print(f"  Short Title: {verify_row['short_title']}")
            print(f"  Date: {verify_row['date']}")
            print(f"  Full Text Header Preview:\n{verify_row['left']}")
            print("="*60)
        else:
            raise ValueError("Merged row 73287 could not be loaded for verification!")
            
        # Commit the transaction safely
        conn.commit()
        print("Transaction committed successfully.")
        
    except Exception as e:
        conn.rollback()
        print("Transaction rolled back due to error:", e)
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    main()
