import logging
import os
import io
import re
import json
import time
import threading
from datetime import datetime, timedelta

# Removed local file logging as it causes permission errors in production
import azure.functions as func

# Database connection
from psycopg2.extras import RealDictCursor
from db_pool import get_db_connection, put_db_connection

# Azure Storage (optional - used for caching)
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions, ContentSettings

# Azure Speech (optional - used if key is available)
try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_SPEECH_AVAILABLE = True
except Exception:
    AZURE_SPEECH_AVAILABLE = False

audio_provider_bp = func.Blueprint()

# ----- Configuration & Versioning -----
CACHE_VERSION = "v1"  # Reset to v1 as blobs are being cleared

# Global lock: Azure Speech F0 allows only 1 concurrent real-time synthesis.
# This prevents 429 errors when multiple requests overlap (e.g. fast track skipping).
_TTS_LOCK = threading.Lock()
_TTS_LOCK_TIMEOUT = 30  # seconds to wait before giving up and using gTTS

# ----- Custom Pronunciation Rules -----
LATIN_REPLACEMENTS = {
    r"certiorari": "ser-sho-rah-ree",
    r"mandamus": "man-dah-mus",
    r"habeas corpus": "hah-be-as kor-pus",
    r"mens rea": "mens re-yah",
    r"actus reus": "ak-tus re-yus",
    r"prima facie": "pree-ma fah-she",
    r"pro bono": "pro bo-no",
    r"stare decisis": "stah-re de-si-sis",
    r"obiter dictum": "o-bi-ter dik-tum",
    r"ratio decidendi": "rah-sho de-si-den-dee",
    r"inter alia": "in-ter ah-lya",
    r"mutatis mutandis": "mu-tah-tis mu-tan-dis",
    r"ex parte": "eks par-te",
    r"de facto": "de fak-to",
    r"de jure": "de ju-re",
    r"per se": "per seh",
    r"ultra vires": "ul-tra vi-res",
    r"bona fide": "bo-na fi-de",
    r"in solidum": "in so-li-dum",
    r"lis pendens": "lis pen-dens",
    r"quo warranto": "kwo wa-ran-to",
    r"in re": "in reh",
}

SPANISH_TERMS = [
    # ── Compound phrases first (longest match wins) ──────────────────────────
    "reclusión perpetua", "reclusion perpetua",
    "reclusión temporal", "reclusion temporal",
    "reclusión mayor",   "reclusion mayor",      # ← was missing
    "prisión mayor",     "prision mayor",
    "prisión correccional", "prision correccional",
    "prisión correccional mayor", "prision correccional mayor",  # ← was missing
    "arresto mayor",
    "arresto menor",
    # ── Individual terms ─────────────────────────────────────────────────────
    "prisión", "prision",
    "arresto",
    "reclusión", "reclusion",
    "correccional",
    "perpetua",
    "temporal",
    "mayor",
    "menor",
    "destierro",
    "fianza",
    "multa",
]

FILIPINO_LEGAL_TERMS = [
    "barangay", "sangguniang", "pambansa", "batas", "republika", "poblacion",
    "katarungang", "pambarangay", "tagapamayapa", "lupon", "tanod", "malacañang",
    "cedula", "hacienda", "panlalawigan", "panlungsod", "pambayan", "pinuno",
    "kagawad", "kapitan", "sanggunian", "bayan", "punong"
]

LATIN_MAXIMS = [
    "ignorantia legis non excusat",
    "dura lex sed lex",
    "res ipsa loquitur",
    "caveat emptor",
    "pacta sunt servanda",
    "salus populi suprema lex esto",
    "amicus curiae",
    "nemo dat quod non habet",
    "actus non facit reum nisi mens sit rea",
    "expressio unius est exclusio alterius",
    "lex loci celebrationis",
    "lex rei sitae",
    "pari delicto",
    "res judicata",
    "falsus in uno, falsus in omnibus",
    "nullum crimen, nulla poena sine lege",
    "pro hac vice",
    "quantum meruit",
    "quid pro quo",
    "terra nullius",
    "jus cogens",
    "erga omnes",
    "prima facie",
    "stare decisis",
    "ultra vires",
    "bona fide",
    "ex post facto",
    "habeas corpus",
    "mandamus",
    "certiorari",
    "quo warranto",
    "subpoena duces tecum",
    "subpoena ad testificandum",
    "de facto",
    "de jure",
    "in re",
    "per se",
    "lis pendens",
    "inter alia",
    "mutatis mutandis",
    "ex parte"
]

FILIPINO_NAME_REPLACEMENTS = {
    r"macabuhay": "mah-kah-bu-hai",
    r"virgillio": "vir-hee-lyo",
    r"garcia": "gar-si-ya",
    r"pineda": "pi-ne-dah",
    r"bautista": "bah-oo-tis-tah",
    r"santos": "san-tos",
    r"reyes": "re-yes",
    r"quisumbing": "ki-sum-bing",
    r"pangilinan": "pa-ngi-li-nan",
    r"guingona": "gi-ngo-nah",
    r"angeles": "an-he-les",
}

