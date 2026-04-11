import os
import re
import sys
import psycopg2
import json

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_API_DIR = os.path.normpath(os.path.join(_SCRIPT_DIR, '..', 'api'))
if _API_DIR not in sys.path:
    sys.path.insert(0, _API_DIR)
from codal_text import normalize_storage_markdown

CODAL_DIR = os.path.normpath("LexCode/Codals/md")
RPC_MD_PATH = os.path.normpath("LexCode/Codals/md/RPC.md")

def load_base_rpc():
    print("Loading Base RPC.md...")
    with open(RPC_MD_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    articles = {}
    pattern = r'#####\s*Article\s+(\d+(?:-[A-Za-z]+)?)(?:\.|)\s*(.*?)\n(.*?)(?=(?:\n#####\s*Article|\Z))'
    matches = re.findall(pattern, content, flags=re.IGNORECASE | re.DOTALL)
    for match in matches:
        art_num = match[0].strip()
        art_title = match[1].strip()
        art_body = match[2].strip()
        articles[art_num] = {
            'title': art_title,
            'body': art_body,
            'amended_by': ''
        }
    print(f"Extracted {len(articles)} Base RPC articles.")
    return articles


def _article_nums_from_amendment_header(header_rest: str):
    """
    RPC section lines only, e.g. 'Article 266-A (1)(d) of Act...' or 'Articles 337 and 338 of...'
    Does not scan quoted amendment bodies (avoids matching Article 335 in cross-references).
    """
    m_pl = re.search(
        r"Articles\s+(\d+(?:-[A-Za-z]+)?)\s+and\s+(\d+(?:-[A-Za-z]+)?)\b",
        header_rest,
        re.IGNORECASE,
    )
    if m_pl:
        return [m_pl.group(1), m_pl.group(2)]
    m_sg = re.search(
        r"\bArticle\s+(\d+(?:-[A-Za-z]+)?)(?:\s*\([^)]*\))?",
        header_rest,
        re.IGNORECASE,
    )
    return [m_sg.group(1)] if m_sg else []


def _split_amendment_body_by_articles(full_text: str, nums: list) -> dict:
    """Map article_num -> quoted substring when one section amends multiple RPC articles."""
    if len(nums) <= 1:
        return {nums[0]: full_text} if nums else {}
    markers = []
    for n in nums:
        m = re.search(
            rf'(?m)^"?\s*Article\s+{re.escape(str(n))}\.',
            full_text,
        )
        if m:
            markers.append((m.start(), str(n)))
    markers.sort(key=lambda x: x[0])
    out = {}
    for i, (pos, n) in enumerate(markers):
        end = markers[i + 1][0] if i + 1 < len(markers) else len(full_text)
        out[n] = full_text[pos:end].strip()
    return out


def _parse_amendment_block(full_text, art_num, base_articles):
    """
    Split amendment quote block into (title, body).
    Handles Art. 266. *Italics* - body, Article 266-A.Rape; ... .- body, etc.
    """
    ft = full_text.strip().lstrip('"').strip()
    n = re.escape(str(art_num))

    m = re.match(rf'^"?\s*Art\.\s*{n}\.\s+\*(.*?)\*\s*[-–]*\s*(.*)$', ft, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).replace('*', '').strip(), m.group(2).strip()

    m = re.match(rf'^"?\s*Article\s+{n}\.(.+?)\.-\s*(.*)$', ft, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip().replace('*', '').strip(), m.group(2).strip()

    m = re.match(rf'^"?\s*Article\s+{n}\.\s+(.+?)\s*[-–]\s*(.*)$', ft, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    art_title = base_articles.get(art_num, {}).get('title', '')
    body = re.sub(rf'^"?\s*Art(?:icle)?\.\s*{n}\.?\s*', '', ft, flags=re.IGNORECASE)
    return art_title, body.strip()


def load_all_amendments(base_articles):
    import glob
    amendatory_files = []
    amendatory_files.extend(glob.glob(os.path.join(CODAL_DIR, "ra_*.md")))
    amendatory_files.extend(glob.glob(os.path.join(CODAL_DIR, "pd_*.md")))
    amendatory_files.extend(glob.glob(os.path.join(CODAL_DIR, "ca_*.md")))
    amendatory_files.sort()

    amended_count = 0

    for file_path in amendatory_files:
        filename = os.path.basename(file_path)
        law_label = filename.replace('.md', '').upper()

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Split on **Section N.** so we only read Article numbers from the enactment header line
        # (not from cross-references inside quotes).
        sections = re.split(r'(?=\n\*\*Section\s+\d+\.\*\*|\A\*\*Section\s+\d+\.\*\*)', content)
        for sec in sections:
            sec = sec.strip()
            if not sec.startswith('**Section'):
                continue
            m = re.search(
                r'\*\*Section\s+\d+\.\*\*\s*(.+?)\bamended to read as follows:\s*\n',
                sec,
                re.IGNORECASE | re.DOTALL,
            )
            if not m:
                continue
            header_rest = m.group(1)
            raw_amendment = sec[m.end():]
            raw_amendment = re.split(r'\n(?=\*\*Section\s+\d+\.\*\*)', raw_amendment)[0]

            nums = _article_nums_from_amendment_header(header_rest)
            if not nums:
                continue

            lines = raw_amendment.split('\n')
            clean_lines = []
            for line in lines:
                line = re.sub(r'^>\s*', '', line).strip()
                if line:
                    clean_lines.append(line)
            full_text = '\n\n'.join(clean_lines)

            chunks = _split_amendment_body_by_articles(full_text, nums)
            for art_num in nums:
                chunk = chunks.get(str(art_num), full_text if len(nums) == 1 else '')
                if not chunk:
                    continue
                art_title, art_body = _parse_amendment_block(chunk, art_num, base_articles)
                art_body = re.sub(r'(?m)^"\s*', '', art_body)
                art_body = re.sub(r'"\s*$', '', art_body)
                art_body = art_body.replace('\\"', '"')

                base_articles[str(art_num)] = {
                    'title': art_title,
                    'body': art_body,
                    'amended_by': law_label,
                }
                amended_count += 1

    print(f"Total amendments applied across all laws: {amended_count}")
    return base_articles

def scrub_tts_glitches(text):
    if not text: return text
    
    # Strip hanging structural headers (e.g. ## TITLE THREE) that got appended to the end of the previous article's body.
    text = re.sub(r'\n+#+\s*(?:TITLE|CHAPTER|BOOK|SECTION).*$', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    text = re.sub(r'\.\.+', '.', text)
    text = re.sub(r'\.\s*,', ',', text)
    text = re.sub(r'\s+,', ',', text)
    text = re.sub(r';;+', ';', text)
    return text.strip()

def connect_and_update(articles):
    from psycopg2.extras import execute_batch
    with open('api/local.settings.json', 'r') as f:
        conn_string = json.load(f)['Values']['DB_CONNECTION_STRING']
    
    print("Connecting to independent db session...")
    with psycopg2.connect(conn_string) as conn:
        
        with conn.cursor() as cur:
            cur.execute("SELECT id, article_num FROM rpc_codal")
            rows = cur.fetchall()
            
        print(f"Fetched {len(rows)} from db to update...")
        
        batch_data = []
        for row in rows:
            art_id = row[0]
            art_num = str(row[1])
            
            fidelity_data = articles.get(art_num)
            if fidelity_data:
                cleared_body = normalize_storage_markdown(scrub_tts_glitches(fidelity_data['body']))
                cleared_title = scrub_tts_glitches(fidelity_data['title'])
                batch_data.append((cleared_title, cleared_body, art_id))
                
        with conn.cursor() as cur:
            execute_batch(cur, """
                UPDATE rpc_codal 
                SET article_title = %s, content_md = %s
                WHERE id = %s
            """, batch_data, page_size=100)
            
        conn.commit()
                    
        print(f"Successfully committed {len(batch_data)} rows in one batch aligned to Markdown!")

if __name__ == "__main__":
    final_dict = load_base_rpc()
    final_dict = load_all_amendments(final_dict)
    connect_and_update(final_dict)
