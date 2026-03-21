import logging
import os
import io
import re
import json
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
CACHE_VERSION = "v36" # Increment to force-refresh all cached audio
AZURE_VOICE_NAME = "en-PH-RosaNeural" # Hardcoded to bypass invalid production environment variable

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
    "reclusión perpetua", "reclusion perpetua",
    "reclusión temporal", "reclusion temporal",
    "prisión mayor", "prision mayor",
    "prisión correccional", "prision correccional",
    "arresto mayor",
    "arresto menor",
    "prisión", "prision",
    "arresto",
    "mayor",
    "menor",
    "correccional",
    "reclusión", "reclusion",
    "perpetua",
    "temporal",
    "destierro",
    "fianza"
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
                expiry=datetime.utcnow() + timedelta(hours=24)
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
        final_text = re.sub(r'\n{3,}', '\n\n', final_text).strip()

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
            # group_header only exists in const_codal
            cols = "article_num, article_title, content_md"
            if table in ["consti_codal", "const_codal"]:
                cols = "article_num, article_title, group_header, content_md, section_label"
            elif table == "fc_codal":
                cols = "article_num, article_title, content_md, section_label"
            elif table == "roc_codal":
                cols = "rule_section_label AS article_num, section_title AS article_title, section_content AS content_md, group_2_title AS section_label"

            # --- Multi-stage Lookup Strategy ---
            search_patterns = [str(content_id)] # 1. Exact match
            
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
                
                # TTS Cleaning: Remove structural MD only, keep punctuation for better flow
                clean = re.sub(r'[#*`_\[\]]', ' ', str(content))
                clean = re.sub(r'\n{3,}', '\n\n', clean).strip()
                # Replace single newlines with spaces to prevent artificial pauses inside sentences
                clean = re.sub(r'(?<!\n)\n(?!\n)', ' ', clean)
                
                # Strip currency repetitions like (₱40,000) or (P200,000)
                clean = re.sub(r'\(\s*[₱P]\s*[\d,.]+\s*\)', '', clean)
                
                # Strip article version tags at the end of paragraphs like (75a), (n), (1a, n)
                clean = re.sub(r'\s*\(\s*(?:(?:\d+[a-zA-Z]?|n)(?:,\s*(?:\d+[a-zA-Z]?|n))*)\s*\)\s*(?=\n|$)', '', clean.strip())
                
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
                    # Use section_label directly for Constitution to decouple grouping titles
                    s_label = (row.get('section_label') or '').strip().rstrip('.')
                    
                    if "PREAMBLE" in s_label.upper() or "PREAMBLE" in str(clean_num).upper() or "PREAMBLE" in art_title.upper():
                        header = "Preamble"
                    else:
                        header = s_label if s_label else f"Article {clean_num}"
                        # Standalone Header rows should include the title
                        if "ARTICLE" in header.upper():
                            if art_title and not is_redundant and art_title.lower() not in header.lower():
                                header += f'. {art_title}'
                else:
                    if code_id and code_id.lower() == 'roc':
                        # ROC Specific: Suppress Rule repetition for sections > 1
                        # art_num is typically "Rule 1, Section 2"
                        section_match = re.search(r'Section\s+(\d+)', str(clean_num), re.IGNORECASE)
                        if section_match and section_match.group(1) != '1':
                            header = f"Section {section_match.group(1)}"
                        else:
                            header = str(clean_num)
                    elif re.match(r'^(article|preamble|section|rule)\b', str(clean_num), re.IGNORECASE):
                        header = str(clean_num)
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
                full_text = f"{header}.\n\n{clean}" if header else clean
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
        # TTS Cleaning: Remove structural MD only, keep punctuation
        clean = re.sub(r'[#*`_\[\]]', ' ', str(content))
        clean = re.sub(r'\n{3,}', '\n\n', clean).strip()

        # Strip currency repetitions like (₱40,000) or (P200,000)
        clean = re.sub(r'\(\s*[₱P]\s*[\d,.]+\s*\)', '', clean)
        
        # Strip article version tags at the end like (75a), (9a), (10)
        clean = re.sub(r'\(\d+[a-z]?\)\s*$', '', clean.strip())

        header = 'Preliminary Article' if str(art_num) == '0' else f'Article {art_num}'
        full_text = f"{header}.\n\n{clean}"
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
        q_text = row.get('text') or ""
        a_text = row.get('answer') or ""

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
            
        full_text = f"{intro}\n\n{q_clean}\n\n{a_clean}"
        
        # Basic cleanup
        full_text = re.sub(r'[#*`_\[\]]', ' ', full_text)
        full_text = re.sub(r'\n{3,}', '\n\n', full_text).strip()
        
        # Apply custom pronunciations (Latin, Names, etc.)
        full_text = _apply_custom_pronunciations(full_text)
        
        return full_text, None
    finally:
        put_db_connection(conn)

