import re
import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONNECTION = "dbname=lexmateph-ea-db user=postgres password=b66398241bfe483ba5b20ca5356a87be host=localhost port=5432"

def parse_md(md_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    sections = {}
    current_art_label = None
    current_art_num = None
    
    # Simple context tracker
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Article Header: ## ARTICLE I National Territory
        art_match = re.match(r'^##\s+(ARTICLE\s+([IVXLCDM]+))\s+(.*)', line, re.IGNORECASE)
        if art_match:
            current_art_label = art_match.group(1).upper()
            current_art_num = art_match.group(2).upper()
            continue
            
        # Preamble: ## PREAMBLE
        if line.upper() == "## PREAMBLE":
            sections["PREAMBLE-0"] = {"article_label": "PREAMBLE", "section_label": "PREAMBLE", "text": ""}
            current_art_label = "PREAMBLE"
            current_art_num = "PRE"
            continue
            
        # Section Header: ### SECTION 1. ...
        sec_match = re.match(r'^###\s+(SECTION\s+(\d+)\.)\s*(.*)', line, re.IGNORECASE)
        if sec_match:
            sec_label = sec_match.group(1).strip()
            sec_num = sec_match.group(2)
            content = sec_match.group(3)
            key = f"{current_art_num}-{sec_num}"
            sections[key] = {
                "article_label": current_art_label,
                "section_label": sec_label,
                "text": content
            }
            continue
            
        # If it's not a header, append to last section
        if current_art_num:
            # Find the latest section for this article
            # This is a bit complex since markdown is sequential
            # For now, let's just append to the last key added
            if sections:
                last_key = list(sections.keys())[-1]
                sections[last_key]["text"] += " " + line
                
    return sections

def compare():
    md_sections = parse_md(r"C:\Users\rnlar\.gemini\antigravity\scratch\bar_project_v2\CodexPhil\Codals\md\1987_Philippine_Constitution_Structured.md")
    
    try:
        conn = psycopg2.connect(DB_CONNECTION)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Filter for Constitution only
        cur.execute("""
            SELECT article_num, article_label, section_label, content_md 
            FROM const_codal 
            WHERE book_code IS NULL OR book_code = 'CONST'
            ORDER BY list_order;
        """)
        db_rows = cur.fetchall()
        
        print(f"{'ArticleKey':<12} | {'DB Label':<25} | {'MD Label':<25} | Status")
        print("-" * 90)
        
        db_keys = set()
        for row in db_rows:
            key = row['article_num']
            db_keys.add(key)
            db_text = row['content_md'].strip()
            
            # Map DB 'PREAMBLE' to MD 'PREAMBLE-0'
            md_key = "PREAMBLE-0" if key == "PREAMBLE" else key
            
            if md_key in md_sections:
                md_text = md_sections[md_key]['text'].strip()
                # Remove extra spaces/newlines for comparison
                db_clean = " ".join(db_text.split())
                md_clean = " ".join(md_text.split())
                
                if db_clean == md_clean:
                    status = "OK"
                elif abs(len(db_clean) - len(md_clean)) < 10:
                    status = "MINOR DIFF"
                else:
                    status = f"DIFF (DB:{len(db_clean)}, MD:{len(md_clean)})"
                
                print(f"{key:<12} | {str(row['section_label']):<25} | {md_sections[md_key]['section_label']:<25} | {status}")
            else:
                print(f"{key:<12} | {str(row['section_label']):<25} | {'MISSING':<25} | MISSING IN MD")
                
        # Check for items in MD but not in DB
        for md_key in md_sections:
            db_key = "PREAMBLE" if md_key == "PREAMBLE-0" else md_key
            if db_key not in db_keys:
                print(f"{db_key:<12} | {'MISSING IN DB':<25} | {md_sections[md_key]['section_label']:<25} | EXTRA IN MD")
                
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    compare()
