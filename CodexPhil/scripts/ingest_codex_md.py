import psycopg2
import json
import re
import os
from psycopg2.extras import execute_batch

def get_db_connection():
    try:
        with open('local.settings.json') as f:
            settings = json.load(f)
            conn_str = settings['Values']['DB_CONNECTION_STRING']
    except Exception:
        conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
    return psycopg2.connect(conn_str)

def parse_markdown_articles(filepath):
    """
    Parses the Markdown file to extract articles.
    Assumes format:
    ### Article X. Title
    Content...
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    articles = []
    current_label = None
    current_content = []
    preamble_content = []


    # Regex to identify Article headers in Markdown (e.g., "### Article 1.")
    header_pattern = re.compile(r'^###\s+(Article\s+(\d+)\..+)')

    for line in lines:
        match = header_pattern.match(line)
        if match:
            # Save previous article if exists
            if current_label:
                # HEADER STEALING LOGIC:
                # Check if the last few lines of current_content are actually headers for the NEW article
                # e.g. "CHAPTER TWO" appearing before "### Article 11"
                stolen_headers = []
                # Iterate backwards
                while current_content:
                    last_line = current_content[-1].strip()
                    if not last_line:
                        # Keep empty lines with the headers? Or discard?
                        # Usually format is \nHEADER\n### Art
                        # So empty line usually goes with header.
                        stolen_headers.insert(0, current_content.pop())
                        continue
                        
                    # Check if HEADER (Upper case, short, keywords)
                    is_header = False
                    if len(last_line) < 100 and last_line.isupper() and not last_line.endswith('.'):
                         # Strict keywords check to avoid stealing shouted text
                         if any(x in last_line for x in ["BOOK", "TITLE", "CHAPTER", "SECTION"]):
                             is_header = True
                             
                    if is_header:
                        stolen_headers.insert(0, current_content.pop())
                    else:
                        # Hit non-header text, stop stealing
                        break
                
                # Format content with proper markdown header
                # Previous article gets what's left
                full_content = f"### {current_label}\n\n{''.join(current_content).strip()}"
                articles.append((current_label, full_content))
            
            # Start new article
            current_label = match.group(1).strip() # Full label e.g. "Article 1. Time when Act takes effect."
            
            # New article starts with Stolen Headers (if any)
            current_content = []
            if 'stolen_headers' in locals() and stolen_headers:
                 current_content.extend(stolen_headers) 
        else:
            if current_label:
                current_content.append(line)
            else:
                preamble_content.append(line)

    # Add Preamble if exists
    if preamble_content and not any(art[0] == '0' for art in articles):
        # Clean up preamble
        p_text = ''.join(preamble_content).strip()
        if p_text:
            articles.insert(0, ('0', p_text))

    # Save last article
    if current_label:
        full_content = f"### {current_label}\n\n{''.join(current_content).strip()}"
        articles.append((current_label, full_content))
        
    return articles

def ingest_rpc_md():
    filepath = 'data/CodexPhil/Codals/md/RPC.md'
    print(f"Reading from {filepath}...")
    
    if not os.path.exists(filepath):
        print("File not found.")
        return

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 1. Get Code ID for RPC
        cur.execute("SELECT code_id FROM legal_codes WHERE short_name = 'RPC'")
        row = cur.fetchone()
        
        if row:
            code_id = row[0]
        else:
            print("RPC Code entry not found. Creating...")
            cur.execute("""
                INSERT INTO legal_codes (full_name, short_name, description)
                VALUES ('Revised Penal Code', 'RPC', 'The Revised Penal Code of the Philippines (Act No. 3815)')
                RETURNING code_id;
            """)
            code_id = cur.fetchone()[0]
            
        print(f"Code ID for RPC: {code_id}")

        # 2. CLEAR EXISTING VERSIONS (Clean Re-ingest)
        cur.execute("DELETE FROM article_versions WHERE code_id = %s", (code_id,))
        print(f"Cleared existing versions for {code_id}. Processing new file...")

        # 3. Parse Markdown
        articles = parse_markdown_articles(filepath)
        print(f"Found {len(articles)} articles.")
        
        batch_args = []
        for label, content in articles:
            # Extract number for ordering/labeling if needed, though label has it.
            # We use the full label as the article_number column is loose text or we can extract just the number.
            # The schema likely has article_number as text.
            
            # Attempt to extract just the number "1" from "Article 1. ..."
            # If complex like "Article 1-A", it handles it.
            match = re.search(r'Article\s+([0-9A-Za-z\-]+)\.', label)
            art_num = match.group(1) if match else label
            
            # Prepare batch insert
            # valid_from default 1932 for RPC
            batch_args.append((code_id, art_num, content, '1932-01-01', None, 'Act No. 3815'))

        # 4. Execute Batch Insert
        if batch_args:
             query = """
                INSERT INTO article_versions 
                (code_id, article_number, content, valid_from, valid_to, amendment_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
             execute_batch(cur, query, batch_args)
        
        conn.commit()
        print(f"Ingested {len(batch_args)} articles into the Codex.")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    ingest_rpc_md()
