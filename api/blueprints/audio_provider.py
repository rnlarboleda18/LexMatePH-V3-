import logging
import os
import io
import re
import json
import time
import threading
import uuid
from datetime import datetime, timedelta

# Removed local file logging as it causes permission errors in production
import azure.functions as func

# Database connection
from psycopg2.extras import RealDictCursor
from db_pool import get_db_connection, put_db_connection
from codal_text import (
    _ROMAN_TO_ARABIC,
    body_embeds_rpc_section,
    body_starts_with_article_identifier,
    dedupe_codal_header_prefix,
    fix_rcc_structural_heading_glue,
    rcc_section_number_from_article_num,
    raw_markdown_opens_with_article_line,
    repair_rpc_article_266_for_tts,
    strip_codal_citation_tail,
    tts_book_heading_line,
    tts_flatten_codal_body,
    tts_format_structural_label,
    tts_strip_leading_embedded_section,
    tts_strip_leading_embedded_title,
    tts_strip_rcc_spurious_book_from_flat,
    tts_strip_rcc_spurious_book_markdown,
)
from codal_structural import fetch_codal_family_bounds, normalize_codal_label_key

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
CACHE_VERSION = "v27"  # v27: RCC "Section N." in spoken header; v26: TTS "one (1)" collapse; RCC lead/UI parity

# Global lock: Azure Speech F0 allows only 1 concurrent real-time synthesis.
# This prevents 429 errors when multiple requests overlap (e.g. fast track skipping).
_TTS_LOCK = threading.Lock()
_TTS_LOCK_TIMEOUT = 30  # seconds to wait before giving up and using gTTS

# Default: Edge TTS. Set LEXPLAY_USE_AZURE_SPEECH=true for Azure Speech only (no Edge fallback if Azure fails).
_USE_AZURE_SPEECH = os.environ.get("LEXPLAY_USE_AZURE_SPEECH", "").lower() in ("1", "true", "yes")

# Reuse one BlobServiceClient + container client per instance (fewer storage API calls).
_BLOB_INIT_LOCK = threading.Lock()
_BLOB_SERVICE_CLIENT = None
_BLOB_CONTAINER_NAME = "lexplay-audio-cache"
_CONTAINER_READY = False

# Browser/CDN caching for immutable audio at a stable URL (30d; bump CACHE_VERSION to refresh).
_AUDIO_CACHE_CONTROL = "public, max-age=2592000, stale-while-revalidate=86400"


def _audio_http_headers(
    body_len,
    cache_status,
    *,
    tts_engine=None,
    blob_name=None,
):
    h = {
        "Content-Length": str(body_len),
        "Accept-Ranges": "bytes",
        "Cache-Control": _AUDIO_CACHE_CONTROL,
        "X-Cache-Status": cache_status,
        "X-Cache-Version": CACHE_VERSION,
    }
    if tts_engine:
        h["X-TTS-Engine"] = tts_engine
    if blob_name:
        h["ETag"] = f'W/"{CACHE_VERSION}-{blob_name}"'
    return h

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

    # 8. Legal statute abbreviations (spell out so TTS doesn't read letters)
    text = re.sub(r'\bR\.A\.\s*(?=\d)', 'Republic Act ', text)
    text = re.sub(r'\bP\.D\.\s*(?=\d)', 'Presidential Decree ', text)
    text = re.sub(r'\bB\.P\.\s*(?=\d)', 'Batas Pambansa ', text)
    text = re.sub(r'\bE\.O\.\s*(?=\d)', 'Executive Order ', text)
    text = re.sub(r'\bR\.R\.\s*(?=\d)', 'Revenue Regulation ', text)

    # 9. Structural abbreviations
    text = re.sub(r'\b[Ss]ecs?\.\s*(?=\d)', lambda m: 'Sections ' if m.group(0).lower().startswith('secs') else 'Section ', text)
    text = re.sub(r'\b[Pp]ars?\.\s*(?=\d)', lambda m: 'paragraphs ' if m.group(0).lower().startswith('pars') else 'paragraph ', text)
    text = re.sub(r'\b[Cc]h\.\s*(?=\d)', 'Chapter ', text)

    # 10. Common Latin/English abbreviations that TTS spells out
    text = re.sub(r'\bi\.e\.', 'that is,', text)
    text = re.sub(r'\be\.g\.', 'for example,', text)
    text = re.sub(r'\bet al\.', 'and others', text)
    text = re.sub(r'\b[Vv]s\.(?=\s)', ' versus ', text)

    return text