def _apply_custom_pronunciations(text):
    if not text: return text
    
    # Convert Roman Numerals for ARTICLE headers (e.g., ARTICLE I -> ARTICLE 1) to force Azure speaking accuracy
    def _roman_to_arabic(match):
        roman_num = match.group(1).upper()
        roman_map = {
            'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10,
            'XI': 11, 'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15, 'XVI': 16, 'XVII': 17, 'XVIII': 18
        }
        if roman_num in roman_map:
            return f"ARTICLE {roman_map[roman_num]}"
        return match.group(0)
        
    text = re.sub(r'\bARTICLE\s+([IVX]+)\b', _roman_to_arabic, text, flags=re.IGNORECASE)
    
    # 1. Base Symbols & Abbreviations
    text = text.replace("PHP", " Pesos ")
    text = text.replace(" v. ", " versus ")
    
    # Currency replacements: P2000, ₱2,000.00 -> "2000 pesos"
    text = re.sub(r'(?<![a-zA-Z])(?:[Pp₱]|PhP|PHP)\.?\s*([\d,]+(?:\.\d{2})?)', r'\1 pesos', text)
    
    # 2. Latin Maxims & Phrases (Wrapped for it-IT pronunciation)
    # Sort by length descending to match longest phrases first
    for maxim in sorted(LATIN_MAXIMS, key=len, reverse=True):
        text = re.sub(fr'(?i)(?<!__LATIN_START__)\b({maxim})\b(?!__LATIN_END__)', r'__LATIN_START__\1__LATIN_END__', text)

    # 3. Filipino Legal terms (Wrapped for fil-PH pronunciation)
    for term in FILIPINO_LEGAL_TERMS:
        text = re.sub(fr'(?i)(?<!__PH_START__)\b({term})\b(?!__PH_END__)', r'__PH_START__\1__PH_END__', text)

    # 4. Spanish Legal terms wrapped in SSML boundary tokens
    for term in SPANISH_TERMS:
        # Avoid wrapping terms that are already enclosed
        text = re.sub(fr'(?i)(?<!__ES_START__)\b({term})\b(?!__ES_END__)', r'__ES_START__\1__ES_END__', text)

    # 5. Latin Individual Terms (Phonetic fallback for anything not caught in maxims)
    for latin, phonetic in LATIN_REPLACEMENTS.items():
        # Only apply if not already inside a LATIN block
        if f"__LATIN_START__{latin}__LATIN_END__" not in text:
            text = re.sub(fr'(?i)(?<!__LATIN_START__)\b{latin}\b(?!__LATIN_END__)', phonetic, text)

    # 4. Filipino Surnames & Names (Case Insensitive)
    for name, phonetic in FILIPINO_NAME_REPLACEMENTS.items():
        text = re.sub(fr'(?i)\b{name}\b', phonetic, text)
        
    # 5. Cleanup redundant figures in parentheses e.g. "one (1)" -> "one"
    text = re.sub(r'([a-zA-Z-]+)\s*\(\d+\)', r'\1', text)
    
    # 6. Bar Question specific: Fix "NO" (word) vs "No." (number)
    # Force uppercase NO to lowercase to prevent spelling out (N-O)
    text = re.sub(r'\bNO\b', 'no', text)
    # Replace "No." or "no." with "number"
    text = re.sub(r'\b[Nn]o\.', 'number', text)
    
    # 7. Article abbreviations
    # Plural: Arts. or Arts or arts -> Articles
    text = re.sub(r'\b[Aa]rts\.?', 'Articles', text)
    # Singular: Art. or art. -> Article
    text = re.sub(r'\b[Aa]rt\.', 'Article', text)
    
    return text

# ----- Blob Cache (best-effort, degrades silently) -----
def _get_blob_client(blob_name):
    try:
        conn_str = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "UseDevelopmentStorage=true")
        if conn_str == "UseDevelopmentStorage=true":
            logging.warning("AZURE_STORAGE_CONNECTION_STRING not configured, blob cache disabled.")
            return None
        svc = BlobServiceClient.from_connection_string(
            conn_str,
            connection_timeout=15,
            read_timeout=30,
            retry_total=2
        )
        container = svc.get_container_client("lexplay-audio-cache")
        try:
            if not container.exists():
                container.create_container()
        except Exception as e:
            logging.warning(f"Failed to check/create container: {e}")
            return None
            
        return container.get_blob_client(blob_name)
    except Exception as e:
        logging.warning(f"Blob client initialization failed: {e}")
        return None

def _get_from_cache(blob_name):
    client = _get_blob_client(blob_name)
    if not client:
        return None
    try:
        if client.exists():
            logging.info(f"CACHE HIT: {blob_name}")
            sas = generate_blob_sas(
                account_name=client.account_name,
                container_name=client.container_name,
                blob_name=client.blob_name,
                account_key=client.credential.account_key,
                permission=BlobSasPermissions(read=True),
                start=datetime.utcnow() - timedelta(minutes=15),
                expiry=datetime.utcnow() + timedelta(days=3) # Long-lived cache redirect (72h)
            )
            return f"{client.url}?{sas}"
    except Exception as e:
        logging.warning(f"Cache read error: {e}")
    return None

def _save_to_cache(blob_name, data, mime_type='audio/mpeg'):
    client = _get_blob_client(blob_name)
    if not client:
        return
    try:
        client.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=mime_type)
        )
        logging.info(f"Cached: {blob_name} ({mime_type})")
    except Exception as e:
        logging.warning(f"Cache write error: {e}")

def _chunk_text(text, max_len=2000):
    """Split text into chunks of at most max_len at sentence boundaries."""
    if not text:
        return []
    
    # Split by common sentence terminators but keep them
    sentences = re.split(r'([.!?]\s+)', text)
    chunks = []
    current_chunk = ""
    
    for s in sentences:
        if len(current_chunk) + len(s) <= max_len:
            current_chunk += s
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # If a single sentence is longer than max_len, split it by whitespace
            if len(s) > max_len:
                words = s.split()
                temp_chunk = ""
                for word in words:
                    if len(temp_chunk) + len(word) + 1 <= max_len:
                        temp_chunk += (word + " ")
                    else:
                        chunks.append(temp_chunk.strip())
                        temp_chunk = word + " "
                current_chunk = temp_chunk
            else:
                current_chunk = s
                
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return [c for c in chunks if c]


# ----- Text fetch from DB -----
import threading
_codal_boundaries = {}
_codal_boundaries_lock = threading.Lock()