# ----- Audio generation -----
def _generate_audio_gtts(text):
    """Generate MP3 audio bytes using gTTS (free, needs internet).
    Supports multi-chunk concatenation.
    """
    from gtts import gTTS
    
    # Use 2000 as safe chunk size for gTTS
    chunks = _chunk_text(text, max_len=2000)
    if not chunks:
        raise ValueError("No text provided for gTTS")
        
    all_audio_data = []
    for chunk in chunks:
        tts = gTTS(text=chunk, lang='en', tld='com.ph', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        all_audio_data.append(fp.getvalue())
        
    # Concatenate MP3 bytes (MP3 can usually be joined simply)
    combined_data = b"".join(all_audio_data)
    return combined_data, 'audio/mpeg', '.mp3'

def _generate_audio_azure(text, voice_name="en-PH-RosaNeural"):
    """Generate MP3 audio using Azure Speech SDK.
    Supports multi-chunk concatenation to bypass 4000 char limit.
    """
    speech_key = os.environ.get("SPEECH_KEY", "")
    speech_region = os.environ.get("SPEECH_REGION", "japaneast")
    if not speech_key or "<insert" in speech_key:
        raise ValueError("Azure Speech key not configured")
        
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    # Use dynamic voice name passed as argument
    speech_config.speech_synthesis_voice_name = voice_name
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz128KBitRateMonoMp3
    )
    
    synth = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    
    # Use en-PH for James/Rosa, or fil-PH for Blessica/Angelo
    lang_code = "en-PH" if "James" in voice_name or "Rosa" in voice_name else "en-US"
    if "Blessica" in voice_name or "Angelo" in voice_name:
        lang_code = "fil-PH"

    # Chunk text to stay under SSML limits
    chunks = _chunk_text(text, max_len=3000)
    if not chunks:
        raise ValueError("No text provided for Azure TTS")
        
    all_audio_data = []
    for chunk in chunks:
        # Escape special XML characters for SSML
        escaped_text = chunk.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        # Hydrate the Multilingual SSML tokens!
        escaped_text = escaped_text.replace("__ES_START__", "<lang xml:lang='es-MX'>")
        escaped_text = escaped_text.replace("__ES_END__", "</lang>")
        escaped_text = escaped_text.replace("__PH_START__", "<lang xml:lang='fil-PH'>")
        escaped_text = escaped_text.replace("__PH_END__", "</lang>")
        escaped_text = escaped_text.replace("__LATIN_START__", "<lang xml:lang='it-IT'>")
        escaped_text = escaped_text.replace("__LATIN_END__", "</lang>")
        
        ssml = (
            f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='{lang_code}'>"
            f"<voice name='{voice_name}'>"
            f"<prosody rate='1.0'>{escaped_text.strip()}</prosody>"
            f"</voice></speak>"
        )
        
        result = synth.speak_ssml_async(ssml).get()
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            all_audio_data.append(result.audio_data)
        else:
            raise RuntimeError(f"Azure TTS chunk failed: {result.reason}")
            
    # Concatenate MP3 bytes
    combined_data = b"".join(all_audio_data)
    return combined_data, 'audio/mpeg', '.mp3'

# ----- Main endpoint: streams audio directly -----
@audio_provider_bp.route(route="audio/{content_type}/{content_id}", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def get_audio_stream(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Audio request received.')

    content_type = req.route_params.get('content_type')
    content_id = req.route_params.get('content_id')
    code_id = req.params.get('code')  # e.g. 'rpc', 'civ', 'labor'

    if content_type not in ['codal', 'case', 'question']:
        return func.HttpResponse(
            json.dumps({"error": "Invalid content type. Use 'codal', 'case', or 'question'."}),
            status_code=400, mimetype="application/json"
        )

    # --- 1. Select Voice based on Content Type ---
    # Globalized JennyMultilingual for natively fluent Spanish parsing
    voice_name = "en-US-JennyMultilingualNeural"

    # --- 1b. Check blob cache first ---
    # Include voice name and cache version in key to ensure fresh/correct audio
    voice_slug = voice_name.split('-')[-1].replace('Neural', '').lower()
    cache_key = f"{content_type}_{code_id or ''}_{content_id}_{voice_slug}_{CACHE_VERSION}"
    
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

    # --- 3. Generate audio via Azure Speech (Required) ---
    audio_data, mime_type, ext = None, None, None
    try:
        if AZURE_SPEECH_AVAILABLE:
            audio_data, mime_type, ext = _generate_audio_azure(text, voice_name=voice_name)
            logging.info("Audio generated via Azure TTS (MP3)")
        else:
            return func.HttpResponse("Azure Speech Services not available/configured", status_code=503)
    except Exception as e:
        logging.error(f"Azure TTS failed: {e}")
        return func.HttpResponse(f"Audio generation failed: {e}", status_code=500)

    # --- 4. Upload to Azure Blob and Redirect ---
    blob_name = f"{cache_key}{ext}"
    _save_to_cache(blob_name, audio_data, mime_type=mime_type)
    sas_url = _get_from_cache(blob_name)
    if sas_url:
        logging.info(f"Uploaded to Azure Blob, Redirecting to SAS URL")
        return func.HttpResponse(
            status_code=302,
            headers={"Location": sas_url}
        )

    # --- 5. Fallback: stream audio directly if blob upload failed ---
    logging.info(f"Blob upload failed, streaming {len(audio_data)} bytes directly")
    return func.HttpResponse(
        body=audio_data,
        status_code=200,
        mimetype=mime_type,
        headers={
            "Content-Length": str(len(audio_data)),
            "Accept-Ranges": "bytes",
        }
    )