# ----- Blob Cache (best-effort, degrades silently) -----
def _get_blob_client(blob_name):
    """Return a BlobClient for blob_name; reuse account/container clients per process."""
    global _BLOB_SERVICE_CLIENT, _CONTAINER_READY
    try:
        conn_str = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "UseDevelopmentStorage=true")
        if conn_str == "UseDevelopmentStorage=true":
            logging.warning("AZURE_STORAGE_CONNECTION_STRING not configured, blob cache disabled.")
            return None
        with _BLOB_INIT_LOCK:
            if _BLOB_SERVICE_CLIENT is None:
                _BLOB_SERVICE_CLIENT = BlobServiceClient.from_connection_string(
                    conn_str,
                    connection_timeout=15,
                    read_timeout=30,
                    retry_total=2,
                )
            container = _BLOB_SERVICE_CLIENT.get_container_client(_BLOB_CONTAINER_NAME)
            if not _CONTAINER_READY:
                try:
                    if not container.exists():
                        container.create_container()
                    _CONTAINER_READY = True
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

def _get_data_from_cache(blob_name):
    """Fetch raw blob data from Azure Storage (Proxy Mode)."""
    client = _get_blob_client(blob_name)
    if not client:
        return None
    try:
        if client.exists():
            logging.info(f"CACHE HIT (PROXY): {blob_name}")
            return client.download_blob().readall()
    except Exception as e:
        logging.warning(f"Cache download error: {e}")
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
        cached = _codal_boundaries[table_name]
        # Self-heal: drop stale entries when structural maps gain new keys (e.g. chapter_start / section_start).
        if table_name in ('rpc_codal', 'civ_codal', 'rcc_codal', 'labor_codal'):
            stale = (
                'title_start_book_num' not in cached
                or 'chapter_start' not in cached
                or 'section_start' not in cached
            )
            if stale:
                with _codal_boundaries_lock:
                    _codal_boundaries.pop(table_name, None)
            else:
                return cached
        elif table_name == 'fc_codal':
            if 'section_label' not in cached:
                with _codal_boundaries_lock:
                    _codal_boundaries.pop(table_name, None)
            else:
                return cached
        else:
            return cached
        
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
                        bounds = {'group_header': {}, 'section_label': {}}
                        if table_name == 'fc_codal':
                            # Family Code: use list_order for correct reading order.
                            from codal_structural import _LABEL_KEY_SQL
                            # Title boundaries (group_header)
                            key_expr = _LABEL_KEY_SQL.format(col='group_header')
                            cur.execute(f"""
                                WITH ranked AS (
                                    SELECT id, {key_expr} AS lk,
                                        ROW_NUMBER() OVER (
                                            PARTITION BY {key_expr}
                                            ORDER BY list_order ASC NULLS LAST
                                        ) AS rn
                                    FROM fc_codal
                                    WHERE group_header IS NOT NULL AND TRIM(group_header) <> ''
                                )
                                SELECT lk, id FROM ranked WHERE rn = 1
                            """)
                            for r in cur.fetchall():
                                bounds['group_header'][r[0]] = str(r[1])
                            # Chapter boundaries (section_label)
                            sec_key_expr = _LABEL_KEY_SQL.format(col='section_label')
                            cur.execute(f"""
                                WITH ranked AS (
                                    SELECT id, {sec_key_expr} AS lk,
                                        ROW_NUMBER() OVER (
                                            PARTITION BY {sec_key_expr}
                                            ORDER BY list_order ASC NULLS LAST
                                        ) AS rn
                                    FROM fc_codal
                                    WHERE section_label IS NOT NULL AND TRIM(section_label) <> ''
                                )
                                SELECT lk, id FROM ranked WHERE rn = 1
                            """)
                            for r in cur.fetchall():
                                bounds['section_label'][r[0]] = str(r[1])
                        else:
                            cur.execute(f"SELECT LOWER(group_header), MIN(id) FROM {table_name} WHERE group_header IS NOT NULL AND group_header != '' GROUP BY LOWER(group_header)")
                            for r in cur.fetchall(): bounds['group_header'][r[0]] = r[1]
                        
                    elif table_name in ['rpc_codal', 'civ_codal', 'rcc_codal', 'labor_codal']:
                        bounds = fetch_codal_family_bounds(cur, table_name)
                            
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


