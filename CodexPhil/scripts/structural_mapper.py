
import psycopg2
import difflib
import json
import re
import os

# Use env var or default
CONN_STR = os.environ.get("DB_CONNECTION_STRING") or "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"

def split_paragraphs(text):
    if not text:
        return []
    # Split by double newlines, trimming whitespace
    return [p.strip() for p in re.split(r'\n\n+', text) if p.strip()]

def generate_and_save_map(article_num, conn=None):
    """
    Generates the structural lineage map for a given article based on its version history
    and saves it to the rpc_codal table.
    """
    should_close = False
    if conn is None:
        conn = psycopg2.connect(CONN_STR)
        should_close = True
        
    try:
        cur = conn.cursor()
        
        # 1. Fetch Article Metadata (Suffix, Amendments)
        cur.execute("SELECT article_suffix, amendments FROM rpc_codal WHERE article_num = %s", (article_num,))
        res = cur.fetchone()
        if not res:
            print(f"Article {article_num} not found.")
            return
            
        article_suffix, amendments_data = res
        amendments_data = amendments_data or []
        
        # Map "Act No. 4117" ID -> 1, "CA 99" -> 2 based on order in generic list?
        # OR better: The map values should correspond to the order they appear in the UI 'amendments' list?
        # The UI renders standard amendments list.
        # We need a stable ID mapping.
        # Let's map Amendment Database ID -> Index in the 'amendments' array (1-based).
        amendment_map = { a['id']: i+1 for i, a in enumerate(amendments_data) }
        
        # 2. Fetch History ordered by valid_from
        query = """
        SELECT 
            content, 
            amendment_id,
            valid_from
        FROM article_versions 
        WHERE article_number = %s
        ORDER BY valid_from ASC NULLS FIRST, created_at ASC;
        """
        cur.execute(query, (str(article_num),))
        versions = cur.fetchall()
        
        if not versions:
            print(f"No history found for Article {article_num}")
            return

        # Base Version
        current_text = versions[0][0]
        current_paras = split_paragraphs(current_text)
        
        # Determine Base ID
        # If Suffix exists OR Number contains letters (e.g. "266-A"), Base is Added (-1).
        # Else Base is Original (0).
        is_added = article_suffix or (isinstance(article_num, str) and re.search(r'[A-Za-z]', article_num))
        base_id = -1 if is_added else 0
        current_map = [[base_id] for _ in current_paras] 
        
        # Iterate subsequent versions
        for idx, (ver_text, ver_id, ver_date) in enumerate(versions[1:], start=1):
            # Determine Source ID
            source_id = amendment_map.get(ver_id, idx) # Fallback to loop idx
            
            new_paras = split_paragraphs(ver_text)
            new_map = []
            
            matcher = difflib.SequenceMatcher(None, current_paras, new_paras)
            
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == 'equal':
                    for k in range(j2 - j1):
                        new_map.append(current_map[i1 + k])
                elif tag == 'replace':
                    # Inherit history + Add New Source
                    # Only take history from the first replaced block to avoid explosion
                    base_hist = current_map[i1] if i1 < i2 else [base_id]
                    for _ in range(j2 - j1):
                        # Add new source, filter duplicates, sort
                        new_hist = sorted(list(set(base_hist + [source_id])))
                        new_map.append(new_hist)
                elif tag == 'insert':
                    # Inserted blocks inherit Base + New Source
                    # If it's an Added Article, it just gets [source_id]?
                    # No, user wants accumulation.
                    for _ in range(j2 - j1):
                        new_map.append([base_id, source_id]) 
                elif tag == 'delete':
                    pass
                    
            current_paras = new_paras
            current_map = new_map
            
        print(f"Generated Map for Art {article_num}: {len(current_map)} paras")
        
        # Save to DB
        # Save to DB
        cur.execute("UPDATE rpc_codal SET structural_map = %s WHERE article_num = %s", (json.dumps(current_map), str(article_num)))
        conn.commit()
        conn.commit()

    except Exception as e:
        print(f"Error mapping Article {article_num}: {e}")
        if conn: conn.rollback()
    finally:
        if should_close and conn:
            conn.close()

if __name__ == "__main__":
    # Test on Art 80
    generate_and_save_map(80)
