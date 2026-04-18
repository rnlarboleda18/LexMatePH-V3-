import os
import json
import re
import psycopg2
from pathlib import Path
import sys

# Setup environment
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "api"))
from codal_text import normalize_storage_markdown

def get_db_connection():
    api_settings = _REPO_ROOT / "api" / "local.settings.json"
    try:
        with open(api_settings, encoding="utf-8") as f:
            conn_str = json.load(f)["Values"]["DB_CONNECTION_STRING"]
    except Exception:
        # Fallback to env or default
        conn_str = os.environ.get("DB_CONNECTION_STRING")
    return psycopg2.connect(conn_str)

def parse_baseline_md(filepath):
    """
    Parses a large RPC.md file into article chunks using regex.
    Expects format: "##### Article 1. Title. \n\n Content..."
    """
    content = Path(filepath).read_text(encoding="utf-8")
    
    # Split by Article headers
    # We look for "##### Article N. Title."
    articles = []
    
    # Find all article blocks
    pattern = r"(##### Article\s+(\d+[A-Za-z-]*)\.\s+(.*?)\.\n\s*(.*?)(?=\n##### Article|\Z))"
    matches = re.finditer(pattern, content, re.DOTALL)
    
    for m in matches:
        full_block = m.group(1).strip()
        num = m.group(2)
        title = m.group(3).strip()
        body = m.group(4).strip()
        articles.append({
            "num": num,
            "title": title,
            "content": f"Article {num}. {title}. - {body}"
        })
    
    return articles

def ingest_baseline():
    baseline_path = _REPO_ROOT / "LexCode" / "Codals" / "md" / "RPC.md"
    if not baseline_path.exists():
        print("ERROR: RPC.md not found")
        return

    print(f"Parsing baseline {baseline_path.name}...")
    articles = parse_baseline_md(baseline_path)
    print(f"Found {len(articles)} articles.")

    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # We don't wipe, we just upsert the baseline state
        # Set amendment_id to 'BASELINE_1932'
        amendment_id = "BASELINE_1932"
        date = "1932-01-01"
        description = "Original Revised Penal Code of 1932"

        for art in articles:
            num = art["num"]
            title = art["title"]
            content = art["content"]
            
            # 1. Update/Insert article_versions
            # First, check if baseline version already exists
            cur.execute("""
                SELECT version_id FROM article_versions 
                WHERE article_number = %s 
                AND amendment_id = %s
                AND code_id = (SELECT code_id FROM legal_codes WHERE full_name ILIKE '%%Revised Penal Code%%' LIMIT 1)
            """, (num, amendment_id))
            if cur.fetchone():
                # Skip if already exists or update?
                # For baseline, we overwrite to ensure the title case/format fix is applied
                update_ver = """
                    UPDATE article_versions 
                    SET content = %s 
                    WHERE article_number = %s AND amendment_id = %s
                    AND code_id = (SELECT code_id FROM legal_codes WHERE full_name ILIKE '%%Revised Penal Code%%' LIMIT 1)
                """
                cur.execute(update_ver, (content, num, amendment_id))
            else:
                insert_ver = """
                    INSERT INTO article_versions 
                    (code_id, article_number, content, valid_from, amendment_id)
                    VALUES ((SELECT code_id FROM legal_codes WHERE full_name ILIKE '%%Revised Penal Code%%' LIMIT 1), %s, %s, %s, %s)
                """
                cur.execute(insert_ver, (num, content, date, amendment_id))

            # 2. Update rpc_codal (The active view)
            # Find existing or insert new
            cur.execute("SELECT id FROM rpc_codal WHERE article_num = %s", (num,))
            row = cur.fetchone()
            
            if row:
                cur.execute("""
                    UPDATE rpc_codal 
                    SET article_title = %s, content_md = %s, updated_at = NOW()
                    WHERE article_num = %s
                """, (title, normalize_storage_markdown(content), num))
            else:
                # Basic insert (Book/Title info will be missing unless we parse it too,
                # but we'll assume the subsequent amendments will fill the gaps or 
                # we can fetch from sibling)
                cur.execute("""
                    INSERT INTO rpc_codal (article_num, article_title, content_md, created_at, updated_at)
                    VALUES (%s, %s, %s, NOW(), NOW())
                """, (num, title, normalize_storage_markdown(content)))

        conn.commit()
        print("Successfully ingested 1932 baseline.")
    except Exception as e:
        conn.rollback()
        print(f"CRITICAL ERROR: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    ingest_baseline()