def _looks_like_uuid(s: str) -> bool:
    try:
        uuid.UUID(str(s).strip())
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def _rpc_normalize_article_token(s: str) -> str:
    t = (s or "").strip()
    t = re.sub(r"[\u2010-\u2015\u2212]", "-", t)
    m = re.match(r"(?i)^(?:article|art\.)\s+(.+)$", t)
    if m:
        t = m.group(1).strip()
    return t


def _rpc_article_num_regex_pattern(cid_str: str):
    """
    PostgreSQL ~* pattern: match rpc_codal.article_num for exactly one provision.
    e.g. '266' matches '266' and 'Article 266' but not '266-A' (which would otherwise
    match a loose 'Art% 266%' LIKE and return the wrong row).
    """
    t = (cid_str or "").strip()
    if not t:
        return None
    m = re.match(r"(?i)^article\s+(.+)$", t)
    if m:
        t = m.group(1).strip()
    if not re.fullmatch(r"\d+(?:-[A-Za-z]+)?", t):
        return None
    esc = re.escape(t)
    return rf"^([Aa]rticle[[:space:]]+|[Aa]rt\.[[:space:]]*)?{esc}[[:space:]]*$"


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
        'rcc': 'rcc_codal',
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
            elif table in ["rpc_codal", "civ_codal", "rcc_codal", "labor_codal"]:
                # labor_codal has no section_label column; civ_codal / rcc_codal and rpc_codal do.
                # civ_codal / labor_codal store plain chapter descriptions; chapter_num needed.
                # rpc_codal embeds "CHAPTER ONE -" in chapter_label directly.
                if table == "labor_codal":
                    cols = (
                        "id, book, book_label, title_num, title_label, "
                        "chapter_num, chapter_label, "
                        "article_num, article_title, content_md"
                    )
                elif table in ("civ_codal", "rcc_codal"):
                    cols = (
                        "id, book, book_label, title_num, title_label, "
                        "chapter_num, chapter_label, section_label, "
                        "article_num, article_title, content_md"
                    )
                else:  # rpc_codal
                    cols = (
                        "id, book, book_label, title_num, title_label, "
                        "chapter_label, section_label, "
                        "article_num, article_title, content_md"
                    )
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
                # Loose LIKE 'Art% 266%' matches 266-A; only use when regex cannot apply
                if not cid_str.lower().startswith("art") and _rpc_article_num_regex_pattern(cid_str) is None:
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

            if not row and table == 'rpc_codal':
                rpc_pat = _rpc_article_num_regex_pattern(cid_str)
                if rpc_pat:
                    try:
                        cur.execute(
                            f"SELECT {cols} FROM {table} WHERE article_num ~* %s{extra_filter} LIMIT 1",
                            (rpc_pat,),
                        )
                        row = cur.fetchone()
                    except Exception:
                        conn.rollback()

            # If we matched a row but article_num does not match requested token (e.g. wrong row),
            # replace with a strict regex row — only for non-UUID content_id.
            if (
                row
                and table == "rpc_codal"
                and code_id
                and code_id.lower() == "rpc"
                and not _looks_like_uuid(str(content_id))
            ):
                want = _rpc_normalize_article_token(str(content_id))
                got = _rpc_normalize_article_token(str(row.get("article_num") or ""))
                if (
                    want
                    and got
                    and re.fullmatch(r"\d+(?:-[A-Za-z]+)?", want, re.I)
                    and want.lower() != got.lower()
                ):
                    pat = _rpc_article_num_regex_pattern(want)
                    if pat:
                        try:
                            cur.execute(
                                f"SELECT {cols} FROM {table} WHERE article_num ~* %s{extra_filter} LIMIT 1",
                                (pat,),
                            )
                            row2 = cur.fetchone()
                            if row2:
                                row = row2
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
                art_title = strip_codal_citation_tail((row.get('article_title') or '').strip())
                group_header = (row.get('group_header') or '').strip()
                content = (row.get('content_md') or '').strip()
                content = content.replace('\r\n', '\n').replace('\r', '\n')
                if table == 'rpc_codal':
                    content = repair_rpc_article_266_for_tts(art_num, content)
                if table in ('rpc_codal', 'civ_codal', 'rcc_codal', 'labor_codal'):
                    content = tts_strip_leading_embedded_section(
                        content,
                        row.get("section_label"),
                        art_num,
                    )
                    content = tts_strip_leading_embedded_title(
                        content, row.get("title_label")
                    )
                    if table == "rcc_codal":
                        content = tts_strip_rcc_spurious_book_markdown(content)

                clean = tts_flatten_codal_body(content)
                if table == "rcc_codal":
                    clean = tts_strip_rcc_spurious_book_from_flat(clean)
                
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

                        # Build article identifier - always top-level Roman numeral only.
                        # Sub-chapter letters (A/B/C/D in Art. IX) are announced via
                        # group_header; including them in art_roman causes the letter
                        # to be spoken twice ("Article IX-A … A. Common Provisions").
                        art_roman = parts[0]  # e.g. 'IX' for IX-A-1, 'II' for II-5

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

                            # Is this a sub-chapter article? (e.g. IX-A-1 has 3 parts, middle is a letter)
                            is_sub_chapter = len(parts) == 3 and not parts[1].isdigit()
                            # Include the article name only for the very first sub-chapter (A)
                            # or for plain articles (no sub-chapter letter). B/C/D sub-chapters
                            # only announce their group header — the article was already introduced by A.
                            include_art_name = not is_sub_chapter or parts[1] == 'A'

                            if is_group_start:
                                if sect_num == '1' and include_art_name:
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
                    elif table in ['rpc_codal', 'civ_codal', 'rcc_codal', 'labor_codal']:
                        # Structural lines only on the first article in *codal order* where each
                        # division starts (not MIN(uuid), which does not follow article sequence).
                        hdr_parts = []
                        starts = get_codal_boundaries(table)
                        curr_id_str = str(row.get('id')) if row.get('id') is not None else ''
                        is_rcc_table = table == 'rcc_codal'

                        bk = row.get('book')
                        # RCC (RA 11232) has no Books; legacy book_num=1 must not be spoken.
                        if not is_rcc_table and bk is not None:
                            bstart = starts.get('book_start', {}).get(str(bk).strip())
                            if bstart and bstart == curr_id_str:
                                book_line = tts_book_heading_line(dict(row))
                                if book_line:
                                    hdr_parts.append(book_line)

                        t_lbl = (row.get('title_label') or '').strip()
                        c_lbl = (row.get('chapter_label') or '').strip()
                        s_lbl = (row.get('section_label') or '').strip()
                        if is_rcc_table:
                            t_lbl = fix_rcc_structural_heading_glue(t_lbl)
                            c_lbl = fix_rcc_structural_heading_glue(c_lbl)
                            s_lbl = fix_rcc_structural_heading_glue(s_lbl)
                        chapter_num = row.get('chapter_num')  # None for rpc_codal (not fetched)

                        bk_s2 = "" if row.get("book") is None else str(row.get("book")).strip()
                        tn_s2 = "" if row.get("title_num") is None else str(row.get("title_num")).strip()
                        clk_s2 = normalize_codal_label_key(c_lbl) if c_lbl else ""

                        # Title: only announce when title_num is set (articles without title_num,
                        # e.g. 266-A–D amendments, must not treat their title_label as a structural header).
                        tbmap = starts.get("title_start_book_num") or {}
                        tn = row.get("title_num")
                        if t_lbl and tn is not None:
                            tkey = f"{bk_s2}|{str(tn).strip()}"
                            if tbmap.get(tkey) == curr_id_str:
                                hdr_parts.append(tts_format_structural_label(t_lbl, tn, "Title"))
                            elif tkey not in tbmap:
                                nk_t = normalize_codal_label_key(t_lbl)
                                if nk_t and starts.get("title_label", {}).get(nk_t) == curr_id_str:
                                    hdr_parts.append(tts_format_structural_label(t_lbl, tn, "Title"))

                        # Chapter: compound key (book|title_num|chapter_label_key) prevents
                        # duplicate labels like "General Provisions" from colliding across titles.
                        if c_lbl and clk_s2:
                            ch_compound = f"{bk_s2}|{tn_s2}|{clk_s2}"
                            ch_map = starts.get('chapter_start', {})
                            if ch_map.get(ch_compound) == curr_id_str:
                                hdr_parts.append(tts_format_structural_label(c_lbl, chapter_num, "Chapter"))
                            elif not ch_map:
                                # Fallback: legacy single-key map (older cache entries)
                                if starts.get('chapter_label', {}).get(clk_s2) == curr_id_str:
                                    hdr_parts.append(tts_format_structural_label(c_lbl, chapter_num, "Chapter"))

                        # Section: compound key (book|title_num|chapter_label_key|section_label_key)
                        if s_lbl and not body_embeds_rpc_section(content, clean, s_lbl):
                            slk_s2 = normalize_codal_label_key(s_lbl)
                            if slk_s2:
                                sec_compound = f"{bk_s2}|{tn_s2}|{clk_s2}|{slk_s2}"
                                sec_map = starts.get('section_start', {})
                                if sec_map.get(sec_compound) == curr_id_str:
                                    hdr_parts.append(strip_codal_citation_tail(s_lbl).title())
                                elif not sec_map:
                                    # Fallback: legacy single-key map
                                    if starts.get('section_label', {}).get(slk_s2) == curr_id_str:
                                        hdr_parts.append(strip_codal_citation_tail(s_lbl).title())

                        art_title = strip_codal_citation_tail(art_title)
                        if is_rcc_table and art_title:
                            art_title = fix_rcc_structural_heading_glue(art_title)
                        if is_rcc_table:
                            rcc_disp = rcc_section_number_from_article_num(str(clean_num))
                            cn0 = str(clean_num).strip() == "0" or rcc_disp == "0"
                            art_name = "Preliminary Section" if cn0 else f"Section {rcc_disp}."
                        else:
                            art_name = 'Preliminary Article' if clean_num == '0' else f'Article {clean_num}'
                        if art_title and not is_redundant:
                            if is_rcc_table and art_name.endswith("."):
                                art_name = f"{art_name} {art_title}"
                            else:
                                art_name += f". {art_title}"

                        struct_text = '. '.join(hdr_parts)
                        body_already_has_article = body_starts_with_article_identifier(
                            clean,
                            str(clean_num),
                            art_title if not is_redundant else None,
                        ) or raw_markdown_opens_with_article_line(content, str(clean_num))
                        if body_already_has_article:
                            header = struct_text
                        else:
                            header = f"{struct_text}. {art_name}" if struct_text else art_name
                        
                    elif table == 'fc_codal':
                        hdr_parts = []
                        starts = get_codal_boundaries('fc_codal')
                        curr_id_str = str(row.get('id')) if row.get('id') is not None else ''

                        # Title header — group_header holds "FAMILY CODE\nTITLE N description"
                        g_hdr = (row.get('group_header') or '').strip()
                        if g_hdr:
                            gnk = normalize_codal_label_key(g_hdr)
                            if gnk and starts['group_header'].get(gnk) == curr_id_str:
                                lines = [l.strip() for l in g_hdr.splitlines() if l.strip()]
                                # Take the "TITLE N description" line (second line); fall back to full header
                                title_line = lines[1] if len(lines) >= 2 else (lines[0] if lines else g_hdr)
                                # FC format: "TITLE III RIGHTS AND OBLIGATIONS..." (space separator, no dash)
                                mt = re.match(r'^TITLE\s+([IVX]+|\d+)\s+(.+)$', title_line, re.IGNORECASE)
                                if mt:
                                    raw_num = mt.group(1).lower()
                                    title_desc = mt.group(2).strip().title()
                                    arabic_num = _ROMAN_TO_ARABIC.get(raw_num, raw_num)
                                    hdr_parts.append(f"Title {arabic_num}. {title_desc}")
                                else:
                                    hdr_parts.append(tts_format_structural_label(title_line, None, "Title"))

                        # Chapter header — section_label holds "Chapter N. Description"
                        s_lbl = (row.get('section_label') or '').strip()
                        if s_lbl:
                            snk = normalize_codal_label_key(s_lbl)
                            if snk and starts.get('section_label', {}).get(snk) == curr_id_str:
                                hdr_parts.append(strip_codal_citation_tail(s_lbl))

                        art_title = strip_codal_citation_tail(art_title)
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
                    
                # Dedupe: RPC/CIV/Labor already drop only the article line when the body repeats it,
                # keeping Book/Title/Section. Other codals use full-header dedupe.
                if table not in ['rpc_codal', 'civ_codal', 'rcc_codal', 'labor_codal']:
                    header, _ = dedupe_codal_header_prefix(clean, header, str(clean_num))
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
        clean = tts_flatten_codal_body(str(content))

        header = 'Preliminary Article' if str(art_num) == '0' else f'Article {art_num}'
        header, _ = dedupe_codal_header_prefix(clean, header, str(art_num).strip())
        full_text = f"{header}. {clean}" if header else clean
        full_text = _apply_custom_pronunciations(full_text)
        return full_text, None
    finally:
        put_db_connection(conn)

