
import psycopg2
import difflib
import json
import re
import os
import sys
from pathlib import Path


def _resolve_conn_str() -> str:
    env = os.environ.get("DB_CONNECTION_STRING")
    if env:
        return env
    settings = Path(__file__).resolve().parents[2] / "api" / "local.settings.json"
    try:
        if settings.is_file():
            raw = json.loads(settings.read_text(encoding="utf-8"))
            v = raw.get("Values", {}).get("DB_CONNECTION_STRING")
            if v:
                return v
    except OSError:
        pass
    return os.environ.get("DB_CONNECTION_STRING") or (
        "postgres://postgres:b66398241bfe483ba5b20ca5356a87be@localhost:5432/lexmateph-ea-db"
    )

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
        conn = psycopg2.connect(_resolve_conn_str())
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
        
        # 2. Fetch History ordered by valid_from (STRICTLY for RPC code_id)
        cur.execute("SELECT code_id FROM legal_codes WHERE short_name = 'RPC'")
        rpc_code_id = cur.fetchone()[0]
        
        query = """
        SELECT 
            av.content, 
            av.amendment_id,
            av.valid_from
        FROM article_versions av
        WHERE av.article_number = %s AND av.code_id = %s
        ORDER BY av.valid_from ASC NULLS FIRST, av.created_at ASC;
        """
        cur.execute(query, (str(article_num), rpc_code_id))
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
                    # Paragraph text unchanged vs prior version, but a new statute still "passes"
                    # the whole article — list items that are word-identical must still show this
                    # amendment layer (e.g. RA 10592 re-enacted Art. 29 including items 1 and 2).
                    for k in range(j2 - j1):
                        old_hist = current_map[i1 + k]
                        new_hist = sorted(list(set(old_hist + [source_id])))
                        new_map.append(new_hist)
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
            
        print(f"Generated Map for Art {article_num}: {len(current_map)} paras", flush=True)
        
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

def _natural_sort_key(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", str(s))]


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a]
    if args and args[0] in ("-h", "--help"):
        print("Usage: python structural_mapper.py [article_num] | --all")
        print("  Regenerates rpc_codal.structural_map from article_versions (paragraph lineage).")
        sys.exit(0)
    if args and args[0] == "--all":
        conn = psycopg2.connect(_resolve_conn_str())
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT av.article_number::text
            FROM article_versions av
            INNER JOIN legal_codes lc ON lc.code_id = av.code_id
            WHERE lc.short_name = 'RPC'
            """
        )
        nums = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
        nums.sort(key=_natural_sort_key)
        print(f"Regenerating structural_map for {len(nums)} RPC articles with version history…", flush=True)
        for anum in nums:
            print(f"  Article {anum}…", flush=True)
            generate_and_save_map(anum)
        print("Done.", flush=True)
    elif args:
        generate_and_save_map(args[0])
    else:
        generate_and_save_map("29")
