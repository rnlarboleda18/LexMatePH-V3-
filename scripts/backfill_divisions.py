
import psycopg2
import os
import re
import sys
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"

def get_db_connection():
    return psycopg2.connect(DB_CONNECTION_STRING)

def add_column_if_not_exists():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE supreme_decisions ADD COLUMN IF NOT EXISTS division VARCHAR(50);")
        conn.commit()
        logging.info("Column 'division' ensured.")
    except Exception as e:
        logging.error(f"Error adding column: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def extract_division(text):
    if not text:
        return None
    
    # Check first 3000 chars
    header = text[:3000].upper()
    
    if "EN BANC" in header:
        return "En Banc"
    
    match = re.search(r'\b(FIRST|SECOND|THIRD)\s+DIVISION\b', header)
    if match:
        return f"{match.group(1).title()} Division"
        
    return None

def backfill():
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get count
        cur.execute("SELECT COUNT(*) FROM supreme_decisions WHERE division IS NULL")
        count = cur.fetchone()[0]
        logging.info(f"Docs to process: {count}")
        
        # Batch process
        limit = 1000
        processed = 0
        
        while True:
            cur.execute("""
                SELECT id, raw_content 
                FROM supreme_decisions 
                WHERE division IS NULL 
                ORDER BY date DESC
                LIMIT %s
            """, (limit,))
            rows = cur.fetchall()
            
            if not rows:
                break
                
            updates = []
            for row in rows:
                doc_id, content = row
                division = extract_division(content)
                if division:
                    updates.append((division, doc_id))
            
            if updates:
                # Bulk update
                cur.executemany("UPDATE supreme_decisions SET division = %s WHERE id = %s", updates)
                conn.commit()
                processed += len(updates)
                logging.info(f"Processed batch. Total updated: {processed}")
            else:
                logging.info("Batch yielded no extracts. Stopping to avoid infinite loop on unextractable data.")
                # Mark as 'Unknown' to prevent retry loop?
                # Actually, filtering out 'Unknown' might be better, or just set to 'Unknown'
                # Let's set the unmatchable ones to 'Unspecified'
                unmatched_ids = [(row[0],) for row in rows if extract_division(row[1]) is None]
                if unmatched_ids:
                    cur.executemany("UPDATE supreme_decisions SET division = 'Unspecified' WHERE id = %s", unmatched_ids)
                    conn.commit()
                    logging.info(f"Marked {len(unmatched_ids)} as Unspecified")

    except Exception as e:
        logging.error(f"Error: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    add_column_if_not_exists()
    backfill()
