
import psycopg2
import json
import re
import uuid
import zipfile
import xml.etree.ElementTree as ET
import os

# Database Connection
def get_db_connection():
    try:
        with open('local.settings.json') as f:
            settings = json.load(f)
            conn_str = settings['Values']['DB_CONNECTION_STRING']
    except Exception:
        conn_str = "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
    return psycopg2.connect(conn_str)

# DOCX Text Extraction
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

# Parsing Logic (Standardizing Headers)
def parse_and_standardize(text):
    """
    Parses text into articles and enforces the canonical formatting:
    **Article X. Title.** - Body
    """
    # Split by "Article" keyword, but be careful
    # Regex findall is better
    
    parsed_articles = []
    
    # Pattern: Article <Num><Suffix?>. <Title?> <Sep> <Body>
    # Matches: Article 1. Title. - Body
    # Matches: Article 266-A. Title. - Body
    # Matches: Article 2. - Body (No title)
    
    # We look for "Article" at start of line
    pattern = re.compile(r'(^|\n)(Article\s+(\d+)([A-Za-z]?)\.?\s*(.*?))(?=(\nArticle\s+\d+|$))', re.DOTALL)
    
    matches = pattern.findall(text)
    
    for _, raw_block, num_str, suffix_str, content_tail, _ in matches:
        full_num = f"{num_str}{'-' + suffix_str if suffix_str else ''}"
        
        # Detect Title vs Body in content_tail
        # Usually separated by period-dash ".-" or just period "."
        # Standard: **Article X. Title.** - Body
        
        # Heuristic: First sentence is specific title?
        # Or did the regex capture the title in `content_tail`?
        
        # Let's clean up content_tail
        content_tail = content_tail.strip()
        
        # Try to split Title and Body
        title = "No Title"
        body = content_tail
        
        # Check for "- " separator
        if ' - ' in content_tail[:100]: # Look in first 100 chars
            parts = content_tail.split(' - ', 1)
            raw_title = parts[0].strip().strip('.')
            body = parts[1].strip()
            title = raw_title
        elif content_tail.endswith('.'): # Short content might just be title? Unlikely for base law.
             # Check for Period space
             if '. ' in content_tail[:100]:
                 parts = content_tail.split('. ', 1)
                 raw_title = parts[0].strip()
                 body = parts[1].strip()
                 title = raw_title
        
        # Canonicalize Markdown
        # If title is found, bold it.
        # Header: **Article {full_num}. {title}.**
        
        # Remove any existing markdown from title
        clean_title = title.replace('*', '')
        
        if title != "No Title":
            md_header = f"**Article {full_num}. {clean_title}.**"
            final_content = f"{md_header} - {body}"
        else:
            md_header = f"**Article {full_num}.**"
            final_content = f"{md_header} - {body}"
            
        parsed_articles.append({
            "num": int(num_str),
            "suffix": suffix_str if suffix_str else None,
            "full_num": full_num,
            "title": clean_title,
            "content": final_content
        })
        
    return parsed_articles

def ingest_codex(filepath, code_short_name, code_full_name, valid_from="1900-01-01"):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        print(f"Ingesting {filepath} as {code_short_name}...")
        
        # 1. Register Code
        cur.execute("SELECT code_id FROM legal_codes WHERE short_name = %s", (code_short_name,))
        res = cur.fetchone()
        if not res:
            cur.execute("INSERT INTO legal_codes (full_name, short_name) VALUES (%s, %s) RETURNING code_id",
                        (code_full_name, code_short_name))
            code_id = cur.fetchone()[0]
        else:
            code_id = res[0]
            
        # 2. Parse Content
        if filepath.endswith('.docx'):
            raw_text = get_docx_text(filepath)
        else:
             with open(filepath, 'r', encoding='utf-8') as f:
                raw_text = f.read()
                
        articles = parse_and_standardize(raw_text)
        print(f"Parsed {len(articles)} articles.")
        
        # 3. Insert Versions & Sync rpc_codal logic
        for art in articles:
            # A. Insert into article_versions
            cur.execute("""
                INSERT INTO article_versions (code_id, article_number, content, valid_from, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """, (code_id, art['full_num'], art['content'], valid_from))
            
            # B. Generate Structural Map
            # Logic: If suffix exists -> [-1] (Teal), else [0] (Red)
            # Split content to count paragraphs
            segments = art['content'].split('\n\n')
            base_id = -1 if art['suffix'] else 0
            struct_map = [[base_id] for _ in segments]
            
            # C. Sync to rpc_codal (The display table)
            # Check existence
            cur.execute("SELECT id FROM rpc_codal WHERE article_num = %s AND (article_suffix = %s OR (article_suffix IS NULL AND %s IS NULL))", 
                        (art['num'], art['suffix'], art['suffix']))
            existing = cur.fetchone()
            
            if existing:
                cur.execute("""
                    UPDATE rpc_codal SET 
                        article_title = %s,
                        content_md = %s,
                        structural_map = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (art['title'], art['content'], json.dumps(struct_map), existing[0]))
            else:
                # Default "Book 1", "Title 1" for generic laws if structure is unknown
                # Ideally we parse this too, but for automation we set safe defaults.
                cur.execute("""
                    INSERT INTO rpc_codal 
                    (book, title_num, title_label, article_num, article_suffix, article_title, content_md, structural_map)
                    VALUES (1, 1, 'Generic Title', %s, %s, %s, %s, %s)
                """, (art['num'], art['suffix'], art['title'], art['content'], json.dumps(struct_map)))
                
        conn.commit()
        print(f"Successfully processed {code_short_name}.")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--code", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    
    ingest_codex(args.file, args.code, args.name)
