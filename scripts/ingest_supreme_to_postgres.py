import os
import json
import psycopg2
from psycopg2 import pool
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
import time
import re

# Configuration
DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING") or "postgres://barappadmin:BRApass021819!@bar-reviewer-app-db.postgres.database.azure.com:5432/postgres?sslmode=require"
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SCRAPER_DIR = os.path.join(BASE_DIR, 'sc_scraper')
DOWNLOADS_DIR = os.path.join(SCRAPER_DIR, 'downloads')

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

GENERIC_TERMS = [
    "people of the philippines", "republic of the philippines", "city of manila",
    "commission on elections", "court of appeals", "sandiganbayan",
    "civil service commission", "nlrc", "ombudsman"
]

def get_db_connection():
    return psycopg2.connect(DB_CONNECTION_STRING)

def init_db():
    """Ensures the table exists."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS supreme_decisions (
            id SERIAL PRIMARY KEY,
            case_number TEXT,
            title TEXT,
            short_title TEXT,
            date DATE,
            sc_url TEXT DEFAULT 'https://sc.judiciary.gov.ph/decisions/',
            ponente TEXT,
            raw_content TEXT,
            main_doctrine TEXT,
            digest_facts TEXT,
            digest_issues TEXT,
            digest_ruling TEXT,
            digest_ratio TEXT,
            digest_significance TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_supreme_case_number ON supreme_decisions(case_number);
        CREATE INDEX IF NOT EXISTS idx_supreme_date ON supreme_decisions(date);
        CREATE INDEX IF NOT EXISTS idx_supreme_ponente ON supreme_decisions(ponente);
    """)
    conn.commit()
    conn.close()

def clean_text(text):
    if not text: return ""
    return " ".join(text.split())

def clean_party_name(name):
    """
    Cleans a party name to extract the surname or simplified entity name.
    """
    name = name.strip()
    
    # Remove roles
    role_pattern = r",\s*(Petitioner|Respondent|Appellant|Appellee|Accused|Plaintiff|Defendant|et al\.|et al)[s\.]*$"
    name = re.sub(role_pattern, "", name, flags=re.IGNORECASE).strip()
    
    # Handle "People of the Philippines" -> "People"
    if "people of the philippines" in name.lower():
        return "People"
    
    # Handle "Republic of the Philippines" -> "Republic"
    if "republic of the philippines" in name.lower():
        return "Republic"
        
    keywords = ["commissioner", "commission", "corporation", "inc.", "corp.", "bank", "company", "university", "school", "union", "association", "republic", "people", "united", "city", "municipality", "province", "administration", "senate", "house", "congress", "office", "court", "tribunal", "board", "bureau", "agency", "department"]
    if any(k in name.lower() for k in keywords):
        return name 
        
    tokens = name.split()
    if not tokens: return name
    
    if len(tokens) == 1: return tokens[0]
    
    last = tokens[-1]
    second_last = tokens[-2].lower() if len(tokens) > 1 else ""
    third_last = tokens[-3].lower() if len(tokens) > 2 else ""
    
    if second_last in ['dela', 'del', 'de', 'di', 'van', 'von', 'san', 'st.', 'sta.']:
        return f"{tokens[-2]} {last}"
    elif third_last in ['de', 'la'] and second_last in ['la', 'del']:
         return f"{tokens[-3]} {tokens[-2]} {last}"
         
    return last

def generate_short_title(full_title):
    if not full_title: return ""
    
    clean_title = full_title
    if " - " in full_title:
        parts = full_title.split(" - ", 1)
        if parts[0].strip().startswith(("G.R.", "A.M.", "A.C.", "B.M.", "I.P.I.")):
             clean_title = parts[1]

    separator = None
    if " v. " in clean_title: separator = " v. "
    elif " vs. " in clean_title: separator = " vs. "
    elif " VS. " in clean_title: separator = " VS. "
    elif " V. " in clean_title: separator = " V. "
    elif " versus " in clean_title.lower(): separator = " versus " 
    
    if not separator:
        if clean_title.lower().startswith("in re:") or clean_title.lower().startswith("re:"):
            return clean_title
        if clean_title.lower().startswith("in the matter of"):
            return clean_title.replace("In the matter of", "In re:")
        return clean_title 

    parties = clean_title.split(separator)
    if len(parties) < 2: return clean_title
    
    p_a = re.split(r'\s+(?:and|AND|&)\s+|,\s+', parties[0])[0].strip()
    p_b = re.split(r'\s+(?:and|AND|&)\s+|,\s+', parties[1])[0].strip()
    
    short_a = clean_party_name(p_a)
    short_b = clean_party_name(p_b)
    
    return f"{short_a} v. {short_b}"