def _get_text_for_flashcard(term):
    """Fetch flashcard concept text for TTS by term (URL-decoded)."""
    from urllib.parse import unquote
    term_decoded = unquote(str(term)).strip()
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            "SELECT term, definition, sources FROM flashcard_concepts WHERE LOWER(term) = LOWER(%s) LIMIT 1",
            (term_decoded,)
        )
        row = cur.fetchone()
        if not row:
            return None, f"Flashcard concept '{term_decoded}' not found"

        t = (row.get('term') or '').strip()
        d = (row.get('definition') or '').strip()
        sources = row.get('sources') or []
        if isinstance(sources, str):
            try:
                sources = json.loads(sources)
            except Exception:
                sources = []

        subject = ''
        if sources and isinstance(sources, list) and sources[0]:
            subject = (sources[0].get('subject') or '').strip()

        parts = []
        if t:
            parts.append(f"Legal concept: {t}.")
        if subject:
            parts.append(f"Under {subject}.")
        if d:
            parts.append(d)

        full_text = ' '.join(parts)
        full_text = re.sub(r'[#*`_\[\]]', ' ', full_text)
        full_text = re.sub(r'\s+', ' ', full_text).strip()
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
        full_text = re.sub(r'[#*`_\[\]^]', ' ', full_text)
        full_text = re.sub(r';', '. ', full_text)
        full_text = re.sub(r':', ', ', full_text)
        full_text = re.sub(r'\s+', ' ', full_text).strip()
        full_text = re.sub(r'(?<=[.,]) (\d{1,2})\. (?=[A-Za-z])', r' \1, ', full_text)
        full_text = strip_codal_citation_tail(full_text)
        
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

    if content_type not in ['codal', 'case', 'question', 'flashcard']:
        return func.HttpResponse(
            json.dumps({"error": "Invalid content type. Use 'codal', 'case', 'question', or 'flashcard'."}),
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
    
    # Try legacy base key, then engine-suffixed blobs (matches writes + precache_rpc)
    for suffix in ("", "_azure", "_edge_tts"):
        for ext in (".mp3", ".wav"):
            blob_name = f"{cache_key}{suffix}{ext}"
            cached_data = _get_data_from_cache(blob_name)
            if cached_data:
                logging.info(f"CACHE HIT: Proxying {len(cached_data)} bytes ({blob_name})...")
                return func.HttpResponse(
                    body=cached_data,
                    status_code=200,
                    mimetype="audio/mpeg",
                    headers=_audio_http_headers(
                        len(cached_data), "HIT", blob_name=blob_name
                    ),
                )

    # --- 2. Fetch text from DB ---
    text = None
    err = None
    try:
        if content_type == 'case':
            text, err = _get_text_for_case(content_id)
        elif content_type == 'question':
            text, err = _get_text_for_question(content_id)
        elif content_type == 'flashcard':
            text, err = _get_text_for_flashcard(content_id)
        else:
            text, err = _get_text_for_codal(content_id, code_id=code_id)
    except Exception as e:
        logging.error(f"DB error: {e}")
        return func.HttpResponse(f"Database error: {e}", status_code=500)

    if err:
        return func.HttpResponse(err, status_code=404)
    if not text or not text.strip():
        return func.HttpResponse("No text content to synthesize", status_code=404)

    # --- 3. Generate audio: Edge TTS by default; optional Azure-only path (no Edge fallback) ---
    audio_data, mime_type, ext = None, None, None
    tts_engine = "unknown"
    try:
        if _USE_AZURE_SPEECH and AZURE_SPEECH_AVAILABLE:
            azure_success = False
            last_azure_error = None
            max_retries = 3

            lock_acquired = _TTS_LOCK.acquire(timeout=_TTS_LOCK_TIMEOUT)
            if not lock_acquired:
                logging.warning("TTS lock timeout — another Azure synthesis is still running.")
                return func.HttpResponse(
                    json.dumps({"error": "Audio synthesis is busy. Try again in a few seconds."}),
                    status_code=503,
                    mimetype="application/json",
                )
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
                    err_msg = str(last_azure_error) if last_azure_error else "Azure TTS failed"
                    logging.error(f"Azure TTS unavailable (no Edge fallback): {err_msg}")
                    return func.HttpResponse(
                        json.dumps({"error": "Azure Speech synthesis failed.", "detail": err_msg[:500]}),
                        status_code=502,
                        mimetype="application/json",
                    )
            finally:
                _TTS_LOCK.release()
        elif _USE_AZURE_SPEECH and not AZURE_SPEECH_AVAILABLE:
            return func.HttpResponse(
                json.dumps({"error": "LEXPLAY_USE_AZURE_SPEECH is set but Azure Speech SDK is not available."}),
                status_code=503,
                mimetype="application/json",
            )
        else:
            audio_data, mime_type, ext = _generate_audio_edge_tts(text, rate=rate)
            tts_engine = "edge_tts"
    except Exception as e:
        logging.error(f"TTS generation failed entirely: {e}")
        return func.HttpResponse(f"Audio generation failed: {e}", status_code=500)

    # --- 4. Upload to Azure Blob and return data ---
    # Use a separate cache key suffix for TTS engines so they can be explicitly identified
    effective_cache_key = f"{cache_key}_{tts_engine}"
    blob_name = f"{effective_cache_key}{ext}"
    _save_to_cache(blob_name, audio_data, mime_type=mime_type)

    if not audio_data:
        return func.HttpResponse("Audio generation produced no data", status_code=500)

    return func.HttpResponse(
        body=audio_data,
        status_code=200,
        mimetype=mime_type,
        headers=_audio_http_headers(
            len(audio_data),
            "MISS",
            tts_engine=tts_engine,
            blob_name=blob_name,
        ),
    )