def get_codal_boundaries(table_name):
    global _codal_boundaries
    if table_name in _codal_boundaries:
        return _codal_boundaries[table_name]
        
    with _codal_boundaries_lock:
        if table_name in _codal_boundaries:
            return _codal_boundaries[table_name]
            
        bounds = {}
        try:
            conn = get_db_connection()
            try:
                with conn.cursor() as cur:
                    if table_name == 'roc_codal':
                        bounds = {'g1': {}, 'g2': {}}
                        cur.execute("SELECT id, LOWER(group_1_title), LOWER(group_2_title) FROM roc_codal ORDER BY rule_num ASC, section_num ASC")
                        for row in cur.fetchall():
                            id_val, g1, g2 = row
                            id_str = str(id_val)
                            if g1 and g1 not in bounds['g1']: bounds['g1'][g1] = id_str
                            if g2 and g2 not in bounds['g2']: bounds['g2'][g2] = id_str
                        
                    elif table_name in ['const_codal', 'consti_codal', 'fc_codal']:
                        bounds = {'group_header': {}}
                        cur.execute(f"SELECT LOWER(group_header), MIN(id) FROM {table_name} WHERE group_header IS NOT NULL AND group_header != '' GROUP BY LOWER(group_header)")
                        for r in cur.fetchall(): bounds['group_header'][r[0]] = r[1]
                        
                    elif table_name in ['rpc_codal', 'civ_codal', 'labor_codal']:
                        bounds = {'book_label': {}, 'title_label': {}, 'chapter_label': {}}
                        for col in bounds.keys():
                            cur.execute(f"SELECT LOWER({col}), MIN(id) FROM {table_name} WHERE {col} IS NOT NULL AND {col} != '' GROUP BY LOWER({col})")
                            for r in cur.fetchall(): bounds[col][r[0]] = r[1]
                            
            finally:
                put_db_connection(conn)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to load boundaries for {table_name}: {e}")
            
        _codal_boundaries[table_name] = bounds
        return bounds