def process_year(year):
    """Worker function to process a single year."""
    metadata_file = os.path.join(SCRAPER_DIR, f"metadata_{year}.json")
    if not os.path.exists(metadata_file):
        return f"Year {year}: No metadata found."

    try:
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata_list = json.load(f)
    except Exception as e:
        return f"Year {year}: JSON Error - {e}"

    if not metadata_list:
        return f"Year {year}: Empty metadata."

    # Prepare data for bulk insert
    records = []
    
    for item in metadata_list:
        sc_id = item.get('id')
        month = item.get('month', '').lower()
        if not sc_id: continue

        # File path for full text
        content_file = os.path.join(DOWNLOADS_DIR, str(year), month, f"{sc_id}.json")
        raw_content = ""
        if os.path.exists(content_file):
            try:
                with open(content_file, 'r', encoding='utf-8') as cf:
                    c_data = json.load(cf)
                    raw_content = c_data.get('main_text', '')
            except: pass

        # Short Title
        full_title = item.get('title', '')
        short_title = generate_short_title(full_title) or item.get('short_title') or full_title

        # Date handling (some dates might be incomplete in metadata, construct if needed)
        # Assuming metadata has 'year', 'month'. Day usually missing in simple metadata unless parsed.
        # For this pass, we might default to 1st of month if day missing, or just year-month-01.
        # But wait, metadata usually has a specific date string in scraping? 
        # Looking at previous view_file, metadata has 'year', 'month'. 
        # If we need exact date, we might need to parse it from title or content.
        # For now, let's strictly use YYYY-MM-01 to satisfy Date type if day is unknown.
        
        month_map = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
            'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        m_int = month_map.get(month.lower(), 1)
        date_str = f"{year}-{m_int:02d}-01"

        records.append((
            item.get('case_number', ''),
            clean_text(full_title),
            clean_text(short_title),
            date_str,
            item.get('url', 'https://sc.judiciary.gov.ph/decisions/'),
            '', # ponente (pending AI)
            clean_text(raw_content)
        ))

    if not records:
        return f"Year {year}: No valid records to insert."

    # Bulk Insert using COPY
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # We use a temp table to avoid massive conflict handling complexity in COPY
        cur.execute("""
            CREATE TEMP TABLE temp_decisions (
                case_number TEXT,
                title TEXT,
                short_title TEXT,
                date DATE,
                sc_url TEXT,
                ponente TEXT,
                raw_content TEXT
            ) ON COMMIT DROP;
        """)
        
        # Prepare CSV buffer
        import io
        csv_buffer = io.StringIO()
        for r in records:
            # Escape tabs and newlines for TSV
            clean_r = [str(x).replace('\t', ' ').replace('\n', '\\n').replace('\r', '') for x in r]
            csv_buffer.write('\t'.join(clean_r) + '\n')
        
        csv_buffer.seek(0)
        
        cur.copy_from(csv_buffer, 'temp_decisions', sep='\t', null='')
        
        # Upsert from Temp to Main
        # Conflict on case_number might be tricky if not unique constraints yet.
        # Let's just INSERT for now. If we need idempotency, we delete by year first.
        
        cur.execute(f"DELETE FROM supreme_decisions WHERE date >= '{year}-01-01' AND date <= '{year}-12-31'")
        
        cur.execute("""
            INSERT INTO supreme_decisions (case_number, title, short_title, date, sc_url, ponente, raw_content)
            SELECT case_number, title, short_title, date, sc_url, ponente, raw_content FROM temp_decisions
            ON CONFLICT (case_number, date) DO UPDATE 
            SET 
                title = EXCLUDED.title,
                short_title = EXCLUDED.short_title,
                sc_url = EXCLUDED.sc_url,
                ponente = EXCLUDED.ponente,
                raw_content = EXCLUDED.raw_content,
                updated_at = CURRENT_TIMESTAMP;
        """)
        
        conn.commit()
        return f"Year {year}: Successfully inserted {len(records)} records."
        
    except Exception as e:
        conn.rollback()
        return f"Year {year}: DB Error - {e}"
    finally:
        conn.close()

def main():
    print("Initializing Database...")
    init_db()
    
    years = list(range(2000, 2025)) # Processing recent years first as per user request
    # years = list(range(1901, 2025)) # Full range
    
    print(f"Starting ingestion for {len(years)} years with 10 workers...")
    
    start_time = time.time()
    
    with ProcessPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_year, year): year for year in years}
        
        for future in as_completed(futures):
            year = futures[future]
            try:
                result = future.result()
                print(result)
            except Exception as e:
                print(f"Year {year}: Unhandled Exception - {e}")
                
    print(f"Total time: {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    main()
