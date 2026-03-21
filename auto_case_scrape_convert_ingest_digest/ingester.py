import os
import psycopg2
import re
from pathlib import Path
from datetime import datetime
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MD_DIR = Path(BASE_DIR).parent / "data" / "lawphil_md"
DB_CONNECTION_STRING = "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:6432/postgres?sslmode=require"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def get_metadata_from_text(text):
    meta = {'case_number': None, 'date': None, 'title': None}
    
    # 1. G.R. No.
    # Look for "G.R. No. XXXXX"
    gr_match = re.search(r'(G\.R\.\s*No\.\s*[\w\-]+)', text, re.IGNORECASE)
    if gr_match:
        meta['case_number'] = gr_match.group(1).upper()
        
    # 2. Date
    # Look for Month DD, YYYY
    date_match = re.search(r'([A-Z][a-z]+\s+\d{1,2},?\s*\d{4})', text)
    if date_match:
        try:
            d_str = date_match.group(1).replace(',', '')
            dt = datetime.strptime(d_str, "%B %d %Y")
            meta['date'] = dt.strftime("%Y-%m-%d")
        except: pass

    # 3. Title (Simple Fallback: First line or filename logic)
    # We'll rely on the text content usually having the title near top.
    # Or just use the first line that looks like X vs Y.
    vs_match = re.search(r'(.+?\s+v(?:s)?\.?\s+.+?)(?:\n|$)', text, re.IGNORECASE)
    if vs_match:
        meta['title'] = vs_match.group(1).strip()
    
    return meta

def ingest_cases():
    conn = psycopg2.connect(DB_CONNECTION_STRING)
    cur = conn.cursor()
    
    files = list(MD_DIR.rglob("*.md"))
    logging.info(f"Scanning {len(files)} MD files for ingestion...")
    
    count = 0
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as md_file:
                content = md_file.read()
            
            meta = get_metadata_from_text(content[:2000]) # Scan header
            
            # Require at least GR or Title
            if not meta['case_number'] and not meta['title']:
                logging.warning(f"Skipping {f.name}: No metadata found.")
                continue

            # Default date if missing (safeguard)
            if not meta['date']:
                # Try directory year
                try: 
                    year = f.parent.name
                    if year.isdigit(): meta['date'] = f"{year}-01-01"
                except: pass

            case_no = meta['case_number'] or f.stem
            title = meta['title'] or f.stem
            date = meta['date'] or '1900-01-01'

            # Manual UPSERT Loop
            # Check existence
            cur.execute("SELECT id FROM sc_decided_cases WHERE case_number = %s", (case_no,))
            existing = cur.fetchone()
            
            if existing:
                # Update
                cur.execute("""
                    UPDATE sc_decided_cases
                    SET title = %s,
                        date = %s,
                        full_text_md = %s,
                        sc_url = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (title, date, content, 'https://lawphil.net', existing[0]))
            else:
                # Insert
                cur.execute("""
                    INSERT INTO sc_decided_cases (case_number, title, date, full_text_md, sc_url)
                    VALUES (%s, %s, %s, %s, %s)
                """, (case_no, title, date, content, 'https://lawphil.net'))
            
            count += 1
            if count % 10 == 0: conn.commit()
            
        except Exception as e:
            logging.error(f"Error ingesting {f.name}: {e}")
            conn.rollback()

    conn.commit()
    conn.close()
    logging.info(f"Ingested {count} cases.")

if __name__ == "__main__":
    ingest_cases()