def _get_text_for_case(content_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT spoken_script, main_doctrine, digest_facts, digest_issues, 
                   digest_ruling, digest_significance, digest_ratio,
                   short_title, case_number
            FROM sc_decided_cases WHERE id = %s
        """, (content_id,))
        row = cur.fetchone()
        if not row:
            return None, "Case not found"

        # Build concatenated text in the order requested by user:
        parts = []
        
        # 1. LexPlay Audio Summary
        summary = row.get('spoken_script')
        if summary:
            parts.append(summary)
            
        # 2. Main Doctrine
        doctrine = row.get('main_doctrine')
        if doctrine:
            parts.append(f"Main Doctrine. {doctrine}")

        # 3. Facts
        facts = row.get('digest_facts')
        if facts:
            # Clean facts (strip common markdown/headers)
            clean_facts = re.sub(r'#.*?\n', '', facts)
            parts.append(f"The Facts of the case. {clean_facts}")

        # 4. Issues
        issues = row.get('digest_issues')
        if issues:
            parts.append(f"The Issues presented. {issues}")

        # 5. Ruling
        ruling = row.get('digest_ruling')
        if ruling:
            parts.append(f"The Court's Ruling. {ruling}")

        # 6. Other Rulings or Collateral Rulings/Matter (Significance) - REMOVED BY USER REQUEST

        # 7. Ratio Decidendi
        ratio = row.get('digest_ratio')
        if ratio:
            parts.append(f"The Ratio Decidendi. {ratio}")

        if not parts:
            # Fallback for very old data
            t = row.get('short_title') or row.get('title') or row.get('case_number') or "Case"
            return f"No summary available for {t}.", None

        # Clean all parts: Remove structural MD only, keep punctuation
        final_text = "\n\n".join(parts)
        final_text = re.sub(r'[#*`_\[\]]', ' ', final_text)
        # Replace all newlines with spaces for smoothTTS flow
        final_text = re.sub(r'\s+', ' ', final_text).strip()

        # Apply central custom pronunciations (Latin, PHP, Mayor, etc.)
        final_text = _apply_custom_pronunciations(final_text)

        return final_text, None
    finally:
        put_db_connection(conn)

def _get_text_for_codal(content_id, code_id=None):
    """
    Fetch article text for TTS.
    content_id may be:
       - an article_num string like "1", "266-A", "0" (Preliminary)
       - a UUID (version_id in article_versions)
    Strategy:
       1. If code_id maps to a legacy table, try article_num lookup first (string match).
       2. Fall back to UUID lookup in article_versions.
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    LEGACY_TABLES = {
        'rpc': 'rpc_codal',
        'civ': 'civ_codal',
        'labor': 'labor_codal',
        'const': 'consti_codal',
        'fc': 'fc_codal',
        'roc': 'roc_codal',
    }
    try:
        if code_id and code_id.lower() in LEGACY_TABLES:
            table = LEGACY_TABLES[code_id.lower()]
            cols = "id, article_num, article_title, content_md"
            if table in ["consti_codal", "const_codal"]:
                cols = "id, article_num, article_title, group_header, content_md, section_label"
            elif table == "fc_codal":
                cols = "id, article_num, article_title, content_md, section_label, group_header"
            elif table in ["rpc_codal", "civ_codal", "labor_codal"]:
                cols = "id, book_label, title_label, chapter_label, article_num, article_title, content_md"
            elif table == "roc_codal":
                cols = (
                    "id, rule_section_label AS article_num, section_title AS article_title, "
                    "section_content AS content_md, group_1_title, group_2_title, "
                    "part_num, part_title, "
                    "COALESCE(rule_title_full, ("
                    "  SELECT r2.rule_title_full FROM roc_codal r2 "
                    "  WHERE r2.rule_num = roc_codal.rule_num "
                    "  AND r2.rule_title_full IS NOT NULL LIMIT 1"
                    ")) AS group_header"
                )

            # --- Multi-stage Lookup Strategy ---
            search_patterns = [str(content_id)] # 1. Exact match
            
            # Backward compat: '0' used to be the Preamble/Preliminary before we renamed or for specific codal indexing
            if str(content_id) == '0' and code_id:
                if code_id.lower() == 'const':
                    search_patterns.insert(0, 'PREAMBLE')
                elif code_id.lower() == 'rpc':
                    # RPC first record or Preliminary
                    search_patterns.insert(0, '1') # Fallback to Art 1 if 0 is used for indexing
            
            cid_str = str(content_id).strip()
            extra_filter = ""
            if code_id.lower() == 'fc':
                # FC articles usually look like FC-I-2 or FC-IX-236
                search_patterns.append(f"%-{cid_str}")
            elif code_id.lower() == 'const':
                # Const articles look like II-1, X-2
                search_patterns.append(f"%-{cid_str}")
                extra_filter = " AND article_num NOT LIKE 'FC-%%'"
            elif code_id.lower() == 'rpc':
                if not cid_str.lower().startswith("art"):
                    search_patterns.append(f"Art% {cid_str}%")

            search_column = "rule_section_label" if table == "roc_codal" else "article_num"

            row = None
            for pattern in search_patterns:
                op = "LIKE" if "%" in pattern else "="
                try:
                    cur.execute(
                        f"SELECT {cols} FROM {table} WHERE {search_column} {op} %s{extra_filter} LIMIT 1",
                        (pattern,)
                    )
                    row = cur.fetchone()
                    if row: break
                except Exception:
                    conn.rollback()
            
            # Fallback: Absolute ID lookup (UUID)
            if not row:
                try:
                    cur.execute(
                        f"SELECT {cols} FROM {table} WHERE id::text = %s LIMIT 1",
                        (str(content_id),)
                    )
                    row = cur.fetchone()
                except Exception:
                    conn.rollback()

            if row:
                art_num = str(row.get('article_num') or '')
                art_title = (row.get('article_title') or '').strip()
                group_header = (row.get('group_header') or '').strip()
                content = (row.get('content_md') or '').strip()
                content = content.replace('\r\n', '\n').replace('\r', '\n')
                
                # TTS Cleaning: Remove structural MD only, replace harsh stops with commas
                clean = re.sub(r'[#*`_\[\]]', ' ', str(content))
                clean = re.sub(r'[:;]', ',', clean)
                # Replace all newlines and excessive whitespace with a single space
                clean = re.sub(r'\s+', ' ', clean).strip()

                # Strip literal backslash-escape text stored in DB content
                # e.g. DB may store literal '\n' (backslash+n as 2 chars) between enumeration items
                # Azure TTS reads these as "backslash en" — audible as "backslash TWO backslash"
                clean = re.sub(r'\\[nrtfvb]', ' ', clean)  # \n \r \t etc. as text
                clean = clean.replace('\\', ' ')           # any remaining lone backslash
                clean = re.sub(r'\s+', ' ', clean).strip() # re-collapse after removals

                # Strip redundant digit clarifications like "one (1)" -> "one", "five (5) years" -> "five years"
                # MUST run BEFORE enumeration conversion while (N) is still in paren form
                clean = re.sub(r'([a-zA-Z-]+)\s*\(\s*\d+\s*\)', r'\1', clean)

                # Convert enumerated item labels (1) (2) (3) to "1," so TTS reads them naturally
                # Uses \s* around digit to handle spaces left by backslash stripping: \(2\) -> " (2 )" -> "2,"
                clean = re.sub(r'\(\s*(\d+)\s*\)', r'\1,', clean)

                # Strip currency repetitions like (₱40,000) or (P200,000)
                clean = re.sub(r'\(\s*[₱P]\s*[\d,.]+\s*\)', '', clean)
                
                # Strip legal citation/version tags ANYWHERE in text:
                # Matches (n), (1a), (6a), (1a, R2), (1a, n) etc.
                # Does NOT match pure subsection labels (a),(b),(c) — those have a single letter only
                clean = re.sub(
                    r'\s*\(\s*(?:(?:\d+[a-zA-Z]?|n|[A-Z]\d+)(?:\s*,\s*(?:\d+[a-zA-Z]?|n|[A-Z]\d+))*)\s*\)',
                    ' ', clean
                )
                clean = re.sub(r'\s+', ' ', clean).strip()
                
                # Deduplication logic (for Family Code mostly):
                is_redundant = False
                if code_id and code_id.lower() == 'fc':
                    # FC articles do not have individual titles. The db article_title column stores the overarching group ("Marriage")
                    # which is incredibly annoying to hear at the start of every single article.
                    is_redundant = True
                elif art_title and len(art_title) > 3:
                    if group_header and art_title.lower() in group_header.lower():
                        is_redundant = True
                    elif clean.lower().startswith(art_title.lower()):
                        is_redundant = True
                
                # Format Header - only strip dash prefix for FC-style articles (FC-I-36), NOT RPC (266-A)
                clean_num = art_num
                if '-' in art_num and not art_num[0].isdigit() and (code_id and code_id.lower() not in ['rpc']):
                    clean_num = art_num.split('-')[-1]
                
                if code_id and code_id.lower() == 'const':
                    # Use article_num (DB value) for routing logic
                    art_num_db = str(art_num).strip()
                    s_label = (row.get('section_label') or '').strip().rstrip('.')

                    if "PREAMBLE" in art_num_db.upper() or "PREAMBLE" in s_label.upper():
                        # Preamble row: prepend Codal name
                        header = "1987 Constitution of the Republic of the Philippines. Preamble"

                    else:
                        # Section row: article_num like 'I-0', 'II-1', 'IX-A-1', 'XVIII-5'
                        parts = art_num_db.split('-')
                        sect_num = parts[-1]  # Always the last segment (e.g. '0', '1', '5')

                        # Build article identifier
                        if len(parts) == 3 and not parts[1].isdigit():
                            # e.g. IX-A-1 → sub-article "IX-A"
                            art_roman = f"{parts[0]}-{parts[1]}"
                        else:
                            art_roman = parts[0]  # e.g. 'I', 'II', 'XVIII'

                        # Handle special Article I (has body but no sections, encoded as I-0)
                        if sect_num == '0':
                            art_label = f"Article {art_roman}"
                            if art_title and not is_redundant:
                                art_label += f'. {art_title}'
                            header = art_label
                        else:
                            # Integrated Boundary Detection (Handles sub-headers like "Principles", "State Policies")
                            group_val = row.get('group_header')
                            section_id = row.get('id')
                            
                            # Use boundary map to determine if we should announce a header update
                            boundaries = get_codal_boundaries(table)
                            is_group_start = False
                            if group_val and boundaries and 'group_header' in boundaries:
                                g_lower = group_val.lower()
                                if g_lower in boundaries['group_header'] and str(boundaries['group_header'][g_lower]) == str(section_id):
                                    is_group_start = True

                            if is_group_start:
                                # Prepend the group header naturally
                                # For Section 1, also include Article name
                                if sect_num == '1':
                                    art_label = f"Article {art_roman}"
                                    if art_title and not is_redundant:
                                        art_label += f'. {art_title}'
                                    header = f"{art_label}. {group_val}. Section 1"
                                else:
                                    header = f"{group_val}. Section {sect_num}"
                            elif sect_num == '1':
                                # Standard Section 1 (no mid-section group header)
                                art_label = f"Article {art_roman}"
                                if art_title and not is_redundant:
                                    art_label += f'. {art_title}'
                                header = f"{art_label}. Section 1"
                            else:
                                # Normal section
                                header = f"Section {sect_num}"

                        # FIX: Strip leading "SECTION N." from clean to avoid double-mention
                        # e.g. header="...Section 1" and clean starts with "SECTION 1, The Philippines..."
                        import re as _re
                        clean = _re.sub(r'^SECTION\s+\d+[\.,]?\s*', '', clean, flags=_re.IGNORECASE).strip()
                else:
                    if code_id and code_id.lower() == 'roc':
                        # ROC: art_num looks like "Rule 2, Section 1" or "Rule 2, Section 8"
                        roc_rule_m = re.search(r'(Rule\s+\d+)', str(clean_num), re.IGNORECASE)
                        roc_sect_m = re.search(r'Section\s+(\d+)', str(clean_num), re.IGNORECASE)
                        rule_label = roc_rule_m.group(1) if roc_rule_m else str(clean_num)
                        sect_num_roc = roc_sect_m.group(1) if roc_sect_m else '1'
                        
                        rule_num_int = 0
                        if roc_rule_m:
                            try:
                                rule_num_int = int(re.search(r'\d+', rule_label).group())
                            except:
                                pass

                        hdr_parts = []
                        starts = get_codal_boundaries('roc_codal')
                        curr_id = row.get('id')
                        
                        # 0. Codal Title & Part - Only on first rule of a Part (always sect 1)
                        if sect_num_roc == '1' and rule_num_int in [1, 72, 110, 128]:
                            hdr_parts.append("Rules of Court of the Philippines")
                            p_num = row.get('part_num')
                            p_title = (row.get('part_title') or '').title()
                            if p_num and p_title:
                                hdr_parts.append(f"Part {p_num}. {p_title}")
                        
                        # 1. Group 1 Title
                        g1 = (row.get('group_1_title') or '').strip()
                        if g1 and starts['g1'].get(g1.lower()) == str(curr_id):
                            hdr_parts.append(g1.title())
                        
                        # 2. Group 2 Title
                        g2 = (row.get('group_2_title') or '').strip()
                        if g2 and starts['g2'].get(g2.lower()) == str(curr_id):
                            hdr_parts.append(g2.title())

                        if sect_num_roc == '1':
                            # 3. Rule Number
                            hdr_parts.append(rule_label)
                            
                            # 4. Rule Title
                            g_hdr = (row.get('group_header') or '').strip()
                            if g_hdr:
                                # Strip artifact 'RULE N' prefix if somehow still present
                                clean_g_hdr = re.sub(r'^RULE\s+\d+\s+', '', g_hdr, flags=re.IGNORECASE).strip()
                                if clean_g_hdr: hdr_parts.append(clean_g_hdr.title())
                            
                            roc_hdr = '. '.join(hdr_parts)
                            header = f"{roc_hdr}. Section 1"
                        else:
                            if hdr_parts:
                                header = f"{'. '.join(hdr_parts)}. Section {sect_num_roc}"
                            else:
                                header = f"Section {sect_num_roc}"
                            
                        if art_title and not is_redundant:
                            header += f". {art_title}"
                    elif table in ['rpc_codal', 'civ_codal', 'labor_codal']:
                        hdr_parts = []
                        starts = get_codal_boundaries(table)
                        curr_id = row.get('id')
                        
                        b_lbl = (row.get('book_label') or '').strip()
                        if b_lbl and starts['book_label'].get(b_lbl.lower()) == curr_id:
                            hdr_parts.append(b_lbl.title())
                            
                        t_lbl = (row.get('title_label') or '').strip()
                        if t_lbl and starts['title_label'].get(t_lbl.lower()) == curr_id:
                            hdr_parts.append(t_lbl.title())
                            
                        c_lbl = (row.get('chapter_label') or '').strip()
                        if c_lbl and starts['chapter_label'].get(c_lbl.lower()) == curr_id:
                            hdr_parts.append(c_lbl.title())
                            
                        art_name = 'Preliminary Article' if clean_num == '0' else f'Article {clean_num}'
                        if art_title and not is_redundant:
                            art_name += f'. {art_title}'
                            
                        hdr_parts.append(art_name)
                        header = '. '.join(hdr_parts)
                        
                    elif table == 'fc_codal':
                        hdr_parts = []
                        starts = get_codal_boundaries('fc_codal')
                        curr_id = row.get('id')
                        
                        g_hdr = (row.get('group_header') or '').strip()
                        if g_hdr and starts['group_header'].get(g_hdr.lower()) == curr_id:
                            hdr_parts.append(g_hdr.title())
                            
                        art_name = str(clean_num) if re.match(r'^(article|preamble|section|rule)\b', str(clean_num), re.IGNORECASE) else f'Article {clean_num}'
                        if art_title and not is_redundant:
                            art_name += f'. {art_title}'
                            
                        hdr_parts.append(art_name)
                        header = '. '.join(hdr_parts)
                        
                    elif re.match(r'^(article|preamble|section|rule)\b', str(clean_num), re.IGNORECASE):
                        header = str(clean_num)
                        if art_title and not is_redundant: 
                            header += f'. {art_title}'
                    else:
                        header = 'Preliminary Article' if clean_num == '0' else f'Article {clean_num}'
                        if art_title and not is_redundant: 
                            header += f'. {art_title}'
                    
                # Deduplicate: if the stored content body already BEGINS with the article header, skip the prefix
                # This handles cases like 266-A where content starts with "Article 266-A. Rape..."
                header_bare = f'article {clean_num}'.lower()
                clean_header = (header or '').lower().rstrip('.')
                if header and (clean.lower().startswith(header_bare) or clean.lower().startswith(clean_header)):
                    header = ""
                full_text = f"{header}. {clean}" if header else clean
                full_text = _apply_custom_pronunciations(full_text)
                return full_text, None

        # ---- Strategy B: UUID lookup in article_versions ----
        try:
            cur.execute(
                "SELECT article_number, content FROM article_versions WHERE version_id::text = %s",
                (str(content_id),)
            )
            row = cur.fetchone()
        except Exception:
            conn.rollback()
            row = None

        if not row:
            return None, f"Codal article '{content_id}' not found for code '{code_id}'"
        
        art_num = row.get('article_number', '')
        content = row.get('content', '') or ''
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        # TTS Cleaning: Remove structural MD, soften colons/semicolons
        clean = re.sub(r'[#*`_\[\]]', ' ', str(content))
        clean = re.sub(r'[:;]', ',', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()

        # Strip literal backslash-escape text stored in DB content
        # e.g. DB stores \(1\) as Markdown-escaped parens — TTS reads \ as "backslash"
        clean = re.sub(r'\\[nrtfvb]', ' ', clean)  # literal \n \r \t as text
        clean = clean.replace('\\', ' ')           # any remaining lone backslash
        clean = re.sub(r'\s+', ' ', clean).strip() # re-collapse

        # Convert enumerated item labels \(1\) / (1) to "1," for natural TTS speech
        clean = re.sub(r'\(\s*(\d+)\s*\)', r'\1,', clean)

        # Strip currency repetitions like (₱40,000) or (P200,000)
        clean = re.sub(r'\(\s*[₱P]\s*[\d,.]+\s*\)', '', clean)
        
        # Strip legal citation/version tags ANYWHERE in text (n), (1a), (6a), (1a, R2)
        clean = re.sub(
            r'\s*\(\s*(?:(?:\d+[a-zA-Z]?|n|[A-Z]\d+)(?:\s*,\s*(?:\d+[a-zA-Z]?|n|[A-Z]\d+))*)\s*\)',
            ' ', clean
        )
        clean = re.sub(r'\s+', ' ', clean).strip()

        header = 'Preliminary Article' if str(art_num) == '0' else f'Article {art_num}'
        full_text = f"{header}. {clean}" if header else clean
        full_text = _apply_custom_pronunciations(full_text)
        return full_text, None
    finally:
        put_db_connection(conn)

def _get_text_for_question(content_id):
    """
    Fetch Bar Question and Answer for TTS.
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT q.year, q.subject, q.text, (SELECT text FROM answers a WHERE a.question_id = q.id LIMIT 1) as answer 
            FROM questions q WHERE q.id = %s
        """, (content_id,))
        row = cur.fetchone()
        if not row:
            return None, "Bar Question not found"

        year = row.get('year')
        subject = row.get('subject')
        q_text = (row.get('text') or "").replace('\r\n', '\n').replace('\r', '\n')
        a_text = (row.get('answer') or "").replace('\r\n', '\n').replace('\r', '\n')

        # Format Intro (Restored Year and BAR to intro only)
        intro = f"{year} BAR Question in {subject}."
        
        # Clean Question/Answer markers
        # Replace Q: with Question: and A: with Answer: (case-insensitive, at start of lines or words)
        q_clean = re.sub(r'(?i)^Q[:\.]\s*', 'Question: ', q_text.strip())
        a_clean = re.sub(r'(?i)^A[:\.]\s*', 'Answer: ', a_text.strip())
        
        # Strip year info immediately after marker: e.g. "Question: (2023 BAR)" or "Question: 2023"
        # Handles cases like (2023 BAR), 2023 BAR, (2023), 2023
        # Including a possible trailing period after the year/BAR info
        q_clean = re.sub(r'^(Question:\s*)\(?20[0-9]{2}(\s*BAR)?\)?[\s.]*', r'\1', q_clean)
        a_clean = re.sub(r'^(Answer:\s*)\(?20[0-9]{2}(\s*BAR)?\)?[\s.]*', r'\1', a_clean)
        
        # Globally strip the word "BAR" (case-insensitive)
        q_clean = re.sub(r'(?i)\bBAR\b', '', q_clean)
        a_clean = re.sub(r'(?i)\bBAR\b', '', a_clean)
        
        # Join
        if not a_clean.lower().startswith("answer:"):
            a_clean = f"Suggested Answer: {a_clean}"
            
        full_text = f"{intro} {q_clean} {a_clean}"
        
        # Basic cleanup
        full_text = re.sub(r'[#*`_\[\]]', ' ', full_text)
        full_text = re.sub(r'[:;]', ',', full_text)
        full_text = re.sub(r'\s+', ' ', full_text).strip()
        
        # Apply custom pronunciations (Latin, Names, etc.)
        full_text = _apply_custom_pronunciations(full_text)
        
        return full_text, None
    finally:
        put_db_connection(conn)

def _strip_ssml_tokens(text):
    """Remove internal SSML placeholder tokens that are only meaningful for Azure TTS.
    If passed to gTTS they get read aloud literally as underscores."""
    text = text.replace("__ES_START__", "").replace("__ES_END__", "")
    text = text.replace("__PH_START__", "").replace("__PH_END__", "")
    text = text.replace("__LATIN_START__", "").replace("__LATIN_END__", "")
    # Clean up any double spaces left behind
    text = re.sub(r'  +', ' ', text)
    return text.strip()

# ----- Audio generation -----
def _generate_audio_edge_tts(text, voice="en-US-JennyNeural", rate=1.0):
    """Generate MP3 audio bytes using edge-tts (free, needs internet).
    Supports multi-chunk concatenation.
    """
    import subprocess
    import tempfile
    import os
    
    # Strip SSML tokens that are only for Azure APIs
    text = _strip_ssml_tokens(text)
    
    # Scale the playback speed down by default (1.0x LexPlayer speed = 90% Jenny speed)
    adjusted_rate = rate * 0.9
    
    # Format the rate string for edge-tts (e.g., +20%, -10%, +0%)
    # Edge-TTS expects percentage offsets relative to its own baseline 100%
    rate_str = "+0%" if adjusted_rate == 1.0 else f"{int((adjusted_rate - 1.0) * 100)}%"
    if int((adjusted_rate - 1.0) * 100) > 0 and not rate_str.startswith('+'):
        rate_str = "+" + rate_str
    
    # Use 2000 as safe chunk size to avoid any CLI max argument limits
    chunks = _chunk_text(text, max_len=2000)
    if not chunks:
        raise ValueError("No text provided for edge-tts")
        
    # Concatenate MP3 bytes using the native Python API (reliable in Cloud)
    import asyncio
    import edge_tts

    async def _amain():
        _all_data = []
        for chunk in chunks:
            communicate = edge_tts.Communicate(chunk, voice, rate=rate_str)
            # Use a memory/temp pipe or write to temp then read
            fd, temp_path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
            try:
                await communicate.save(temp_path)
                with open(temp_path, 'rb') as f:
                    _all_data.append(f.read())
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        return b"".join(_all_data)

    try:
        # Run the async loop inside the sync function
        combined_data = asyncio.run(_amain())
    except Exception as e:
        logging.error(f"Edge-TTS Python API failed: {e}")
        raise RuntimeError(f"Fallback audio engine failed: {str(e)}")
        
    return combined_data, 'audio/mpeg', '.mp3'

def _generate_audio_azure(text, voice_name="en-PH-RosaNeural", rate=1.0):
    """Generate MP3 audio using Azure Speech REST API (HTTP POST, not WebSocket SDK).
    The REST API avoids WebSocket connection rate limiting issues on the F0 tier.
    Supports multi-chunk concatenation to bypass SSML size limits.
    """
    import requests as _requests

    speech_key = os.environ.get("SPEECH_KEY", "")
    speech_region = os.environ.get("SPEECH_REGION", "japaneast")
    if not speech_key or "<insert" in speech_key:
        raise ValueError("Azure Speech key not configured")

    tts_url = f"https://{speech_region}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": speech_key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
    }

    # Use en-PH for James/Rosa, or fil-PH for Blessica/Angelo
    lang_code = "en-PH" if "James" in voice_name or "Rosa" in voice_name else "en-US"
    if "Blessica" in voice_name or "Angelo" in voice_name:
        lang_code = "fil-PH"

    # Clamp rate to a safe range (Azure supports 0.5x - 2.0x natively)
    rate = max(0.5, min(2.0, float(rate)))
    rate_str = f"{rate}"

    # Chunk text to stay under SSML limits
    chunks = _chunk_text(text, max_len=3000)
    if not chunks:
        raise ValueError("No text provided for Azure TTS")

    all_audio_data = []
    for chunk in chunks:
        # Escape special XML characters for SSML
        escaped_text = chunk.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # Hydrate the Multilingual SSML tokens
        escaped_text = escaped_text.replace("__ES_START__", "<lang xml:lang='es-MX'>")
        escaped_text = escaped_text.replace("__ES_END__", "</lang>")
        escaped_text = escaped_text.replace("__PH_START__", "<lang xml:lang='fil-PH'>")
        escaped_text = escaped_text.replace("__PH_END__", "</lang>")
        escaped_text = escaped_text.replace("__LATIN_START__", "<lang xml:lang='it-IT'>")
        escaped_text = escaped_text.replace("__LATIN_END__", "</lang>")

        # mstts namespace required for multilingual language switching
        ssml = (
            f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis'"
            f" xmlns:mstts='http://www.w3.org/2001/mstts' xml:lang='{lang_code}'>"
            f"<voice name='{voice_name}'>"
            f"<prosody rate='{rate_str}'>{escaped_text.strip()}</prosody>"
            f"</voice></speak>"
        )

        resp = _requests.post(tts_url, headers=headers, data=ssml.encode("utf-8"), timeout=30)
        if resp.status_code == 200:
            all_audio_data.append(resp.content)
        else:
            raise RuntimeError(
                f"Azure TTS REST API failed: HTTP {resp.status_code} | {resp.text[:200]}"
            )

    combined_data = b"".join(all_audio_data)
    return combined_data, 'audio/mpeg', '.mp3'


