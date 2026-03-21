import psycopg2
import json
import re
import uuid
import zipfile
import xml.etree.ElementTree as ET
from psycopg2.extras import execute_batch

def get_db_connection():
    try:
        with open('local.settings.json') as f:
            settings = json.load(f)
            conn_str = settings['Values']['DB_CONNECTION_STRING']
    except Exception:
        conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/bar_reviewer_local"
    return psycopg2.connect(conn_str)

def get_docx_text(path):
    document = zipfile.ZipFile(path)
    xml_content = document.read('word/document.xml')
    document.close()
    
    tree = ET.XML(xml_content)
    
    PARA_TAG = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'
    TEXT_TAG = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'
    
    full_text = []
    
    for paragraph in tree.iter(PARA_TAG):
        texts = [node.text for node in paragraph.iter(TEXT_TAG) if node.text]
        if texts:
            full_text.append(''.join(texts))
            
    return '\n'.join(full_text)


def ingest_base_codex(filepath, code_short_name, code_full_name, valid_from_date="1900-01-01"):
    print(f"Reading from {filepath}...")
    
    if not os.path.exists(filepath):
        print("File not found.")
        return

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 1. Get or Create Code ID
        cur.execute("SELECT code_id FROM legal_codes WHERE short_name = %s", (code_short_name,))
        row = cur.fetchone()
        
        if row:
            code_id = row[0]
            print(f"Using existing Code ID for {code_short_name}: {code_id}")
        else:
            print(f"Creating new entry for {code_short_name}...")
            cur.execute("""
                INSERT INTO legal_codes (full_name, short_name, description)
                VALUES (%s, %s, %s)
                RETURNING code_id;
            """, (code_full_name, code_short_name, f"The {code_full_name}"))
            code_id = cur.fetchone()[0]
            print(f"Created Code ID: {code_id}")

        # 2. CLEAR EXISTING VERSIONS (Clean Re-ingest)
        cur.execute("DELETE FROM article_versions WHERE code_id = %s", (code_id,))
        print(f"Cleared existing versions for {code_id}. Processing new file...")

        # 3. Parse DOCX
        text = get_docx_text(filepath)
            
        # Regex to find Articles
        # Pattern: Starts with "Article X." and captures until the next "Article Y." or End
        article_pattern = re.compile(r'(Article\s+(\d+[A-Za-z]*)\..+?)(?=Article\s+\d+[A-Za-z]*\.|$)', re.DOTALL)
        
        matches = article_pattern.findall(text)
        print(f"Found {len(matches)} articles.")
        
        count = 0
        batch_args = []
        
        for raw_content, art_num in matches:
            label = f"Article {art_num}"
            content = raw_content.strip()
            
            # Prepare batch insert
            batch_args.append((code_id, label, content, valid_from_date, None, f'{code_short_name} Base'))
            count += 1
            
        # Execute Batch Insert
        if batch_args:
             query = """
                INSERT INTO article_versions 
                (code_id, article_number, content, valid_from, valid_to, amendment_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
             execute_batch(cur, query, batch_args)
        
        conn.commit()
        print(f"Ingested {count} articles into the Codex ({code_short_name}).")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest Base Codex from DOCX")
    parser.add_argument("--file", required=True, help="Path to DOCX file")
    parser.add_argument("--code", required=True, help="Short code name (e.g. RPC, CC, FC)")
    parser.add_argument("--name", required=True, help="Full code name (e.g. 'Civil Code of the Philippines')")
    parser.add_argument("--date", default="1950-08-30", help="Effectivity date (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    ingest_base_codex(args.file, args.code, args.name, args.date)