# ----- Main endpoint: streams audio directly -----
@audio_provider_bp.route(route="audio/{content_type}/{content_id}", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def get_audio_stream(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Audio request received.')

    content_type = req.route_params.get('content_type')
    content_id = req.route_params.get('content_id')
    code_id = req.params.get('code')  # e.g. 'rpc', 'civ', 'labor'

    # Read playback rate - default to 1.0 if not provided or invalid
    try:
        rate = float(req.params.get('rate', '1.0'))
        rate = max(0.5, min(2.0, rate))  # Clamp to safe range
    except (ValueError, TypeError):
        rate = 1.0

    if content_type not in ['codal', 'case', 'question']:
        return func.HttpResponse(
            json.dumps({"error": "Invalid content type. Use 'codal', 'case', or 'question'."}),
            status_code=400, mimetype="application/json"
        )

    # --- 1. Select Voice based on Content Type ---
    # Globalized JennyMultilingual for natively fluent Spanish parsing
    voice_name = "en-US-JennyMultilingualNeural"

    # --- 1b. Check blob cache first ---
    # Smart format the content_id to include 'article' if it's purely a number for codals
    formatted_id = content_id
    if content_type == 'codal':
        # Default to prepending 'article' if it's a pure number or doesn't have an explict prefix
        if not formatted_id.lower().startswith(('art', 'sec', 'rule', 'preamble')):
            formatted_id = f"article{formatted_id}"
            
    # Include voice name, rate, and cache version in key to ensure fresh/correct audio
    voice_slug = voice_name.split('-')[-1].replace('Neural', '').lower()
    rate_slug = str(rate).replace('.', 'p')  # e.g. 0.8 -> "0p8"
    cache_key = f"{content_type}_{code_id or ''}_{formatted_id}_{voice_slug}_r{rate_slug}_{CACHE_VERSION}"
    
    cache_status = "MISS"
    for ext in ['.mp3', '.wav']:
        cached_url = _get_from_cache(f"{cache_key}{ext}")
        if cached_url:
            logging.info(f"CACHE HIT: Redirecting to {cached_url[:60]}...")
            return func.HttpResponse(
                status_code=302,
                headers={
                    "Location": cached_url,
                    "X-Cache-Status": "HIT",
                    "X-Cache-Version": CACHE_VERSION
                }
            )

    # --- 2. Fetch text from DB ---
    text = None
    err = None
    try:
        if content_type == 'case':
            text, err = _get_text_for_case(content_id)
        elif content_type == 'question':
            text, err = _get_text_for_question(content_id)
        else:
            text, err = _get_text_for_codal(content_id, code_id=code_id)
    except Exception as e:
        logging.error(f"DB error: {e}")
        return func.HttpResponse(f"Database error: {e}", status_code=500)

    if err:
        return func.HttpResponse(err, status_code=404)
    if not text or not text.strip():
        return func.HttpResponse("No text content to synthesize", status_code=404)

    # --- 3. Generate audio via Azure Speech (Preferred) with retry on 429 ---
    # Acquire global TTS lock to prevent concurrent synthesis on F0 (1 concurrent session limit)
    audio_data, mime_type, ext = None, None, None
    tts_engine = "unknown"
    try:
        if AZURE_SPEECH_AVAILABLE:
            azure_success = False
            last_azure_error = None
            max_retries = 3

            lock_acquired = _TTS_LOCK.acquire(timeout=_TTS_LOCK_TIMEOUT)
            if not lock_acquired:
                logging.warning("TTS lock timeout — another synthesis is running too long. Falling back to edge_tts.")
                audio_data, mime_type, ext = _generate_audio_edge_tts(text, rate=rate)
                tts_engine = "edge_tts"
            else:
                try:
                    for attempt in range(1, max_retries + 1):
                        try:
                            audio_data, mime_type, ext = _generate_audio_azure(text, voice_name=voice_name, rate=rate)
                            logging.info(f"Audio generated via Azure TTS ({voice_name}) at rate={rate} (attempt {attempt})")
                            tts_engine = "azure"
                            azure_success = True
                            break
                        except Exception as e:
                            last_azure_error = e
                            err_str = str(e).lower()
                            is_throttle = "429" in err_str or "too many" in err_str or "toomany" in err_str
                            if is_throttle and attempt < max_retries:
                                wait_sec = 2 ** attempt  # 2s, 4s
                                logging.warning(f"Azure TTS throttled (429), retry {attempt}/{max_retries} in {wait_sec}s")
                                time.sleep(wait_sec)
                            else:
                                logging.warning(f"Azure TTS failed after {attempt} attempt(s): {e}")
                                break
                    if not azure_success:
                        logging.warning(f"Azure TTS unavailable, falling back to edge_tts. Last error: {last_azure_error}")
                        audio_data, mime_type, ext = _generate_audio_edge_tts(text, rate=rate)
                        tts_engine = "edge_tts"
                finally:
                    _TTS_LOCK.release()
        else:
            logging.warning("Azure Speech SDK not available, falling back to edge_tts")
            audio_data, mime_type, ext = _generate_audio_edge_tts(text, rate=rate)
            tts_engine = "edge_tts"
    except Exception as e:
        logging.error(f"TTS generation failed entirely: {e}")
        return func.HttpResponse(f"Audio generation failed: {e}", status_code=500)

    # --- 4. Upload to Azure Blob and Redirect ---
    # Use a separate cache key suffix for TTS engines so they can be explicitly identified
    effective_cache_key = f"{cache_key}_{tts_engine}"
    blob_name = f"{effective_cache_key}{ext}"
    _save_to_cache(blob_name, audio_data, mime_type=mime_type)
    sas_url = _get_from_cache(blob_name)
    if sas_url:
        logging.info(f"Uploaded to Azure Blob ({tts_engine}), Redirecting to SAS URL")
        return func.HttpResponse(
            status_code=302,
            headers={
                "Location": sas_url,
                "X-TTS-Engine": tts_engine,
            }
        )

    # --- 5. Fallback: stream audio directly if blob upload failed ---
    if not audio_data:
        return func.HttpResponse("Audio generation produced no data", status_code=500)
    logging.info(f"Blob upload failed, streaming {len(audio_data)} bytes directly ({tts_engine})")
    return func.HttpResponse(
        body=audio_data,
        status_code=200,
        mimetype=mime_type,
        headers={
            "Content-Length": str(len(audio_data)),
            "Accept-Ranges": "bytes",
            "X-TTS-Engine": tts_engine,
        }
    )
